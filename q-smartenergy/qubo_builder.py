"""
QUBO (Quadratic Unconstrained Binary Optimization) Builder for Q-SmartEnergy.

Input:
  - Prepared appliance and solar data (from data_prep.py)
  - EVN tiered pricing structure (from calc.py)
  - Time slot discretization (hours or time steps)

Output:
  - QUBO matrix (binary quadratic form) representing the optimization problem
  - Penalty weights for hard constraints (tier jumps, appliance deadlines, etc.)
  - Mapping between QUBO variables and actual appliance scheduling decisions

Economic/Physical Meaning:
  - Encodes two competing objectives: avoid EVN tier jumps + maximize self-consumption
  - Quadratic penalties enforce appliance timing constraints and physical limits
  - QUBO form is standard input for quantum annealers (QAOA, D-Wave, etc.)

Rubric Mapping:
  - III.3 (Technical Quality): Correct QUBO formulation, penalty weight tuning
  - III.6 (Algorithm Correctness): QUBO accurately models the economic problem
  - III.2 (Quantum Computing): Proper quadratic encoding for quantum solvers
"""


def build_qubo() -> None:
    """Stub for Task 3 implementation."""
    raise NotImplementedError("Task 3 will implement QUBO builder logic")
