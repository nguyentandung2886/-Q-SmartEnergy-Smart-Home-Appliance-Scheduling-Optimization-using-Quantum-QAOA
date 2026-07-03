"""
POST /optimize: run the QAOA pipeline using the current user's appliances; save result to
schedules history. GET /schedules: return optimization history newest-first.
Charts are returned as base64-encoded PNG so the React frontend only needs <img src="data:...">.
Per-user bill: calculated from the user's OWN appliance list total, not the global calc.MONTHLY_KWH.
"""
import base64
import io
import json
import logging
import os
from dataclasses import replace
from typing import Dict, List, Literal, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # headless, thread-safe backend for rendering charts in request handlers
import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import calc
from core import data_prep
from core import visualizer
from core.business_calc import EVN_BUSINESS_TIERS, calculate_business_bill, classify_hour_tou
from core.appliance_catalog import DEFAULT_USAGE_WINDOWS, split_by_flexibility, usage_windows
from auth import get_current_user
from db.database import get_db
from db.models import ApplianceModel, ScheduleModel, User
from core.quantum_runner import QuantumScheduler, compare_qaoa_hyperparameters, solve_classical_bruteforce
from core.qubo_builder import Appliance, DEFAULT_POWER_THRESHOLD_W

router = APIRouter(tags=["optimize"])

logger = logging.getLogger(__name__)

# DEFAULT_POWER_THRESHOLD_W (ngưỡng công suất đồng thời W mặc định cho hộ gia đình) được import từ
# core.qubo_builder — ĐỊNH NGHĨA DUY NHẤT, khớp default H_power của build_qubo và banner frontend.
# Business dùng công suất hợp đồng đã khai báo (xem _power_threshold_for_user). Re-export để
# test_power_threshold.py và các caller cũ vẫn import được từ đây.

# Thương mại cảnh báo quá tải SỚM hơn sản xuất: với CÙNG công suất hợp đồng, ngưỡng thương mại chỉ
# bằng 80% (sản xuất chịu tải máy móc nặng theo thiết kế; thương mại ưu tiên an toàn nên hạ ngưỡng).
COMMERCIAL_SAFETY_MARGIN = 0.8


def _qaoa_is_default() -> bool:
    """Thuật toán tối ưu mặc định của server, đọc từ env OPTIMIZATION_ALGORITHM=qaoa|brute_force.

    Mặc định "qaoa". Đặt "brute_force" để tắt QAOA toàn server khi cần debug (vd nghi ngờ
    QAOA cho nghiệm lạ) mà không phải sửa code hay từng request. Giá trị không hợp lệ -> coi
    như "qaoa" (mặc định an toàn cho demo)."""
    return os.getenv("OPTIMIZATION_ALGORITHM", "qaoa").strip().lower() != "brute_force"


