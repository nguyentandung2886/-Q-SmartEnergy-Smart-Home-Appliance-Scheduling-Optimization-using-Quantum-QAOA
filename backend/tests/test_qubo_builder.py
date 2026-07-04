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
import pandas as pd
import pytest

from core.data_prep import build_daily_profile
from core.qubo_builder import (
    Appliance,
    TimeSlot,
    DEFAULT_APPLIANCES,
    COMFORT_UNIT_VND,
    build_qubo,
)


def _price_at(profile, hour: int) -> float:
    return float(profile.loc[profile["hour"] == hour, "price_per_kwh"].iloc[0])


def _solar_at(profile, hour: int) -> float:
    return float(profile.loc[profile["hour"] == hour, "solar_kwh"].iloc[0])


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


def test_appliance_is_flexible_defaults_to_true():
    """New is_flexible field must default to True so every existing Appliance
    construction (including DEFAULT_APPLIANCES) is unaffected by this change."""
    appliance = Appliance(name="Test", power_w=100, duration_hours=1, candidate_hours=(7, 13))
    assert appliance.is_flexible is True


def test_appliance_is_flexible_can_be_set_false():
    appliance = Appliance(
        name="Tủ lạnh", power_w=34, duration_hours=24, candidate_hours=(), is_flexible=False
    )
    assert appliance.is_flexible is False


# --- Multi-objective weights (w_cost / w_comfort / w_solar) ------------------
# Additive feature: default weights (1.0, 0.0, 1.0) must reproduce the legacy objective
# exactly (H_cost + H_solar, no comfort term). w_cost/w_solar scale the two objective axes;
# w_comfort adds a NEW penalty proportional to how far a candidate hour is from the
# appliance's FIRST (default-convenient) candidate hour. lambda_onehot/lambda_power are
# constraint weights and are never scaled by these.


def test_weight_kwargs_default_to_legacy_identity():
    """Not passing weights == passing (w_cost=1, w_comfort=0, w_solar=1): the defaults are the
    legacy objective, so every existing call is byte-identical (regression guard)."""
    profile = build_daily_profile()
    Q_default, _ = build_qubo(DEFAULT_APPLIANCES, profile)
    Q_explicit, _ = build_qubo(DEFAULT_APPLIANCES, profile, w_cost=1.0, w_comfort=0.0, w_solar=1.0)
    assert np.array_equal(Q_default, Q_explicit)


def test_w_cost_scales_only_the_cost_term():
    """Doubling w_cost adds exactly one more H_cost (= energy_kwh * price) to each diagonal,
    with w_solar/w_comfort neutralized so nothing else moves."""
    profile = build_daily_profile()
    app = Appliance("Solo", power_w=1000, duration_hours=1, candidate_hours=(9, 15))  # 1 kWh
    Q1, vm = build_qubo([app], profile, w_cost=1.0, w_solar=0.0, w_comfort=0.0)
    Q2, _ = build_qubo([app], profile, w_cost=2.0, w_solar=0.0, w_comfort=0.0)
    for j, (_name, hour) in vm.items():
        expected = _price_at(profile, hour)  # energy_kwh = 1.0
        assert Q2[j, j] - Q1[j, j] == pytest.approx(expected)
        assert expected > 0


def test_w_solar_scales_only_the_solar_credit():
    """Doubling w_solar adds one more H_solar (= -min(energy, solar) * price, a credit) to each
    diagonal; with w_cost=0 the diagonal is pure solar credit and moves down."""
    profile = build_daily_profile()
    app = Appliance("Solo", power_w=1000, duration_hours=1, candidate_hours=(9, 15))  # 1 kWh
    Q1, vm = build_qubo([app], profile, w_cost=0.0, w_solar=1.0, w_comfort=0.0)
    Q2, _ = build_qubo([app], profile, w_cost=0.0, w_solar=2.0, w_comfort=0.0)
    for j, (_name, hour) in vm.items():
        solar = _solar_at(profile, hour)
        expected = -min(1.0, solar) * _price_at(profile, hour)  # h_solar, <= 0
        assert Q2[j, j] - Q1[j, j] == pytest.approx(expected)
        assert expected <= 0
    # At least one midday candidate has solar, so the credit is a real (negative) lever.
    assert _solar_at(profile, 15) > 0


