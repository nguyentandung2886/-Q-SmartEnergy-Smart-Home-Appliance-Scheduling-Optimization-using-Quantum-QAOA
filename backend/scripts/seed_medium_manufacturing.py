"""Seed một tài khoản DOANH NGHIỆP SẢN XUẤT QUY MÔ VỪA (production, vừa)
kèm thiết bị đầy đủ thông số để test tính năng tối ưu hóa.

Quy trình (giống hệt seed_demo_business_accounts.py — real signup flow):
  1. Tạo Supabase Auth user với user_metadata phù hợp.
  2. Đăng nhập lấy access_token.
  3. GET /auth/me → kích hoạt tạo local User + BusinessProfile.
  4. POST từng thiết bị còn thiếu (có quantity > 1).

Chạy:
    python backend/scripts/seed_medium_manufacturing.py
"""
import os
import sys

import httpx
from dotenv import dotenv_values, load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)

load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

DEFAULT_API_BASE_URL = "http://localhost:8000"
PASSWORD = "Demo@12345"

# --- Thông số doanh nghiệp ---
# Công suất hợp đồng 150 kVA — phù hợp sản xuất vừa với ~10-15 thiết bị
BUSINESS_CONFIG = {
    "voltage_level": "6_den_22kv",   # trung áp 6-22kV
    "contracted_power_kw": 150,
}

# (name, power_w, duration_hours, is_flexible, candidate_hours, quantity)
# Tổng khoảng 10 loại thiết bị, quantity phản ánh xưởng vừa
MANUFACTURING_APPLIANCES = [
    # --- Thiết bị linh hoạt (có thể dời giờ) ---
    ("Máy nén khí trục vít 15HP",  11000, 4,  True, [3, 5, 14],      3),
    ("Máy hàn hồ quang inverter",   5000,  2,  True, [8, 10, 15],    5),
    ("Lò sấy công nghiệp",         12000,  3,  True, [2, 6, 13],      2),
    ("Máy CNC cỡ trung",            8000,  4,  True, [4, 8, 12],     4),
    ("Máy bơm nước công nghiệp",    5500,  2,  True, [1, 5, 8],      3),
    ("Máy phay CNC",                7000,  3,  True, [3, 7, 11],     2),

    # --- Thiết bị cố định (chạy theo ca) ---
    ("Motor băng chuyền 3 pha",     7500,  8,  False, [],             6),
    ("Đèn nhà xưởng LED",          3000, 10,  False, [],             2),
    ("Hệ thống điều hòa trung tâm",15000,  8,  False, [],             1),
    ("Quạt thông gió công nghiệp",  1500, 10,  False, [],            10),
    ("Máy nén lạnh kho mát",        4000, 24,  False, [],             2),
    ("Hệ thống lọc bụi",            5000,  8,  False, [],             1),
]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"ERROR: {name} phải được đặt trong môi trường.")
    return value


