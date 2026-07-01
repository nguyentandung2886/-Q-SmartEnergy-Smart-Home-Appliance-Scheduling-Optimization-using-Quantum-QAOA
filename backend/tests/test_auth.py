"""Tests for Supabase-Auth-backed request handling (GET /auth/me + get-or-create)."""


def test_me_returns_current_user(client, auth_headers):
    headers = auth_headers("alice-uid")
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["supabase_uid"] == "alice-uid"
    assert body["email"] == "alice-uid@test.local"


def test_first_request_seeds_12_appliances(client, auth_headers):
    headers = auth_headers("bob-uid")
    response = client.get("/appliances", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 12


def test_same_uid_reuses_user_without_reseeding(client, auth_headers):
    headers = auth_headers("carol-uid")
    client.get("/appliances", headers=headers)  # first request seeds
    second = client.get("/appliances", headers=headers)  # must not seed again
    assert second.status_code == 200
    assert len(second.json()) == 12


def test_missing_token_returns_401(client):
    response = client.get("/appliances")
    assert response.status_code == 401
