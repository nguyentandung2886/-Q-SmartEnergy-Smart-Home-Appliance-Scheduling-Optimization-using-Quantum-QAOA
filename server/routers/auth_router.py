"""
Auth endpoints: POST /auth/register, POST /auth/login.
On register: user created + appliances seeded from appliance_catalog.HOUSEHOLD_APPLIANCES.
Passwords hashed with bcrypt — never stored as plaintext.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import appliance_catalog
from auth import create_access_token, hash_password, verify_password
from database import get_db
from models import ApplianceModel, User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()  # flush to get user.id before creating appliances

    for a in appliance_catalog.HOUSEHOLD_APPLIANCES:
        db.add(ApplianceModel(
            user_id=user.id,
            name=a.name,
            power_w=a.power_w,
            duration_hours=a.duration_hours,
            candidate_hours=list(a.candidate_hours),
            is_flexible=a.is_flexible,
        ))

    db.commit()
    return TokenResponse(access_token=create_access_token(user.username))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username))
