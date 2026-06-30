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

# SQLite stores TEXT as Unicode natively, so create_all builds the complete
# current schema for a fresh DB — no per-column ALTER TABLE migrations needed.
Base.metadata.create_all(bind=engine)

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
import forecast_router

app.include_router(auth_router.router)
app.include_router(appliances_router.router)
app.include_router(optimize_router.router)
app.include_router(explain_router.router)
app.include_router(forecast_router.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Q-SmartEnergy API"}
