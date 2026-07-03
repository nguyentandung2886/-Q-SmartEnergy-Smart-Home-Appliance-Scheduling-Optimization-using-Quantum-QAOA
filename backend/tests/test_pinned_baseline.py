"""
Regression tests cho bug "Hóa đơn trước bị thổi phồng ảo khi pin thiết bị linh hoạt trên Gantt".

TẠI SAO test ở tầng _compute_schedule_bills (không qua QAOA/DB): bug nằm ở baseline "trước",
là hàm thuần và tất định — kéo QAOA vào chỉ thêm nhiễu, không chứng minh thêm điều gì. Kịch bản
tái hiện đúng thực tế: một thiết bị DOANH NGHIỆP linh hoạt KHÔNG có trong DEFAULT_USAGE_WINDOWS
(vd "Máy nén khí", "Máy hàn hồ quang") bị người dùng kéo (pin) trên Gantt. Khi pin, optimize()
coerce nó sang is_flexible=False cho lượt chạy này; nếu baseline "trước" tính trên list đã pin,
thiết bị rơi vào fallback usage_windows() = khung 18h (cao_diem/giờ đắt nhất TOU) — bill_before
bị thổi phồng bất kể người dùng kéo vào giờ nào, tạo % tiết kiệm ảo.
"""

import pytest

from api.optimize_router import _compute_schedule_bills, _default_fixed_hours
from core import data_prep
from core.appliance_catalog import DEFAULT_USAGE_WINDOWS, split_by_flexibility
from core.qubo_builder import Appliance


def _pin_to_fixed(app: Appliance, hour: int) -> Appliance:
    """Tái hiện đúng cách optimize() coerce một thiết bị bị pin: khóa cứng về 1 giờ, is_flexible=False."""
    return Appliance(
        name=app.name, power_w=app.power_w, duration_hours=app.duration_hours,
        candidate_hours=(hour,), is_flexible=False,
    )


def test_pinning_flexible_appliance_keeps_bill_before_stable():
    """Pin 1 thiết bị linh hoạt (KHÔNG có trong DEFAULT_USAGE_WINDOWS) vào 1 giờ ban ngày:
    bill_before PHẢI xấp xỉ bằng bill_before khi chưa pin — baseline "trước" là mức worst-solar
    trên tập TRUE flexible, độc lập với chỗ người dùng kéo khối. Đồng thời chứng minh bug: nếu
    baseline tính trên list đã pin (true_flexible=None), bill_before bị thổi phồng do rơi vào 18h."""
    # Máy nén khí: thiết bị SX linh hoạt, các giờ ứng viên đều ban ngày (nhiều nắng), KHÔNG nằm
    # trong catalog hộ gia đình -> usage_windows() sẽ fallback về khung 18h nếu bị coi là cố định.
    app = Appliance(name="Máy nén khí", power_w=3000, duration_hours=2,
                    candidate_hours=(8, 10, 12), is_flexible=True)
    assert app.name not in DEFAULT_USAGE_WINDOWS  # tiền đề của bug

    profile = data_prep.build_daily_profile(9, weather_condition="sunny", monthly_kwh=600.0)
    flex_after = {app.name: 10}  # giờ tối ưu bất kỳ; chỉ ảnh hưởng bill_after, không ảnh hưởng bill_before

    # (1) CHƯA pin: thiết bị vẫn linh hoạt.
    unpinned = [app]
    before_unpinned, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(unpinned), unpinned, profile, user=None,
    )

    # (2) ĐÃ pin + fix: list bị coerce sang cố định, nhưng truyền snapshot true_flexible (chụp
    #     trước khi pin) như optimize() làm.
    pinned = [_pin_to_fixed(app, 10)]
    true_flexible, _ = split_by_flexibility(unpinned)
    before_pinned_fixed, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(pinned), pinned, profile, user=None,
        true_flexible=true_flexible,
    )

    # (3) ĐÃ pin + BUG (true_flexible=None): tái hiện hành vi cũ để chứng minh test bắt được lỗi.
    before_pinned_buggy, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(pinned), pinned, profile, user=None,
        true_flexible=None,
    )

    # Fix: baseline sau pin trùng khít baseline chưa pin.
    assert before_pinned_fixed == pytest.approx(before_unpinned, rel=1e-9)
    # Bug: nếu không có fix, baseline bị thổi phồng rõ rệt (rơi vào 18h, mất phần nắng ban ngày).
    assert before_pinned_buggy > before_unpinned * 1.05


