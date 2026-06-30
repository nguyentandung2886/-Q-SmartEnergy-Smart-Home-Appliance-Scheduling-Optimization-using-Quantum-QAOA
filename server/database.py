"""
SQLAlchemy engine, session, and base for Q-SmartEnergy backend.
Connection string comes from .env — never hard-coded (see .env.example).
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# SQLite by default — zero-config for local dev and the Docker demo.
# Override with DATABASE_URL in .env for another backend.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./q_smartenergy.db")

# SQLite + multithreaded FastAPI needs check_same_thread disabled.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
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
