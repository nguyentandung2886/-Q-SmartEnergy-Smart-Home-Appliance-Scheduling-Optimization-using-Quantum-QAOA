"""
POST /optimize: run the QAOA pipeline using the current user's appliances; save result to
schedules history. GET /schedules: return optimization history newest-first.
Charts are returned as base64-encoded PNG so the React frontend only needs <img src="data:...">.
Per-user bill: calculated from the user's OWN appliance list total, not the global calc.MONTHLY_KWH.
"""
import base64
import io
import json
from dataclasses import replace
from typing import Dict, List, Literal, Optional

import matplotlib
matplotlib.use("Agg")  # headless, thread-safe backend for rendering charts in request handlers
import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import calc
from core import data_prep
from core import visualizer
from core.appliance_catalog import split_by_flexibility, usage_windows
from auth import get_current_user
from db.database import get_db
from db.models import ApplianceModel, ScheduleModel, User
from core.quantum_runner import QuantumScheduler, compare_qaoa_hyperparameters, solve_classical_bruteforce
from core.qubo_builder import Appliance

router = APIRouter(tags=["optimize"])


class OptimizeRequest(BaseModel):
    day_of_month: int = Field(9, ge=1, le=30)
    weather_condition: Literal["sunny", "cloudy", "rainy"] = "sunny"
    use_quantum: bool = True
    pinned_schedule: Optional[Dict[str, int]] = None
    # ML-forecasted run durations (giờ) per appliance name, from /forecast. Override the
    # catalog duration_hours before building the QUBO so the classical ML layer feeds QAOA.
    duration_overrides: Optional[Dict[str, float]] = None


class _ScheduleBase(BaseModel):
    id: int
    created_at: str
    day_of_month: int
    weather_condition: str
    solver_used: str
    used_fallback: bool
    energy: float
    schedule: dict
    monthly_kwh: float
    bill_before_vnd: float
    bill_after_vnd: float
    savings_percent: float


class ScheduleOut(_ScheduleBase):
    gantt_chart_png: str
    bill_chart_png: str
    # Fixed appliances' realistic daily usage windows for the Gantt: {name: [[start, length], ...]}.
    # Each appliance may run in SEVERAL disjoint windows (e.g. fan at noon + evening), not one block.
    # Flexible appliances aren't here — they live in `schedule` at their single optimized hour.
    fixed_windows: Dict[str, List[List[int]]]


class ScheduleHistoryOut(_ScheduleBase):
    # Empty for older rows saved before this column existed.
    fixed_windows: Dict[str, List[List[int]]] = {}


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _hourly_load(flex_schedule: dict, fixed_hours: dict, appliances: List) -> List[float]:
    """Build the household's 24-hour load profile (kWh per hour) from the ACTUAL usage:
    flexible appliances run for their duration starting at their scheduled hour; fixed
    appliances run in exactly the hours the user turned on (fixed_hours[name]). power_w
    already includes quantity (see _db_rows_to_appliances)."""
    load = [0.0] * 24
    for app in appliances:
        eff_kw = app.power_w / 1000.0
        if app.is_flexible:
            hour = flex_schedule.get(app.name)
            if hour is None:
                # Not in the optimized schedule (e.g. no candidate hours): fall back to a
                # candidate hour so its energy is still counted — never silently drop load,
                # or before/after totals diverge and savings become meaningless.
                hour = app.candidate_hours[0] if app.candidate_hours else 0
            remaining = app.duration_hours
            k = 0
            while remaining > 1e-9:
                load[(hour + k) % 24] += eff_kw * min(1.0, remaining)
                remaining -= 1.0
                k += 1
        else:
            for hour in fixed_hours.get(app.name, []):
                load[int(hour) % 24] += eff_kw
    return load


def _bill_from_load(load: List[float], solar: List[float]) -> float:
    """Monthly EVN bill from a daily load profile. Solar self-consumption per hour is
    min(load[h], solar[h]) — only the part of the load NOT covered by rooftop solar is bought
    from the grid; that monthly grid total is charged through calc's tiered tariff."""
    daily_total = sum(load)
    daily_self = sum(min(load[h], solar[h]) for h in range(24))
    monthly_grid = max(0.0, (daily_total - daily_self) * 30.0)
    return calc.calculate_bill(monthly_grid)