def _power_threshold_for_user(user: User) -> float:
    """Ngưỡng công suất đồng thời (W) đưa vào H_power của QUBO cho user này.

    - household / không có business_profile / chưa khai công suất hợp đồng: giữ mặc định 5000W.
    - business + production: đúng công suất hợp đồng (kW -> W).
    - business + commercial: công suất hợp đồng × COMMERCIAL_SAFETY_MARGIN (cảnh báo sớm hơn).
    """
    profile = getattr(user, "business_profile", None)
    if user.role != "business" or profile is None or profile.contracted_power_kw is None:
        return DEFAULT_POWER_THRESHOLD_W
    contracted_w = profile.contracted_power_kw * 1000
    if profile.business_type == "commercial":
        return contracted_w * COMMERCIAL_SAFETY_MARGIN
    return contracted_w


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
    # Ngưỡng công suất đồng thời (W) đã dùng cho H_power của run này — frontend đọc đúng ngưỡng
    # (theo role) thay vì hardcode. Không lưu DB nên lịch sử (ScheduleHistoryOut) không có trường này.
    power_threshold_w: float
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
    appliances with an entry in flex_schedule run for their duration starting at that
    scheduled hour (the hour QAOA or a pin actually chose — checked BEFORE is_flexible,
    because pinning/coercion forces is_flexible=False while the true hour lives in
    flex_schedule); other fixed appliances run in the hours the user turned on
    (fixed_hours[name]). power_w already includes quantity (see _db_rows_to_appliances)."""
    load = [0.0] * 24
    for app in appliances:
        eff_kw = app.power_w / 1000.0
        hour = flex_schedule.get(app.name)
        if hour is not None or app.is_flexible:
            if hour is None:
                # Flexible but not in the optimized schedule (e.g. no candidate hours):
                # fall back to a candidate hour so its energy is still counted — never
                # silently drop load, or before/after totals diverge and savings become
                # meaningless.
                hour = app.candidate_hours[0] if app.candidate_hours else 0
            remaining = app.duration_hours
            k = 0
            while remaining > 1e-9:
                load[(hour + k) % 24] += eff_kw * min(1.0, remaining)
                remaining -= 1.0
                k += 1
        elif app.name in DEFAULT_USAGE_WINDOWS:
            # Real usage pattern from the catalog: every ON hour is a full hour of use
            # (the pattern is independent of duration_hours, e.g. Lò vi sóng's lunch window).
            for hour_on in fixed_hours.get(app.name, []):
                load[int(hour_on) % 24] += eff_kw
        else:
            # Unknown fixed appliance: its hours come from usage_windows()'s fallback,
            # a ceil(duration)-wide DISPLAY window. Bill the true duration_hours spread
            # across those hours, or fractional durations get rounded up into extra kWh.
            remaining = app.duration_hours
            for hour_on in sorted(fixed_hours.get(app.name, [])):
                if remaining <= 1e-9:
                    break
                load[int(hour_on) % 24] += eff_kw * min(1.0, remaining)
                remaining -= 1.0
    return load


def _load_by_tou_period(load: List[float]) -> Dict[str, float]:
    """Gộp 24 giá trị kWh/giờ trong MỘT NGÀY thành tổng kWh/THÁNG theo 3 khung giờ TOU
    (classify_hour_tou), nhân 30 ngày — nhất quán với cách _bill_from_load nhân 30 cho
    hộ gia đình."""
    monthly = {"binh_thuong": 0.0, "thap_diem": 0.0, "cao_diem": 0.0}
    for hour, kwh in enumerate(load):
        monthly[classify_hour_tou(hour)] += kwh * 30.0
    return monthly


def _business_billing_params(user: Optional[User]) -> Optional[Tuple[str, str]]:
    """(business_type, voltage_level) nếu user được tính theo biểu giá DOANH NGHIỆP, else None.

    Business thiếu voltage_level (tài khoản tạo trước khi có field) fallback "duoi_6kv"
    (cấp phổ biến nhất) và ghi log — KHÔNG âm thầm coi là chính xác. Business thiếu hẳn
    business_profile rơi về biểu giá sinh hoạt như trước (None)."""
    if user is None or user.role != "business":
        return None
    profile = getattr(user, "business_profile", None)
    if profile is None or profile.business_type not in EVN_BUSINESS_TIERS:
        return None
    voltage_level = profile.voltage_level
    if voltage_level not in EVN_BUSINESS_TIERS[profile.business_type]:
        logger.warning(
            "BusinessProfile user_id=%s không có voltage_level hợp lệ (%r) — fallback "
            "'duoi_6kv' để tính bill; user nên cập nhật cấp điện áp thật.",
            user.id, voltage_level,
        )
        voltage_level = "duoi_6kv"
    return profile.business_type, voltage_level


def _business_price_profile(profile, business_type: str, voltage_level: str):
    """BẢN SAO daily_profile với price_per_kwh thay bằng giá TOU theo giờ của biểu giá DOANH
    NGHIỆP (classify_hour_tou + EVN_BUSINESS_TIERS[business_type][voltage_level]) — để H_cost
    của QUBO minimize ĐÚNG đại lượng mà calculate_business_bill() tính cho bill_after (Bug #1).
    Nếu không, QUBO tối ưu nhầm proxy giá bậc thang hộ gia đình và có thể trả nghiệm đắt hơn
    theo TOU thật (savings âm). Cột solar_kwh giữ nguyên; không mutate profile gốc."""
    prices = EVN_BUSINESS_TIERS[business_type][voltage_level]
    profile = profile.copy()
    profile["price_per_kwh"] = [prices[classify_hour_tou(int(h))] for h in profile["hour"]]
    return profile


def _bill_from_load(load: List[float], solar: List[float], user: Optional[User] = None) -> float:
    """Monthly EVN bill from a daily load profile. Solar self-consumption per hour is
    min(load[h], solar[h]) — only the part of the load NOT covered by rooftop solar is bought
    from the grid. Household: that monthly grid total goes through calc's tiered tariff.
    Business (user role="business" with a business_profile): the per-hour grid load is
    grouped by TOU period (QĐ 963/QĐ-BCT) and charged through the EVN business tariff for
    the profile's business_type + voltage_level instead — Bug #1 fix."""
    business = _business_billing_params(user)
    if business is not None:
        business_type, voltage_level = business
        grid = [load[h] - min(load[h], solar[h]) for h in range(24)]
        return calculate_business_bill(_load_by_tou_period(grid), business_type, voltage_level)
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


def _compute_schedule_bills(flex_after: dict, fixed_hours: dict, appliances: List, profile,
                            user: Optional[User] = None, true_flexible: Optional[List] = None):
    """bill_before/after and monthly kWh from the actual whole-house schedule. Both bills use
    the SAME fixed-appliance usage, so the savings isolate the value of optimizing flexible
    loads into solar hours; turning appliances off (fewer hours) lowers both bills (real
    consumption drops). `user` picks the tariff: business accounts are billed through the
    EVN business TOU tariff, everyone else through the household tiers (_bill_from_load).

    `true_flexible`: the appliances that are flexible BY CATALOG, before `pinned_schedule`
    (drag-and-drop on the Gantt) coerces some of them to is_flexible=False for this one run
    (see optimize()'s pinned-schedule block). Defaults to `[a for a in appliances if
    a.is_flexible]` when not given (matches recompute-bill, which never pins).

    Bug fixed here: previously `flexible` was derived from `appliances` directly, so a pinned
    appliance dropped out of `_worst_solar_schedule` (the 'before' baseline) and its 'before'
    hour fell back to `usage_windows()` — which, for appliances outside the household
    DEFAULT_USAGE_WINDOWS catalog (e.g. business/production equipment), defaults to an 18:00
    (peak/"cao_diem", the most expensive TOU tier) window. That inflated bill_before with a
    baseline unrelated to where the user actually dragged the block, producing a fake
    savings% every time a flexible load got pinned. Fix: always compute the 'before' baseline
    over the TRUE flexible set (their real candidate_hours), and treat those appliances as
    flexible for load_before too — regardless of whether this run pinned them.
    Returns (bill_before, bill_after, savings_percent, monthly_kwh)."""
    solar = [float(s) for s in profile["solar_kwh"]]
    flexible = true_flexible if true_flexible is not None else [a for a in appliances if a.is_flexible]
    flex_before = _worst_solar_schedule(flexible, solar)

    # For the 'before' load only: force is_flexible=True on originally-flexible appliances so
    # _hourly_load reads their hour from flex_before (worst-solar) instead of falling through
    # to a fixed catalog usage window that has nothing to do with their real candidate_hours.
    true_flexible_names = {a.name for a in flexible}
    appliances_for_before = [
        replace(a, is_flexible=True) if a.name in true_flexible_names else a
        for a in appliances
    ]

    load_after = _hourly_load(flex_after, fixed_hours, appliances)
    load_before = _hourly_load(flex_before, fixed_hours, appliances_for_before)
    bill_after = _bill_from_load(load_after, solar, user)
    bill_before = _bill_from_load(load_before, solar, user)
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


def _fixed_load_w_by_hour(appliances: List[Appliance]) -> Dict[int, float]:
    """Tổng công suất tức thời (W) của các tải CỐ ĐỊNH đang bật tại mỗi giờ 0-23, lấy giờ bật
    từ usage_windows (khớp cách _default_fixed_hours xác định giờ tải cố định). Đưa vào H_power
    của QUBO để ngưỡng quá tải tính cả tải nền cố định (đèn/điều hòa/motor... đang bật), không
    chỉ cặp thiết bị linh hoạt (Bug #5). Bỏ qua thiết bị linh hoạt (chúng là biến quyết định)."""
    load = {h: 0.0 for h in range(24)}
    for app in appliances:
        if app.is_flexible:
            continue
        on_hours = set()
        for start, length in usage_windows(app):
            on_hours.update((start + k) % 24 for k in range(length))
        for h in on_hours:
            load[h] += app.power_w
    return load


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


def _estimate_user_monthly_kwh(appliances: List[Appliance]) -> float:
    """Tổng kWh/tháng ước tính của user từ danh sách thiết bị — dùng để xác định user đang ở
    bậc giá EVN nào khi XÂY QUBO (build_daily_profile), thay cho catalog mặc định MONTHLY_KWH
    (bug #4). Công thức khớp AppData.jsx frontend: Σ power_w/1000 * duration_hours * 30.
    power_w ở đây ĐÃ gồm quantity (xem _db_rows_to_appliances)."""
    return sum(a.power_w / 1000.0 * a.duration_hours * 30.0 for a in appliances)


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

    # Snapshot the TRUE flexible set (real is_flexible/candidate_hours) BEFORE pinned_schedule
    # below coerces some of them to fixed for this run — the 'before' baseline must always be
    # computed against real candidate_hours, not the post-pin appliance list (see
    # _compute_schedule_bills docstring for the bug this avoids).
    true_flexible_appliances, _true_fixed_appliances = split_by_flexibility(user_appliances)

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

    flexible, fixed = split_by_flexibility(user_appliances)

    # Tổng kWh thật của user quyết định bậc giá biên trong QUBO (H_cost), không dùng catalog
    # mặc định MONTHLY_KWH — bug #4.
    user_monthly_kwh_estimate = _estimate_user_monthly_kwh(user_appliances)
    profile = data_prep.build_daily_profile(
        payload.day_of_month, weather_condition=payload.weather_condition,
        monthly_kwh=user_monthly_kwh_estimate,
    )
    # Business: đổi price_per_kwh của QUBO sang giá TOU doanh nghiệp để H_cost khớp bill_after
    # (Bug #1). Household giữ nguyên giá bậc thang (_business_billing_params trả None).
    business = _business_billing_params(current_user)
    if business is not None:
        profile = _business_price_profile(profile, *business)
    power_threshold_w = _power_threshold_for_user(current_user)
    # Tải nền cố định (W) theo giờ để H_power cộng dồn khi xét ngưỡng quá tải (Bug #5).
    fixed_load_w = _fixed_load_w_by_hour(fixed)
    scheduler = QuantumScheduler(
        flexible, profile, power_threshold_w=power_threshold_w, fixed_load_w=fixed_load_w
    )
    # TẠI SAO mặc định QAOA: bài lập lịch thiết bị là tối ưu tổ hợp (combinatorial). Brute-force
    # duyệt toàn bộ 2^n tổ hợp -> đúng tuyệt đối nhưng bùng nổ theo cấp số mũ, không scale khi
    # số biến (thiết bị × giờ ứng viên) tăng. QAOA cho lời giải GẦN ĐÚNG với chi phí thấp hơn
    # trên bài lớn, nên đặt làm mặc định (env OPTIMIZATION_ALGORITHM=qaoa). Có thể chuyển về
    # brute_force (env) hoặc use_quantum=False (per-request) để debug.
    # LƯU Ý TRUNG THỰC: ở quy mô PoC hiện tại (4-5 qubit) 2^n rất nhỏ nên brute-force thực ra
    # NHANH HƠN và chắc chắn tối ưu; QuantumScheduler.solve() vì thế vẫn đối chiếu brute-force
    # và lấy nghiệm đó nếu tốt hơn. QAOA ở đây là để chứng minh pipeline lượng tử, chưa phải
    # thắng về hiệu năng — lợi thế QAOA chỉ xuất hiện khi số biến lớn (>20-25 qubit).
    use_quantum = payload.use_quantum and _qaoa_is_default()
    result = scheduler.solve(use_quantum=use_quantum)

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
        result.schedule, default_fixed_hours, user_appliances, profile, current_user,
        true_flexible=true_flexible_appliances,
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
        fixed_windows=fixed_windows, power_threshold_w=power_threshold_w,
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

    # Validate từng giờ trong schedule như /optimize làm với pinned (bug #7): 0-23 và, nếu
    # appliance có khai candidate_hours, hour phải nằm trong đó — nếu không bill_after tính ra
    # sai (giờ ngoài 0-23 bị wrap %24 âm thầm, giờ ngoài candidate không phản ánh lịch thật).
    user_app_map = {a.name: a for a in user_appliances}
    for name, hour in payload.schedule.items():
        app = user_app_map.get(name)
        if app is None:
            continue  # bỏ qua thiết bị không thuộc danh sách user (khớp cách /optimize xử lý pinned)
        if not (0 <= hour <= 23):
            raise HTTPException(status_code=422, detail=f"'{name}': hour {hour} phải trong 0-23")
        if app.candidate_hours and hour not in app.candidate_hours:
            raise HTTPException(
                status_code=422,
                detail=f"'{name}': hour {hour} not in candidate_hours {list(app.candidate_hours)}",
            )

    profile = data_prep.build_daily_profile(payload.day_of_month, weather_condition=payload.weather_condition)
    bill_before, bill_after, savings_percent, monthly_kwh = _compute_schedule_bills(
        payload.schedule, payload.fixed_hours, user_appliances, profile, current_user
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

    profile = data_prep.build_daily_profile(
        payload.day_of_month, weather_condition=payload.weather_condition,
        monthly_kwh=_estimate_user_monthly_kwh(user_appliances),
    )
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
