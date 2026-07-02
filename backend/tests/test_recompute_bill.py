"""Tests for POST /recompute-bill — bill follows actual usage (fixed-hour edits)."""


def _flex_schedule(client, headers):
    appliances = client.get("/appliances", headers=headers).json()
    return {a["name"]: (a["candidate_hours"][0] if a["candidate_hours"] else 0)
            for a in appliances if a["is_flexible"]}


def test_recompute_bill_returns_fields(client, auth_headers):
    headers = auth_headers("rbuser1")
    schedule = _flex_schedule(client, headers)
    r = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny", "schedule": schedule,
              "fixed_hours": {"Tủ lạnh": list(range(24)), "Tivi": [19, 20, 21, 22]}},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bill_before_vnd"] >= data["bill_after_vnd"]
    assert data["savings_percent"] >= 0
    assert data["monthly_kwh"] > 0


def test_recompute_bill_fewer_hours_lowers_bill(client, auth_headers):
    headers = auth_headers("rbuser2")
    schedule = _flex_schedule(client, headers)
    full = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny", "schedule": schedule,
              "fixed_hours": {"Tủ lạnh": list(range(24)), "Tivi": [18, 19, 20, 21]}},
        headers=headers,
    ).json()
    fewer = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny", "schedule": schedule,
              "fixed_hours": {"Tủ lạnh": list(range(12)), "Tivi": []}},
        headers=headers,
    ).json()
    # Turning appliances off (fewer ON hours) lowers real consumption and the bill.
    assert fewer["bill_after_vnd"] < full["bill_after_vnd"]
    assert fewer["monthly_kwh"] < full["monthly_kwh"]


def test_recompute_bill_requires_auth(client):
    r = client.post("/recompute-bill", json={"day_of_month": 9, "weather_condition": "sunny",
                                             "schedule": {}, "fixed_hours": {}})
    assert r.status_code == 401


def test_recompute_bill_hour_out_of_range_rejected(client, auth_headers):
    """A schedule hour outside 0-23 must 422, not silently wrap %24 into a wrong bill (bug #7)."""
    headers = auth_headers("rbuser_oob")
    schedule = _flex_schedule(client, headers)
    assert schedule, "expected at least one flexible appliance seeded"
    name = next(iter(schedule))
    schedule[name] = 99
    r = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny", "schedule": schedule, "fixed_hours": {}},
        headers=headers,
    )
    assert r.status_code == 422


def test_recompute_bill_hour_outside_candidate_hours_rejected(client, auth_headers):
    """A schedule hour valid (0-23) but NOT in the appliance's candidate_hours must 422 —
    it wouldn't reflect a schedule the optimizer could actually produce (bug #7)."""
    headers = auth_headers("rbuser_cand")
    appliances = client.get("/appliances", headers=headers).json()
    flex = next((a for a in appliances if a["is_flexible"] and a["candidate_hours"]), None)
    assert flex is not None, "expected a flexible appliance with candidate_hours"
    bad_hour = next(h for h in range(24) if h not in flex["candidate_hours"])
    r = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny",
              "schedule": {flex["name"]: bad_hour}, "fixed_hours": {}},
        headers=headers,
    )
    assert r.status_code == 422


def test_recompute_bill_valid_hours_still_ok(client, auth_headers):
    """Regression guard: the new validation must not reject legitimate schedules."""
    headers = auth_headers("rbuser_ok")
    schedule = _flex_schedule(client, headers)
    r = client.post(
        "/recompute-bill",
        json={"day_of_month": 9, "weather_condition": "sunny", "schedule": schedule, "fixed_hours": {}},
        headers=headers,
    )
    assert r.status_code == 200
