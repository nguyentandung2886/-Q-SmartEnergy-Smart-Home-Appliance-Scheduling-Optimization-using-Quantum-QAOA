"""
Data Preparation Module for Q-SmartEnergy.

Input:
  - Monthly appliance load profiles (hourly or 15-min granularity)
  - EVN tiered electricity pricing structure (from calc.py)
  - Solar generation forecast (kW, hourly)

Output:
  - Cleaned time-series data ready for QUBO formulation
  - Appliance load bounds and flexibility parameters
  - Time slot definitions (e.g., peak load hours, off-peak windows)

Economic/Physical Meaning:
  - Identifies which appliances can be shifted in time to minimize tiered bill
  - Aligns consumption timing with solar generation to maximize self-consumption
  - Prepares cost penalties for EVN tier jumps

Rubric Mapping:
  - III.3 (Technical Quality): Data quality, handling missing values, normalization
  - III.5 (Data Generator): Realistic appliance schedules based on EVN tiered pricing
  - III.6 (Algorithm Correctness): Accurate forecasts feed downstream optimization
"""


def prepare_data() -> None:
    """Stub for Task 2 implementation."""
    raise NotImplementedError("Task 2 will implement data preparation logic")
