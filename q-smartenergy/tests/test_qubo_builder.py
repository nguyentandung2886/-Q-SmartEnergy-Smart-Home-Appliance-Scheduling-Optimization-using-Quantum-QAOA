"""
Tests for qubo_builder.py.

Verifies (per Task 3 brief):
1. Appliance.energy_kwh property computes power_w/1000 * duration_hours.
2. build_qubo() on DEFAULT_APPLIANCES + build_daily_profile() returns a 4x4
   upper-triangular Q and a 4-entry var_map with the exact expected mapping.
3. One-hot penalty dominance: brute-forcing all 2^4 binary assignments, every
   valid (one-hot per appliance) assignment scores lower than every invalid one
   by a large margin (proves lambda_onehot overpowers the cost/reward terms).
4. Power-threshold penalty: two appliances sharing a candidate hour whose combined
   power exceeds power_threshold_w get a >= lambda_power off-diagonal entry, while
   a non-overlapping pair gets 0.
5. build_qubo() raises ValueError if any candidate hour is outside 0-23.
"""

import itertools

import numpy as np
import pytest

from data_prep import build_daily_profile
from qubo_builder import (
    Appliance,
    TimeSlot,
    DEFAULT_APPLIANCES,
    build_qubo,
)


def evaluate(Q: np.ndarray, x) -> float:
    """Evaluate x^T Q x under the upper-triangular convention used by build_qubo:
    diagonal Q[j,j] carries the linear coefficient (since x_j^2 = x_j) and
    Q[j,j'] (j<j') carries the quadratic coefficient. Lower (j>j') entries are 0."""
    x = np.asarray(x, dtype=float)
    return float(x @ Q @ x)


def test_energy_kwh_property():
    appliance = Appliance("X", power_w=500, duration_hours=2, candidate_hours=(7, 13))
    assert appliance.energy_kwh == 1.0


def test_timeslot_dataclass_fields():
    slot = TimeSlot(hour=12, price_per_kwh=2700.0, solar_kwh=2.4)
    assert slot.hour == 12
    assert slot.price_per_kwh == 2700.0
    assert slot.solar_kwh == 2.4


class TestBuildQuboShapeAndVarMap:
    """Test 2: shape, var_map content, upper-triangular property."""

    def setup_method(self):
        self.profile = build_daily_profile()
        self.Q, self.var_map = build_qubo(DEFAULT_APPLIANCES, self.profile)

    def test_shape_is_4x4(self):
        assert self.Q.shape == (4, 4)

    def test_var_map_exact(self):
        assert self.var_map == {
            0: ("Máy giặt", 7),
            1: ("Máy giặt", 13),
            2: ("Bình nước nóng", 6),
            3: ("Bình nước nóng", 12),
        }

    def test_upper_triangular(self):
        n = self.Q.shape[0]
        for j in range(n):
            for jp in range(n):
                if j > jp:
                    assert self.Q[j, jp] == 0.0, f"Q[{j},{jp}] must be 0 (upper-tri)"


def test_onehot_penalty_dominance():
    """Test 3: every valid one-hot assignment beats every invalid one by a wide margin."""
    profile = build_daily_profile()
    Q, var_map = build_qubo(DEFAULT_APPLIANCES, profile)

    # Variables 0,1 belong to appliance A (Máy giặt); 2,3 to appliance B (Bình nước nóng).
    def is_valid(x):
        return (x[0] + x[1] == 1) and (x[2] + x[3] == 1)

    valid_scores = []
    invalid_scores = []
    for bits in itertools.product([0, 1], repeat=4):
        score = evaluate(Q, bits)
        if is_valid(bits):
            valid_scores.append(score)
        else:
            invalid_scores.append(score)

    assert len(valid_scores) == 4
    assert len(invalid_scores) == 12

    margin = min(invalid_scores) - max(valid_scores)
    assert margin >= 100_000, (
        f"one-hot penalty too weak: worst valid={max(valid_scores)}, "
        f"best invalid={min(invalid_scores)}, margin={margin}"
    )


def test_power_threshold_penalty():
    """Test 4: overlapping-hour over-threshold pair penalized; non-overlapping pair not."""
    profile = build_daily_profile()
    # Two 3000W appliances both able to run at hour 10 -> 6000W > 5000W default threshold.
    appliances = [
        Appliance(name="A", power_w=3000, duration_hours=1, candidate_hours=(10, 14)),
        Appliance(name="B", power_w=3000, duration_hours=1, candidate_hours=(10, 16)),
    ]
    Q, var_map = build_qubo(appliances, profile)

    # var_map: 0=(A,10) 1=(A,14) 2=(B,10) 3=(B,16)
    inv = {v: k for k, v in var_map.items()}
    j_a10 = inv[("A", 10)]
    j_b10 = inv[("B", 10)]
    j_a14 = inv[("A", 14)]
    j_b16 = inv[("B", 16)]

    # Overlapping over-threshold pair (A,10)&(B,10): penalized, upper-triangular slot.
    lo, hi = sorted((j_a10, j_b10))
    assert Q[lo, hi] >= 1_000_000.0

    # Non-overlapping pair (A,14)&(B,16): different hours -> no power penalty.
    lo2, hi2 = sorted((j_a14, j_b16))
    assert Q[lo2, hi2] == 0.0


def test_invalid_hour_raises():
    """Test 5: candidate hour outside 0-23 raises ValueError."""
    profile = build_daily_profile()
    bad = [
        Appliance(name="Bad", power_w=500, duration_hours=1, candidate_hours=(7, 25)),
    ]
    with pytest.raises(ValueError):
        build_qubo(bad, profile)
