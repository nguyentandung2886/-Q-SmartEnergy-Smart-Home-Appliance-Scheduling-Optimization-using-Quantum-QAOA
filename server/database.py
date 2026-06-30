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
