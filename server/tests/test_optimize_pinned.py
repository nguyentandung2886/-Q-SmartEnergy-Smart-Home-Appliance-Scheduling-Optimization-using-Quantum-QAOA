"""Tests for POST /optimize pinned_schedule parameter."""


def test_pinned_appliance_fixed_in_result(client, auth_headers):
    """Pinned appliance must appear in result.schedule at the pinned hour."""
    headers = auth_headers("pinuser1")
    # Máy giặt has candidate_hours=(9, 14) in the default seed — pin to 14
    response = client.post(
        "/optimize",
        json={
            "day_of_month": 9,
            "weather_condition": "sunny",
            "use_quantum": False,
            "pinned_schedule": {"Máy giặt": 14},
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Máy giặt" in data["schedule"]
    assert data["schedule"]["Máy giặt"] == 14


def test_pinned_empty_dict_behaves_same_as_omitting(client, auth_headers):
    """pinned_schedule={} must not crash and must return 200."""
    headers = auth_headers("pinuser2")
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "pinned_schedule": {}},
        headers=headers,
    )
    assert response.status_code == 200


def test_pinned_invalid_hour_returns_422(client, auth_headers):
    """Pinning to an hour outside candidate_hours must return 422."""
    headers = auth_headers("pinuser3")
    # Máy giặt candidate_hours=(9, 14) — hour 3 is invalid
    response = client.post(
        "/optimize",
        json={
            "day_of_month": 9,
            "weather_condition": "sunny",
            "pinned_schedule": {"Máy giặt": 3},
        },
        headers=headers,
    )
    assert response.status_code == 422
