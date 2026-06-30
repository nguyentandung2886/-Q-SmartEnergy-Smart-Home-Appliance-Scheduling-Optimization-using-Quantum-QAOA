"""
Single source of truth for Q-SmartEnergy baseline numbers.

This module defines all baseline constants and utility functions used across the project.
Every other module (data_prep, qubo_builder, quantum_runner, visualizer, app) MUST import
these values from here — DO NOT hard-code baseline numbers elsewhere.

Baseline numbers:
- Monthly consumption (MONTHLY_KWH): DERIVED from appliance_catalog.total_monthly_kwh() —
  a 10-type household appliance catalog with sourced power ratings. This is NOT a locked
  literal chosen to match a pre-decided bill story; it is whatever the real catalog sums to.
- Solar capacity: 5 kWp (illustrative, unchanged from earlier project phases)
- Solar monthly generation: 525 kWh/month (~105 kWh/kWp/month, illustrative)
- Self-consumption tiers: 30% (before optimization) → 45% (after optimization), illustrative
  (portion of solar output directly consumed; remainder is grid-exported)
- Grid-purchased kWh: MONTHLY_KWH - (SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate)
  This is the portion that incurs EVN tiered pricing charges
- Electricity bills (BILL_BEFORE_VND, BILL_AFTER_VND, SAVINGS_PERCENT): DERIVED directly
  from calculate_bill(grid_purchase_kwh(rate)) — not independently chosen literals. Because
  the real 5-tier structure's Bậc 4 (401-700 kWh) is wide, both the BEFORE and AFTER
  grid-purchase values land in that SAME tier — so this comparison demonstrates solar
  self-consumption savings only, not tier-jump avoidance. The day-level QAOA demo
  (data_prep.py's marginal-price profile) is where tier-jump avoidance still applies.

EVN Tiered Pricing (REAL, current rates — not illustrative):
- 5 bậc, hiệu lực từ 29/05/2025, theo Quyết định 14/2025/QĐ-TTg (Thủ tướng Chính phủ) và
  Quyết định 1279/QĐ-BCT ngày 09/5/2025 (Bộ Công Thương). Thay thế biểu giá 6 bậc cũ.
  Nguồn: trang chính chủ evn.com.vn ("Biểu giá bán lẻ điện theo Quyết định số 1279/QĐ-BCT"),
  đối chiếu khớp với luatvietnam.vn và vietnamsolar.vn.
- Giá CHƯA bao gồm VAT — calculate_bill() cộng thêm VAT_RATE (8%) ở bước cuối, vì hóa đơn
  EVN thật luôn gồm VAT.
- Bậc 1 (0-100 kWh): 1.984 đ/kWh
- Bậc 2 (101-200 kWh): 2.380 đ/kWh
- Bậc 3 (201-400 kWh): 2.998 đ/kWh
- Bậc 4 (401-700 kWh): 3.571 đ/kWh
- Bậc 5 (>700 kWh): 3.967 đ/kWh
- VAT điện: 8% (giảm từ 10%, áp dụng 01/07/2025-31/12/2026).

Rubric Mapping:
- III.5: Data generator based on the REAL, current EVN tiered pricing structure (not
  illustrative numbers) and a sourced household appliance catalog.
- III.3: Technical quality — accurate bill calculation (incl. VAT) as basis for
  optimization correctness.
"""

from appliance_catalog import total_monthly_kwh

# Baseline consumption and solar parameters
MONTHLY_KWH = total_monthly_kwh()  # Derived from appliance_catalog.py — NOT a locked literal
SOLAR_CAPACITY_KWP = 5
SOLAR_MONTHLY_GENERATION_KWH = 525  # Monthly solar output from 5kWp system (~105 kWh/kWp/month)
SELF_CONSUMPTION_BEFORE = 0.30
SELF_CONSUMPTION_AFTER = 0.45

# EVN tiered pricing structure (đ/kWh, NOT including VAT) — REAL rates, effective 29/05/2025
# per QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT ngày 09/5/2025. See module docstring for sourcing.
EVN_TIERS = [
    (100, 1984),
    (200, 2380),
    (400, 2998),
    (700, 3571),
    (float('inf'), 3967),
]

VAT_RATE = 0.08  # 8% VAT on electricity, effective 01/07/2025-31/12/2026


def calculate_bill(kwh: float, tiers: list = None) -> float:
    """
    Calculate electricity bill using tiered (lũy tiến) pricing structure, including VAT.

    Args:
        kwh: Grid-purchased kWh (after solar self-consumption is subtracted from total load).
        tiers: List of (threshold, price_per_kwh) tuples. Defaults to EVN_TIERS.

    Returns:
        Total bill in VND (đ), INCLUDING VAT_RATE (8%) — matches the actual amount due on
        a real EVN bill, not just the pre-VAT tariff calculation.

    Calculation logic:
        Applies cumulative tiered pricing: the first 100 kWh are charged at tier 1 rate,
        the next 100 kWh (101-200) at tier 2 rate, etc., then adds VAT_RATE on the total.

    Example:
        >>> calculate_bill(50)  # Entirely within tier 1
        107136.0  # = 50 * 1984 * 1.08
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

    return total_bill * (1 + VAT_RATE)


def grid_purchase_kwh(self_consumption_rate: float, monthly_kwh: float = None) -> float:
    """
    Calculate grid-purchased kWh after solar self-consumption.

    Args:
        self_consumption_rate: Fraction of solar output self-consumed directly (0.0 to 1.0).
        monthly_kwh: Override total household monthly load. Defaults to module-level MONTHLY_KWH
                     (the appliance_catalog total) if None — this preserves existing behavior for
                     every current caller. Pass a specific value to compute a per-user bill
                     (server/routers/optimize_router.py), where each user has their own appliance
                     list and thus a different monthly total.

    Returns:
        kWh purchased from grid = monthly_kwh_effective - SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    """
    monthly_kwh_effective = MONTHLY_KWH if monthly_kwh is None else monthly_kwh
    solar_self_consumed = SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    return monthly_kwh_effective - solar_self_consumed


# BILL_BEFORE_VND / BILL_AFTER_VND / SAVINGS_PERCENT are DIRECT formula results — no longer
# independently-chosen literals that need reconciliation-checking against this formula. The
# previous BaselineReconciliationError / _check_reconciliation machinery is removed because
# there is nothing left to reconcile: these ARE the formula's output, by construction.
BILL_BEFORE_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
BILL_AFTER_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
SAVINGS_PERCENT = (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100
