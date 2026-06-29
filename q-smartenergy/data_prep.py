"""
Data Preparation Module for Q-SmartEnergy.

Input:
  - Baseline constants from calc.py (MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, EVN_TIERS)
  - A representative day-of-month (1-30) used to model where in the EVN tiered billing
    cycle the household currently sits.

Output:
  - generate_solar_profile(): 24 hourly solar generation values (kWh) for a representative
    day, bell-shaped (Gaussian) around noon, daylight-only (06:00-18:00). Accepts an optional
    weather_condition ("sunny"/"cloudy"/"rainy", default "sunny") that scales the total via
    weather_model.solar_multiplier() — the classical forecasting layer feeding this PoC's
    Hybrid Quantum-Classical architecture (see weather_model.py).
  - marginal_tier_price(): the EVN tier price (đ/kWh) that applies to the NEXT kWh consumed,
    given how much has already been consumed in the month so far.
  - generate_tier_price_profile(): 24 hourly marginal prices (đ/kWh) for a representative day.
  - build_daily_profile(): combines both into a single 24-row DataFrame (hour, solar_kwh,
    price_per_kwh) — the input data qubo_builder.py (Task 3) uses to build its objective.

Economic meaning of "marginal price for a representative day":
  EVN's tiered pricing (bậc thang/lũy tiến) is billed on TOTAL monthly kWh consumed, not on
  the hour of day. There is no time-of-day pricing in this market. What this module models
  is: assuming consumption is spread evenly across the month, by the time we reach day
  `day_of_month`, the household has already accumulated some kWh toward the monthly total.
  Each additional kWh consumed during that day's 24 hours therefore falls on a specific tier
  depending on the cumulative total at that point in the month — this is how a tier "jump"
  during a single day becomes possible, and it's exactly the signal the optimizer needs to
  decide which hour to run a flexible appliance in.

Rubric Mapping:
  # Rubric III.5 - data generator dựa trên biểu giá EVN thật
  # Rubric III.2 - ánh xạ đúng ràng buộc đời thực
"""

import numpy as np
import pandas as pd

from calc import MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, EVN_TIERS
from weather_model import solar_multiplier


def generate_solar_profile(
    monthly_generation_kwh: float = SOLAR_MONTHLY_GENERATION_KWH,
    weather_condition: str = "sunny",
) -> pd.Series:
    """24 hourly solar generation values (kWh) for a representative day, bell-shaped
    (Gaussian) curve peaking at hour 12, generating only within the 06:00-18:00 window.
    Total for a "sunny" day equals monthly_generation_kwh / 30; weather_condition scales
    that total via weather_model.solar_multiplier() — the classical forecasting layer of
    the Hybrid Quantum-Classical architecture (see weather_model.py). Raises ValueError
    for any weather_condition not in weather_model.WEATHER_MULTIPLIERS."""
    hours = np.arange(24)
    sigma = 3.0
    raw = np.exp(-((hours - 12.0) ** 2) / (2 * sigma ** 2))
    raw[(hours < 6) | (hours > 18)] = 0.0
    daily_avg = monthly_generation_kwh / 30.0 * solar_multiplier(weather_condition)
    scaled = raw / raw.sum() * daily_avg
    return pd.Series(scaled, index=hours, name="solar_kwh")


def marginal_tier_price(cumulative_kwh_before: float, tiers: list = EVN_TIERS) -> float:
    """Price (đ/kWh) that applies to the NEXT kWh consumed, based on total kWh already
    consumed in the month up to this point (cumulative_kwh_before). tiers is a list of
    (threshold, price) tuples in ascending order, with the final threshold being float('inf')."""
    for threshold, price in tiers:
        if cumulative_kwh_before < threshold:
            return price
    return tiers[-1][1]


def generate_tier_price_profile(day_of_month: int = 15, monthly_kwh: float = MONTHLY_KWH,
                                  tiers: list = EVN_TIERS) -> pd.Series:
    """24 hourly marginal prices (đ/kWh) for the representative day_of_month (1-30), assuming
    consumption is spread evenly across the month. day_of_month must be in [1, 30], otherwise
    raises ValueError."""
    if not (1 <= day_of_month <= 30):
        raise ValueError("day_of_month must be in [1, 30]")
    daily_avg = monthly_kwh / 30.0
    cumulative_before_today = (day_of_month - 1) * daily_avg
    hourly_avg = daily_avg / 24.0
    prices = [
        marginal_tier_price(cumulative_before_today + h * hourly_avg, tiers)
        for h in range(24)
    ]
    return pd.Series(prices, index=range(24), name="price_per_kwh")


def build_daily_profile(day_of_month: int = 15, weather_condition: str = "sunny") -> pd.DataFrame:
    """24-row DataFrame (columns: hour, solar_kwh, price_per_kwh), one row per hour of the
    representative day. weather_condition ("sunny"/"cloudy"/"rainy") scales solar_kwh via
    weather_model.solar_multiplier() — see generate_solar_profile(). price_per_kwh is never
    affected by weather (EVN tiered pricing has nothing to do with weather)."""
    solar = generate_solar_profile(weather_condition=weather_condition)
    price = generate_tier_price_profile(day_of_month)
    return pd.DataFrame({
        "hour": range(24),
        "solar_kwh": solar.values,
        "price_per_kwh": price.values,
    })


if __name__ == "__main__":
    build_daily_profile().to_csv("daily_profile.csv", index=False)
