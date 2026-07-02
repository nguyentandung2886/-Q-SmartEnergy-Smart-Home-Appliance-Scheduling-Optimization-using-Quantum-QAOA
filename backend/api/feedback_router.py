"""Feedback endpoints.

Most routes require valid JWT (see auth.get_current_user): any logged-in user may
submit feedback and read every user's feedback — the project has no admin role yet,
so the feedback list is shared across all authenticated users.

The one exception is GET /feedback/public, which serves the landing page's
testimonials to logged-out visitors and never exposes user_id/email.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from db.database import get_db
from db.models import FeedbackModel, User

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _customer_name(user: User) -> str:
    """Display name for a feedback author. Never empty: falls back to the email
    local-part, then to a generic anonymous label."""
    if user is not None:
        if user.username:
            return user.username
        if user.email:
            local = user.email.split("@")[0]
            if local:
                return local
    return "Khách hàng ẩn danh"


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    message: str = Field(min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    id: int
    rating: int
    message: str
    customer_name: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _derive_customer_name(cls, data):
        # When serialising an ORM row, resolve the author's display name from the
        # related User so the authenticated endpoints keep returning rows unchanged.
        if isinstance(data, FeedbackModel):
            return {
                "id": data.id,
                "rating": data.rating,
                "message": data.message,
                "customer_name": _customer_name(data.user),
                "created_at": data.created_at,
            }
        return data


class PublicFeedbackOut(BaseModel):
    rating: int
    message: str
    customer_name: str
    created_at: datetime


@router.get("", response_model=List[FeedbackOut])
def list_feedback(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(FeedbackModel)
        .order_by(FeedbackModel.created_at.desc(), FeedbackModel.id.desc())
        .all()
    )


@router.get("/me", response_model=List[FeedbackOut])
def list_my_feedback(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(FeedbackModel)
        .filter(FeedbackModel.user_id == current_user.id)
        .order_by(FeedbackModel.created_at.desc(), FeedbackModel.id.desc())
        .all()
    )


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = FeedbackModel(user_id=current_user.id, rating=payload.rating, message=payload.message)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/public", response_model=List[PublicFeedbackOut])
def list_public_feedback(db: Session = Depends(get_db)):
    """Latest feedback for the public landing page. No auth; no user_id/email exposed."""
    rows = (
        db.query(FeedbackModel)
        .order_by(FeedbackModel.created_at.desc(), FeedbackModel.id.desc())
        .limit(9)
        .all()
    )
    return [
        PublicFeedbackOut(
            rating=r.rating,
            message=r.message,
            customer_name=_customer_name(r.user),
            created_at=r.created_at,
        )
        for r in rows
    ]
