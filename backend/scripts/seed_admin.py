"""Bootstrap the admin account — safely, from environment variables only.

Reads ADMIN_EMAIL, ADMIN_PASSWORD, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
from the environment (never hard-coded). It:

  1. Creates the Supabase Auth user (or finds the existing one) via the Admin REST
     API, stamping `app_metadata: {"role": "admin"}`. Only the service-role key can
     write app_metadata — which is exactly why admin is trusted only from there
     (see backend/auth.py::_resolve_role).
  2. Upserts the matching local `users` row with role="admin".

Run from the backend/ directory:

    python -m scripts.seed_admin

Requires the variables above set in backend/.env (see .env.example). The
SERVICE_ROLE_KEY is a secret — never log it or commit its real value.
"""
import os
import sys

import httpx
from dotenv import load_dotenv

# Allow running as `python scripts/seed_admin.py` from backend/ as well as `-m`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal  # noqa: E402
from db.models import User  # noqa: E402

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"ERROR: {name} must be set in the environment (see backend/.env.example).")
    return value


def _find_user_id_by_email(base_url: str, headers: dict, email: str) -> str | None:
    """Look up an existing Supabase Auth user id by email (admin list endpoint)."""
    resp = httpx.get(
        f"{base_url}/auth/v1/admin/users",
        headers=headers,
        params={"per_page": 200},
        timeout=30,
    )
    resp.raise_for_status()
    for user in resp.json().get("users", []):
        if (user.get("email") or "").lower() == email.lower():
            return user.get("id")
    return None


def _ensure_supabase_admin(base_url: str, service_key: str, email: str, password: str) -> str:
    """Create the admin auth user (or update the existing one) and return its uid."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    admin_meta = {"role": "admin"}

    resp = httpx.post(
        f"{base_url}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "app_metadata": admin_meta,
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        uid = resp.json()["id"]
        print(f"Created Supabase admin user {email} ({uid}).")
        return uid

    # Already exists → find it and make sure app_metadata.role is "admin".
    uid = _find_user_id_by_email(base_url, headers, email)
    if not uid:
        sys.exit(f"ERROR: could not create or find admin user ({resp.status_code}): {resp.text}")

    update = httpx.put(
        f"{base_url}/auth/v1/admin/users/{uid}",
        headers=headers,
        json={"app_metadata": admin_meta},
        timeout=30,
    )
    update.raise_for_status()
    print(f"Updated existing Supabase user {email} ({uid}) → app_metadata.role=admin.")
    return uid


def _upsert_local_admin(uid: str, email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.supabase_uid == uid).first()
        if user is None:
            user = User(supabase_uid=uid, email=email, role="admin")
            db.add(user)
            print(f"Created local users row for admin {email}.")
        else:
            user.role = "admin"
            print(f"Updated local users row {user.id} → role=admin.")
        db.commit()
    finally:
        db.close()


def main() -> None:
    base_url = _require_env("SUPABASE_URL").rstrip("/")
    service_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    email = _require_env("ADMIN_EMAIL")
    password = _require_env("ADMIN_PASSWORD")

    uid = _ensure_supabase_admin(base_url, service_key, email, password)
    _upsert_local_admin(uid, email)
    print("Admin seed complete.")


if __name__ == "__main__":
    main()
