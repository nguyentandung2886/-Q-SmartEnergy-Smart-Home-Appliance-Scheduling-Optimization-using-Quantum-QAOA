"""Tests for POST /optimize and GET /schedules. QAOA tests are slow — run them last."""

from api.optimize_router import _estimate_user_monthly_kwh
from core.qubo_builder import Appliance


def test_estimate_user_monthly_kwh_matches_frontend_formula():
    """Per-user monthly kWh (bug #4) = Σ power_w/1000 * duration_hours * 30, matching
    AppData.jsx. power_w already includes quantity here."""
    apps = [
        Appliance(name="A", power_w=1000, duration_hours=2, candidate_hours=(7, 13)),
        Appliance(name="B", power_w=500, duration_hours=1, candidate_hours=(), is_flexible=False),
    ]
    # 1000/1000*2*30 + 500/1000*1*30 = 60 + 15 = 75
    assert _estimate_user_monthly_kwh(apps) == 75.0


def test_estimate_differs_for_users_with_different_total_power():
    """Two users with different appliance totals feed a different tier signal into the QUBO."""
    light = [Appliance(name="A", power_w=200, duration_hours=1, candidate_hours=(7, 13))]
    heavy = [Appliance(name="A", power_w=3000, duration_hours=4, candidate_hours=(7, 13))]
    assert _estimate_user_monthly_kwh(heavy) > _estimate_user_monthly_kwh(light)


def test_optimize_requires_auth(client):
    response = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"})
    assert response.status_code == 401


def test_optimize_returns_valid_schedule_and_charts(client, auth_headers):
    headers = auth_headers("optuser")
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["solver_used"] in ("qaoa", "classical_bruteforce")
    assert data["bill_before_vnd"] > data["bill_after_vnd"]
    assert data["savings_percent"] > 0
    assert data["gantt_chart_png"] is not None
    assert data["bill_chart_png"] is not None


def test_optimize_fixed_windows_cover_fixed_appliances_with_real_windows(client, auth_headers):
    headers = auth_headers("dispuser")
    appliances = client.get("/appliances", headers=headers).json()
    data = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False},
        headers=headers,
    ).json()
    fw = data["fixed_windows"]
    flexible_names = {a["name"] for a in appliances if a["is_flexible"]}
    # Every FIXED appliance has at least one usage window; flexible ones are not here.
    for a in appliances:
        if a["is_flexible"]:
            assert a["name"] not in fw
        else:
            assert a["name"] in fw
            assert len(fw[a["name"]]) >= 1
            for start, length in fw[a["name"]]:
                assert 0 <= start <= 23 and length >= 1 and start + length <= 24
    # Fan runs in multiple disjoint windows (not one continuous block).
    assert len(fw["Quạt điện"]) >= 2
    assert fw["Tủ lạnh"] == [[0, 24]]  # fridge runs all day


def test_optimize_saves_to_schedules_history(client, auth_headers):
    headers = auth_headers("histuser")
    client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers)
    response = client.get("/schedules", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_optimize_with_all_appliances_deleted_does_not_crash(client, auth_headers):
    """If user deletes all flexible appliances, /optimize must still return 200
    (empty schedule, no QUBO variables to solve — existing fallback handles it)."""
    headers = auth_headers("noflexuser")
    appliances = client.get("/appliances", headers=headers).json()
    for a in appliances:
        if a["is_flexible"]:
            client.delete(f"/appliances/{a['id']}", headers=headers)
    response = client.post(
        "/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["schedule"] == {}


def test_bill_is_personalized_to_user_appliances(client, auth_headers):
    """User A (has all 12 appliances) vs User B (has deleted all appliances) must have
    different bill values — confirms per-user billing, not a static global number."""
    headers_a = auth_headers("billusera")
    headers_b = auth_headers("billuserb")
    # Delete all of B's appliances to make B's appliance list empty (total_monthly_kwh = 0)
    appliances_b = client.get("/appliances", headers=headers_b).json()
    for a in appliances_b:
        client.delete(f"/appliances/{a['id']}", headers=headers_b)

    result_a = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers_a).json()
    result_b = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers_b).json()
    assert result_a["bill_before_vnd"] != result_b["bill_before_vnd"]
