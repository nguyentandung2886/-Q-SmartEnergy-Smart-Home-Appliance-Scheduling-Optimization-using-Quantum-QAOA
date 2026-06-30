# Backend API + Database + Auth + React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI backend, SQL Server database, JWT auth, and a full React frontend (replacing Streamlit as the primary UX) to Q-SmartEnergy — turning the existing PoC into a multi-user web app. Finish with Framer Motion animations for a polished, professional feel.

**Architecture:** New `server/` directory (FastAPI, SQLAlchemy, pyodbc for SQL Server) and rebuilt `client/` (React + react-router-dom + axios + framer-motion). Backend imports Python pipeline from `q-smartenergy/` directly via PYTHONPATH — no code ported to another language. Database: SQL Server (already installed locally) with 3 tables: users, appliances, schedules.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pyodbc (SQL Server), python-jose (JWT), passlib[bcrypt], pytest, httpx; React 19, react-router-dom 7, axios, framer-motion 11.

## Global Constraints

- Backend code lives in `server/` (new, parallel to `client/` and `q-smartenergy/`).
- `server/` imports `q-smartenergy/` modules via `sys.path.insert(0, <path-to-q-smartenergy>)` done ONCE at top of `server/main.py` before any router imports — do NOT duplicate this path insertion in individual router files.
- JWT secret and SQL Server connection string MUST come from `.env` file, NEVER hard-coded. Commit `.env.example` to git, never `.env` itself.
- Passwords stored as bcrypt hashes (passlib), never plaintext.
- CORS origin configured for React dev server `http://localhost:5173`.
- No new pip dependency inside `q-smartenergy/` — only `server/requirements.txt` and `client/package.json` gain new packages.
- NEVER use "giờ cao điểm" / "peak hour" / "time-of-use" anywhere.
- `q-smartenergy/calc.py` gets ONE additive change (optional `monthly_kwh` param on `grid_purchase_kwh`) — all other q-smartenergy modules are untouched by this plan.
- Frontend animations (Framer Motion) are layered ON TOP of working functional pages — implement in Task 11 only after Tasks 7-10 confirm the pages work correctly without animation.
- SQL Server test database name: `q_smartenergy_test` (separate from `q_smartenergy` production DB). Tests use transaction rollback — no leftover data.

---

### Task 1: `server/` scaffold — requirements, DB engine, ORM models, schema creation

**Files:**
- Create: `server/requirements.txt`
- Create: `server/.env.example`
- Create: `server/database.py`
- Create: `server/models.py`
- Create: `server/routers/__init__.py` (empty)

**Interfaces:**
- Produces: `database.Base`, `database.SessionLocal`, `database.engine`, `database.get_db()`, `models.User`, `models.ApplianceModel`, `models.ScheduleModel`.
- Consumes: nothing from `q-smartenergy/` yet (this is pure DB scaffolding).

- [ ] **Step 1: Create `server/requirements.txt`**

```
fastapi
uvicorn[standard]
sqlalchemy
pyodbc
python-jose[cryptography]
passlib[bcrypt]
python-multipart
python-dotenv
pytest
httpx
```

- [ ] **Step 2: Create `server/.env.example`** (commit this; do NOT commit `.env`)

```
# Copy this file to .env and fill in your values.
# SQL Server with Windows trusted authentication (no username/password required for local dev).
# Replace INSTANCE_NAME if using a named instance (e.g. SQLEXPRESS).
JWT_SECRET=replace-this-with-a-long-random-string
DATABASE_URL=mssql+pyodbc://localhost/q_smartenergy?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
DATABASE_URL_TEST=mssql+pyodbc://localhost/q_smartenergy_test?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

- [ ] **Step 3: Create `server/database.py`**

```python
"""
SQLAlchemy engine, session, and base for Q-SmartEnergy backend.
Connection string comes from .env — never hard-coded (see .env.example).
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mssql+pyodbc://localhost/q_smartenergy?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `server/models.py`**

```python
"""
SQLAlchemy ORM models: User, ApplianceModel, ScheduleModel.
Schema:
  users       — id, username (unique), password_hash (bcrypt), created_at
  appliances  — id, user_id FK, name, power_w, duration_hours,
                candidate_hours (comma-separated string, "" if is_flexible=False),
                is_flexible, created_at
  schedules   — id, user_id FK, created_at, day_of_month, weather_condition,
                solver_used, used_fallback, energy, schedule_json (JSON string),
                monthly_kwh (snapshot), bill_before_vnd (snapshot), bill_after_vnd (snapshot)
"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    appliances = relationship("ApplianceModel", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("ScheduleModel", back_populates="user", cascade="all, delete-orphan")


class ApplianceModel(Base):
    __tablename__ = "appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    power_w = Column(Float, nullable=False)
    duration_hours = Column(Float, nullable=False)
    candidate_hours = Column(String(50), default="")
    is_flexible = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="appliances")


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    day_of_month = Column(Integer, nullable=False)
    weather_condition = Column(String(20), nullable=False)
    solver_used = Column(String(30), nullable=False)
    used_fallback = Column(Boolean, nullable=False)
    energy = Column(Float, nullable=False)
    schedule_json = Column(Text, nullable=False)
    monthly_kwh = Column(Float, nullable=False)
    bill_before_vnd = Column(Float, nullable=False)
    bill_after_vnd = Column(Float, nullable=False)

    user = relationship("User", back_populates="schedules")
