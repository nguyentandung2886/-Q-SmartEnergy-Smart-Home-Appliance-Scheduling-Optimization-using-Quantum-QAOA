"""Multi-objective weight sliders on /optimize (w_cost / w_comfort / w_solar).

These lock the end-to-end wiring OptimizeRequest -> _prepare_run -> QuantumScheduler -> build_qubo:
  - omitting the weights reproduces the legacy schedule exactly (additive, non-breaking);
  - a high comfort weight pulls every flexible appliance to its FIRST (convenient) candidate hour,
    and demonstrably moves at least one that the cost/solar optimum had placed elsewhere;
  - out-of-range weights are rejected at the schema boundary (422), not silently clamped, so a
    pathological weight can never overwhelm the lambda one-hot/power constraints.
use_quantum=False so the solver is the deterministic brute-force global optimum (no QAOA noise).
"""


def _flexible_candidates(client, headers):
    apps = client.get("/appliances", headers=headers).json()
    return {
        a["name"]: a["candidate_hours"]
        for a in apps
        if a["is_flexible"] and len(a["candidate_hours"]) >= 2
    }


def _optimize(client, headers, **extra):
    body = {"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False, **extra}
    return client.post("/optimize", json=body, headers=headers)


def test_omitting_weights_matches_default_weights(client, auth_headers):
    """No weight fields == explicitly passing (1, 0, 1): identical schedule + energy (regression)."""
    headers = auth_headers("w_regress")
    base = _optimize(client, headers).json()
    explicit = _optimize(client, headers, w_cost=1.0, w_comfort=0.0, w_solar=1.0).json()
    assert explicit["schedule"] == base["schedule"]
    assert explicit["energy"] == base["energy"]


def test_high_comfort_pulls_all_flexible_to_first_candidate(client, auth_headers):
    """Raising 'Tiện lợi' high schedules every flexible appliance at its first candidate hour,
    and at least one differs from the plain cost/solar optimum — proving comfort moved the plan."""
    headers = auth_headers("w_comfort")
    flex = _flexible_candidates(client, headers)
    assert flex, "seeded household must have flexible appliances with >=2 candidate hours"

    base = _optimize(client, headers).json()["schedule"]
    comfort = _optimize(client, headers, w_comfort=10.0).json()["schedule"]

    for name, cands in flex.items():
        assert comfort[name] == cands[0], f"{name} should sit at its first candidate under high comfort"
    assert any(base[name] != cands[0] for name, cands in flex.items()), (
        "test is vacuous unless the default optimum placed at least one appliance off its first hour"
    )


def test_weight_out_of_range_is_rejected(client, auth_headers):
    """A weight above the allowed ceiling is a 422 (schema validation), never silently accepted —
    keeps w_comfort*COMFORT_UNIT_VND*hours safely below the lambda one-hot/power penalties."""
    headers = auth_headers("w_bounds")
    assert _optimize(client, headers, w_comfort=999.0).status_code == 422
    assert _optimize(client, headers, w_cost=-1.0).status_code == 422


def test_weights_do_not_rescue_a_power_overloaded_appliance(client, auth_headers):
    """Audit guard: an appliance drawing 6000W (> the 5000W household threshold) at every candidate
    hour has no feasible slot, so /optimize returns 422 — NOT a 500 crash. Objective weights only
    scale H_cost/H_solar/H_comfort (all « lambda_power), so even a maxed-out comfort weight cannot
    buy back the power constraint: it stays 422."""
    headers = auth_headers("w_overload")
    client.post(
        "/appliances",
        json={"name": "Máy quá tải", "power_w": 6000, "duration_hours": 1,
              "candidate_hours": [10, 14], "is_flexible": True},
        headers=headers,
    )
    assert _optimize(client, headers).status_code == 422
    assert _optimize(client, headers, w_comfort=10.0, w_cost=10.0).status_code == 422
