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
from core.business_calc import EVN_BUSINESS_TIERS
from db.database import get_db
from db.models import ApplianceModel, BusinessProfile, User

_BUSINESS_TYPES = {"production", "commercial"}

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


def _resolve_role(payload: dict) -> str:
    """Decide a new user's role from the JWT claims.

    SECURITY: `admin` is trusted only from `app_metadata`, which the public signup
    flow cannot write — only the seed script (service-role key) can. Any `role` a
    user places in `user_metadata` is user-controlled, so an `admin` value there is
    ignored and forced down to `household`.
    """
    app_metadata = payload.get("app_metadata") or {}
    if app_metadata.get("role") == "admin":
        return "admin"

    user_metadata = payload.get("user_metadata") or {}
    if user_metadata.get("role") == "business":
        return "business"
    # Anything else — including a forged "admin" in user_metadata — is a household.
    return "household"


def _create_business_profile(db: Session, user: User, payload: dict) -> None:
    meta = payload.get("user_metadata") or {}
    business_type = meta.get("business_type")
    if business_type not in _BUSINESS_TYPES:
        business_type = "commercial"

    contracted_power_kw = meta.get("contracted_power_kw")
    try:
        contracted_power_kw = float(contracted_power_kw) if contracted_power_kw is not None else None
    except (TypeError, ValueError):
        contracted_power_kw = None

    # Cấp điện áp đấu nối: chỉ nhận key có trong biểu giá của business_type đã chọn
    # (kinh doanh không có "tren_110kv"); giá trị lạ để None — billing sẽ fallback
    # "duoi_6kv" và ghi log (xem optimize_router).
    voltage_level = meta.get("voltage_level")
    if voltage_level not in EVN_BUSINESS_TIERS[business_type]:
        voltage_level = None

    db.add(BusinessProfile(
        user_id=user.id,
        business_type=business_type,
        scale=meta.get("scale"),
        contracted_power_kw=contracted_power_kw,
        voltage_level=voltage_level,
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
        # First time we see this Supabase user: create their local row. Role comes
        # from the JWT claims (see _resolve_role — admin only via app_metadata).
        role = _resolve_role(payload)
        user = User(supabase_uid=supabase_uid, email=payload.get("email"), role=role)
        db.add(user)
        db.flush()  # get user.id before seeding appliances / profile
        if role == "business":
            # Businesses declare their own machinery via the Devices tab — no
            # default household appliances.
            _create_business_profile(db, user, payload)
        elif role == "household":
            _seed_default_appliances(db, user)
        # admin: no appliances, no business profile.
        db.commit()
        db.refresh(user)
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the caller to be an admin. Layered on get_current_user so token
    validation (and the test override) is reused; raises 403 for any other role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
