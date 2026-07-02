"""Role-based power-overload threshold (W) fed into the QUBO H_power penalty by /optimize.

Household must stay at the historical 5000W default; business customers use their declared
contracted power, with commercial warning earlier than production at the same contracted power.
"""
from api.optimize_router import DEFAULT_POWER_THRESHOLD_W, _power_threshold_for_user
from db.models import BusinessProfile, User


def test_household_uses_default_threshold():
    assert DEFAULT_POWER_THRESHOLD_W == 5000.0
    assert _power_threshold_for_user(User(role="household")) == 5000.0


def test_business_without_profile_uses_default():
    assert _power_threshold_for_user(User(role="business")) == 5000.0


def test_business_production_uses_full_contracted_power():
    user = User(role="business")
    user.business_profile = BusinessProfile(business_type="production", contracted_power_kw=10)
    assert _power_threshold_for_user(user) == 10000.0


def test_business_commercial_warns_earlier_than_production():
    user = User(role="business")
    user.business_profile = BusinessProfile(business_type="commercial", contracted_power_kw=10)
    assert _power_threshold_for_user(user) == 8000.0


def test_commercial_threshold_below_production_for_same_power():
    prod = User(role="business")
    prod.business_profile = BusinessProfile(business_type="production", contracted_power_kw=10)
    comm = User(role="business")
    comm.business_profile = BusinessProfile(business_type="commercial", contracted_power_kw=10)
    assert _power_threshold_for_user(comm) < _power_threshold_for_user(prod)


def test_optimize_response_exposes_household_threshold(client, auth_headers):
    headers = auth_headers("threshuser")
    resp = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["power_threshold_w"] == 5000.0
