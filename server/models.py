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
    savings_percent = Column(Float, nullable=True)

    user = relationship("User", back_populates="schedules")
