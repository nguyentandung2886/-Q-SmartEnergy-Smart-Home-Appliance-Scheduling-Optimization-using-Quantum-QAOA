"""Tests for the business EVN tariff scaffold — placeholders must refuse to fabricate a bill
rather than compute a wrong number from unconfigured (None) rates."""
import pytest

from core.business_calc import EVN_BUSINESS_TIERS, calculate_business_bill


def test_business_tiers_ship_both_branches_all_placeholder():
    assert set(EVN_BUSINESS_TIERS) == {"production", "commercial"}
    for tiers in EVN_BUSINESS_TIERS.values():
        assert all(price is None for price in tiers.values())


def test_calculate_business_bill_raises_notimplemented_when_unconfigured():
    with pytest.raises(NotImplementedError):
        calculate_business_bill({"binh_thuong": 100.0}, "production")


def test_calculate_business_bill_rejects_unknown_business_type():
    with pytest.raises(ValueError):
        calculate_business_bill({"binh_thuong": 100.0}, "nonexistent")