```

- [ ] **Step 5: Create the two SQL Server databases and install backend packages**

Run in SSMS or `sqlcmd`:
```sql
CREATE DATABASE q_smartenergy;
CREATE DATABASE q_smartenergy_test;
```

Then:
```bash
cd server
pip install -r requirements.txt
pip install -r ../q-smartenergy/requirements.txt
```

- [ ] **Step 6: Verify SQLAlchemy can connect (no tables yet)**

Run:
```bash
cd server
python -c "from database import engine; print('connection OK:', engine.url)"
```
Expected: prints the connection URL without raising an exception. If it raises `pyodbc.Error`, check that the ODBC Driver 17 for SQL Server is installed and the `DATABASE_URL` in your `.env` is correct.

- [ ] **Step 7: Create `server/routers/__init__.py`** (empty file — needed for Python package resolution)

```python
```

- [ ] **Step 8: Commit**

```bash
cd "c:/Users/MYPC/OneDrive/Desktop/JS Coding"
git add server/
git commit -m "Add server/ scaffold: requirements, DB engine, ORM models"
```

---

### Task 2: `q-smartenergy/calc.py` — add optional `monthly_kwh` parameter to `grid_purchase_kwh`

**Files:**
- Modify: `q-smartenergy/calc.py:120-144` (`grid_purchase_kwh` function)
- Modify: `q-smartenergy/tests/test_baseline.py`

**Interfaces:**
- Produces: `grid_purchase_kwh(self_consumption_rate, monthly_kwh=None)` — default `None` uses the module-level `MONTHLY_KWH`, preserving ALL existing behavior. Passing an explicit value computes a per-user bill (used by `server/routers/optimize_router.py`).
- Consumes: nothing new — only modifies an existing function's signature.

**Why:** the spec requires per-user bill calculation: each user's bill depends on THEIR appliance list's total kWh (not the global `MONTHLY_KWH`). Adding an optional parameter (default `None` → falls back to module-level constant) is the minimal change that supports this while keeping every existing caller working unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `q-smartenergy/tests/test_baseline.py` (in the `TestGridPurchaseKwh` class, after the existing tests, same indentation level as the existing test methods):

```python
    def test_grid_purchase_kwh_default_unchanged(self):
        """Calling with no monthly_kwh must produce the same result as before this change."""
        from calc import MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, grid_purchase_kwh
        assert grid_purchase_kwh(0.30) == pytest.approx(MONTHLY_KWH - SOLAR_MONTHLY_GENERATION_KWH * 0.30)

    def test_grid_purchase_kwh_with_custom_monthly_kwh(self):
        """Passing monthly_kwh overrides the module-level MONTHLY_KWH — used for per-user billing."""
        from calc import grid_purchase_kwh, SOLAR_MONTHLY_GENERATION_KWH
        custom_kwh = 1000.0
        result = grid_purchase_kwh(0.30, monthly_kwh=custom_kwh)
        assert result == pytest.approx(custom_kwh - SOLAR_MONTHLY_GENERATION_KWH * 0.30)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_baseline.py -k "custom_monthly_kwh or default_unchanged" -v`
Expected: FAIL — `TypeError: grid_purchase_kwh() got an unexpected keyword argument 'monthly_kwh'`.

- [ ] **Step 3: Update `grid_purchase_kwh` in `q-smartenergy/calc.py`**

Find the current `grid_purchase_kwh` function and replace it with:

```python
def grid_purchase_kwh(self_consumption_rate: float, monthly_kwh: float = None) -> float:
    """
    Calculate grid-purchased kWh after solar self-consumption.

    Args:
        self_consumption_rate: Fraction of solar output self-consumed directly (0.0 to 1.0).
        monthly_kwh: Override total household monthly load. Defaults to module-level MONTHLY_KWH
                     (the appliance_catalog total) if None — this preserves existing behavior for
                     every current caller. Pass a specific value to compute a per-user bill
                     (server/routers/optimize_router.py), where each user has their own appliance
                     list and thus a different monthly total.

    Returns:
        kWh purchased from grid = monthly_kwh_effective - SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    """
    monthly_kwh_effective = MONTHLY_KWH if monthly_kwh is None else monthly_kwh
    solar_self_consumed = SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    return monthly_kwh_effective - solar_self_consumed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, including the 2 new ones.

- [ ] **Step 5: Commit**

```bash
git add q-smartenergy/calc.py q-smartenergy/tests/test_baseline.py
git commit -m "calc.py: add optional monthly_kwh param to grid_purchase_kwh for per-user billing"
```

---

### Task 3: `server/auth.py` + `server/main.py` (skeleton) + `server/tests/conftest.py`

**Files:**
- Create: `server/auth.py`
- Create: `server/main.py` (skeleton with health-check route, CORS, no routers yet)
- Create: `server/tests/__init__.py` (empty)
- Create: `server/tests/conftest.py`

**Interfaces:**
- Produces: `auth.hash_password`, `auth.verify_password`, `auth.create_access_token`, `auth.get_current_user` (FastAPI dependency); `main.app` (FastAPI instance, used by all router tests via `TestClient`); `conftest.client` fixture, `conftest.db_session` fixture, `conftest.auth_headers` fixture.
- Consumes: `database.Base`, `database.engine`, `database.get_db`, `models.User`.

- [ ] **Step 1: Create `server/auth.py`**

```python
"""
JWT + bcrypt utilities for Q-SmartEnergy backend.
JWT secret must come from JWT_SECRET env var (see .env.example).
Passwords stored as bcrypt hashes — never plaintext.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_error
    return user
```

- [ ] **Step 2: Create `server/main.py`** (skeleton — routers added in later tasks)

```python
"""
Q-SmartEnergy FastAPI application entry point.
Run from the server/ directory:
    uvicorn main:app --reload --port 8000

Imports q-smartenergy modules (calc, appliance_catalog, etc.) via sys.path.
"""
import os
import sys

# Allow importing q-smartenergy pipeline modules directly (calc, appliance_catalog,
# data_prep, qubo_builder, quantum_runner, visualizer) without installing them as a package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "q-smartenergy"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Q-SmartEnergy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers are added here in Tasks 4-6:
# from routers import auth_router, appliances_router, optimize_router
# app.include_router(auth_router.router)
# app.include_router(appliances_router.router)
# app.include_router(optimize_router.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Q-SmartEnergy API"}
```

- [ ] **Step 3: Create `server/tests/__init__.py`** (empty)

- [ ] **Step 4: Create `server/tests/conftest.py`**

```python
"""
Pytest fixtures for server/ tests.
Each test gets a fresh DB transaction rolled back after it finishes —
no leftover data in the test database between tests.
"""
import os
import sys

# Add both server/ and q-smartenergy/ to sys.path so tests can import from both.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "q-smartenergy"))

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL_TEST",
    "mssql+pyodbc://localhost/q_smartenergy_test?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes",
)

_test_engine = create_engine(TEST_DATABASE_URL)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    """Create all tables in the test DB once per test session, drop them after."""
    from database import Base

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
    from database import get_db
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
```

- [ ] **Step 5: Verify the health-check endpoint**

Run from `server/`:
```bash
cd server
uvicorn main:app --port 8000 &
sleep 2
python -c "import urllib.request, json; r=urllib.request.urlopen('http://localhost:8000/'); print(json.loads(r.read()))"
kill %1 2>/dev/null
```
Expected: prints `{'status': 'ok', 'service': 'Q-SmartEnergy API'}`.

- [ ] **Step 6: Run a smoke test via pytest**

