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


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import Base, engine

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

from api import auth_router, appliances_router, optimize_router
from api import explain_router
from api import forecast_router
from api import weather_router, alert_router
from api import feedback_router
from api import admin_router

app.include_router(auth_router.router)
app.include_router(appliances_router.router)
app.include_router(optimize_router.router)
app.include_router(explain_router.router)
app.include_router(forecast_router.router)
app.include_router(weather_router.router)
app.include_router(alert_router.router)
app.include_router(feedback_router.router)
app.include_router(admin_router.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Q-SmartEnergy API"}
