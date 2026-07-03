"""C7 regression lock: /optimize and /qaoa-analysis build the QUBO through the SAME
_prepare_run helper, so for identical input they must report the same problem size
(num_variables) and the same global optimum (energy). Before C7, /qaoa-analysis used a
separate build that ignored coerce/duration_overrides/pinned/business-TOU/threshold, so its
num_variables/energy could diverge from a real /optimize run.

/optimize does not return num_variables directly; the cross-checks used here:
  - energy:        /optimize(use_quantum=False).energy == /qaoa-analysis.brute_force_energy
                   (both = the deterministic brute-force optimum of the same Q).
  - num_variables: driven by the same appliance set, verified against the seeded count and
                   its change under pinning (a pinned appliance drops out of the QUBO).
"""
import pytest


def _flexible_appliances(client, headers):
    apps = client.get("/appliances", headers=headers).json()
    return [a for a in apps if a["is_flexible"] and len(a["candidate_hours"]) >= 2]


def test_optimize_and_qaoa_analysis_same_energy_with_duration_overrides(client, auth_headers):
    headers = auth_headers("c7_energy")
    flex = _flexible_appliances(client, headers)
    assert len(flex) >= 1
    # Override a real flexible appliance's duration: this feeds energy_kwh into the QUBO. Before
    # C7, /qaoa-analysis ignored duration_overrides, so its Q (hence brute_force_energy) differed.
    payload = {
        "day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
        "duration_overrides": {flex[0]["name"]: 1.5},
    }
    opt = client.post("/optimize", json=payload, headers=headers)
    ana = client.post("/qaoa-analysis", json=payload, headers=headers)
    assert opt.status_code == 200 and ana.status_code == 200
    opt, ana = opt.json(), ana.json()

    # Both endpoints build the QUBO via the same _prepare_run -> identical variable count.
    assert opt["num_variables"] == ana["num_variables"]
    # Same Q on both sides -> same brute-force global optimum, exactly.
    assert opt["energy"] == pytest.approx(ana["brute_force_energy"])


def test_optimize_and_qaoa_analysis_same_variables_when_pinned(client, auth_headers):
    headers = auth_headers("c7_pin")
    flex = _flexible_appliances(client, headers)
    assert len(flex) >= 2  # need at least one appliance left in the QUBO after pinning one
    pin_name = flex[0]["name"]
    pin_hour = flex[0]["candidate_hours"][0]
    payload = {
        "day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
        "pinned_schedule": {pin_name: pin_hour},
    }
    opt = client.post("/optimize", json=payload, headers=headers)
    ana = client.post("/qaoa-analysis", json=payload, headers=headers)
    assert opt.status_code == 200 and ana.status_code == 200
    opt, ana = opt.json(), ana.json()

    # Pinning removes that appliance's variables from the QUBO. Before C7, /qaoa-analysis ignored
    # pinned_schedule and would report a higher count than /optimize actually solved — so assert
    # the two responses agree directly, and that pinning did shrink the problem below the unpinned
    # seeded size (3 flexible x 2 candidate hours = 6).
    assert opt["num_variables"] == ana["num_variables"]
    assert opt["num_variables"] < 6
    # And both still agree on the optimum energy of the (reduced) shared Q.
    assert opt["energy"] == pytest.approx(ana["brute_force_energy"])