Create `server/tests/test_smoke.py`:
```python
def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

Run: `cd server && pytest tests/test_smoke.py -v`
Expected: 1 PASS.

- [ ] **Step 7: Commit**

```bash
git add server/auth.py server/main.py server/tests/
git commit -m "Add server auth utilities, FastAPI skeleton, and pytest test fixtures"
```

---

### Task 4: `server/routers/auth_router.py` — register + login

**Files:**
- Create: `server/routers/auth_router.py`
- Modify: `server/main.py` (uncomment/add auth router)
- Create: `server/tests/test_auth.py`

**Interfaces:**
- Produces: `POST /auth/register` (creates user, seeds 12 appliances from `appliance_catalog.HOUSEHOLD_APPLIANCES`, returns JWT), `POST /auth/login` (verifies bcrypt, returns JWT).
- Consumes: `auth.hash_password`, `auth.verify_password`, `auth.create_access_token`, `models.User`, `models.ApplianceModel`, `appliance_catalog.HOUSEHOLD_APPLIANCES`.

- [ ] **Step 1: Create `server/routers/auth_router.py`**

```python
"""
Auth endpoints: POST /auth/register, POST /auth/login.
On register: user created + appliances seeded from appliance_catalog.HOUSEHOLD_APPLIANCES.
Passwords hashed with bcrypt — never stored as plaintext.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import appliance_catalog
from auth import create_access_token, hash_password, verify_password
from database import get_db
from models import ApplianceModel, User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()  # flush to get user.id before creating appliances

    for a in appliance_catalog.HOUSEHOLD_APPLIANCES:
        db.add(ApplianceModel(
            user_id=user.id,
            name=a.name,
            power_w=a.power_w,
            duration_hours=a.duration_hours,
            candidate_hours=",".join(str(h) for h in a.candidate_hours),
            is_flexible=a.is_flexible,
        ))

    db.commit()
    return TokenResponse(access_token=create_access_token(user.username))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username))
```

- [ ] **Step 2: Register the router in `server/main.py`**

Replace the commented-out router section in `main.py` with:

```python
from routers import auth_router

app.include_router(auth_router.router)
```

- [ ] **Step 3: Create `server/tests/test_auth.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd server && pytest tests/test_auth.py tests/test_smoke.py -v`
Expected: 6+1 = 7 tests PASS. (`test_register_creates_user_and_seeds_12_appliances` only checks the token, not the appliances count — that requires /appliances which is in Task 5.)

- [ ] **Step 5: Commit**

```bash
git add server/routers/auth_router.py server/main.py server/tests/test_auth.py
git commit -m "Add /auth/register and /auth/login endpoints with bcrypt + JWT"
```

---

### Task 5: `server/routers/appliances_router.py` — CRUD

**Files:**
- Create: `server/routers/appliances_router.py`
- Modify: `server/main.py` (add appliances router)
- Create: `server/tests/test_appliances.py`

**Interfaces:**
- Produces: `GET /appliances`, `POST /appliances`, `PUT /appliances/{id}`, `DELETE /appliances/{id}`. All require Bearer JWT.
- Consumes: `auth.get_current_user`, `models.ApplianceModel`.

- [ ] **Step 1: Create `server/routers/appliances_router.py`**

```python
"""Appliance CRUD endpoints. All routes require valid JWT (see auth.get_current_user)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import ApplianceModel, User

router = APIRouter(prefix="/appliances", tags=["appliances"])


class ApplianceIn(BaseModel):
    name: str
    power_w: float
    duration_hours: float
    candidate_hours: List[int] = []
    is_flexible: bool = True


class ApplianceOut(BaseModel):
    id: int
    name: str
    power_w: float
    duration_hours: float
    candidate_hours: List[int]
    is_flexible: bool

    model_config = {"from_attributes": True}


def _to_out(row: ApplianceModel) -> ApplianceOut:
    hours = [int(h) for h in row.candidate_hours.split(",") if h] if row.candidate_hours else []
    return ApplianceOut(
        id=row.id, name=row.name, power_w=row.power_w, duration_hours=row.duration_hours,
        candidate_hours=hours, is_flexible=row.is_flexible,
    )