def _worst_solar_schedule(flexible: List, solar: List[float]) -> dict:
    """Each flexible appliance at its LEAST-sunny candidate hour — the un-optimized 'before'
    baseline that Q-SmartEnergy improves on by shifting these loads into solar hours."""
    def run_solar(hour: int, duration: float) -> float:
        total, remaining, k = 0.0, duration, 0
        while remaining > 1e-9:
            total += solar[(hour + k) % 24] * min(1.0, remaining)
            remaining -= 1.0
            k += 1
        return total

    worst = {}
    for app in flexible:
        cands = app.candidate_hours or (0,)
        worst[app.name] = min(cands, key=lambda h: run_solar(h, app.duration_hours))
    return worst


def _compute_schedule_bills(flex_after: dict, fixed_hours: dict, appliances: List, profile):
    """bill_before/after and monthly kWh from the actual whole-house schedule. Both bills use
    the SAME fixed-appliance usage, so the savings isolate the value of optimizing flexible
    loads into solar hours; turning appliances off (fewer hours) lowers both bills (real
    consumption drops). Returns (bill_before, bill_after, savings_percent, monthly_kwh)."""
    solar = [float(s) for s in profile["solar_kwh"]]
    flexible = [a for a in appliances if a.is_flexible]
    flex_before = _worst_solar_schedule(flexible, solar)

    load_after = _hourly_load(flex_after, fixed_hours, appliances)
    load_before = _hourly_load(flex_before, fixed_hours, appliances)
    bill_after = _bill_from_load(load_after, solar)
    bill_before = _bill_from_load(load_before, solar)
    monthly_kwh = sum(load_after) * 30.0
    savings = (bill_before - bill_after) / bill_before * 100 if bill_before > 0 else 0.0
    return bill_before, bill_after, savings, monthly_kwh


def _default_fixed_hours(appliances: List) -> dict:
    """Expand each fixed appliance's realistic usage windows into a flat list of ON hours."""
    result = {}
    for app in appliances:
        if app.is_flexible:
            continue
        hours = []
        for start, length in usage_windows(app):
            hours.extend((start + k) % 24 for k in range(length))
        result[app.name] = sorted(set(hours))
    return result


def _coerce_unoptimizable_to_fixed(appliances: List[Appliance]) -> List[Appliance]:
    """A flexible appliance needs >= 2 candidate hours to become a QUBO decision variable.
    Without them the optimizer can't schedule it, so it would vanish from the optimized
    ('after') load while the worst-solar ('before') baseline still counts it at a fallback
    hour — conjuring impossible savings (energy must be conserved between before and after).
    Treat such appliances as fixed loads so their consumption is billed consistently in both."""
    return [
        replace(a, is_flexible=False, candidate_hours=())
        if a.is_flexible and len(a.candidate_hours) < 2
        else a
        for a in appliances
    ]


def _db_rows_to_appliances(rows: List[ApplianceModel]) -> List[Appliance]:
    result = []
    for row in rows:
        hours = tuple(row.candidate_hours or ())
        result.append(Appliance(
            name=row.name,
            power_w=row.power_w * (row.quantity if row.quantity else 1),
            duration_hours=row.duration_hours,
            candidate_hours=hours, is_flexible=row.is_flexible,
        ))
    return result


