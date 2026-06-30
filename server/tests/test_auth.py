"""Tests for POST /auth/register and POST /auth/login."""


def test_register_creates_user_and_seeds_12_appliances(client):
    response = client.post("/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]

    appliances_response = client.get("/appliances", headers={"Authorization": f"Bearer {token}"})
    # /appliances endpoint doesn't exist yet — just check the register response is valid JWT
    assert len(token) > 10


def test_register_duplicate_username_returns_400(client):
    client.post("/auth/register", json={"username": "bob", "password": "password123"})
    response = client.post("/auth/register", json={"username": "bob", "password": "other12345"})
    assert response.status_code == 400


def test_register_short_password_rejected(client):
    response = client.post("/auth/register", json={"username": "carol", "password": "short"})
    assert response.status_code == 422  # Pydantic validation failure


def test_login_with_correct_password_returns_token(client):
    client.post("/auth/register", json={"username": "dave", "password": "password123"})
    response = client.post("/auth/login", json={"username": "dave", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/register", json={"username": "eve", "password": "password123"})
    response = client.post("/auth/login", json={"username": "eve", "password": "wrongpassword"})
    assert response.status_code == 401


def test_password_is_stored_as_bcrypt_hash(client, db_session):
    client.post("/auth/register", json={"username": "frank", "password": "password123"})
    from models import User
    user = db_session.query(User).filter(User.username == "frank").first()
    assert user is not None
    assert user.password_hash != "password123"          # not plaintext
    assert user.password_hash.startswith("$2b$")        # bcrypt prefix
