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

from database import Base, engine

Base.metadata.create_all(bind=engine)

# Idempotent migration: add savings_percent column if not present (existing installs).
with engine.begin() as _conn:
    try:
        _conn.execute(text("ALTER TABLE schedules ADD savings_percent FLOAT NULL"))
    except Exception:
        pass  # Column already exists

app = FastAPI(title="Q-SmartEnergy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React Vite dev server
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