@router.post("/optimize", response_model=ScheduleOut)
def optimize(
    payload: OptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    user_appliances = _coerce_unoptimizable_to_fixed(_db_rows_to_appliances(rows))

    # Apply ML-forecasted durations (from /forecast) before building the QUBO: duration drives
    # energy_kwh, which sits in both QUBO value axes and the Gantt block length.
    overrides = payload.duration_overrides or {}
    if overrides:
        user_appliances = [
            replace(a, duration_hours=float(overrides[a.name]))
            if a.name in overrides and float(overrides[a.name]) > 0
            else a
            for a in user_appliances
        ]

    # --- pinned_schedule: validate hours then override flexibility for this run only ---
    pinned = payload.pinned_schedule or {}
    if pinned:
        user_app_map = {a.name: a for a in user_appliances}
        pinned_to_apply = {}
        for pinned_name, hour in pinned.items():
            app = user_app_map.get(pinned_name)
            if app is None:
                continue  # silently ignore appliances not in user's list
            if app.candidate_hours and hour not in app.candidate_hours:
                raise HTTPException(
                    status_code=422,
                    detail=f"'{pinned_name}': hour {hour} not in candidate_hours {list(app.candidate_hours)}",
                )
            pinned_to_apply[pinned_name] = hour
        user_appliances = [
            Appliance(
                name=a.name,
                power_w=a.power_w,
                duration_hours=a.duration_hours,
                candidate_hours=(pinned_to_apply[a.name],),
                is_flexible=False,
            )
            if a.name in pinned_to_apply
            else a
            for a in user_appliances
        ]
    else:
        pinned_to_apply = {}

    flexible, _fixed = split_by_flexibility(user_appliances)

    profile = data_prep.build_daily_profile(payload.day_of_month, weather_condition=payload.weather_condition)
    scheduler = QuantumScheduler(flexible, profile)
    result = scheduler.solve(use_quantum=payload.use_quantum)

    # Merge pinned entries back — QAOA only ran on remaining flexible appliances
    for name, hour in pinned_to_apply.items():
        result.schedule[name] = hour

    # Per-user bill from the ACTUAL whole-house schedule: every appliance's real usage (fixed
    # appliances at their default usage hours, flexible at the optimized hour) is laid against
    # the solar curve, and only the grid-purchased remainder is charged through the EVN tiers.
    # bill_before runs the flexible loads at their least-sunny hour, so savings isolate the
    # value of optimizing into solar; using fewer hours lowers real consumption and both bills.
    default_fixed_hours = _default_fixed_hours(user_appliances)
    bill_before, bill_after, savings_percent, user_monthly_kwh = _compute_schedule_bills(
        result.schedule, default_fixed_hours, user_appliances, profile
    )

    # Fixed appliances' realistic usage windows for the Gantt (flexible ones are already in
    # result.schedule at their optimized hour). Each fixed appliance can run in several disjoint
    # windows across the day — typical-usage hours for display, not an optimization result.
    fixed_windows = {
        app.name: [[start, length] for start, length in usage_windows(app)]
        for app in user_appliances
        if app.name not in result.schedule
    }

    gantt_fig = visualizer.plot_schedule_gantt(result.schedule, user_appliances)
    bill_fig = visualizer.plot_cost_comparison(bill_before, bill_after)
    gantt_png = _fig_to_base64(gantt_fig)
    bill_png = _fig_to_base64(bill_fig)
    plt.close(gantt_fig)
    plt.close(bill_fig)

    row = ScheduleModel(
        user_id=current_user.id,
        day_of_month=payload.day_of_month,
        weather_condition=payload.weather_condition,
        solver_used=result.solver_used,
        used_fallback=result.used_fallback,
        energy=result.energy,
        schedule_json=json.dumps(result.schedule, ensure_ascii=False),
        monthly_kwh=user_monthly_kwh,
        bill_before_vnd=bill_before,
        bill_after_vnd=bill_after,
        savings_percent=savings_percent,
        fixed_windows_json=fixed_windows,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ScheduleOut(
        id=row.id, created_at=row.created_at.isoformat(),
        day_of_month=row.day_of_month, weather_condition=row.weather_condition,
        solver_used=row.solver_used, used_fallback=row.used_fallback, energy=row.energy,
        schedule=result.schedule, monthly_kwh=user_monthly_kwh,
        bill_before_vnd=bill_before, bill_after_vnd=bill_after,
        savings_percent=savings_percent, gantt_chart_png=gantt_png, bill_chart_png=bill_png,
        fixed_windows=fixed_windows,
    )


class RecomputeBillRequest(BaseModel):
    day_of_month: int = Field(9, ge=1, le=30)
    weather_condition: Literal["sunny", "cloudy", "rainy"] = "sunny"
    schedule: Dict[str, int] = {}          # flexible appliance name -> chosen hour
    fixed_hours: Dict[str, List[int]] = {}  # fixed appliance name -> list of ON hours
    duration_overrides: Optional[Dict[str, float]] = None


class BillOut(BaseModel):
    bill_before_vnd: float
    bill_after_vnd: float
    savings_percent: float
    monthly_kwh: float


@router.post("/recompute-bill", response_model=BillOut)
def recompute_bill(
    payload: RecomputeBillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recompute the bill from an edited schedule WITHOUT re-running QAOA. Used when the user
    toggles fixed-appliance usage hours on the Gantt grid: their real consumption changes, so
    the bill must follow, but the quantum optimization of flexible loads is unchanged."""
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    user_appliances = _coerce_unoptimizable_to_fixed(_db_rows_to_appliances(rows))
    
    overrides = payload.duration_overrides or {}
    if overrides:
        user_appliances = [
            replace(a, duration_hours=float(overrides[a.name]))
            if a.name in overrides and float(overrides[a.name]) > 0
            else a
            for a in user_appliances
        ]

    profile = data_prep.build_daily_profile(payload.day_of_month, weather_condition=payload.weather_condition)
    bill_before, bill_after, savings_percent, monthly_kwh = _compute_schedule_bills(
        payload.schedule, payload.fixed_hours, user_appliances, profile
    )
    return BillOut(
        bill_before_vnd=bill_before, bill_after_vnd=bill_after,
        savings_percent=savings_percent, monthly_kwh=monthly_kwh,
    )


class QaoaConfigResult(BaseModel):
    reps: int
    maxiter: int
    energy: Optional[float]
    runtime_seconds: float
    matches_global_optimum: bool
    error: Optional[str]


class QaoaAnalysisOut(BaseModel):
    num_appliances: int
    num_variables: int      # binary variables = qubits
    brute_force_energy: Optional[float]
    configs: List[QaoaConfigResult]


@router.post("/qaoa-analysis", response_model=QaoaAnalysisOut)
def qaoa_analysis(
    payload: OptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run QAOA across several (reps, maxiter) configs on the user's flexible-appliance QUBO and
    compare each against the classical brute-force optimum. Surfaces the hyperparameter-tuning
    evidence (III.3) in the web demo: qubit count, runtime, and whether each config reached the
    global optimum. On-demand because it runs QAOA several times."""
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    user_appliances = _db_rows_to_appliances(rows)
    flexible, _fixed = split_by_flexibility(user_appliances)

    profile = data_prep.build_daily_profile(payload.day_of_month, weather_condition=payload.weather_condition)
    scheduler = QuantumScheduler(flexible, profile)
    n = scheduler.Q.shape[0]

    if n == 0:
        return QaoaAnalysisOut(num_appliances=0, num_variables=0, brute_force_energy=None, configs=[])

    _, brute_force_energy = solve_classical_bruteforce(scheduler.Q)
    raw = compare_qaoa_hyperparameters(scheduler.Q)
    configs = [
        QaoaConfigResult(
            reps=r["reps"], maxiter=r["maxiter"], energy=r["energy"],
            runtime_seconds=round(r["runtime_seconds"], 3),
            matches_global_optimum=r["matches_global_optimum"], error=r["error"],
        )
        for r in raw
    ]
    return QaoaAnalysisOut(
        num_appliances=len(flexible), num_variables=n,
        brute_force_energy=brute_force_energy, configs=configs,
    )


@router.get("/schedules", response_model=List[ScheduleHistoryOut])
def list_schedules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.user_id == current_user.id)
        .order_by(ScheduleModel.created_at.desc())
        .all()
    )
    return [
        ScheduleHistoryOut(
            id=r.id, created_at=r.created_at.isoformat(),
            day_of_month=r.day_of_month, weather_condition=r.weather_condition,
            solver_used=r.solver_used, used_fallback=r.used_fallback, energy=r.energy,
            schedule=json.loads(r.schedule_json), monthly_kwh=r.monthly_kwh,
            bill_before_vnd=r.bill_before_vnd, bill_after_vnd=r.bill_after_vnd,
            savings_percent=(
                r.savings_percent if r.savings_percent is not None
                else (r.bill_before_vnd - r.bill_after_vnd) / r.bill_before_vnd * 100 if r.bill_before_vnd > 0 else 0.0
            ),
            fixed_windows=r.fixed_windows_json or {},
        )
        for r in rows
    ]
