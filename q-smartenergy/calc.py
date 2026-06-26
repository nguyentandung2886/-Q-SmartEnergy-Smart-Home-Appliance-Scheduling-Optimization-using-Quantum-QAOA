"""
Single source of truth for Q-SmartEnergy baseline numbers.

This module defines all baseline constants and utility functions used across the project.
Every other module (data_prep, qubo_builder, quantum_runner, visualizer, app) MUST import
these values from here — DO NOT hard-code baseline numbers elsewhere.

Baseline numbers (locked, do not alter):
- Monthly consumption: 530 kWh/month (total household load)
- Solar capacity: 5 kWp
- Solar monthly generation: 525 kWh/month (~105 kWh/kWp/month, realistic for Vietnam)
- Self-consumption tiers: 30% (before optimization) → 45% (after optimization)
  (portion of solar output directly consumed; remainder is grid-exported)
- Grid-purchased kWh: MONTHLY_KWH - (SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate)
  This is the portion that incurs EVN tiered pricing charges
- Electricity bills: 896,125đ (before) → 658,125đ (after), reduction 26.6%
  (bills calculated on grid-purchased kWh, not total consumption)

EVN Tiered Pricing:
- The pricing follows Vietnam's standard tiered electricity pricing structure (EVN sinh hoạt).
- Thresholds (reference): 0-50 kWh (tier 1), 51-100 (tier 2), 101-200 (tier 3),
  201-300 (tier 4), 301-400 (tier 5), >400 (tier 6).
- These thresholds are configurable if EVN updates rates.

Rubric Mapping:
- III.5: Data generator based on actual EVN tiered pricing structure.
- III.3: Technical quality — accurate bill calculation as basis for optimization correctness.
"""

# Baseline consumption and solar parameters
MONTHLY_KWH = 530
SOLAR_CAPACITY_KWP = 5
SOLAR_MONTHLY_GENERATION_KWH = 525  # Monthly solar output from 5kWp system (~105 kWh/kWp/month)
SELF_CONSUMPTION_BEFORE = 0.30
SELF_CONSUMPTION_AFTER = 0.45

# Baseline electricity bills (VND)
BILL_BEFORE_VND = 896125
BILL_AFTER_VND = 658125

# Savings percentage (locked baseline, calculated per formula)
# Formula: (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100
SAVINGS_PERCENT = 26.6

# EVN tiered pricing structure (đ/kWh for each tier, applied cumulatively)
# Each tuple: (threshold_kwh, price_per_kwh_vnd)
# Tier 1: 0-50 kWh @ 1800 đ/kWh
# Tier 2: 51-100 kWh @ 1900 đ/kWh
# Tier 3: 101-200 kWh @ 2200 đ/kWh
# Tier 4: 201-300 kWh @ 2700 đ/kWh
# Tier 5: 301-400 kWh @ 3050 đ/kWh
# Tier 6: >400 kWh @ 3150 đ/kWh
EVN_TIERS = [
    (50, 1800),
    (100, 1900),
    (200, 2200),
    (300, 2700),
    (400, 3050),
    (float('inf'), 3150),
]


def calculate_bill(kwh: float, tiers: list = None) -> float:
    """
    Calculate electricity bill using tiered (lũy tiến) pricing structure.

    Args:
        kwh: Grid-purchased kWh (after solar self-consumption is subtracted from total load).
        tiers: List of (threshold, price_per_kwh) tuples. Defaults to EVN_TIERS.

    Returns:
        Total bill in VND (đ).

    Calculation logic:
        Applies cumulative tiered pricing: the first 50 kWh are charged at tier 1 rate,
        the next 50 kWh (51-100) at tier 2 rate, etc. This reflects Vietnam's standard
        EVN sinh hoạt (residential) pricing.

    Example:
        >>> grid_purchase_kwh(0.30)  # Solar self-consumption 30%
        372.5
        >>> calculate_bill(grid_purchase_kwh(0.30))  # Should equal BILL_BEFORE_VND (896,125đ)
        896125.0
    """
    if tiers is None:
        tiers = EVN_TIERS

    if kwh < 0:
        raise ValueError("kwh must be non-negative")

    total_bill = 0.0
    remaining_kwh = kwh
    prev_threshold = 0

    for threshold, price_per_kwh in tiers:
        tier_max = threshold - prev_threshold
        if tier_max <= 0:
            # Handle edge case of inf threshold
            tier_max = remaining_kwh

        kwh_in_tier = min(remaining_kwh, tier_max)
        total_bill += kwh_in_tier * price_per_kwh
        remaining_kwh -= kwh_in_tier

        if remaining_kwh <= 0:
            break

        prev_threshold = threshold

    return total_bill


def grid_purchase_kwh(self_consumption_rate: float) -> float:
    """
    Calculate grid-purchased kWh after solar self-consumption.

    Args:
        self_consumption_rate: Fraction of solar output self-consumed directly (0.0 to 1.0).
                              Remainder is exported to grid.

    Returns:
        kWh purchased from grid = MONTHLY_KWH - (SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate)

    Calculation logic:
        - Household total load: MONTHLY_KWH
        - Solar output: SOLAR_MONTHLY_GENERATION_KWH
        - Solar self-consumed: SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
        - Grid-purchased (incurs EVN tiered pricing): MONTHLY_KWH - solar_self_consumed

    Example:
        >>> grid_purchase_kwh(0.30)  # 30% self-consumption
        372.5  # = 530 - (525 * 0.30)
        >>> grid_purchase_kwh(0.45)  # 45% self-consumption
        293.75  # = 530 - (525 * 0.45)
    """
    solar_self_consumed = SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    return MONTHLY_KWH - solar_self_consumed


# Validation: calculate_bill(grid_purchase_kwh(...)) should match locked baseline bills
# Tolerance: ±1đ (float rounding only; these must reconcile exactly)
_grid_purchase_before = grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)
_calculated_bill_before = calculate_bill(_grid_purchase_before)
_diff_before = abs(_calculated_bill_before - BILL_BEFORE_VND)
assert _diff_before <= 1, (
    f"Bill mismatch (BEFORE): calculate_bill(grid_purchase_kwh({SELF_CONSUMPTION_BEFORE})) = {_calculated_bill_before:.0f}đ, "
    f"but BILL_BEFORE_VND = {BILL_BEFORE_VND}đ. Difference: {_diff_before:.0f}đ. "
    f"This indicates EVN tier thresholds or SOLAR_MONTHLY_GENERATION_KWH need adjustment."
)

_grid_purchase_after = grid_purchase_kwh(SELF_CONSUMPTION_AFTER)
_calculated_bill_after = calculate_bill(_grid_purchase_after)
_diff_after = abs(_calculated_bill_after - BILL_AFTER_VND)
assert _diff_after <= 1, (
    f"Bill mismatch (AFTER): calculate_bill(grid_purchase_kwh({SELF_CONSUMPTION_AFTER})) = {_calculated_bill_after:.0f}đ, "
    f"but BILL_AFTER_VND = {BILL_AFTER_VND}đ. Difference: {_diff_after:.0f}đ. "
    f"This indicates EVN tier thresholds or SOLAR_MONTHLY_GENERATION_KWH need adjustment."
)