def _resolve_anon_key() -> str:
    for name in ("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    client_env = dotenv_values(os.path.join(_ROOT_DIR, "client", ".env"))
    key = client_env.get("VITE_SUPABASE_ANON_KEY")
    if key:
        return key
    sys.exit("ERROR: không tìm thấy Supabase anon key.")


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


def _ensure_supabase_user(base_url: str, service_key: str, email: str) -> str:
    headers = _admin_headers(service_key)
    user_metadata = {
        "role": "business",
        "business_type": "production",
        "voltage_level": BUSINESS_CONFIG["voltage_level"],
        "scale": "Vừa",
        "contracted_power_kw": BUSINESS_CONFIG["contracted_power_kw"],
    }
    resp = httpx.post(
        f"{base_url}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": email,
            "password": PASSWORD,
            "email_confirm": True,
            "user_metadata": user_metadata,
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        uid = resp.json()["id"]
        print(f"  [supabase] tạo mới user {email} ({uid}).")
        return uid

    uid = _find_user_id_by_email(base_url, headers, email)
    if not uid:
        sys.exit(
            f"ERROR: không tạo được và không tìm thấy user {email} "
            f"({resp.status_code}): {resp.text}"
        )
    update = httpx.put(
        f"{base_url}/auth/v1/admin/users/{uid}",
        headers=headers,
        json={
            "password": PASSWORD,
            "email_confirm": True,
            "user_metadata": user_metadata,
        },
        timeout=30,
    )
    update.raise_for_status()
    print(f"  [supabase] đã tồn tại, cập nhật user_metadata {email} ({uid}).")
    return uid


def _login(base_url: str, anon_key: str, email: str) -> str:
    resp = httpx.post(
        f"{base_url}/auth/v1/token",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        params={"grant_type": "password"},
        json={"email": email, "password": PASSWORD},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"ERROR: đăng nhập thất bại cho {email}: {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        sys.exit(f"ERROR: không nhận được access_token cho {email}")
    return token


def _api(method: str, api_base: str, path: str, token: str, **kwargs):
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
            "Hãy chạy backend trước."
        )


def _verify_me(api_base: str, token: str, email: str) -> None:
    resp = _api("GET", api_base, "/auth/me", token)
    if resp.status_code != 200:
        sys.exit(f"ERROR: GET /auth/me thất bại ({resp.status_code}): {resp.text}")
    me = resp.json()
    if me.get("role") != "business":
        sys.exit(f"ERROR: role={me.get('role')} — mong đợi 'business'.")
    profile = me.get("business_profile") or {}
    if profile.get("business_type") != "production":
        sys.exit(f"ERROR: business_type={profile.get('business_type')} — mong đợi 'production'.")
    print(f"  [api] /auth/me OK — role=business, business_type=production.")


def _seed_appliances(api_base: str, token: str, appliances: list) -> tuple[int, int]:
    resp = _api("GET", api_base, "/appliances", token)
    if resp.status_code != 200:
        sys.exit(f"ERROR: GET /appliances thất bại ({resp.status_code}): {resp.text}")
    existing_names = {a["name"] for a in resp.json()}

    added = present = 0
    for name, power_w, duration_hours, is_flexible, candidate_hours, quantity in appliances:
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
                "quantity": quantity,
            },
        )
        if create.status_code != 201:
            sys.exit(f"ERROR: POST /appliances thất bại cho '{name}' ({create.status_code}): {create.text}")
        added += 1
        print(f"    + đã thêm: {name} x{quantity}")
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

    email = "demo.sanxuat.vua@qsmart.local"

    print("=" * 70)
    print(f"Supabase project : {base_url}")
    print(f"Backend API      : {api_base}")
    print(f"Email            : {email}")
    print(f"Password         : {PASSWORD}")
    print("=" * 70)

    print(f"\n>>> {email} (production, quy mô vừa)")
    _ensure_supabase_user(base_url, service_key, email)
    token = _login(base_url, anon_key, email)
    _verify_me(api_base, token, email)
    added, present = _seed_appliances(api_base, token, MANUFACTURING_APPLIANCES)

    total_flexible = sum(1 for a in MANUFACTURING_APPLIANCES if a[3])
    total_fixed = sum(1 for a in MANUFACTURING_APPLIANCES if not a[3])
    total_power_all = sum(a[1] * a[5] for a in MANUFACTURING_APPLIANCES)
    monthly_kwh = sum(a[1]/1000 * a[2] * a[5] * 30 for a in MANUFACTURING_APPLIANCES)

    print("\n" + "=" * 70)
    print("TÓM TẮT")
    print("=" * 70)
    print(f"{'Email':<40} {email}")
    print(f"{'Mật khẩu':<40} {PASSWORD}")
    print(f"{'Loại hình':<40} Sản xuất (production)")
    print(f"{'Quy mô':<40} Vừa")
    print(f"{'Cấp điện áp':<40} 6-22kV")
    print(f"{'Công suất hợp đồng':<40} {BUSINESS_CONFIG['contracted_power_kw']} kW")
    print(f"{'Số thiết bị linh hoạt':<40} {total_flexible}")
    print(f"{'Số thiết bị cố định':<40} {total_fixed}")
    print(f"{'Tổng CS lắp đặt (kW)':<40} {total_power_all/1000:.1f}")
    print(f"{'Tiêu thụ ước tính':<40} {monthly_kwh:,.0f} kWh/tháng")
    print()
    print("Đăng nhập tại /login bằng thông tin trên để chạy tối ưu.")
    print("Nên chọn weather=cloudy, day_of_month=20+ để thấy rõ savings.")
    print("=" * 70)


if __name__ == "__main__":
    main()
