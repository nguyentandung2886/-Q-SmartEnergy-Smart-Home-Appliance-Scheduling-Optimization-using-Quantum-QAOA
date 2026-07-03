"""Tests for POST /forecast and /optimize duration_overrides (ML forecasting subsystem)."""
from db.models import BusinessProfile, User


def _make_business_user(db_session, uid: str, business_type: str) -> None:
    user = User(supabase_uid=uid, email=f"{uid}@test.local", role="business")
    db_session.add(user)
    db_session.flush()
    db_session.add(BusinessProfile(user_id=user.id, business_type=business_type))
    db_session.commit()


def test_forecast_returns_prediction_and_mae(client, auth_headers):
    headers = auth_headers("fcuser1")
    response = client.post(
        "/forecast",
        json={"jobs": {"Máy giặt": {"load_kg": 7, "program": "normal"}}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Máy giặt" in data
    assert data["Máy giặt"]["predicted_hours"] > 0
    assert data["Máy giặt"]["test_mae"] >= 0


def test_forecast_more_load_predicts_longer(client, auth_headers):
    headers = auth_headers("fcuser2")
    light = client.post("/forecast", json={"jobs": {"Máy giặt": {"load_kg": 2, "program": "quick"}}},
                        headers=headers).json()["Máy giặt"]["predicted_hours"]
    heavy = client.post("/forecast", json={"jobs": {"Máy giặt": {"load_kg": 9, "program": "heavy"}}},
                        headers=headers).json()["Máy giặt"]["predicted_hours"]
    assert heavy > light


def test_forecast_schema_lists_features(client, auth_headers):
    headers = auth_headers("fcuser3")
    response = client.get("/forecast/schema", headers=headers)
    assert response.status_code == 200
    schema = response.json()
    assert schema["Máy giặt"] == ["load_kg", "program"]
    assert "people" in schema["Bình nước nóng gián tiếp"]


def test_forecast_invalid_program_returns_422(client, auth_headers):
    headers = auth_headers("fcuser4")
    response = client.post(
        "/forecast",
        json={"jobs": {"Máy giặt": {"load_kg": 5, "program": "turbo"}}},
        headers=headers,
    )
    assert response.status_code == 422


def test_forecast_requires_auth(client):
    response = client.post("/forecast", json={"jobs": {"Máy giặt": {"load_kg": 5, "program": "normal"}}})
    assert response.status_code == 401


def test_forecast_forbidden_for_business_production(client, db_session):
    _make_business_user(db_session, "bizprod_fc", business_type="production")
    headers = {"Authorization": "Bearer bizprod_fc"}
    assert client.get("/forecast/schema", headers=headers).status_code == 403
    resp = client.post(
        "/forecast",
        json={"jobs": {"Máy giặt": {"load_kg": 5, "program": "normal"}}},
        headers=headers,
    )
    assert resp.status_code == 403


def test_forecast_forbidden_for_business_commercial(client, db_session):
    _make_business_user(db_session, "bizcomm_fc", business_type="commercial")
    headers = {"Authorization": "Bearer bizcomm_fc"}
    assert client.get("/forecast/schema", headers=headers).status_code == 403
    resp = client.post(
        "/forecast",
        json={"jobs": {"Máy giặt": {"load_kg": 5, "program": "normal"}}},
        headers=headers,
    )
    assert resp.status_code == 403


def test_optimize_duration_override_changes_monthly_kwh(client, auth_headers):
    headers = auth_headers("fcuser5")
    base = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False},
        headers=headers,
    ).json()
    overridden = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
              "duration_overrides": {"Máy giặt": 3.0}},
        headers=headers,
    ).json()
    # Máy giặt default 1h -> 3h adds (3-1)*0.5kW*30 = 30 kWh/month to the household total.
    assert overridden["monthly_kwh"] > base["monthly_kwh"]
