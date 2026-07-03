"""Bug #1 fix (mảng optimizer): với tài khoản DOANH NGHIỆP, H_cost của QUBO phải dùng ĐÚNG
giá TOU theo giờ (classify_hour_tou + EVN_BUSINESS_TIERS[business_type][voltage_level]) —
cùng đại lượng mà calculate_business_bill() tính cho bill_after — thay vì giá bậc thang hộ
gia đình. Nhờ vậy optimizer minimize đúng thứ user bị tính tiền, không trả nghiệm đắt hơn
baseline (savings âm).

Tài khoản hộ gia đình KHÔNG bị ảnh hưởng (regression).
"""
import pytest

from api.optimize_router import _business_price_profile
from core.business_calc import EVN_BUSINESS_TIERS, classify_hour_tou
from core.data_prep import build_daily_profile
from core.qubo_builder import Appliance, build_qubo
from db.models import ApplianceModel, BusinessProfile, User


def test_business_price_profile_matches_tou_tariff():
    """Cột price_per_kwh sau khi override = giá TOU theo giờ của biểu giá doanh nghiệp."""
    profile = build_daily_profile(9, weather_condition="sunny")
    out = _business_price_profile(profile, "production", "duoi_6kv")
    prices = EVN_BUSINESS_TIERS["production"]["duoi_6kv"]
    for h in range(24):
        expected = prices[classify_hour_tou(h)]
        got = float(out.loc[out["hour"] == h, "price_per_kwh"].iloc[0])
        assert got == pytest.approx(expected)


def test_business_price_profile_does_not_mutate_input():
    """Override phải trả DataFrame mới, không sửa profile gốc (household price giữ nguyên)."""
    profile = build_daily_profile(9, weather_condition="sunny")
    original = list(profile["price_per_kwh"])
    _business_price_profile(profile, "production", "duoi_6kv")
    assert list(profile["price_per_kwh"]) == original


def test_business_qubo_hcost_equals_tou_price_times_energy():
    """H_cost trong QUBO tại 1 giờ = energy_kwh * giá_TOU(giờ) — khớp giá calculate_business_bill
    sẽ tính. Chọn giờ 20 (cao điểm) không có mặt trời -> H_solar=0, cô lập H_cost."""
    bt, vl = "production", "duoi_6kv"
    profile = _business_price_profile(build_daily_profile(9, weather_condition="sunny"), bt, vl)
    # giờ 20: cao_diem, solar_kwh = 0 (ngoài 6-18) -> h_solar = 0.
    app = Appliance(name="Bơm", power_w=2000, duration_hours=2, candidate_hours=(20, 10))
    Q, var_map = build_qubo([app], profile, lambda_onehot=0.0, lambda_power=0.0)
    inv = {v: k for k, v in var_map.items()}
    j20 = inv[("Bơm", 20)]
    expected_price = EVN_BUSINESS_TIERS[bt][vl][classify_hour_tou(20)]  # cao_diem = 3640
    assert Q[j20, j20] == pytest.approx(app.energy_kwh * expected_price)


def test_household_profile_price_is_tiered_not_tou():
    """Regression: profile household (không override) vẫn dùng giá bậc thang — mọi giờ CÙNG một
    giá biên (không có time-of-day). Bảo đảm fix business không đụng hộ gia đình."""
    profile = build_daily_profile(9, weather_condition="sunny")
    prices = set(round(float(p), 6) for p in profile["price_per_kwh"])
    # Bậc thang trong 1 ngày của user nhỏ: giá gần như phẳng (1 bậc) — KHÔNG phải 3 mức TOU.
    assert len(prices) <= 2


def _make_single_flexible_business_user(db_session, uid, candidate_hours, power_w, duration_hours):
    user = User(supabase_uid=uid, email=f"{uid}@test.local", role="business")
    db_session.add(user)
    db_session.flush()
    db_session.add(BusinessProfile(
        user_id=user.id, business_type="production",
        contracted_power_kw=50, voltage_level="duoi_6kv",
    ))
    db_session.add(ApplianceModel(
        user_id=user.id, name="Máy bơm nước", power_w=power_w, duration_hours=duration_hours,
        candidate_hours=list(candidate_hours), is_flexible=True,
    ))
    db_session.commit()


def test_business_optimize_savings_not_negative(client, db_session):
    """End-to-end: thiết bị năng lượng lớn (5kW x 2h = 10 kWh) so solar giữa 1 giờ nắng nhưng
    ĐẮT theo TOU (12h, bình thường) và 1 giờ RẺ (3h, thấp điểm, không nắng). Proxy hộ gia đình
    (giá phẳng) sẽ chọn giờ nắng 12h -> theo TOU doanh nghiệp lại đắt hơn baseline -> savings ÂM.
    Sau fix, QUBO dùng giá TOU nên chọn giờ 3h -> savings không âm."""
    _make_single_flexible_business_user(
        db_session, "bizsave", candidate_hours=(3, 12), power_w=5000, duration_hours=2
    )
    resp = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False},
        headers={"Authorization": "Bearer bizsave"},
    )
    assert resp.status_code == 200
    assert resp.json()["savings_percent"] >= 0
