"""Tests for the business EVN tariff (QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT, khung giờ
QĐ 963/QĐ-BCT): real per-voltage-level TOU prices, hour classification, and the
VAT-inclusive bill — no more NotImplementedError placeholders."""
import pytest

from core.business_calc import (
    EVN_BUSINESS_TIERS,
    calculate_business_bill,
    classify_hour_tou,
)
from core.calc import VAT_RATE


def test_tier_table_structure():
    assert set(EVN_BUSINESS_TIERS) == {"production", "commercial"}
    # Sản xuất: 4 cấp điện áp; Kinh doanh (nhóm 3.3): 3 cấp, KHÔNG có >=110kV.
    assert set(EVN_BUSINESS_TIERS["production"]) == {
        "tren_110kv", "22_den_110kv", "6_den_22kv", "duoi_6kv",
    }
    assert set(EVN_BUSINESS_TIERS["commercial"]) == {
        "22_den_110kv", "6_den_22kv", "duoi_6kv",
    }
    for levels in EVN_BUSINESS_TIERS.values():
        for prices in levels.values():
            assert set(prices) == {"binh_thuong", "thap_diem", "cao_diem"}
            assert all(isinstance(p, (int, float)) and p > 0 for p in prices.values())


def test_tier_values_match_official_tables():
    # Spot-check every price against the sourced tables (đ/kWh, chưa VAT).
    assert EVN_BUSINESS_TIERS["production"]["tren_110kv"] == {
        "binh_thuong": 1811, "thap_diem": 1146, "cao_diem": 3266}
    assert EVN_BUSINESS_TIERS["production"]["22_den_110kv"] == {
        "binh_thuong": 1833, "thap_diem": 1190, "cao_diem": 3398}
    assert EVN_BUSINESS_TIERS["production"]["6_den_22kv"] == {
        "binh_thuong": 1899, "thap_diem": 1234, "cao_diem": 3508}
    assert EVN_BUSINESS_TIERS["production"]["duoi_6kv"] == {
        "binh_thuong": 1987, "thap_diem": 1300, "cao_diem": 3640}
    assert EVN_BUSINESS_TIERS["commercial"]["22_den_110kv"] == {
        "binh_thuong": 2887, "thap_diem": 1609, "cao_diem": 5025}
    assert EVN_BUSINESS_TIERS["commercial"]["6_den_22kv"] == {
        "binh_thuong": 3108, "thap_diem": 1829, "cao_diem": 5202}
    assert EVN_BUSINESS_TIERS["commercial"]["duoi_6kv"] == {
        "binh_thuong": 3152, "thap_diem": 1918, "cao_diem": 5422}


# ---------- classify_hour_tou: khung giờ 963/QĐ-BCT với quy tắc làm tròn đã chốt ----------

def test_classify_hour_tou_full_day():
    for h in range(0, 6):       # 00h-06h: thấp điểm
        assert classify_hour_tou(h) == "thap_diem", h
    for h in range(6, 18):      # 6h-17h: bình thường (giờ 17 đa số phút trước 17h30)
        assert classify_hour_tou(h) == "binh_thuong", h
    for h in range(18, 23):     # 18h-22h: cao điểm (giờ 22 đa số phút trước 22h30)
        assert classify_hour_tou(h) == "cao_diem", h
    assert classify_hour_tou(23) == "binh_thuong"


# ---------- calculate_business_bill: giá thật × khung giờ + VAT 8% ----------

def test_bill_production_duoi_6kv_binh_thuong_only():
    # Acceptance example: 1000 kWh bình thường, sản xuất, dưới 6kV.
    bill = calculate_business_bill(
        {"binh_thuong": 1000, "thap_diem": 0, "cao_diem": 0}, "production", "duoi_6kv")
    assert bill == pytest.approx(1000 * 1987 * 1.08)


def test_bill_mixes_all_three_periods():
    bill = calculate_business_bill(
        {"binh_thuong": 100, "thap_diem": 50, "cao_diem": 10}, "production", "tren_110kv")
    expected = (100 * 1811 + 50 * 1146 + 10 * 3266) * (1 + VAT_RATE)
    assert bill == pytest.approx(expected)


def test_bill_commercial_duoi_6kv():
    bill = calculate_business_bill({"cao_diem": 200}, "commercial", "duoi_6kv")
    assert bill == pytest.approx(200 * 5422 * 1.08)


def test_bill_rejects_unknown_business_type():
    with pytest.raises(ValueError):
        calculate_business_bill({"binh_thuong": 100.0}, "nonexistent", "duoi_6kv")


def test_bill_rejects_unknown_voltage_level():
    with pytest.raises(ValueError):
        calculate_business_bill({"binh_thuong": 100.0}, "production", "500kv")


def test_bill_rejects_voltage_level_not_offered_for_commercial():
    # Kinh doanh không có cấp >=110kV — phải từ chối thay vì đoán giá.
    with pytest.raises(ValueError):
        calculate_business_bill({"binh_thuong": 100.0}, "commercial", "tren_110kv")
