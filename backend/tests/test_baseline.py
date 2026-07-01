"""
Tests for calc.py — rebased on the real EVN tariff (5 tiers + 8% VAT, effective
29/05/2025 per QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT) and a MONTHLY_KWH derived from
appliance_catalog.py (no longer a locked literal).
"""

import pytest

from core.calc import (
    BILL_AFTER_VND,
    BILL_BEFORE_VND,
    EVN_TIERS,
    MONTHLY_KWH,
    SAVINGS_PERCENT,
    SELF_CONSUMPTION_AFTER,
    SELF_CONSUMPTION_BEFORE,
    SOLAR_CAPACITY_KWP,
    SOLAR_MONTHLY_GENERATION_KWH,
    VAT_RATE,
    calculate_bill,
    grid_purchase_kwh,
)


class TestEVNTiers:
    """5-tier structure, real EVN figures (QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT)."""

    def test_evn_tiers_has_five_tiers(self):
        assert len(EVN_TIERS) == 5

    def test_evn_tier_prices_match_official_figures(self):
        expected_prices = [1984, 2380, 2998, 3571, 3967]
        actual_prices = [price for _, price in EVN_TIERS]
        assert actual_prices == expected_prices

    def test_evn_tier_thresholds_match_official_figures(self):
        expected_thresholds = [100, 200, 400, 700, float("inf")]
        actual_thresholds = [threshold for threshold, _ in EVN_TIERS]
        assert actual_thresholds == expected_thresholds

    def test_vat_rate_is_eight_percent(self):
        assert VAT_RATE == 0.08


class TestCalculateBillWithVAT:
    """calculate_bill() now includes 8% VAT — verified against hand-computed,
    single-tier cases to avoid any risk of a multi-tier arithmetic mistake."""

    def test_calculate_bill_zero(self):
        assert calculate_bill(0) == 0

    def test_calculate_bill_tier1_only_includes_vat(self):
        """50 kWh, entirely in tier 1 (0-100): 50 * 1984 = 99,200đ pre-VAT;
        *1.08 = 107,136đ exactly."""
        result = calculate_bill(50)
        assert result == pytest.approx(107136.0, abs=0.01)

    def test_calculate_bill_tier1_boundary_includes_vat(self):
        """100 kWh, exactly tier 1's upper boundary: 100 * 1984 = 198,400đ pre-VAT;
        *1.08 = 214,272đ exactly."""
        result = calculate_bill(100)
        assert result == pytest.approx(214272.0, abs=0.01)

    def test_calculate_bill_negative_input_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_bill(-10)

    def test_calculate_bill_is_monotonic(self):
        for kwh in [0, 50, 100, 200, 400, 600, 700, 900]:
            assert calculate_bill(kwh + 10) >= calculate_bill(kwh)


class TestMonthlyKwhDerivedFromCatalog:
    """MONTHLY_KWH is no longer a locked literal — it comes from appliance_catalog.py."""

    def test_monthly_kwh_matches_catalog_total(self):
        from core.appliance_catalog import total_monthly_kwh

        assert MONTHLY_KWH == pytest.approx(total_monthly_kwh())

    def test_monthly_kwh_is_realistic_household_scale(self):
        """Sanity bound, not a locked target: a single household's monthly consumption
        should plausibly be between 100 and 3000 kWh. This guards against a unit error
        (e.g. Wh vs kWh) in appliance_catalog.py, not a specific expected value."""
        assert 100 < MONTHLY_KWH < 3000


class TestGridPurchaseKwh:
    def test_grid_purchase_kwh_zero_consumption_equals_monthly_kwh(self):
        assert grid_purchase_kwh(0.0) == pytest.approx(MONTHLY_KWH)

    def test_grid_purchase_kwh_full_consumption(self):
        expected = MONTHLY_KWH - SOLAR_MONTHLY_GENERATION_KWH
        assert grid_purchase_kwh(1.0) == pytest.approx(expected)

    def test_grid_purchase_kwh_before_after_ordering(self):
        """Higher self-consumption must always mean less grid purchase."""
        before = grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)
        after = grid_purchase_kwh(SELF_CONSUMPTION_AFTER)
        assert after < before

    def test_grid_purchase_kwh_default_unchanged(self):
        """Calling with no monthly_kwh must produce the same result as before this change."""
        from core.calc import MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, grid_purchase_kwh
        assert grid_purchase_kwh(0.30) == pytest.approx(MONTHLY_KWH - SOLAR_MONTHLY_GENERATION_KWH * 0.30)

    def test_grid_purchase_kwh_with_custom_monthly_kwh(self):
        """Passing monthly_kwh overrides the module-level MONTHLY_KWH — used for per-user billing."""
        from core.calc import grid_purchase_kwh, SOLAR_MONTHLY_GENERATION_KWH
        custom_kwh = 1000.0
        result = grid_purchase_kwh(0.30, monthly_kwh=custom_kwh)
        assert result == pytest.approx(custom_kwh - SOLAR_MONTHLY_GENERATION_KWH * 0.30)


class TestBillBeforeAfterDerivation:
    """BILL_BEFORE_VND/BILL_AFTER_VND/SAVINGS_PERCENT are now direct formula results,
    not independently-chosen literals — these tests check the formula relationship and
    real-world properties, not a specific locked number."""

    def test_bill_before_equals_formula(self):
        expected = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
        assert BILL_BEFORE_VND == pytest.approx(expected)

    def test_bill_after_equals_formula(self):
        expected = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
        assert BILL_AFTER_VND == pytest.approx(expected)

    def test_bill_after_is_less_than_bill_before(self):
        assert BILL_AFTER_VND < BILL_BEFORE_VND

    def test_savings_percent_matches_formula(self):
        expected = (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100
        assert SAVINGS_PERCENT == pytest.approx(expected)

    def test_savings_percent_is_positive_but_modest(self):
        """Known consequence of the real 5-tier structure: BEFORE and AFTER grid-purchase
        both land in the same (wide) tier 4, so savings come from solar self-consumption
        alone, not tier-jump avoidance — expect single-digit-to-twenties percent, not the
        old illustrative 26.6%. This is intentional; do not adjust the catalog or
        self-consumption assumptions to force a different value here."""
        assert 0 < SAVINGS_PERCENT < 30

    def test_before_and_after_grid_purchase_fall_in_same_tier(self):
        """Documents the known real-data finding: with the actual 5-tier EVN structure,
        the BEFORE/AFTER macro comparison no longer crosses a tier boundary at all."""

        def tier_index(kwh: float) -> int:
            cumulative = 0.0
            for i, (threshold, _price) in enumerate(EVN_TIERS):
                if kwh <= threshold:
                    return i
                cumulative = threshold
            return len(EVN_TIERS) - 1

        before_tier = tier_index(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
        after_tier = tier_index(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
        assert before_tier == after_tier == 3  # Bậc 4 (401-700 kWh), 0-indexed


class TestUnchangedConstants:
    """Solar/self-consumption assumptions are out of scope for this rebase — confirm
    they're still the same illustrative values as before."""

    def test_solar_capacity(self):
        assert SOLAR_CAPACITY_KWP == 5

    def test_solar_monthly_generation(self):
        assert SOLAR_MONTHLY_GENERATION_KWH == 525

    def test_self_consumption_tiers(self):
        assert SELF_CONSUMPTION_BEFORE == 0.30
        assert SELF_CONSUMPTION_AFTER == 0.45
