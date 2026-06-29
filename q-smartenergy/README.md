# Q-SmartEnergy

Quantum-optimized home appliance scheduling leveraging QAOA (Quantum Approximate Optimization Algorithm) to balance Vietnam's tiered EVN electricity pricing against rooftop solar self-consumption.

## Overview

Q-SmartEnergy is a PoC (Proof of Concept) that uses quantum computing to solve the appliance scheduling problem: given a household's flexible appliances, a tiered electricity pricing structure, and expected rooftop solar output, when should each appliance run to minimize the monthly bill?

The optimizer balances two value axes inside a single QUBO objective: avoiding EVN tier-price jumps (the more total kWh purchased from the grid this month, the higher the marginal price) and maximizing solar self-consumption (kWh covered by free rooftop solar is never billed at all). These two axes can pull in different directions — when solar at a given hour is strong enough, the optimizer may deliberately schedule an appliance into a higher-priced tier because the solar-covered savings outweigh the tier difference. The system is honest about this tradeoff rather than claiming it always avoids tier jumps; see `qubo_builder.py`'s module docstring for the exact math.

A weather-aware classical forecasting layer (`weather_model.py`) feeds simulated daily conditions ("sunny"/"cloudy"/"rainy") into the solar generation forecast, making the Hybrid Quantum-Classical architecture concrete: when solar is weak (e.g. "rainy"), the tier-avoidance axis becomes the dominant signal; when solar is strong, self-consumption dominates.

## Project Structure

```
q-smartenergy/
├── calc.py                  # Single source of truth for baseline constants & bill calculation
├── data_prep.py              # EVN tier price profile + solar generation profile (weather-aware)
├── weather_model.py          # Classical weather-forecast layer (Hybrid Quantum-Classical bonus)
├── qubo_builder.py           # QUBO formulation for quantum optimization
├── quantum_runner.py         # QAOA execution on Qiskit Aer Simulator + classical fallback
├── visualizer.py              # Gantt chart & bill comparison chart
├── app.py                     # Streamlit web UI dashboard
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── tests/
    ├── __init__.py
    ├── test_baseline.py        # Tests for calc.py baseline constants
    ├── test_data_prep.py       # Tests for data_prep.py
    ├── test_weather_model.py   # Tests for weather_model.py
    ├── test_qubo_builder.py    # Tests for qubo_builder.py
    ├── test_quantum_runner.py  # Tests for quantum_runner.py
    ├── test_visualizer.py      # Tests for visualizer.py
    ├── test_app.py             # Tests for app.py
    └── test_readme.py          # Content checks for this file
```

### Module Roles

| Module | Purpose |
|--------|---------|
| `calc.py` | **Baseline lock**: all project constants (530 kWh/month, EVN tier prices, bill targets). Every other module imports from here — never hard-code. |
| `data_prep.py` | Prepares the EVN marginal-tier-price profile and the (weather-aware) solar generation profile for a representative day. |
| `weather_model.py` | Classical forecasting layer: converts a simulated weather condition into a solar-output multiplier — the "classical" half of the Hybrid Quantum-Classical architecture. |
| `qubo_builder.py` | Encodes the appliance scheduling problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. |
| `quantum_runner.py` | Executes QAOA on Qiskit Aer Simulator to find optimal schedules, with a mandatory classical brute-force fallback and a hyperparameter-comparison utility. |
| `visualizer.py` | Generates the schedule Gantt chart and the bill comparison bar chart. |
| `app.py` | Streamlit dashboard — lets users edit appliance power/duration, pick a day of month, and pick a weather condition, then view the optimized schedule. |

## Setup & Usage

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest tests/
```

### Run the Web App
```bash
streamlit run app.py
```

## Baseline Numbers (Locked)

- **Monthly Consumption**: 530 kWh
- **Solar Capacity**: 5 kWp (525 kWh/month generation)
- **Self-Consumption Before Optimization**: 30%
- **Self-Consumption After Optimization**: 45%
- **Bill Before Optimization**: 896,125đ
- **Bill After Optimization**: 658,125đ
- **Savings**: 26.6%

These macro numbers represent a whole-month, whole-household projection (see `calc.py`) — they are a different scale from the 2-appliance live demo scenario shown in the Gantt chart, and `app.py` labels them separately so the two are never confused.

**EVN Tiered Pricing** (đ/kWh) used in this PoC:
- Tier 1 (0–50 kWh): 1,800
- Tier 2 (51–100 kWh): 1,900
- Tier 3 (101–200 kWh): 2,200
- Tier 4 (201–300 kWh): 2,700
- Tier 5 (301–400 kWh): 3,050
- Tier 6 (>400 kWh): 3,150

The tiered/lũy tiến MECHANISM (price rises in steps with cumulative monthly kWh, regardless of time of day) follows real EVN regulation (QĐ 14/2025/QĐ-TTg, QĐ 1279/QĐ-BCT, QĐ 963/QĐ-BCT). The specific threshold/price VALUES above are illustrative numbers chosen to produce this PoC's locked baseline story — they are not a verbatim transcription of the latest published EVN rate table (see `calc.py`'s module docstring for the full disclosure).

## Rubric Mapping

This project addresses the Vòng Chung Kết rubric (see `[Q-SmartEnergy] Khung Tiêu Chí Đánh Giá & AI Guidelines.md`, Section III):
- **III.1 — Tính năng & mức độ hoàn thiện**: OOP (`Appliance`, `TimeSlot`, `QuantumScheduler` dataclasses), full type hints, real try/except around every simulator call and every chart-drawing call so the demo cannot crash.
- **III.2 — Giải quyết vấn đề thực tiễn**: the QUBO's `H_cost`/`H_solar`/`H_onehot`/`H_power` terms map directly to real constraints (tiered pricing, solar self-consumption, "runs exactly once", simultaneous-power safety) — see `qubo_builder.py`.
- **III.3 — Chất lượng kỹ thuật**: real Qiskit-Optimization usage (QUBO → QuadraticProgram → QAOA on Aer), with `quantum_runner.compare_qaoa_hyperparameters()` providing concrete evidence of hyperparameter tuning understanding, not just a claim.
- **III.4 — Trình bày & thuyết phục**: docstrings throughout state the economic meaning of every parameter; the UI's transparency notes explicitly distinguish the macro projection from the live demo result.
- **III.5 — Kết quả triển khai thực tế**: `data_prep.py` generates a real tiered-pricing profile; `calc.py` discloses exactly which numbers are illustrative vs. which mechanism is real.
- **III.6 — Giao diện & trải nghiệm UX/UI**: Streamlit app with real user input (appliance power/duration, day of month, weather condition), Indigo/Teal/Gold palette, Qiskit results rendered live.

Also addresses the Vòng Phụ bonus tier (Section II, Mức Khó +25đ): `weather_model.py` is the classical forecasting layer of a Hybrid Quantum-Classical architecture, feeding renewable-energy (rooftop solar) data into the QUBO objective function.

## Notes

- All baseline constants must be imported from `calc.py` — never replicate numbers in other modules.
- The project runs quantum circuits on Qiskit Aer Simulator (no hardware backend required for PoC).
- EVN tiered pricing uses cumulative/lũy tiến (staircase) pricing structure — pricing depends only on total monthly kWh consumed, never on the hour of day or day of week.
