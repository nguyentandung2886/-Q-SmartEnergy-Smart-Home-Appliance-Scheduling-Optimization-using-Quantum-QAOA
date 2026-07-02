"""
SQLAlchemy ORM models: User, ApplianceModel, ScheduleModel.
Schema:
  users       — id, supabase_uid (unique, from Supabase Auth), email,
                username (optional/legacy display), created_at
  appliances  — id, user_id FK, name, power_w, duration_hours,
                candidate_hours (JSON list of ints, [] if is_flexible=False),
                is_flexible, created_at
  schedules   — id, user_id FK, created_at, day_of_month, weather_condition,
                solver_used, used_fallback, energy, schedule_json (JSON string),
                monthly_kwh (snapshot), bill_before_vnd (snapshot), bill_after_vnd (snapshot)
  feedback    — id, user_id FK, rating (1-5), message, is_featured, created_at
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    supabase_uid = Column(String(36), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    username = Column(String(50), nullable=True)
    # "household" (default), "business", or "admin". Admin is granted only via the
    # seed script (app_metadata), never through public signup — see auth.py.
    role = Column(String(20), nullable=False, server_default="household", default="household")
    created_at = Column(DateTime, server_default=func.now())

    appliances = relationship("ApplianceModel", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("ScheduleModel", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("FeedbackModel", back_populates="user", cascade="all, delete-orphan")
    business_profile = relationship(
        "BusinessProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    business_type = Column(String(20), nullable=False)  # "production" | "commercial"
    scale = Column(String(50), nullable=True)
    contracted_power_kw = Column(Float, nullable=True)
    # Cấp điện áp đấu nối — key trong business_calc.EVN_BUSINESS_TIERS ("tren_110kv",
    # "22_den_110kv", "6_den_22kv", "duoi_6kv"). Nullable: tài khoản tạo trước khi có
    # field này — billing fallback về "duoi_6kv" (phổ biến nhất).
    voltage_level = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="business_profile")


class ApplianceModel(Base):
    __tablename__ = "appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    power_w = Column(Float, nullable=False)
    duration_hours = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    candidate_hours = Column(JSON, nullable=False, default=list)
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
    # Fixed appliances' usage windows {name: [[start, length], ...]} — needed to fully
    # rehydrate the schedule (and the Gantt's fixed-appliance hours) after a page reload.
    fixed_windows_json = Column(JSON, nullable=True)

    user = relationship("User", back_populates="schedules")


class FeedbackModel(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    message = Column(Text, nullable=False)
    # Admin-curated: only is_featured=True feedback is served on the public landing
    # page (GET /feedback/public). Toggled via PATCH /admin/feedback/{id}.
    is_featured = Column(Boolean, nullable=False, server_default="0", default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="feedback")