def test_pinning_business_appliance_no_fake_savings_under_tou():
    """Với biểu giá TOU doanh nghiệp, 18h = cao_diem (đắt nhất) nên bug càng nghiêm trọng: baseline
    ảo ở 18h thổi bill_before lên, tạo savings% dương giả. Fix phải giữ bill_before ổn định khi pin."""
    class _FakeProfile:
        business_type = "production"
        voltage_level = "duoi_6kv"
        contracted_power_kw = 50.0

    class _FakeBusinessUser:
        role = "business"
        id = 1
        business_profile = _FakeProfile()

    user = _FakeBusinessUser()
    app = Appliance(name="Máy hàn hồ quang", power_w=5000, duration_hours=2,
                    candidate_hours=(9, 11, 13), is_flexible=True)
    profile = data_prep.build_daily_profile(9, weather_condition="sunny", monthly_kwh=8000.0)
    flex_after = {app.name: 11}

    unpinned = [app]
    before_unpinned, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(unpinned), unpinned, profile, user=user,
    )

    pinned = [_pin_to_fixed(app, 11)]
    true_flexible, _ = split_by_flexibility(unpinned)
    before_pinned, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(pinned), pinned, profile, user=user,
        true_flexible=true_flexible,
    )

    before_buggy, _, _, _ = _compute_schedule_bills(
        flex_after, _default_fixed_hours(pinned), pinned, profile, user=user,
        true_flexible=None,
    )

    assert before_pinned == pytest.approx(before_unpinned, rel=1e-9)
    # 18h là cao_diem: baseline ảo phải đắt hơn hẳn baseline thật (worst-solar trong giờ ban ngày).
    assert before_buggy > before_unpinned * 1.05


def test_optimize_endpoint_bill_before_stable_when_pinning(client, auth_headers):
    """Khóa lại phần WIRING của fix ở tầng endpoint: optimize() phải chụp snapshot true_flexible
    TRƯỚC khi coerce pinned, và truyền vào _compute_schedule_bills. Nếu ai đó bỏ đối số
    true_flexible ở lời gọi trong optimize(), bill_before sẽ nhảy vọt khi pin và test này fail.

    Dùng "Máy giặt" (linh hoạt, giờ ứng viên 9h/14h — đều ban ngày nhiều nắng, KHÔNG có trong
    DEFAULT_USAGE_WINDOWS): pin vào 9h thì baseline "trước" đúng phải là giờ worst-solar ban ngày,
    trong khi bug đẩy về khung 18h — chênh lệch đủ để rel=1e-6 bắt được. Giữ nguyên bộ thiết bị seed
    mặc định để QUBO ổn định (đây là cấu hình bộ test khác đã chạy xanh)."""
    headers = auth_headers("pinbaseline_endpoint")
    appliances = client.get("/appliances", headers=headers).json()
    target = next(a for a in appliances if a["name"] == "Máy giặt")
    assert target["is_flexible"] and 9 in target["candidate_hours"]
    body = {"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False}

    no_pin = client.post("/optimize", json=body, headers=headers).json()
    pinned = client.post(
        "/optimize", json={**body, "pinned_schedule": {target["name"]: 9}}, headers=headers,
    ).json()

    assert pinned["bill_before_vnd"] == pytest.approx(no_pin["bill_before_vnd"], rel=1e-6)
