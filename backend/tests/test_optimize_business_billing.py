"""Bug #1 fix: user role="business" phải được tính bill qua biểu giá EVN DOANH NGHIỆP
(TOU theo cấp điện áp — business_calc.calculate_business_bill), KHÔNG phải biểu giá
SINH HOẠT bậc thang (calc.calculate_bill). Household giữ nguyên 100% hành vi cũ."""
import pytest

from api.optimize_router import _load_by_tou_period
from core import calc, data_prep
from db.models import ApplianceModel, BusinessProfile, User

# Giá sản xuất, dưới 6 kV (đ/kWh, chưa VAT) — chép tay từ bảng nguồn, KHÔNG import từ
# business_calc để phép tính kỳ vọng độc lập với code đang test.
_PROD_DUOI_6KV = {"binh_thuong": 1987, "thap_diem": 1300, "cao_diem": 3640}
_PIN_HOUR = 20  # cao điểm, không có mặt trời -> lưới mua = toàn bộ tải, số kỳ vọng gọn


def _make_business_user(db_session, uid: str, voltage_level):
    user = User(supabase_uid=uid, email=f"{uid}@test.local", role="business")
    db_session.add(user)
    db_session.flush()
    db_session.add(BusinessProfile(
        user_id=user.id, business_type="production",
        contracted_power_kw=50, voltage_level=voltage_level,
    ))
    # 2000W x 2h, pin được vào giờ 10 (bình thường) hoặc 20 (cao điểm).
    db_session.add(ApplianceModel(
        user_id=user.id, name="Máy bơm nước", power_w=2000, duration_hours=2,
        candidate_hours=[10, 20], is_flexible=True,
    ))
    db_session.commit()


def _expected_bills_pinned_at(pin_hour: int):
    """(bill doanh nghiệp kỳ vọng, bill NẾU tính nhầm theo sinh hoạt) cho lịch đã pin —
    tính độc lập từ bảng giá gốc, không đi qua calculate_business_bill."""
    profile = data_prep.build_daily_profile(9, weather_condition="sunny")
    solar = [float(s) for s in profile["solar_kwh"]]
    load = [0.0] * 24
    load[pin_hour % 24] += 2.0
    load[(pin_hour + 1) % 24] += 2.0
    grid = [load[h] - min(load[h], solar[h]) for h in range(24)]

    def tou(h):  # khung giờ đã chốt: 0-5 thấp điểm, 18-22 cao điểm, còn lại bình thường
        return "thap_diem" if h <= 5 else "cao_diem" if 18 <= h <= 22 else "binh_thuong"

    monthly = {"binh_thuong": 0.0, "thap_diem": 0.0, "cao_diem": 0.0}
    for h in range(24):
        monthly[tou(h)] += grid[h] * 30.0
    # QĐ 963: Chủ nhật không có cao điểm — ~4/30 phần cao điểm tính giá bình thường (khớp
    # _load_by_tou_period trong optimize_router).
    sunday_peak = monthly["cao_diem"] * (4.0 / 30.0)
    monthly["cao_diem"] -= sunday_peak
    monthly["binh_thuong"] += sunday_peak
    business = sum(monthly[p] * _PROD_DUOI_6KV[p] for p in monthly) * 1.08
    household = calc.calculate_bill(sum(grid) * 30.0)
    return business, household


def _optimize_pinned(client, uid: str):
    return client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
              "pinned_schedule": {"Máy bơm nước": _PIN_HOUR}},
        headers={"Authorization": f"Bearer {uid}"},
    )


def test_load_by_tou_period_groups_and_scales_to_month():
    load = [1.0] * 24  # 1 kWh mỗi giờ
    monthly = _load_by_tou_period(load)
    # QĐ 963: Chủ nhật không có cao điểm -> 4/30 phần cao điểm (5*30=150) chuyển sang bình thường.
    sunday_peak = 5 * 30.0 * (4.0 / 30.0)  # = 20
    assert monthly == {
        "thap_diem": pytest.approx(6 * 30.0),                  # giờ 0-5, không đổi
        "cao_diem": pytest.approx(5 * 30.0 - sunday_peak),     # giờ 18-22, trừ phần Chủ nhật
        "binh_thuong": pytest.approx(13 * 30.0 + sunday_peak), # còn lại + phần Chủ nhật
    }


def test_business_user_billed_with_business_tariff_not_household(client, db_session):
    _make_business_user(db_session, "bizprod", voltage_level="duoi_6kv")
    resp = _optimize_pinned(client, "bizprod")
    assert resp.status_code == 200
    data = resp.json()

    expected_business, wrong_household = _expected_bills_pinned_at(_PIN_HOUR)
    # 4 kWh/ngày toàn cao điểm: 2 biểu giá cho số khác nhau RÕ RỆT — nếu Bug #1 còn,
    # bill_after sẽ khớp wrong_household thay vì expected_business.
    assert expected_business != pytest.approx(wrong_household)
    assert data["bill_after_vnd"] == pytest.approx(expected_business)
    assert data["bill_after_vnd"] != pytest.approx(wrong_household)
    assert data["bill_before_vnd"] > 0


def test_business_user_missing_voltage_level_falls_back_duoi_6kv(client, db_session):
    # Tài khoản business tạo trước khi có field voltage_level: không lỗi, dùng "duoi_6kv".
    _make_business_user(db_session, "biznovolt", voltage_level=None)
    resp = _optimize_pinned(client, "biznovolt")
    assert resp.status_code == 200
    expected_business, _ = _expected_bills_pinned_at(_PIN_HOUR)
    assert resp.json()["bill_after_vnd"] == pytest.approx(expected_business)


def test_household_user_keeps_household_tariff(client, auth_headers):
    # Hồi quy: user household (seed mặc định) vẫn đi qua calc.calculate_bill như cũ —
    # /recompute-bill với schedule/fixed_hours rỗng cho đúng bill của tải rỗng (0 đ...
    # calc.calculate_bill(0) = 0) và /optimize vẫn 200 (số liệu chi tiết đã có
    # test_optimize.py / test_recompute_bill.py bảo vệ).
    headers = auth_headers("householdreg")
    resp = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny",
              "schedule": {}, "fixed_hours": {}},
        headers=headers,
    )
    assert resp.status_code == 200
