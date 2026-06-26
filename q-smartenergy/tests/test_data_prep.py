"""
Tests for data_prep.py.

Verifies:
1. generate_solar_profile() shape, non-negativity, and zero output outside daylight hours.
2. generate_solar_profile() total monthly energy reconciles with calc.SOLAR_MONTHLY_GENERATION_KWH.
3. marginal_tier_price() returns the correct EVN tier price at and around tier boundaries.
4. generate_tier_price_profile() rejects day_of_month outside [1, 30].
5. build_daily_profile() returns a 24-row DataFrame with the expected columns.
6. build_daily_profile() solar column also reconciles with calc.SOLAR_MONTHLY_GENERATION_KWH.
"""

import pytest
from calc import SOLAR_MONTHLY_GENERATION_KWH
from data_prep import (
    generate_solar_profile,
    marginal_tier_price,
    generate_tier_price_profile,
    build_daily_profile,
)


class TestGenerateSolarProfile:
    """Test generate_solar_profile() shape and physical bounds."""

    def test_returns_24_values(self):
        """generate_solar_profile() must return a Series with 24 values (one per hour)."""
        solar = generate_solar_profile()
        assert len(solar) == 24, f"Expected 24 values, got {len(solar)}"

    def test_all_non_negative(self):
        """All solar output values must be >= 0."""
        solar = generate_solar_profile()
        assert (solar >= 0).all(), "Solar output must be non-negative at every hour"

    def test_zero_outside_daylight_window(self):
        """Hour 0 and hour 23 are outside the 6h-18h daylight window, so output must be 0."""
        solar = generate_solar_profile()
        assert solar[0] == 0, f"Expected 0 at hour 0, got {solar[0]}"
        assert solar[23] == 0, f"Expected 0 at hour 23, got {solar[23]}"

    def test_monthly_total_reconciles_with_calc(self):
        """Daily total * 30 must approximate calc.SOLAR_MONTHLY_GENERATION_KWH."""
        solar = generate_solar_profile()
        monthly_total = solar.sum() * 30
        assert monthly_total == pytest.approx(SOLAR_MONTHLY_GENERATION_KWH, rel=1e-6), (
            f"Expected monthly total ≈ {SOLAR_MONTHLY_GENERATION_KWH}, got {monthly_total}"
        )


class TestMarginalTierPrice:
    """Test marginal_tier_price() at and around EVN tier boundaries."""

    def test_zero_cumulative_is_tier1(self):
        """At cumulative 0 kWh, marginal price must be tier 1 (1800 đ/kWh)."""
        assert marginal_tier_price(0) == 1800

    def test_just_below_tier1_boundary(self):
        """At cumulative 49.9 kWh, marginal price must still be tier 1 (1800 đ/kWh)."""
        assert marginal_tier_price(49.9) == 1800

    def test_just_above_tier1_boundary(self):
        """At cumulative 50.1 kWh, marginal price must be tier 2 (1900 đ/kWh)."""
        assert marginal_tier_price(50.1) == 1900

    def test_far_above_all_tiers(self):
        """At cumulative 10000 kWh, marginal price must be the top tier (3150 đ/kWh)."""
        assert marginal_tier_price(10000) == 3150


class TestGenerateTierPriceProfile:
    """Test generate_tier_price_profile() input validation."""

    def test_day_of_month_31_raises(self):
        """day_of_month=31 is out of [1, 30] and must raise ValueError."""
        with pytest.raises(ValueError):
            generate_tier_price_profile(day_of_month=31)

    def test_day_of_month_0_raises(self):
        """day_of_month=0 is out of [1, 30] and must raise ValueError."""
        with pytest.raises(ValueError):
            generate_tier_price_profile(day_of_month=0)


class TestBuildDailyProfile:
    """Test build_daily_profile() shape and reconciliation with calc.py."""

    def test_returns_24_rows_three_columns(self):
        """build_daily_profile() must return a DataFrame with 24 rows and exactly 3 columns."""
        df = build_daily_profile()
        assert len(df) == 24, f"Expected 24 rows, got {len(df)}"
        assert list(df.columns) == ["hour", "solar_kwh", "price_per_kwh"], (
            f"Expected columns ['hour', 'solar_kwh', 'price_per_kwh'], got {list(df.columns)}"
        )

    def test_hour_column_runs_0_to_23(self):
        """The hour column must run from 0 to 23 in order."""
        df = build_daily_profile()
        assert list(df["hour"]) == list(range(24)), "hour column must run 0..23"

    def test_solar_monthly_total_reconciles_with_calc(self):
        """build_daily_profile(day_of_month=15)['solar_kwh'].sum() * 30 must approximate
        calc.SOLAR_MONTHLY_GENERATION_KWH (acceptance criteria for Phase 1.1)."""
        df = build_daily_profile(day_of_month=15)
        monthly_total = df["solar_kwh"].sum() * 30
        assert monthly_total == pytest.approx(SOLAR_MONTHLY_GENERATION_KWH, rel=1e-6), (
            f"Expected monthly total ≈ {SOLAR_MONTHLY_GENERATION_KWH}, got {monthly_total}"
        )
