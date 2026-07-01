"""
Auth endpoint: GET /auth/me.

Signup/login are handled client-side by Supabase Auth — the backend no longer
issues tokens. On the first authenticated request, `get_current_user` creates the
local user row and seeds default appliances (see auth.py).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from auth import get_current_user
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supabase_uid: str
    email: str | None = None
    username: str | None = None


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
