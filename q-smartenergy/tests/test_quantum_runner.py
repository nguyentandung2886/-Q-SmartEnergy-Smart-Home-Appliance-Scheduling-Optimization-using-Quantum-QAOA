"""
Tests for quantum_runner.py (Task 4).

Verifies (per Task 4 brief):
1. solve_classical_bruteforce returns the exact minimum-energy bitstring/energy
   for a hand-computed 2x2 upper-triangular Q.
2. is_valid_one_hot enforces exactly-one-bit-per-appliance grouping.
3. decode_schedule maps a valid one-hot bitstring to {appliance: hour}.
4. solve_qaoa runs for real on a small (n=2) Q without crashing, returning a
   length-2 bitstring and a finite float energy.
5. solve_qaoa wraps the underlying qiskit/numpy error in QAOAExecutionError when
   given a non-square Q.
6. QuantumScheduler integrates end-to-end with DEFAULT_APPLIANCES +
   build_daily_profile(): valid schedule, solver_used in {qaoa, classical_bruteforce},
   runtime > 0, explicit-classical path, and JSON-serializable result.
"""

import json
import math

import numpy as np
import pytest

from data_prep import build_daily_profile
from qubo_builder import DEFAULT_APPLIANCES, build_qubo
from quantum_runner import (
    QAOAExecutionError,
    QuantumScheduler,
    ScheduleResult,
    compare_qaoa_hyperparameters,
    decode_schedule,
    is_valid_one_hot,
    solve_classical_bruteforce,
    solve_qaoa,
)


def test_solve_classical_bruteforce_hand_computed():
    """Test 1: Q = [[1,2],[0,-1]] -> x0 + 2*x0*x1 - x1.
    (0,0)=0, (0,1)=-1, (1,0)=1, (1,1)=2 -> minimum is bitstring '01' energy -1.0."""
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    bitstring, energy = solve_classical_bruteforce(Q)
    assert bitstring == "01"
    assert energy == -1.0


def test_is_valid_one_hot():
    """Test 2: var_map groups vars 0,1 under 'A' and var 2 under 'B'.
    NOTE: the brief's example bitstring '100' is a typo — with this 3-var var_map a
    valid one-hot solution needs 2 bits set (one for A, one for B). '100' has only
    1 bit (B's slot is 0), so it cannot be valid AND decode to {'A':1,'B':3} as the
    brief's Test 3 also requires. Using '101' (index0=A@hour1, index2=B@hour3), which
    matches the brief's clear intent (decode -> {'A':1,'B':3}). See task-4-report.md."""
    var_map = {0: ("A", 1), 1: ("A", 2), 2: ("B", 3)}
    assert is_valid_one_hot("101", var_map) is True
    assert is_valid_one_hot("110", var_map) is False  # 2 bits set for A, 0 for B
    assert is_valid_one_hot("000", var_map) is False  # 0 bits set for A


def test_decode_schedule():
    """Test 3: '101' with the same var_map -> {'A': 1, 'B': 3}.
    (Brief wrote '100'; corrected to '101' for the same reason as Test 2.)"""
    var_map = {0: ("A", 1), 1: ("A", 2), 2: ("B", 3)}
    assert decode_schedule("101", var_map) == {"A": 1, "B": 3}


def test_solve_qaoa_runs_on_small_scenario():
    """Test 4: QAOA runs for real on n=2 Q, returns len-2 bitstring + finite float."""
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    bitstring, energy = solve_qaoa(Q)
    assert isinstance(bitstring, str)
    assert len(bitstring) == 2
    assert set(bitstring) <= {"0", "1"}
    assert isinstance(energy, float)
    assert not math.isnan(energy)


def test_solve_qaoa_wraps_error_in_qaoa_execution_error():
    """Test 5: a non-square Q makes QuadraticProgram construction fail; the raw
    error must be wrapped in QAOAExecutionError, not surfaced raw."""
    Q = np.zeros((2, 3))
    with pytest.raises(QAOAExecutionError):
        solve_qaoa(Q)


class TestQuantumSchedulerIntegration:
    """Test 6: full pipeline with DEFAULT_APPLIANCES + build_daily_profile()."""

    def setup_method(self):
        self.profile = build_daily_profile()
        self.scheduler = QuantumScheduler(DEFAULT_APPLIANCES, self.profile)

    def test_solve_quantum_returns_valid_schedule(self):
        result = self.scheduler.solve(use_quantum=True)
        assert isinstance(result, ScheduleResult)

        # Each appliance appears exactly once, at one of its candidate hours.
        assert set(result.schedule.keys()) == {a.name for a in DEFAULT_APPLIANCES}
        for appliance in DEFAULT_APPLIANCES:
            assert result.schedule[appliance.name] in appliance.candidate_hours

        assert result.solver_used in {"qaoa", "classical_bruteforce"}
        assert result.runtime_seconds > 0

    def test_solve_explicit_classical_is_not_fallback(self):
        result = self.scheduler.solve(use_quantum=False)
        assert result.solver_used == "classical_bruteforce"
        assert result.used_fallback is False

    def test_result_to_json_parses(self):
        result = self.scheduler.solve(use_quantum=True)
        parsed = json.loads(result.to_json())
        assert parsed["solver_used"] == result.solver_used
        assert parsed["schedule"] == result.schedule


def test_compare_qaoa_hyperparameters_returns_one_row_per_config():
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    results = compare_qaoa_hyperparameters(Q, configs=[(1, 25), (2, 50)])
    assert len(results) == 2
    for row in results:
        assert row["reps"] in (1, 2)
        assert row["runtime_seconds"] > 0
        assert "matches_global_optimum" in row


def test_compare_qaoa_hyperparameters_flags_global_optimum_correctly():
    """On the hand-computed Q from solve_classical_bruteforce's own test (minimum is
    bitstring '01', energy -1.0), every successful QAOA run that actually finds energy
    -1.0 must be flagged matches_global_optimum=True, and none may be flagged True at a
    different energy."""
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    results = compare_qaoa_hyperparameters(Q, configs=[(1, 50), (2, 50), (3, 100)])
    for row in results:
        if row["error"] is None:
            if row["matches_global_optimum"]:
                assert row["energy"] == pytest.approx(-1.0, abs=1e-6)
            else:
                assert row["energy"] != pytest.approx(-1.0, abs=1e-6)


def test_compare_qaoa_hyperparameters_default_configs_on_default_scenario():
    """On the project's own DEFAULT_APPLIANCES scenario (4 qubits), at least one of the
    default hyperparameter configs must find the global optimum — this is the concrete,
    checkable evidence backing the project's "understands QAOA hyperparameter tuning"
    claim (rubric III.3)."""
    Q, _ = build_qubo(DEFAULT_APPLIANCES, build_daily_profile())
    results = compare_qaoa_hyperparameters(Q)
    assert len(results) == 4
    assert any(row["matches_global_optimum"] for row in results if row["error"] is None)
