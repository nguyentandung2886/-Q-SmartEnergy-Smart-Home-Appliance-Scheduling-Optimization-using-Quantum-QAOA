"""Seed two demo business accounts (Production + Commercial) end-to-end.

This reproduces the REAL signup flow instead of writing straight to the backend
DB, so what you get is exactly what the running app would create:

  1. Create the Supabase Auth user via the Admin REST API, stamping the same
     `user_metadata` that client/src/pages/Register.jsx sends on signUp()
     (role/business_type/voltage_level/scale/contracted_power_kw).
  2. Log in with email+password through the Supabase token endpoint (anon key)
     to obtain an access token.
  3. GET {API_BASE_URL}/auth/me with that token — this is what makes the backend
     create the local User + BusinessProfile row (see auth.py::get_current_user).
     We assert role/business_type match before touching appliances.
  4. GET /appliances, then POST only the missing devices from the list below.

Everything is idempotent: re-running never duplicates a user or a device.

Requires:
  * backend running at API_BASE_URL (default http://localhost:8000)
  * SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in backend/.env (like seed_admin.py)
  * a Supabase anon key — read from SUPABASE_ANON_KEY / VITE_SUPABASE_ANON_KEY,
    or auto-loaded from client/.env (VITE_SUPABASE_ANON_KEY).

Run from anywhere:

    python backend/scripts/seed_demo_business_accounts.py
    API_BASE_URL=http://localhost:8000 python backend/scripts/seed_demo_business_accounts.py
    python backend/scripts/seed_demo_business_accounts.py http://localhost:8000
"""
import os
import sys

import httpx
from dotenv import dotenv_values, load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)

# Load backend/.env explicitly so the script works from any CWD.
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEMO_PASSWORD = "Demo@12345"

# Shared business attributes (test data — not secrets).
_COMMON = {
    "voltage_level": "duoi_6kv",   # key valid for both tariffs (see auth.py / Register.jsx)
    "contracted_power_kw": 15,
}

# Device lists — used verbatim. Tuple = (name, power_w, duration_hours, is_flexible, candidate_hours)
PRODUCTION_APPLIANCES = [
    ("Máy nén khí trục vít 7.5HP", 5500, 4, True, [3, 14]),
    ("Máy hàn hồ quang inverter", 4000, 2, True, [9, 15]),
    ("Lò sấy công nghiệp", 6000, 3, True, [2, 13]),
    ("Máy CNC cắt nhỏ", 3000, 3, True, [4, 11]),
    ("Motor băng chuyền 3 pha", 5500, 8, False, []),
    ("Đèn nhà xưởng LED", 2000, 10, False, []),
]

COMMERCIAL_APPLIANCES = [
    ("Điều hòa trung tâm cửa hàng", 3500, 10, False, []),
    ("Tủ đông/tủ mát trưng bày", 800, 24, False, []),
    ("Đèn LED biển hiệu + chiếu sáng", 1200, 12, False, []),
    ("Máy pha cà phê công nghiệp", 2500, 1, True, [5, 6]),
    ("Máy rửa chén công nghiệp", 3000, 1.5, True, [3, 14]),
    ("Quạt/hệ thống thông gió", 500, 10, False, []),
]

DEMO_ACCOUNTS = [
    {
        "email": "demo.sanxuat@qsmart.local",
        "password": DEMO_PASSWORD,
        "business_type": "production",
        "scale": "Vừa",   # valid option value in Register.jsx
        "appliances": PRODUCTION_APPLIANCES,
    },
    {
        "email": "demo.thuongmai@qsmart.local",
        "password": DEMO_PASSWORD,
        "business_type": "commercial",
        "scale": "Nhỏ",   # valid option value in Register.jsx
        "appliances": COMMERCIAL_APPLIANCES,
    },
]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"ERROR: {name} phải được đặt trong môi trường (xem backend/.env.example).")
    return value


def _resolve_anon_key() -> str:
    """The anon key is public; prefer env, else fall back to client/.env."""
    for name in ("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    client_env = dotenv_values(os.path.join(_ROOT_DIR, "client", ".env"))
    key = client_env.get("VITE_SUPABASE_ANON_KEY")
    if key:
        return key
    sys.exit(
        "ERROR: không tìm thấy Supabase anon key. Đặt SUPABASE_ANON_KEY trong môi trường, "
        "hoặc để VITE_SUPABASE_ANON_KEY trong client/.env (xem backend/.env.example)."
    )


def _admin_headers(service_key: str) -> dict:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }


def _find_user_id_by_email(base_url: str, headers: dict, email: str) -> str | None:
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


