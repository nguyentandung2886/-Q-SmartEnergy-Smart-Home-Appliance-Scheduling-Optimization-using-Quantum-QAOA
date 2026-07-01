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

# auth.py requires SUPABASE_URL at import time; tests stub Supabase JWT validation
# (see the client fixture) so the value only needs to be present, not real.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")

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
    """FastAPI TestClient backed by the per-test rolled-back DB session.

    Supabase JWT validation is stubbed: get_current_user is overridden to treat
    the raw Bearer token as the Supabase UID and get-or-create the local user
    (seeding default appliances on first use, exactly like production).
    """
    from fastapi import Depends, HTTPException, Request, status
    from auth import _seed_default_appliances, get_current_user
    from db.database import get_db
    from db.models import User
    from main import app

    def _override_get_db():
        yield db_session

    def _override_get_current_user(request: Request, db=Depends(get_db)) -> User:
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate credentials")
        user = db.query(User).filter(User.supabase_uid == token).first()
        if user is None:
            user = User(supabase_uid=token, email=f"{token}@test.local")
            db.add(user)
            db.flush()
            _seed_default_appliances(db, user)
            db.commit()
            db.refresh(user)
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Returns a factory that yields Bearer headers for a given identity.

    The identity string is used as the fake Supabase UID; the first request for
    a new identity get-or-creates the user and seeds default appliances.
    """
    def _make(identity: str = "testuser", password: str = "unused") -> dict:
        return {"Authorization": f"Bearer {identity}"}
    return _make
