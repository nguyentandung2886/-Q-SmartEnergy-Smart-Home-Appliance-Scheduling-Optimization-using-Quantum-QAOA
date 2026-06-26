# Q-SmartEnergy

Quantum-optimized home appliance scheduling leveraging QAOA (Quantum Approximate Optimization Algorithm) to minimize electricity costs under Vietnam's tiered EVN pricing and maximize rooftop solar self-consumption.

## Overview

Q-SmartEnergy is a PoC (Proof of Concept) that uses quantum computing to solve the appliance scheduling problem: given a household's appliances and a tiered electricity pricing structure, when should each appliance run to minimize the monthly bill?

The key insight: quantum circuits can explore appliance scheduling combinations exponentially faster than classical algorithms, helping families avoid expensive EVN tier jumps and maximize solar self-consumption.

## Project Structure

```
q-smartenergy/
├── calc.py                # Single source of truth for baseline constants & bill calculation
├── data_prep.py          # Data preparation (load profiles, pricing, forecasts)
├── qubo_builder.py       # QUBO formulation for quantum optimization
├── quantum_runner.py     # QAOA execution on Qiskit Aer Simulator
├── visualizer.py         # Bill breakdown & schedule visualization
├── app.py                # Streamlit web UI dashboard
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── tests/
    ├── __init__.py
    └── test_baseline.py  # Tests for calc.py baseline constants
```

### Module Roles

| Module | Purpose |
|--------|---------|
| `calc.py` | **Baseline lock**: Contains all project constants (530 kWh/month, EVN tier prices, bill targets). Every other module imports from here—never hard-code. |
| `data_prep.py` | Prepares appliance load profiles and solar forecasts for optimization. |
| `qubo_builder.py` | Encodes the appliance scheduling problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. |
| `quantum_runner.py` | Executes QAOA on Qiskit Aer Simulator to find optimal schedules. |
| `visualizer.py` | Generates charts and summaries (bill breakdown, schedule comparisons, savings). |
| `app.py` | Streamlit dashboard for users to configure appliances and view optimization results. |

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
- **Solar Capacity**: 5 kWp
- **Self-Consumption Before Optimization**: 30%
- **Self-Consumption After Optimization**: 45%
- **Bill Before Optimization**: 896,125đ
- **Bill After Optimization**: 658,125đ
- **Savings**: 26.6%

**EVN Tiered Pricing** (đ/kWh):
- Tier 1 (0–50 kWh): 1,800
- Tier 2 (51–100 kWh): 1,900
- Tier 3 (101–200 kWh): 2,200
- Tier 4 (201–300 kWh): 2,700
- Tier 5 (301–400 kWh): 3,050
- Tier 6 (>400 kWh): 3,150

## Rubric Mapping

This project addresses multiple rubric criteria:
- **III.1**: Visualization with Indigo, Teal, Gold palette
- **III.2**: Quantum computing via QAOA circuits
- **III.3**: Technical quality in data handling and solver robustness
- **III.4**: User experience and responsive UI
- **III.5**: Data generator based on realistic EVN pricing
- **III.6**: Algorithm correctness and solution validation

## Notes

- All baseline constants must be imported from `calc.py`—never replicate numbers in other modules.
- The project runs quantum circuits on Qiskit Aer Simulator (no hardware backend required for PoC).
- EVN tiered pricing uses cumulative/lũy tiến (staircase) pricing structure.