def _ensure_supabase_user(base_url: str, service_key: str, account: dict) -> str:
    """Create the Supabase Auth user (or update the existing one) with the exact
    user_metadata the Register.jsx signup flow sends. Returns the user id."""
    headers = _admin_headers(service_key)
    user_metadata = {
        "role": "business",
        "business_type": account["business_type"],
        "voltage_level": _COMMON["voltage_level"],
        "scale": account["scale"],
        "contracted_power_kw": _COMMON["contracted_power_kw"],
    }

    resp = httpx.post(
        f"{base_url}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": account["email"],
            "password": account["password"],
            "email_confirm": True,
            "user_metadata": user_metadata,
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        uid = resp.json()["id"]
        print(f"  [supabase] tạo mới user {account['email']} ({uid}).")
        return uid

    # Already exists → find it and re-apply metadata + password (idempotent).
    uid = _find_user_id_by_email(base_url, headers, account["email"])
    if not uid:
        sys.exit(
            f"ERROR: không tạo được và không tìm thấy user {account['email']} "
            f"({resp.status_code}): {resp.text}"
        )
    update = httpx.put(
        f"{base_url}/auth/v1/admin/users/{uid}",
        headers=headers,
        json={
            "password": account["password"],
            "email_confirm": True,
            "user_metadata": user_metadata,
        },
        timeout=30,
    )
    update.raise_for_status()
    print(f"  [supabase] đã tồn tại, cập nhật user_metadata {account['email']} ({uid}).")
    return uid


def _login(base_url: str, anon_key: str, email: str, password: str) -> str:
    resp = httpx.post(
        f"{base_url}/auth/v1/token",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        params={"grant_type": "password"},
        json={"email": email, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"ERROR: đăng nhập Supabase thất bại cho {email} ({resp.status_code}): {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        sys.exit(f"ERROR: không nhận được access_token cho {email}: {resp.text}")
    return token


def _api(method: str, api_base: str, path: str, token: str, **kwargs):
    """Call the backend, turning a connection refusal into a clear message."""
    try:
        return httpx.request(
            method,
            f"{api_base}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            **kwargs,
        )
    except httpx.ConnectError:
        sys.exit(
            f"ERROR: không kết nối được backend tại {api_base}. "
            "Backend chưa chạy — hãy `uvicorn main:app --reload` trong thư mục backend/ trước."
        )


def _verify_me(api_base: str, token: str, account: dict) -> None:
    """Trigger local User/BusinessProfile creation and assert config is correct."""
    resp = _api("GET", api_base, "/auth/me", token)
    if resp.status_code != 200:
        sys.exit(f"ERROR: GET /auth/me thất bại cho {account['email']} ({resp.status_code}): {resp.text}")
    me = resp.json()
    if me.get("role") != "business":
        sys.exit(
            f"ERROR: {account['email']} có role='{me.get('role')}' (mong đợi 'business'). "
            "Dừng lại, không thêm thiết bị vào tài khoản sai cấu hình."
        )
    profile = me.get("business_profile") or {}
    if profile.get("business_type") != account["business_type"]:
        sys.exit(
            f"ERROR: {account['email']} có business_type='{profile.get('business_type')}' "
            f"(mong đợi '{account['business_type']}'). Dừng lại, không thêm thiết bị."
        )
    print(f"  [api] /auth/me OK — role=business, business_type={account['business_type']}.")


def _seed_appliances(api_base: str, token: str, appliances: list) -> tuple[int, int]:
    """POST only the devices missing by name. Returns (added, already_present)."""
    resp = _api("GET", api_base, "/appliances", token)
    if resp.status_code != 200:
        sys.exit(f"ERROR: GET /appliances thất bại ({resp.status_code}): {resp.text}")
    existing_names = {a["name"] for a in resp.json()}

    added = present = 0
    for name, power_w, duration_hours, is_flexible, candidate_hours in appliances:
        if name in existing_names:
            present += 1
            print(f"    - đã tồn tại, bỏ qua: {name}")
            continue
        create = _api(
            "POST", api_base, "/appliances", token,
            json={
                "name": name,
                "power_w": power_w,
                "duration_hours": duration_hours,
                "is_flexible": is_flexible,
                "candidate_hours": candidate_hours,
            },
        )
        if create.status_code != 201:
            sys.exit(f"ERROR: POST /appliances thất bại cho '{name}' ({create.status_code}): {create.text}")
        added += 1
        print(f"    + đã thêm: {name}")
    return added, present


def main() -> None:
    api_base = (
        (sys.argv[1] if len(sys.argv) > 1 else None)
        or os.environ.get("API_BASE_URL")
        or DEFAULT_API_BASE_URL
    ).rstrip("/")

    base_url = _require_env("SUPABASE_URL").rstrip("/")
    service_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = _resolve_anon_key()

    print("=" * 70)
    print(f"Supabase project : {base_url}")
    print(f"Backend API      : {api_base}")
    print("Nếu Supabase URL ở trên KHÔNG phải project dev/local, hãy Ctrl+C ngay.")
    print("=" * 70)

    summary = []
    for account in DEMO_ACCOUNTS:
        print(f"\n>>> {account['email']} ({account['business_type']})")
        _ensure_supabase_user(base_url, service_key, account)
        token = _login(base_url, anon_key, account["email"], account["password"])
        _verify_me(api_base, token, account)
        added, present = _seed_appliances(api_base, token, account["appliances"])
        summary.append((account, added, present))

    print("\n" + "=" * 70)
    print("TÓM TẮT")
    print("=" * 70)
    print(f"{'Email':<30} {'Mật khẩu':<12} {'Loại':<11} {'Thêm':>5} {'Có sẵn':>7}")
    print("-" * 70)
    for account, added, present in summary:
        print(
            f"{account['email']:<30} {account['password']:<12} "
            f"{account['business_type']:<11} {added:>5} {present:>7}"
        )
    print("-" * 70)
    print("Đăng nhập tại /login bằng thông tin trên để xem trên web.")


if __name__ == "__main__":
    main()
