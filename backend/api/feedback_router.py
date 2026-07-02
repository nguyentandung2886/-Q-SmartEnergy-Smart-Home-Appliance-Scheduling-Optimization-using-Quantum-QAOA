"""Feedback endpoints. All routes require valid JWT (see auth.get_current_user).

Any logged-in user may submit feedback and read every user's feedback — the project
has no admin role yet, so the feedback list is shared across all authenticated users.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from db.database import get_db
from db.models import FeedbackModel, User

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    message: str = Field(min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    id: int
    rating: int
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[FeedbackOut])
def list_feedback(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(FeedbackModel)
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
