"""
Supabase Auth token validation for Q-SmartEnergy backend.

Signup/login happen client-side via Supabase Auth. The backend only *validates*
the Supabase access token (asymmetric JWKS — ES256/RS256) and maps it to a local
`users` row (get-or-create), keyed by the Supabase user UUID (`sub`).
Requires SUPABASE_URL in the environment (see .env.example).
"""
import os
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWKClient, PyJWKClientError
from sqlalchemy.orm import Session

from core import appliance_catalog
from db.database import get_db
from db.models import ApplianceModel, User

SUPABASE_URL = os.environ.get("SUPABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL must be set (e.g. https://<ref>.supabase.co) — used to verify "
        "Supabase Auth tokens. See .env.example."
    )
SUPABASE_URL = SUPABASE_URL.rstrip("/")

JWT_ISSUER = f"{SUPABASE_URL}/auth/v1"
JWT_AUDIENCE = "authenticated"
_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
# Tolerate clock skew between this machine and Supabase so freshly-issued tokens
# (iat ~= now) aren't rejected as "not yet valid". Also relaxes exp by the same margin.
_CLOCK_SKEW_LEEWAY = timedelta(seconds=120)

# PyJWKClient caches fetched signing keys, so this is a single lazy HTTP fetch.
_jwks_client = PyJWKClient(_JWKS_URL)
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=True)


def _seed_default_appliances(db: Session, user: User) -> None:
    for a in appliance_catalog.HOUSEHOLD_APPLIANCES:
        db.add(ApplianceModel(
            user_id=user.id,
            name=a.name,
            power_w=a.power_w,
            duration_hours=a.duration_hours,
            candidate_hours=list(a.candidate_hours),
            is_flexible=a.is_flexible,
        ))


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            leeway=_CLOCK_SKEW_LEEWAY,
        )
        supabase_uid: str = payload.get("sub")
        if not supabase_uid:
            raise credentials_error
    except (jwt.PyJWTError, PyJWKClientError):
        raise credentials_error

    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()
    if user is None:
        # First time we see this Supabase user: create their local row and seed
        # the default household appliances (previously done on /auth/register).
        user = User(supabase_uid=supabase_uid, email=payload.get("email"))
        db.add(user)
        db.flush()  # get user.id before seeding appliances
        _seed_default_appliances(db, user)
        db.commit()
        db.refresh(user)
    return user
