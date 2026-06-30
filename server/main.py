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

from sqlalchemy import text

from database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

# Idempotent migration: add savings_percent column if not present (existing installs).
with engine.begin() as _conn:
    try:
        _conn.execute(text("ALTER TABLE schedules ADD savings_percent FLOAT NULL"))
    except Exception:
        pass  # Column already exists

# Idempotent migration: add quantity column if not present.
with engine.begin() as _conn:
    try:
        _conn.execute(text("ALTER TABLE appliances ADD quantity INT NOT NULL DEFAULT 1"))
    except Exception:
        pass  # Column already exists

# Idempotent migration: convert VARCHAR → NVARCHAR for Unicode (Vietnamese text).
# appliances.name and schedules.schedule_json are the critical columns.
with engine.begin() as _conn:
    for _stmt in [
        "ALTER TABLE appliances ALTER COLUMN name NVARCHAR(100) NOT NULL",
        "ALTER TABLE schedules ALTER COLUMN schedule_json NVARCHAR(MAX) NOT NULL",
    ]:
        try:
            _conn.execute(text(_stmt))
        except Exception:
            pass  # Already NVARCHAR, or not applicable

# Re-seed appliances whose names were corrupted by old VARCHAR storage (contain '?').
from models import ApplianceModel as _ApplianceModel
import appliance_catalog as _catalog

_db = SessionLocal()
try:
    _corrupted_ids = [
        r[0] for r in _db.execute(
            text("SELECT DISTINCT user_id FROM appliances WHERE name LIKE '%?%'")
        ).fetchall()
    ]
    for _uid in _corrupted_ids:
        _db.query(_ApplianceModel).filter(_ApplianceModel.user_id == _uid).delete()
        for _a in _catalog.HOUSEHOLD_APPLIANCES:
            _db.add(_ApplianceModel(
                user_id=_uid,
                name=_a.name,
                power_w=_a.power_w,
                duration_hours=_a.duration_hours,
                candidate_hours=",".join(str(h) for h in _a.candidate_hours),
                is_flexible=_a.is_flexible,
            ))
    if _corrupted_ids:
        _db.commit()
finally:
    _db.close()

app = FastAPI(title="Q-SmartEnergy API", version="1.0.0")

_default_origins = "http://localhost:5173,http://localhost:3000"
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import auth_router, appliances_router, optimize_router
import explain_router

app.include_router(auth_router.router)
app.include_router(appliances_router.router)
app.include_router(optimize_router.router)
app.include_router(explain_router.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Q-SmartEnergy API"}
