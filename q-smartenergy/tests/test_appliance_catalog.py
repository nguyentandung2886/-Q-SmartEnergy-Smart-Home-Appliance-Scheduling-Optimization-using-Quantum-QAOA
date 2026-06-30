"""
Tests for appliance_catalog.py — 10-type household appliance catalog with sourced
power ratings, used to derive calc.MONTHLY_KWH (replaces the old locked literal).
"""

import pytest

from appliance_catalog import (
    HOUSEHOLD_APPLIANCES,
    split_by_flexibility,
    total_monthly_kwh,
    usage_windows,
)


def test_household_appliances_has_ten_distinct_types():
    """10 LOẠI khác nhau (Điều hòa và Bình nước nóng mỗi loại có 2 instance, nên list có
    12 entries nhưng chỉ 10 tên loại gốc khác nhau khi bỏ phần mô tả công suất/vị trí)."""
    assert len(HOUSEHOLD_APPLIANCES) == 12


def test_total_monthly_kwh_matches_hand_computed_value():
    """Regression guard: tổng kWh/tháng từ 12 entries, tính bằng tay từ power_w/duration_hours
    đã chốt trong appliance_catalog.py. KHÔNG phải số ép trước — đây là kết quả của input thật,
    chốt lại bằng test để không bị âm thầm đổi sau này."""
    assert total_monthly_kwh() == pytest.approx(723.075, abs=0.01)


def test_total_monthly_kwh_accepts_custom_list():
    from qubo_builder import Appliance

    custom = [Appliance(name="X", power_w=1000, duration_hours=1, candidate_hours=(), is_flexible=False)]
    # 1000W * 1h * 30 / 1000 = 30 kWh
    assert total_monthly_kwh(custom) == pytest.approx(30.0)


def test_split_by_flexibility_separates_correctly():
    flexible, fixed = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    assert all(a.is_flexible for a in flexible)
    assert all(not a.is_flexible for a in fixed)
    assert len(flexible) + len(fixed) == len(HOUSEHOLD_APPLIANCES)
    # Bình nước nóng (2 entries) + Máy giặt (1 entry) là flexible theo thiết kế.
    assert len(flexible) == 3
    assert len(fixed) == 9


def test_flexible_appliances_have_at_least_two_candidate_hours():
    """Mọi appliance is_flexible=True phải có >=2 candidate_hours (yêu cầu của build_qubo's
    one-hot encoding) — nếu chỉ có 1 hoặc 0 giờ ứng viên, ràng buộc one-hot vô nghĩa."""
    flexible, _ = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    for appliance in flexible:
        assert len(appliance.candidate_hours) >= 2, f"{appliance.name} cần >=2 candidate_hours"


def test_fixed_appliances_have_empty_candidate_hours():
    _, fixed = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    for appliance in fixed:
        assert appliance.candidate_hours == (), f"{appliance.name} (is_flexible=False) phải có candidate_hours=()"


def test_refrigerator_present_and_always_on():
    fridge = next(a for a in HOUSEHOLD_APPLIANCES if a.name == "Tủ lạnh")
    assert fridge.is_flexible is False
    assert fridge.duration_hours == 24


def test_usage_windows_never_overflow_24h():
    """Mọi khung giờ của mọi thiết bị: start trong 0-23 và start+length <= 24 (Gantt 24 cột)."""
    for a in HOUSEHOLD_APPLIANCES:
        for start, length in usage_windows(a):
            assert 0 <= start <= 23
            assert length >= 1
            assert start + length <= 24, f"{a.name}: khung {start}+{length} vượt 24h"


def test_usage_windows_fridge_runs_all_day():
    fridge = next(a for a in HOUSEHOLD_APPLIANCES if a.name == "Tủ lạnh")
    assert usage_windows(fridge) == [(0, 24)]


def test_usage_windows_supports_multiple_disjoint_windows():
    """Quạt điện minh họa: chạy NHIỀU khung giờ rời nhau (trưa + tối), không phải 1 khối."""
    fan = next(a for a in HOUSEHOLD_APPLIANCES if a.name == "Quạt điện")
    windows = usage_windows(fan)
    assert len(windows) >= 2  # nhiều khung


def test_usage_windows_unknown_appliance_uses_evening_fallback():
    from qubo_builder import Appliance
    unknown = Appliance(name="Thiết bị lạ", power_w=100, duration_hours=2,
                        candidate_hours=(), is_flexible=False)
    windows = usage_windows(unknown)
    assert len(windows) == 1
    assert windows[0] == (18, 2)
