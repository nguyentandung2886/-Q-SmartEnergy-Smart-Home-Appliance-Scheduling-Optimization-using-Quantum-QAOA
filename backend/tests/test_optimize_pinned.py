"""Tests for POST /optimize pinned_schedule parameter."""


def test_pinned_appliance_fixed_in_result(client, auth_headers):
    headers = auth_headers("pinuser1")
    appliances = client.get("/appliances", headers=headers).json()
    target = next(a for a in appliances if a["is_flexible"] and a["candidate_hours"])
    pin_hour = target["candidate_hours"][0]
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
              "pinned_schedule": {target["name"]: pin_hour}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert target["name"] in data["schedule"]
    assert data["schedule"][target["name"]] == pin_hour


def test_pinned_empty_dict_behaves_same_as_omitting(client, auth_headers):
    headers = auth_headers("pinuser2")
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "pinned_schedule": {}},
        headers=headers,
    )
    assert response.status_code == 200


def test_pinned_invalid_hour_returns_422(client, auth_headers):
    headers = auth_headers("pinuser3")
    appliances = client.get("/appliances", headers=headers).json()
    target = next(a for a in appliances if a["is_flexible"] and a["candidate_hours"])
    invalid_hour = next(h for h in range(24) if h not in target["candidate_hours"])
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
              "pinned_schedule": {target["name"]: invalid_hour}},
        headers=headers,
    )
    assert response.status_code == 422
