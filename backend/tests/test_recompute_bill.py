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