def test_w_comfort_penalizes_distance_from_first_candidate_hour():
    """H_comfort = w_comfort * COMFORT_UNIT_VND * |hour - first_candidate_hour|, added to the
    diagonal. The FIRST candidate hour (distance 0) gets no penalty; a later one gets a penalty
    proportional to its hour-distance. This is the only term w_comfort touches."""
    profile = build_daily_profile()
    app = Appliance("Solo", power_w=1000, duration_hours=1, candidate_hours=(8, 14))  # first=8
    Q0, vm = build_qubo([app], profile, w_comfort=0.0)
    Q1, _ = build_qubo([app], profile, w_comfort=1.0)
    inv = {v: k for k, v in vm.items()}
    j_first, j_far = inv[("Solo", 8)], inv[("Solo", 14)]
    # First candidate hour: zero distance -> unchanged by comfort.
    assert Q1[j_first, j_first] == pytest.approx(Q0[j_first, j_first])
    # Far candidate hour (distance 6): penalty = 1.0 * COMFORT_UNIT_VND * 6.
    added = Q1[j_far, j_far] - Q0[j_far, j_far]
    assert added == pytest.approx(COMFORT_UNIT_VND * 6)
    assert added > 0


def test_w_comfort_does_not_touch_onehot_or_power_penalties():
    """Comfort only shifts diagonal objective coefficients; the one-hot off-diagonal and the
    power off-diagonal penalties (lambda-scaled constraints) stay exactly as before."""
    profile = build_daily_profile()
    apps = [
        Appliance("A", power_w=3000, duration_hours=1, candidate_hours=(10, 14)),
        Appliance("B", power_w=3000, duration_hours=1, candidate_hours=(10, 16)),
    ]
    Q0, _ = build_qubo(apps, profile, w_comfort=0.0)
    Q1, _ = build_qubo(apps, profile, w_comfort=5.0)
    n = Q0.shape[0]
    for i in range(n):
        for k in range(i + 1, n):
            assert Q1[i, k] == Q0[i, k], f"off-diagonal ({i},{k}) must be untouched by w_comfort"


def test_high_comfort_makes_first_candidate_hour_the_optimum():
    """Behavioral: with comfort weighted high enough to outweigh the cost/solar spread, the
    brute-force optimum schedules the appliance at its first (convenient) candidate hour."""
    from core.quantum_runner import solve_classical_bruteforce, decode_schedule

    profile = build_daily_profile()
    app = Appliance("Solo", power_w=1000, duration_hours=1, candidate_hours=(8, 14))
    Q, vm = build_qubo([app], profile, w_comfort=10.0)
    bitstring, _ = solve_classical_bruteforce(Q)
    assert decode_schedule(bitstring, vm) == {"Solo": 8}


def _profile_with(prices: dict, solars: dict) -> pd.DataFrame:
    """A 24-row daily_profile with per-hour overrides (default price 2000đ, solar 0) — lets a test
    craft a time-varying (TOU-style) price/solar curve to isolate the cost vs solar tradeoff."""
    return pd.DataFrame({
        "hour": range(24),
        "solar_kwh": [solars.get(h, 0.0) for h in range(24)],
        "price_per_kwh": [prices.get(h, 2000.0) for h in range(24)],
    })


def test_cost_and_solar_weights_steer_the_schedule_oppositely():
    """Behavioral tradeoff on a crafted profile: hour 8 is cheap (1000đ) but sunless; hour 12 is
    pricey (3000đ) but fully solar-covered. Emphasizing cost picks the cheap gross-price hour;
    emphasizing solar picks the sunny hour. This is what the 'cost' vs 'solar' sliders do."""
    from core.quantum_runner import solve_classical_bruteforce, decode_schedule

    profile = _profile_with(prices={8: 1000.0, 12: 3000.0}, solars={12: 5.0})
    app = Appliance("Solo", power_w=1000, duration_hours=1, candidate_hours=(8, 12))  # 1 kWh

    Q_cost, vm = build_qubo([app], profile, w_cost=5.0, w_solar=1.0, w_comfort=0.0)
    assert decode_schedule(solve_classical_bruteforce(Q_cost)[0], vm) == {"Solo": 8}

    Q_solar, vm2 = build_qubo([app], profile, w_cost=1.0, w_solar=5.0, w_comfort=0.0)
    assert decode_schedule(solve_classical_bruteforce(Q_solar)[0], vm2) == {"Solo": 12}
