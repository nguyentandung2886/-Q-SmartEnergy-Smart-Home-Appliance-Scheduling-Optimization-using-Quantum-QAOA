"""Admin-only endpoints (role="admin").

Every route depends on get_current_admin, which raises 403 for non-admins — access
is enforced at the backend, not merely hidden in the UI. Provides system-wide stats,
feedback curation (is_featured toggle for the public landing page), a user directory,
and an activity log derived from the existing `schedules` table (no new audit table).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.feedback_router import _customer_name
from auth import get_current_admin
from db.database import get_db
from db.models import BusinessProfile, FeedbackModel, ScheduleModel, User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


class StatsOut(BaseModel):
    users_by_role: dict[str, int]
    total_users: int
    total_feedback: int
    average_rating: float | None
    total_schedules: int
    average_savings_percent: float | None


class AdminFeedbackOut(BaseModel):
    id: int
    rating: int
    message: str
    customer_name: str
    is_featured: bool
    created_at: datetime


class FeaturedUpdate(BaseModel):
    is_featured: bool


class AdminUserOut(BaseModel):
    id: int
    email: str | None
    username: str | None
    role: str
    business_type: str | None
    created_at: datetime | None


class AdminLogOut(BaseModel):
    id: int
    user_email: str | None
    created_at: datetime | None
    solver_used: str
    energy: float
    savings_percent: float | None


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    role_counts = dict(
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    )
    total_users = sum(role_counts.values())
    total_feedback = db.query(func.count(FeedbackModel.id)).scalar() or 0
    avg_rating = db.query(func.avg(FeedbackModel.rating)).scalar()
    total_schedules = db.query(func.count(ScheduleModel.id)).scalar() or 0
    avg_savings = db.query(func.avg(ScheduleModel.savings_percent)).scalar()

    return StatsOut(
        users_by_role={
            "household": role_counts.get("household", 0),
            "business": role_counts.get("business", 0),
            "admin": role_counts.get("admin", 0),
        },
        total_users=total_users,
        total_feedback=total_feedback,
        average_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        total_schedules=total_schedules,
        average_savings_percent=round(float(avg_savings), 2) if avg_savings is not None else None,
    )


@router.get("/feedback", response_model=List[AdminFeedbackOut])
def list_all_feedback(
    rating: Optional[int] = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
):
    query = db.query(FeedbackModel)
    if rating is not None:
        query = query.filter(FeedbackModel.rating == rating)
    rows = query.order_by(FeedbackModel.created_at.desc(), FeedbackModel.id.desc()).all()
    return [
        AdminFeedbackOut(
            id=r.id,
            rating=r.rating,
            message=r.message,
            customer_name=_customer_name(r.user),
            is_featured=r.is_featured,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.patch("/feedback/{feedback_id}", response_model=AdminFeedbackOut)
def update_feedback_featured(
    feedback_id: int,
    payload: FeaturedUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    row.is_featured = payload.is_featured
    db.commit()
    db.refresh(row)
    return AdminFeedbackOut(
        id=row.id,
        rating=row.rating,
        message=row.message,
        customer_name=_customer_name(row.user),
        is_featured=row.is_featured,
        created_at=row.created_at,
    )


@router.get("/users", response_model=List[AdminUserOut])
def list_users(db: Session = Depends(get_db)):
    rows = (
        db.query(User, BusinessProfile.business_type)
        .outerjoin(BusinessProfile, BusinessProfile.user_id == User.id)
        .order_by(User.created_at.desc(), User.id.desc())
        .all()
    )
    return [
        AdminUserOut(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            business_type=business_type,
            created_at=user.created_at,
        )
        for user, business_type in rows
    ]


@router.get("/logs", response_model=List[AdminLogOut])
def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ScheduleModel, User.email)
        .join(User, User.id == ScheduleModel.user_id)
        .order_by(ScheduleModel.created_at.desc(), ScheduleModel.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        AdminLogOut(
            id=schedule.id,
            user_email=email,
            created_at=schedule.created_at,
            solver_used=schedule.solver_used,
            energy=schedule.energy,
            savings_percent=schedule.savings_percent,
        )
        for schedule, email in rows
    ]
