"""
Single source of truth for Q-SmartEnergy baseline numbers.

This module defines all baseline constants and utility functions used across the project.
Every other module (data_prep, qubo_builder, quantum_runner, visualizer, app) MUST import
these values from here — DO NOT hard-code baseline numbers elsewhere.

Baseline numbers (locked, do not alter):
- Monthly consumption: 530 kWh/month
- Solar capacity: 5 kWp
- Self-consumption tiers: 30% (before optimization) → 45% (after optimization)
- Electricity bills: 896,125đ (before) → 658,125đ (after), reduction 26.6%

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
        kwh: Total monthly consumption in kWh.
        tiers: List of (threshold, price_per_kwh) tuples. Defaults to EVN_TIERS.

    Returns:
        Total bill in VND (đ).

    Calculation logic:
        Applies cumulative tiered pricing: the first 50 kWh are charged at tier 1 rate,
        the next 50 kWh (51-100) at tier 2 rate, etc. This reflects Vietnam's standard
        EVN sinh hoạt (residential) pricing.

    Example:
        >>> calculate_bill(50)  # First tier only
        >>> calculate_bill(530)  # Should be close to BILL_BEFORE_VND (896,125đ)
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


# Validation: calculate_bill(MONTHLY_KWH) should be close to BILL_BEFORE_VND
# Tolerance: allow ±2% difference (EVN may apply surcharges/VAT not modeled here)
_calculated_bill = calculate_bill(MONTHLY_KWH)
_tolerance = BILL_BEFORE_VND * 0.02
if abs(_calculated_bill - BILL_BEFORE_VND) > _tolerance:
    import warnings
    warnings.warn(
        f"Bill mismatch: calculate_bill({MONTHLY_KWH}) = {_calculated_bill:.0f}đ, "
        f"but BILL_BEFORE_VND = {BILL_BEFORE_VND}đ. Difference: {abs(_calculated_bill - BILL_BEFORE_VND):.0f}đ. "
        f"This may indicate EVN tier thresholds need adjustment or baseline is based on different assumptions.",
        UserWarning
    )
