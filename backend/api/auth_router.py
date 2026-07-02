"""
Auth endpoint: GET /auth/me.

Signup/login are handled client-side by Supabase Auth — the backend no longer
issues tokens. On the first authenticated request, `get_current_user` creates the
local user row and seeds default appliances (see auth.py).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from db.database import get_db
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supabase_uid: str
    email: str | None = None
    username: str | None = None


class MeUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=50)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=MeResponse)
def update_me(
    payload: MeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.username = payload.username
    db.commit()
    db.refresh(current_user)
    return current_user