def _get_owned(appliance_id: int, user_id: int, db: Session) -> ApplianceModel:
    row = db.query(ApplianceModel).filter(
        ApplianceModel.id == appliance_id, ApplianceModel.user_id == user_id
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appliance not found")
    return row


@router.get("", response_model=List[ApplianceOut])
def list_appliances(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ApplianceOut, status_code=status.HTTP_201_CREATED)
def create_appliance(
    payload: ApplianceIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = ApplianceModel(
        user_id=current_user.id,
        name=payload.name, power_w=payload.power_w, duration_hours=payload.duration_hours,
        candidate_hours=",".join(str(h) for h in payload.candidate_hours),
        is_flexible=payload.is_flexible,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.put("/{appliance_id}", response_model=ApplianceOut)
def update_appliance(
    appliance_id: int,
    payload: ApplianceIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned(appliance_id, current_user.id, db)
    row.name = payload.name
    row.power_w = payload.power_w
    row.duration_hours = payload.duration_hours
    row.candidate_hours = ",".join(str(h) for h in payload.candidate_hours)
    row.is_flexible = payload.is_flexible
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{appliance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appliance(
    appliance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned(appliance_id, current_user.id, db)
    db.delete(row)
    db.commit()
```

- [ ] **Step 2: Add to `server/main.py`**

```python
from routers import auth_router, appliances_router

app.include_router(auth_router.router)
app.include_router(appliances_router.router)
```

- [ ] **Step 3: Create `server/tests/test_appliances.py`**

```python
"""Tests for appliance CRUD endpoints."""


def test_register_seeds_12_appliances(client, auth_headers):
    headers = auth_headers("seeduser")
    response = client.get("/appliances", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 12  # HOUSEHOLD_APPLIANCES has 12 entries


def test_list_appliances_requires_auth(client):
    response = client.get("/appliances")
    assert response.status_code == 401


def test_create_appliance_returns_201(client, auth_headers):
    headers = auth_headers("createuser")
    response = client.post(
        "/appliances",
        json={"name": "Test Device", "power_w": 500, "duration_hours": 1,
              "candidate_hours": [7, 13], "is_flexible": True},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Device"
    assert data["candidate_hours"] == [7, 13]


def test_update_appliance(client, auth_headers):
    headers = auth_headers("updateuser")
    create = client.post(
        "/appliances",
        json={"name": "X", "power_w": 100, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    aid = create.json()["id"]
    update = client.put(
        f"/appliances/{aid}",
        json={"name": "X", "power_w": 200, "duration_hours": 2, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["power_w"] == 200


def test_delete_appliance(client, auth_headers):
    headers = auth_headers("deleteuser")
    create = client.post(
        "/appliances",
        json={"name": "Y", "power_w": 50, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    aid = create.json()["id"]
    delete = client.delete(f"/appliances/{aid}", headers=headers)
    assert delete.status_code == 204
    remaining = client.get("/appliances", headers=headers).json()
    assert all(a["id"] != aid for a in remaining)


def test_cannot_touch_other_users_appliance(client, auth_headers):
    headers_a = auth_headers("usera")
    headers_b = auth_headers("userb")
    create = client.post(
        "/appliances",
        json={"name": "Z", "power_w": 50, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers_a,
    )
    aid = create.json()["id"]
    assert client.delete(f"/appliances/{aid}", headers=headers_b).status_code == 404
```

- [ ] **Step 4: Run tests**

Run: `cd server && pytest tests/ -v`
Expected: all previous + 5 new = 13 PASS.

- [ ] **Step 5: Commit**

```bash
git add server/routers/appliances_router.py server/main.py server/tests/test_appliances.py
git commit -m "Add /appliances CRUD endpoints with per-user ownership check"
```

---

### Task 6: `server/routers/optimize_router.py` — optimize + schedules history

**Files:**
- Create: `server/routers/optimize_router.py`
- Modify: `server/main.py` (add optimize router)
- Create: `server/tests/test_optimize.py`

**Interfaces:**
- Produces: `POST /optimize` (runs QAOA pipeline on user's flexible appliances, computes per-user bill, saves to `schedules`, returns schedule + PNG charts); `GET /schedules` (history, newest first).
- Consumes: `auth.get_current_user`, `models.ApplianceModel`, `models.ScheduleModel`; `q-smartenergy/` modules: `appliance_catalog.split_by_flexibility`, `appliance_catalog.total_monthly_kwh`, `qubo_builder.Appliance`, `data_prep.build_daily_profile`, `quantum_runner.QuantumScheduler`, `visualizer.plot_schedule_gantt`, `visualizer.plot_cost_comparison`, `calc.calculate_bill`, `calc.grid_purchase_kwh`, `calc.SELF_CONSUMPTION_BEFORE`, `calc.SELF_CONSUMPTION_AFTER`.

- [ ] **Step 1: Create `server/routers/optimize_router.py`**

```python
"""
POST /optimize: run the QAOA pipeline using the current user's appliances; save result to
schedules history. GET /schedules: return optimization history newest-first.
Charts are returned as base64-encoded PNG so the React frontend only needs <img src="data:...">.
Per-user bill: calculated from the user's OWN appliance list total, not the global calc.MONTHLY_KWH.
"""
import base64
import io
import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import calc
import data_prep
import visualizer
from appliance_catalog import split_by_flexibility, total_monthly_kwh
from auth import get_current_user
from database import get_db
from models import ApplianceModel, ScheduleModel, User
from quantum_runner import QuantumScheduler
from qubo_builder import Appliance

router = APIRouter(tags=["optimize"])


class OptimizeRequest(BaseModel):
    day_of_month: int = 9
    weather_condition: str = "sunny"
    use_quantum: bool = True


class ScheduleOut(BaseModel):
    id: int
    created_at: str
    day_of_month: int
    weather_condition: str
    solver_used: str
    used_fallback: bool
    energy: float
    schedule: dict
    monthly_kwh: float
    bill_before_vnd: float
    bill_after_vnd: float
    savings_percent: float
    gantt_chart_png: Optional[str] = None
    bill_chart_png: Optional[str] = None


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _db_rows_to_appliances(rows: List[ApplianceModel]) -> List[Appliance]:
    result = []
    for row in rows:
        hours = tuple(int(h) for h in row.candidate_hours.split(",") if h) if row.candidate_hours else ()
        result.append(Appliance(
            name=row.name, power_w=row.power_w, duration_hours=row.duration_hours,
            candidate_hours=hours, is_flexible=row.is_flexible,
        ))
    return result


@router.post("/optimize", response_model=ScheduleOut)
def optimize(
    payload: OptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    user_appliances = _db_rows_to_appliances(rows)
    flexible, _fixed = split_by_flexibility(user_appliances)

    profile = data_prep.build_daily_profile(payload.day_of_month, weather_condition=payload.weather_condition)
    scheduler = QuantumScheduler(flexible, profile)
    result = scheduler.solve(use_quantum=payload.use_quantum)

    # Per-user bill: uses user's OWN appliance list total, not global calc.MONTHLY_KWH
    user_monthly_kwh = total_monthly_kwh(user_appliances)
    bill_before = calc.calculate_bill(calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_BEFORE, user_monthly_kwh))
    bill_after = calc.calculate_bill(calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_AFTER, user_monthly_kwh))
    savings_percent = (bill_before - bill_after) / bill_before * 100 if bill_before > 0 else 0.0

    gantt_fig = visualizer.plot_schedule_gantt(result.schedule, flexible)
    bill_fig = visualizer.plot_cost_comparison(bill_before, bill_after)
    gantt_png = _fig_to_base64(gantt_fig)
    bill_png = _fig_to_base64(bill_fig)

    row = ScheduleModel(
        user_id=current_user.id,
        day_of_month=payload.day_of_month,
        weather_condition=payload.weather_condition,
        solver_used=result.solver_used,
        used_fallback=result.used_fallback,
        energy=result.energy,
        schedule_json=json.dumps(result.schedule, ensure_ascii=False),
        monthly_kwh=user_monthly_kwh,
        bill_before_vnd=bill_before,
        bill_after_vnd=bill_after,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ScheduleOut(
        id=row.id, created_at=row.created_at.isoformat(),
        day_of_month=row.day_of_month, weather_condition=row.weather_condition,
        solver_used=row.solver_used, used_fallback=row.used_fallback, energy=row.energy,
        schedule=result.schedule, monthly_kwh=user_monthly_kwh,
        bill_before_vnd=bill_before, bill_after_vnd=bill_after,
        savings_percent=savings_percent, gantt_chart_png=gantt_png, bill_chart_png=bill_png,
    )


@router.get("/schedules", response_model=List[ScheduleOut])
def list_schedules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.user_id == current_user.id)
        .order_by(ScheduleModel.created_at.desc())
        .all()
    )
    return [
        ScheduleOut(
            id=r.id, created_at=r.created_at.isoformat(),
            day_of_month=r.day_of_month, weather_condition=r.weather_condition,
            solver_used=r.solver_used, used_fallback=r.used_fallback, energy=r.energy,
            schedule=json.loads(r.schedule_json), monthly_kwh=r.monthly_kwh,
            bill_before_vnd=r.bill_before_vnd, bill_after_vnd=r.bill_after_vnd,
            savings_percent=(r.bill_before_vnd - r.bill_after_vnd) / r.bill_before_vnd * 100,
        )
        for r in rows
    ]
```

- [ ] **Step 2: Add to `server/main.py`**

```python
from routers import auth_router, appliances_router, optimize_router

app.include_router(auth_router.router)
app.include_router(appliances_router.router)
app.include_router(optimize_router.router)
```

- [ ] **Step 3: Create `server/tests/test_optimize.py`**

```python
"""Tests for POST /optimize and GET /schedules. QAOA tests are slow — run them last."""


def test_optimize_requires_auth(client):
    response = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"})
    assert response.status_code == 401


def test_optimize_returns_valid_schedule_and_charts(client, auth_headers):
    headers = auth_headers("optuser")
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "use_quantum": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["solver_used"] in ("qaoa", "classical_bruteforce")
    assert data["bill_before_vnd"] > data["bill_after_vnd"]
    assert data["savings_percent"] > 0
    assert data["gantt_chart_png"] is not None
    assert data["bill_chart_png"] is not None


def test_optimize_saves_to_schedules_history(client, auth_headers):
    headers = auth_headers("histuser")
    client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers)
    response = client.get("/schedules", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_optimize_with_all_appliances_deleted_does_not_crash(client, auth_headers):
    """If user deletes all flexible appliances, /optimize must still return 200
    (empty schedule, no QUBO variables to solve — existing fallback handles it)."""
    headers = auth_headers("noflexuser")
    appliances = client.get("/appliances", headers=headers).json()
    for a in appliances:
        if a["is_flexible"]:
            client.delete(f"/appliances/{a['id']}", headers=headers)
    response = client.post(
        "/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["schedule"] == {}


def test_bill_is_personalized_to_user_appliances(client, auth_headers):
    """User A (has all 12 appliances) vs User B (has deleted all appliances) must have
    different bill values — confirms per-user billing, not a static global number."""
    headers_a = auth_headers("billusera")
    headers_b = auth_headers("billuserb")
    # Delete all of B's appliances to make B's appliance list empty (total_monthly_kwh = 0)
    appliances_b = client.get("/appliances", headers=headers_b).json()
    for a in appliances_b:
        client.delete(f"/appliances/{a['id']}", headers=headers_b)

    result_a = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers_a).json()
    result_b = client.post("/optimize", json={"day_of_month": 9, "weather_condition": "sunny"}, headers=headers_b).json()
    assert result_a["bill_before_vnd"] != result_b["bill_before_vnd"]
```

- [ ] **Step 4: Run the full backend test suite**

Run: `cd server && pytest tests/ -v`
Expected: all tests pass (this includes the QAOA test which takes ~2-5s — expected, not a hang).

- [ ] **Step 5: Commit**

```bash
git add server/routers/optimize_router.py server/main.py server/tests/test_optimize.py
git commit -m "Add /optimize (QAOA pipeline + per-user billing) and /schedules history endpoints"
```

---

### Task 7: `client/` setup — install dependencies, API client, auth context, routing shell

**Files:**
- Modify: `client/package.json` (install new deps via npm)
- Create: `client/.env.example`
- Create: `client/src/api.js`
- Create: `client/src/AuthContext.jsx`
- Modify: `client/src/App.jsx` (full replace — new routing structure)
- Modify: `client/src/main.jsx` (wrap in Router/AuthProvider)

**Interfaces:**
- Produces: `api.js` exports `register`, `login`, `getAppliances`, `createAppliance`, `updateAppliance`, `deleteAppliance`, `optimize`, `getSchedules`; `AuthContext` exports `AuthProvider`, `useAuth` (provides `token`, `isAuthenticated`, `login`, `register`, `logout`); `App.jsx` configures React Router with 4 routes: `/login`, `/register`, `/dashboard`, `/history`.
- Consumes: axios, react-router-dom, framer-motion (installed in this task but NOT used yet — usage is in Tasks 8-11).

- [ ] **Step 1: Install client dependencies**

```bash
cd client
npm install axios react-router-dom framer-motion
```
Expected: `package.json` gains the 3 new packages under `dependencies`.

- [ ] **Step 2: Create `client/.env.example`** (commit this, do NOT commit `.env`)

```
VITE_API_BASE_URL=http://localhost:8000
```
Then create `client/.env` from the example (do NOT commit `.env`):
```bash
cp .env.example .env
```
Also add `client/.env` to `.gitignore` (check if it's already there — if the root `.gitignore` already covers it, no action needed):
```bash
cd ..
grep -q "\.env$" .gitignore || echo ".env" >> .gitignore
```

- [ ] **Step 3: Create `client/src/api.js`**

```js
/**
 * Axios client + all backend API calls.
 * JWT token is read from localStorage and injected as Authorization header on every request.
 */
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function register(username, password) {
  const { data } = await apiClient.post("/auth/register", { username, password });
  return data;
}

export async function login(username, password) {
  const { data } = await apiClient.post("/auth/login", { username, password });
  return data;
}

export async function getAppliances() {
  const { data } = await apiClient.get("/appliances");
  return data;
}

export async function createAppliance(appliance) {
  const { data } = await apiClient.post("/appliances", appliance);
  return data;
}

export async function updateAppliance(id, appliance) {
  const { data } = await apiClient.put(`/appliances/${id}`, appliance);
  return data;
}

export async function deleteAppliance(id) {
  await apiClient.delete(`/appliances/${id}`);
}

export async function optimize(params) {
  const { data } = await apiClient.post("/optimize", params);
  return data;
}

export async function getSchedules() {
  const { data } = await apiClient.get("/schedules");
  return data;
}

export default apiClient;
```

- [ ] **Step 4: Create `client/src/AuthContext.jsx`**

```jsx
import { createContext, useContext, useState } from "react";
import { login as apiLogin, register as apiRegister } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  async function login(username, password) {
    const data = await apiLogin(username, password);
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
  }

  async function register(username, password) {
    const data = await apiRegister(username, password);
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 5: Replace `client/src/App.jsx` entirely**

```jsx
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";

// Pages created in Tasks 8-10 — import them here once they exist.
// For now, use placeholder stubs so routing is testable immediately.
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";

import "./App.css";

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;
```

- [ ] **Step 6: Update `client/src/main.jsx`**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Step 7: Create stub page files** (will be replaced in Tasks 8-10)

Create `client/src/pages/Login.jsx`, `Register.jsx`, `Dashboard.jsx`, `History.jsx` — each just a labeled placeholder so the app compiles:

```bash
mkdir -p client/src/pages
```

`client/src/pages/Login.jsx`:
```jsx
export default function Login() { return <div>Login – coming in Task 8</div>; }
```

`client/src/pages/Register.jsx`:
```jsx
export default function Register() { return <div>Register – coming in Task 8</div>; }
```

`client/src/pages/Dashboard.jsx`:
```jsx
export default function Dashboard() { return <div>Dashboard – coming in Task 9</div>; }
```

`client/src/pages/History.jsx`:
```jsx
export default function History() { return <div>History – coming in Task 10</div>; }
```

- [ ] **Step 8: Verify the app compiles and serves**

```bash
cd client
npm run dev
```
Expected: Vite starts, no compile errors. Visit `http://localhost:5173` — redirects to `/login` (because not authenticated), shows "Login – coming in Task 8". Ctrl+C to stop.

- [ ] **Step 9: Commit**

```bash
git add client/
git commit -m "client/ setup: add axios/react-router-dom/framer-motion, API client, auth context, routing shell"
```

---

### Task 8: `client/src/pages/Login.jsx` + `Register.jsx` + `App.css` (base styling)

**Files:**
- Modify: `client/src/pages/Login.jsx` (full implementation)
- Modify: `client/src/pages/Register.jsx` (full implementation)
- Modify: `client/src/App.css` (base styling for all pages, palette Indigo/Teal/Gold)

**Interfaces:**
- Consumes: `useAuth()` from AuthContext, `react-router-dom` `useNavigate`/`Link`.
- Produces: working login/register flow that stores JWT and redirects to `/dashboard`.

- [ ] **Step 1: Replace `client/src/App.css`** with the project's base stylesheet

```css
/* Q-SmartEnergy base styles — Indigo #3730A3, Teal #0F766E, Gold #CA8A04 */
:root {
  --indigo: #3730a3;
  --teal: #0f766e;
  --gold: #ca8a04;
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --error: #dc2626;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "Inter", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}

/* Auth pages */
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f0fdfa 100%);
}

.auth-form {
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(55, 48, 163, 0.10);
  padding: 2.5rem;
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.auth-form h1 { color: var(--indigo); font-size: 1.5rem; font-weight: 700; }
.auth-error { color: var(--error); font-size: 0.875rem; }

.auth-form label { display: flex; flex-direction: column; gap: 0.35rem; font-weight: 500; font-size: 0.9rem; }
.auth-form input {
  border: 1.5px solid var(--border);
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 1rem;
  transition: border-color 0.15s;
}
.auth-form input:focus { outline: none; border-color: var(--indigo); }

.auth-form button[type="submit"], button.primary {
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}
.auth-form button[type="submit"]:hover, button.primary:hover { background: #0d6460; }
.auth-form button[type="submit"]:active, button.primary:active { transform: scale(0.98); }

.auth-form p { font-size: 0.875rem; color: var(--text-muted); text-align: center; }
.auth-form a { color: var(--indigo); text-decoration: none; font-weight: 500; }

/* Dashboard */
.dashboard { max-width: 960px; margin: 0 auto; padding: 1.5rem; }

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid var(--indigo);
  margin-bottom: 2rem;
}
.dashboard-header h1 { color: var(--indigo); font-size: 1.75rem; font-weight: 800; }
.dashboard-header nav { display: flex; gap: 0.75rem; }
.dashboard-header button {
  background: none;
  border: 1.5px solid var(--teal);
  color: var(--teal);
  border-radius: 8px;
  padding: 0.4rem 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.dashboard-header button:hover { background: var(--teal); color: #fff; }

.section-card {
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.section-card h2 { color: var(--indigo); margin-bottom: 1rem; font-size: 1.1rem; }

/* Tables */
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
th { font-weight: 600; color: var(--text-muted); background: #f8fafc; }
td input { border: 1px solid var(--border); border-radius: 6px; padding: 0.3rem 0.5rem; width: 90px; }
td button { background: none; border: none; cursor: pointer; color: var(--error); font-weight: 600; font-size: 0.8rem; }

/* Add appliance form */
.add-form { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem; }
.add-form input { flex: 1 1 120px; border: 1.5px solid var(--border); border-radius: 8px; padding: 0.5rem 0.75rem; }
.add-form button { background: var(--indigo); color: #fff; border: none; border-radius: 8px; padding: 0.5rem 1.25rem; font-weight: 600; cursor: pointer; }

/* Optimize controls */
.optimize-controls { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
.optimize-controls label { display: flex; flex-direction: column; gap: 0.3rem; font-weight: 500; font-size: 0.9rem; min-width: 120px; }
.optimize-controls input, .optimize-controls select {
  border: 1.5px solid var(--border); border-radius: 8px; padding: 0.5rem 0.75rem; background: #fff;
}
.btn-optimize {
  background: var(--gold); color: #fff; border: none; border-radius: 8px;
  padding: 0.6rem 1.75rem; font-size: 1rem; font-weight: 700; cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}
.btn-optimize:hover { background: #b97d03; }
.btn-optimize:active { transform: scale(0.97); }
.btn-optimize:disabled { opacity: 0.6; cursor: not-allowed; }

/* Results */
.results-section img { max-width: 100%; border-radius: 8px; margin-top: 0.75rem; }
.savings-highlight { font-size: 1.25rem; font-weight: 700; color: var(--teal); }
.bill-numbers { display: flex; gap: 1.5rem; margin: 1rem 0; flex-wrap: wrap; }
.bill-item { font-size: 0.9rem; color: var(--text-muted); }
.bill-item strong { display: block; font-size: 1.1rem; color: var(--text); }

/* History */
.history-page { max-width: 960px; margin: 0 auto; padding: 1.5rem; }
```

- [ ] **Step 2: Replace `client/src/pages/Login.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Sai tên đăng nhập hoặc mật khẩu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit} className="auth-form">
        <h1>Q-SmartEnergy</h1>
        <p style={{ textAlign: "center", color: "var(--text-muted)" }}>
          Tiết kiệm điện thông minh bằng AI lượng tử
        </p>
        {error && <p className="auth-error">{error}</p>}
        <label>
          Tên đăng nhập
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label>
          Mật khẩu
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
        <p>
          Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
        </p>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Replace `client/src/pages/Register.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Register() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(username, password);
      navigate("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || "Đăng ký thất bại. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit} className="auth-form">
        <h1>Tạo tài khoản</h1>
        {error && <p className="auth-error">{error}</p>}
        <label>
          Tên đăng nhập
          <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} autoFocus />
        </label>
        <label>
          Mật khẩu (tối thiểu 8 ký tự)
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Đang tạo tài khoản..." : "Đăng ký"}
        </button>
        <p>
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </p>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Verify the auth flow in the browser**

Run both services:
```bash
# Terminal 1
cd server && uvicorn main:app --reload --port 8000
# Terminal 2
cd client && npm run dev
```
Visit `http://localhost:5173/register`, create an account, confirm redirect to `/dashboard` (shows "Dashboard – coming in Task 9"). Visit `/login`, log in with the same account, confirm redirect to `/dashboard`. Ctrl+C both servers.

- [ ] **Step 5: Commit**

```bash
git add client/src/
git commit -m "Add Login/Register pages and base CSS stylesheet (Indigo/Teal/Gold palette)"
```

---

### Task 9: `client/src/pages/Dashboard.jsx` — appliance CRUD + optimize + results

**Files:**
- Modify: `client/src/pages/Dashboard.jsx` (full implementation)

**Interfaces:**
- Consumes: `getAppliances`, `createAppliance`, `updateAppliance`, `deleteAppliance`, `optimize` from `api.js`; `useAuth()` for `logout`; `react-router-dom` `useNavigate`.
- Produces: full dashboard — appliance list (inline power/duration editable), add/delete, day-of-month/weather controls, "Tối ưu hóa" button, results section (Gantt + bill comparison PNG images from backend, bill numbers, savings %).

- [ ] **Step 1: Replace `client/src/pages/Dashboard.jsx`**

```jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance,
} from "../api";
import { useAuth } from "../AuthContext";

const WEATHER_OPTIONS = [
  { value: "sunny", label: "☀️ Nắng" },
  { value: "cloudy", label: "⛅ Có mây" },
  { value: "rainy", label: "🌧 Mưa" },
];

function ApplianceRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);

  function save() {
    if (Number(power) !== appliance.power_w || Number(duration) !== appliance.duration_hours) {
      onSave(appliance.id, { ...appliance, power_w: Number(power), duration_hours: Number(duration) });
    }
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input
          type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)}
          onBlur={save}
        />
      </td>
      <td>
        <input
          type="number" value={duration} min={0.1} step={0.1}
          onChange={(e) => setDuration(e.target.value)}
          onBlur={save}
        />
      </td>
      <td style={{ color: appliance.is_flexible ? "var(--teal)" : "var(--text-muted)" }}>
        {appliance.is_flexible ? "Linh hoạt" : "Cố định"}
      </td>
      <td>
        <button onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

export default function Dashboard() {
  const [appliances, setAppliances] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(9);
  const [weather, setWeather] = useState("sunny");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { loadAppliances(); }, []);

  async function loadAppliances() {
    const data = await getAppliances();
    setAppliances(data);
  }

  async function handleSave(id, payload) {
    await updateAppliance(id, payload);
    await loadAppliances();
  }

  async function handleDelete(id) {
    await deleteAppliance(id);
    await loadAppliances();
  }

  async function handleAdd(e) {
    e.preventDefault();
    await createAppliance({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1);
    await loadAppliances();
  }

  async function handleOptimize() {
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await apiOptimize({ day_of_month: Number(dayOfMonth), weather_condition: weather, use_quantum: true });
      setResult(data);
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() { logout(); navigate("/login"); }

  const totalKwh = appliances.reduce((sum, a) => sum + a.power_w / 1000 * a.duration_hours * 30, 0);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Q-SmartEnergy</h1>
        <nav>
          <button onClick={() => navigate("/history")}>📋 Lịch sử</button>
          <button onClick={handleLogout}>Đăng xuất</button>
        </nav>
      </header>

      {/* Appliance list */}
      <div className="section-card">
        <h2>Thiết bị của bạn — tổng ~{totalKwh.toFixed(0)} kWh/tháng</h2>
        <table>
          <thead>
            <tr><th>Tên thiết bị</th><th>Công suất (W)</th><th>Giờ dùng</th><th>Loại</th><th></th></tr>
          </thead>
          <tbody>
            {appliances.map((a) => (
              <ApplianceRow key={a.id} appliance={a} onSave={handleSave} onDelete={handleDelete} />
            ))}
          </tbody>
        </table>
        <form onSubmit={handleAdd} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName} onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1} onChange={(e) => setNewPower(e.target.value)} required />
          <input type="number" placeholder="Giờ/ngày" value={newDuration} min={0.1} step={0.1} onChange={(e) => setNewDuration(e.target.value)} required />
          <button type="submit">+ Thêm thiết bị</button>
        </form>
      </div>

      {/* Optimize controls */}
      <div className="section-card">
        <h2>Tối ưu hóa lịch chạy</h2>
        <div className="optimize-controls">
          <label>
            Ngày trong tháng
            <input type="number" min={1} max={30} value={dayOfMonth} onChange={(e) => setDayOfMonth(e.target.value)} />
          </label>
          <label>
            Thời tiết hôm nay
            <select value={weather} onChange={(e) => setWeather(e.target.value)}>
              {WEATHER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <button className="btn-optimize" onClick={handleOptimize} disabled={loading}>
            {loading ? "⏳ Đang tối ưu..." : "⚡ Tối ưu hóa"}
          </button>
        </div>
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="section-card results-section">
          <h2>Kết quả</h2>
          <div className="bill-numbers">
            <div className="bill-item">
              <strong>{result.bill_before_vnd.toLocaleString("vi-VN")}đ</strong>
              Hóa đơn trước
            </div>
            <div style={{ fontSize: "1.5rem", alignSelf: "center" }}>→</div>
            <div className="bill-item">
              <strong style={{ color: "var(--teal)" }}>{result.bill_after_vnd.toLocaleString("vi-VN")}đ</strong>
              Sau tối ưu hóa
            </div>
            <div className="bill-item">
              <strong className="savings-highlight">↓ {result.savings_percent.toFixed(1)}%</strong>
              Tiết kiệm
            </div>
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Solver: {result.solver_used}{result.used_fallback ? " (dùng fallback cổ điển)" : ""}
          </p>
          {result.gantt_chart_png && (
            <img src={`data:image/png;base64,${result.gantt_chart_png}`} alt="Lịch chạy thiết bị tối ưu" />
          )}
          {result.bill_chart_png && (
            <img src={`data:image/png;base64,${result.bill_chart_png}`} alt="So sánh hóa đơn điện" style={{ marginTop: "1rem" }} />
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

With both servers running, log in, navigate to `/dashboard`, confirm: appliance list loads, power/duration editable on blur, add a new device, delete a device, click "Tối ưu hóa" (waits ~2-5s) and results appear (Gantt chart image + bar chart image + bill numbers).

- [ ] **Step 3: Commit**

```bash
git add client/src/pages/Dashboard.jsx
git commit -m "Add Dashboard: appliance CRUD, optimize trigger, results with PNG charts"
```

---

### Task 10: `client/src/pages/History.jsx`

**Files:**
- Modify: `client/src/pages/History.jsx` (full implementation)

**Interfaces:**
- Consumes: `getSchedules` from `api.js`; `react-router-dom` `useNavigate`.
- Produces: history page listing all past optimizations (newest first) in a table with date, day, weather, solver, before/after bill, savings %.

- [ ] **Step 1: Replace `client/src/pages/History.jsx`**

```jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSchedules } from "../api";

export default function History() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getSchedules()
      .then(setSchedules)
      .finally(() => setLoading(false));
  }, []);

  const WEATHER_LABELS = { sunny: "☀️ Nắng", cloudy: "⛅ Có mây", rainy: "🌧 Mưa" };

  return (
    <div className="history-page">
      <header className="dashboard-header">
        <h1>Lịch sử tối ưu hóa</h1>
        <button onClick={() => navigate("/dashboard")}>← Quay lại</button>
      </header>

      {loading ? (
        <p style={{ color: "var(--text-muted)", textAlign: "center", marginTop: "2rem" }}>
          Đang tải...
        </p>
      ) : schedules.length === 0 ? (
        <div className="section-card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
          <p>Chưa có lần tối ưu nào. Quay lại Dashboard và thử nhé!</p>
        </div>
      ) : (
        <div className="section-card">
          <table>
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Ngày</th>
                <th>Thời tiết</th>
                <th>Solver</th>
                <th>Trước (đ)</th>
                <th>Sau (đ)</th>
                <th>Tiết kiệm</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.created_at).toLocaleString("vi-VN")}</td>
                  <td>Ngày {s.day_of_month}</td>
                  <td>{WEATHER_LABELS[s.weather_condition] ?? s.weather_condition}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {s.solver_used}{s.used_fallback ? "*" : ""}
                  </td>
                  <td>{s.bill_before_vnd.toLocaleString("vi-VN")}</td>
                  <td style={{ color: "var(--teal)", fontWeight: 600 }}>
                    {s.bill_after_vnd.toLocaleString("vi-VN")}
                  </td>
                  <td style={{ color: "var(--gold)", fontWeight: 700 }}>
                    ↓ {s.savings_percent.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            * fallback: QAOA không hội tụ, dùng brute-force cổ điển
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

After running at least 1 optimization in Dashboard, navigate to `/history` — the past run should appear in the table.

- [ ] **Step 3: Commit**

```bash
git add client/src/pages/History.jsx
git commit -m "Add History page with past optimization results table"
```

---

### Task 11: Framer Motion animation polish — page transitions + micro-interactions + loading + results reveal

**Files:**
- Modify: `client/src/App.jsx` (AnimatePresence for page transitions)
- Create: `client/src/useCountUp.js` (count-up hook for bill numbers)
- Modify: `client/src/pages/Login.jsx` (motion.button micro-interaction)
- Modify: `client/src/pages/Register.jsx` (motion.button micro-interaction)
- Modify: `client/src/pages/Dashboard.jsx` (loading skeleton, results reveal, motion.button)

**Note:** Do this task ONLY after Tasks 8-10 confirm the app works correctly without animation. If running behind on time, this is the first task to cut — per the spec's explicit sequencing.

**Interfaces:**
- Consumes: `framer-motion` (already installed in Task 7).
- Produces: polished animated transitions between pages, button hover/tap feedback, loading state during QAOA call, count-up animation on bill numbers.

- [ ] **Step 1: Update `client/src/App.jsx` for page transitions**

```jsx
import { useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import "./App.css";

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <AuthProvider>
      <AnimatedRoutes />
    </AuthProvider>
  );
}

export default App;
```

- [ ] **Step 2: Create `client/src/useCountUp.js`**

```js
import { useEffect, useState } from "react";

/**
 * Animates a number from 0 to targetValue over durationMs milliseconds.
 * Returns the current animated value (updates each animation frame).
 */
export function useCountUp(targetValue, durationMs = 800) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let startTime = null;
    let frameId;

    function step(timestamp) {
      if (startTime === null) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / durationMs, 1);
      setValue(Math.round(targetValue * progress));
      if (progress < 1) frameId = requestAnimationFrame(step);
    }

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [targetValue, durationMs]);

  return value;
}
```

- [ ] **Step 3: Add page transition wrapper to `Login.jsx`**

Wrap the outer div with `motion.div` and add the `motion.button` micro-interaction. At the top of `Login.jsx`, add the import:
```jsx
import { motion } from "framer-motion";
```

Replace `<div className="auth-page">` with:
```jsx
<motion.div
  className="auth-page"
  initial={{ opacity: 0, y: 16 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -16 }}
  transition={{ duration: 0.25 }}
>
```
And close with `</motion.div>`.

Replace the submit `<button type="submit" ...>` with:
```jsx
<motion.button
  type="submit"
  disabled={loading}
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.97 }}
>
  {loading ? "Đang đăng nhập..." : "Đăng nhập"}
</motion.button>
```

- [ ] **Step 4: Apply the same motion wrapper + button to `Register.jsx`**

Same pattern as Step 3 — wrap outer div in `motion.div` with the same initial/animate/exit/transition, and convert the submit button to `motion.button` with whileHover/whileTap.

- [ ] **Step 5: Update `Dashboard.jsx` — loading skeleton + results reveal + count-up**

Add the imports at the top of `Dashboard.jsx`:
```jsx
import { motion, AnimatePresence } from "framer-motion";
import { useCountUp } from "../useCountUp";
```

Wrap the outer `<div className="dashboard">` in `motion.div`:
```jsx
<motion.div
  className="dashboard"
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  exit={{ opacity: 0 }}
  transition={{ duration: 0.2 }}
>
```

Replace the loading state inside `handleOptimize` so when `loading` is true the button area shows a pulsing skeleton. After the optimize button, add a loading indicator div (conditionally rendered):
```jsx
{loading && (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: [0.4, 1, 0.4] }}
    transition={{ repeat: Infinity, duration: 1.2 }}
    style={{ marginTop: "0.75rem", color: "var(--indigo)", fontWeight: 600 }}
  >
    ⚡ Thuật toán lượng tử đang xử lý...
  </motion.div>
)}
```

Wrap the results section in `AnimatePresence` + `motion.div` for reveal:
Replace `{result && (<div className="section-card results-section">` with:
```jsx
<AnimatePresence>
  {result && (
    <motion.div
      className="section-card results-section"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
```
(and close with `</motion.div></AnimatePresence>` at the end of results block).

Add a `ResultsBillNumbers` sub-component inside `Dashboard.jsx` that uses `useCountUp`:
```jsx
function ResultsBillNumbers({ billBefore, billAfter, savingsPct }) {
  const animBefore = useCountUp(billBefore);
  const animAfter = useCountUp(billAfter);
  const animSavings = useCountUp(savingsPct * 10) / 10; // one decimal

  return (
    <div className="bill-numbers">
      <div className="bill-item">
        <strong>{animBefore.toLocaleString("vi-VN")}đ</strong>
        Hóa đơn trước
      </div>
      <div style={{ fontSize: "1.5rem", alignSelf: "center" }}>→</div>
      <div className="bill-item">
        <strong style={{ color: "var(--teal)" }}>{animAfter.toLocaleString("vi-VN")}đ</strong>
        Sau tối ưu hóa
      </div>
      <div className="bill-item">
        <strong className="savings-highlight">↓ {animSavings.toFixed(1)}%</strong>
        Tiết kiệm
      </div>
    </div>
  );
}
```

Then in the results section, replace the static `<div className="bill-numbers">...` block with:
```jsx
<ResultsBillNumbers
  billBefore={result.bill_before_vnd}
  billAfter={result.bill_after_vnd}
  savingsPct={result.savings_percent}
/>
```

Convert the "Tối ưu hóa" button to `motion.button`:
```jsx
<motion.button
  className="btn-optimize"
  onClick={handleOptimize}
  disabled={loading}
  whileHover={{ scale: loading ? 1 : 1.03 }}
  whileTap={{ scale: loading ? 1 : 0.97 }}
>
  {loading ? "⏳ Đang tối ưu..." : "⚡ Tối ưu hóa"}
</motion.button>
```

- [ ] **Step 6: Verify all animations in browser**

With both servers running, test:
1. Navigate login → dashboard → history: confirm smooth fade/slide transitions between pages.
2. Hover/click the "Tối ưu hóa" button: confirm scale response.
3. Click "Tối ưu hóa": confirm the "Thuật toán lượng tử đang xử lý..." pulse animation appears while waiting.
4. When results appear: confirm fade+scale reveal and the bill numbers count up from 0 to final value.

- [ ] **Step 7: Commit**

```bash
git add client/src/
git commit -m "Add Framer Motion: page transitions, button micro-interactions, loading state, results reveal + count-up"
```

---

### Task 12: Full acceptance verification

**Files:** None created or modified — read-only verification.

- [ ] **Step 1: Run backend test suite**

```bash
cd server && pytest tests/ -v
```
Expected: all tests pass. Record the exact pass count. Note: this includes QAOA tests that take ~2-5s total — expected, not a hang.

- [ ] **Step 2: Run q-smartenergy test suite (no regressions)**

```bash
cd q-smartenergy && pytest tests/ -v
```
Expected: all 95+ tests still pass (the only change to q-smartenergy/ was adding an optional parameter to `grid_purchase_kwh` with a default that preserves all prior behavior).

- [ ] **Step 3: Verify the React app builds without errors**

```bash
cd client && npm run build
```
Expected: Vite produces a `dist/` directory with no compile/type errors.

- [ ] **Step 4: Verify backend starts cleanly**

```bash
cd server && uvicorn main:app --port 8000 &
sleep 3
python -c "import urllib.request, json; r=urllib.request.urlopen('http://localhost:8000/'); print(json.loads(r.read()))"
kill %1 2>/dev/null
```
Expected: prints `{'status': 'ok', 'service': 'Q-SmartEnergy API'}`.

- [ ] **Step 5: End-to-end manual smoke test**

Start both servers in two terminals:
```bash
# Terminal 1
cd server && uvicorn main:app --reload --port 8000
# Terminal 2
cd client && npm run dev
```

Execute this flow manually, confirming each step:
1. Visit `http://localhost:5173/` — redirects to `/login`. Page transitions animate.
2. Click "Đăng ký" — register with a new username + password (8+ chars). Redirects to `/dashboard`.
3. Dashboard loads appliance list (12 default devices). Edit one device's power: change value, click elsewhere. Confirm the table updates.
4. Select weather "Mưa", click "Tối ưu hóa". Pulse animation appears, then result fades in with count-up numbers.
5. Navigate to History. Past run appears in the table.
6. Click "Đăng xuất". Redirects to `/login`.
7. Log back in — same account, same appliance list persists.

- [ ] **Step 6: Confirm no new forbidden phrasing**

```bash
grep -rni "giờ cao điểm\|peak hour\|time-of-use" server/ client/src/
```
Expected: no output.

- [ ] **Step 7: Write the final report**

Record: backend test count, q-smartenergy test count, `npm run build` success, health-check output, and the result of each step in the manual smoke test (pass/fail per step). If any step fails, note exactly what failed so it can be fixed as a follow-up, but do NOT expand scope to fix things that weren't in this plan (e.g., don't refactor the React components or add new features).

- [ ] **Step 8: No commit for this task**

No files changed by this task. If Step 2 revealed a regression in q-smartenergy, fix it in a separate commit with a specific commit message and re-run all verification steps.
