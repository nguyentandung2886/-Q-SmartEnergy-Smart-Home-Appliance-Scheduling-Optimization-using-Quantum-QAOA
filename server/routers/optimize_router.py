"""
POST /optimize: run the QAOA pipeline using the current user's appliances; save result to
schedules history. GET /schedules: return optimization history newest-first.
Charts are returned as base64-encoded PNG so the React frontend only needs <img src="data:...">.
Per-user bill: calculated from the user's OWN appliance list total, not the global calc.MONTHLY_KWH.
"""
import base64
import io
import json
import unicodedata
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import calc
import data_prep
import visualizer
from appliance_catalog import split_by_flexibility, total_monthly_kwh
from auth import get_current_user
from database import get_db
from models import ApplianceModel, ScheduleModel, User
from quantum_runner import QuantumScheduler
from qubo_builder import Appliance

router = APIRouter(tags=["optimize"])


class OptimizeRequest(BaseModel):
    day_of_month: int = 9
    weather_condition: str = "sunny"
    use_quantum: bool = True
    pinned_schedule: Optional[Dict[str, int]] = None


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


class ScheduleHistoryOut(_ScheduleBase):
    pass


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _normalize_name(name: str) -> str:
    """Normalize a string for comparison, handling encoding issues.
    Removes combining characters (accents) and normalizes to NFC form.
    This helps match appliance names even if they were corrupted during storage/retrieval."""
    # NFD decomposition separates base characters from combining marks
    nfd = unicodedata.normalize('NFD', name)
    # Remove combining marks (accents, diacritics)
    normalized = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return normalized


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings for fuzzy matching."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _db_rows_to_appliances(rows: List[ApplianceModel]) -> List[Appliance]:
    from appliance_catalog import HOUSEHOLD_APPLIANCES

    result = []
    for row in rows:
        hours = tuple(int(h) for h in row.candidate_hours.split(",") if h) if row.candidate_hours else ()
        # Try to find the correct catalog name by fuzzy matching or normalization
        corrected_name = row.name

        # First try exact normalized match
        normalized_db_name = _normalize_name(row.name)
        for cat_app in HOUSEHOLD_APPLIANCES:
            if _normalize_name(cat_app.name) == normalized_db_name:
                corrected_name = cat_app.name
                break
        else:
            # If no exact normalized match, try fuzzy matching based on Levenshtein distance
            min_distance = float('inf')
            for cat_app in HOUSEHOLD_APPLIANCES:
                distance = _levenshtein_distance(_normalize_name(row.name), _normalize_name(cat_app.name))
                if distance < min_distance:
                    min_distance = distance
                    corrected_name = cat_app.name
                if distance == 0:  # Perfect normalized match found
                    break

        result.append(Appliance(
            name=corrected_name, power_w=row.power_w, duration_hours=row.duration_hours,
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
    user_appliances = _db_rows_to_appliances(rows)

    # --- pinned_schedule: validate hours then override flexibility for this run only ---
    pinned = payload.pinned_schedule or {}
    if pinned:
        # Build map from normalized names to appliances for robust matching (handles encoding issues)
        user_app_by_normalized = {_normalize_name(a.name): a for a in user_appliances}
        pinned_to_apply = {}
        for pinned_name, hour in pinned.items():
            normalized_pinned = _normalize_name(pinned_name)
            app = user_app_by_normalized.get(normalized_pinned)
            if app is None:
                continue  # silently ignore appliances not in user's list
            if app.candidate_hours and hour not in app.candidate_hours:
                raise HTTPException(
                    status_code=422,
                    detail=f"'{pinned_name}': hour {hour} not in candidate_hours {list(app.candidate_hours)}",
                )
            # Store using the appliance's actual name (from DB), not the pinned_name
            pinned_to_apply[app.name] = hour
        # Override pinned appliances to fixed for this run only
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

    # Per-user bill: uses user's OWN appliance list total, not global calc.MONTHLY_KWH.
    # Clamp to 0 so that users with few/no appliances (where solar > load) get bill=0, not a ValueError.
    user_monthly_kwh = total_monthly_kwh(user_appliances)
    grid_before = max(0.0, calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_BEFORE, user_monthly_kwh))
    grid_after = max(0.0, calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_AFTER, user_monthly_kwh))
    bill_before = calc.calculate_bill(grid_before)
    bill_after = calc.calculate_bill(grid_after)
    savings_percent = (bill_before - bill_after) / bill_before * 100 if bill_before > 0 else 0.0

    gantt_fig = visualizer.plot_schedule_gantt(result.schedule, flexible)
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
        )
        for r in rows
    ]
