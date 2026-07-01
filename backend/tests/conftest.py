"""
Pytest fixtures for server/ tests.
Each test gets a fresh DB transaction rolled back after it finishes —
no leftover data in the test database between tests.
"""
import os
import sys

# Add both server/ and q-smartenergy/ to sys.path so tests can import from both.



import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

load_dotenv()

# Tests are hermetic: a shared in-memory SQLite DB, no external server needed.
# StaticPool keeps a single connection so every session sees the same :memory: DB.
_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    """Create all tables in the test DB once per test session, drop them after."""
    from db import models  # noqa: F401 — registers ORM models with Base.metadata
    from db.database import Base

    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def db_session():
    """Yields a DB session wrapped in a transaction rolled back after each test."""
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient backed by the per-test rolled-back DB session."""
    from db.database import get_db
    from main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Returns a factory that registers a user and returns its Bearer headers."""
    def _make(username: str = "testuser", password: str = "password123") -> dict:
        response = client.post("/auth/register", json={"username": username, "password": password})
        assert response.status_code == 200, f"Register failed: {response.text}"
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make
