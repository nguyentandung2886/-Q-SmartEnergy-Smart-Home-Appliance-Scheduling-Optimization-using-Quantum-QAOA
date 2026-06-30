"""Test for POST /qaoa-analysis — surfaces hyperparameter-sweep evidence (III.3)."""


def test_qaoa_analysis_returns_configs_and_qubit_count(client, auth_headers):
    headers = auth_headers("qauser1")
    response = client.post(
        "/qaoa-analysis",
        json={"day_of_month": 9, "weather_condition": "sunny"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Default seeded household has 3 flexible appliances x 2 candidate hours = 6 binary vars.
    assert data["num_appliances"] >= 1
    assert data["num_variables"] >= 1
    assert data["brute_force_energy"] is not None
    assert len(data["configs"]) == 4
    for cfg in data["configs"]:
        assert cfg["reps"] >= 1
        assert cfg["maxiter"] >= 1
        assert cfg["runtime_seconds"] >= 0
        # Each config either produced an energy or recorded an error (never silently empty).
        assert cfg["energy"] is not None or cfg["error"] is not None


def test_qaoa_analysis_requires_auth(client):
    response = client.post("/qaoa-analysis", json={"day_of_month": 9, "weather_condition": "sunny"})
    assert response.status_code == 401
