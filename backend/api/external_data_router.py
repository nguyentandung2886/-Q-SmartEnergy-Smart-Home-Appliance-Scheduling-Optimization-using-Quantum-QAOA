"""
User-supplied external URL fetch — lets a user point at a JSON endpoint (e.g. a grid/load-plan
feed) for extra optimizer context. v1 scope: fetch + display only, not wired into the QUBO
objective yet (no stable schema for that integration).

SECURITY (SSRF): a user-controlled URL fetched server-side is a classic SSRF vector — without
guarding, a user could point the backend at internal infra (cloud metadata endpoints, localhost
services, LAN hosts) to probe or attack it. validate_external_url() only allows https and blocks
loopback/private/link-local/reserved/multicast IPs, checking both IP literals and the IPs a
hostname resolves to. Two easy-to-miss follow-on vectors are guarded too:

- Redirects: a validated URL can respond with a 3xx pointing at an internal address, bypassing
  the check entirely if followed. We never follow redirects (follow_redirects=False, explicit
  even though it's httpx's default — see fetch_external_json) and treat any 3xx as an error
  (belt-and-suspenders: httpx's raise_for_status() already errors on an unfollowed redirect,
  but resp.is_redirect gives a clearer message and doesn't depend on that behavior).
- DNS rebinding: resolving the hostname once to validate it and then letting the HTTP client
  resolve it *again* to connect is a TOCTOU gap — a malicious/attacker-controlled DNS server can
  answer the two lookups differently (public IP for the check, private IP for the real connect).
  validate_external_url() returns the single IP it checked, and fetch_external_json() connects to
  that exact IP (pinning Host/SNI to the original hostname via httpx's `sni_hostname` extension
  for correct TLS verification), so only one resolution ever happens.
"""
import ipaddress
import json
import os
import socket
from urllib.parse import urlparse, urlunparse

import google.generativeai as genai
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from db.models import User

# Same optional-key pattern as explain_router.py: a missing/broken Gemini key must degrade the
# summary to "unavailable", not take down /api/external-data/fetch (the JSON display still works).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(prefix="/api/external-data", tags=["external-data"])

FETCH_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 1_000_000
SUMMARIZE_TIMEOUT_SECONDS = 15
_BLOCKED_HOSTNAMES = {"localhost"}


class ExternalDataRequest(BaseModel):
    url: str


class SummarizeRequest(BaseModel):
    data: dict


class ExternalDataError(Exception):
    """User-facing message explaining why the URL was rejected or the fetch failed."""


def _is_blocked_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_external_url(url: str) -> str:
    """Raises ExternalDataError if url is unsafe to fetch server-side. Returns the single
    IP address that was checked — the caller must connect to this exact IP (see
    fetch_external_json) instead of re-resolving the hostname, to avoid a DNS-rebinding gap."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ExternalDataError("Chỉ chấp nhận URL bắt đầu bằng https://")

    hostname = parsed.hostname
    if not hostname:
        raise ExternalDataError("URL không hợp lệ")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ExternalDataError("Không được phép truy cập địa chỉ mạng nội bộ")

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_blocked_ip(str(literal_ip)):
            raise ExternalDataError("Không được phép truy cập địa chỉ mạng nội bộ")
        return str(literal_ip)

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ExternalDataError("Không thể phân giải tên miền")

    resolved_ips = [sockaddr[0] for *_, sockaddr in addrinfo]
    for ip_str in resolved_ips:
        if _is_blocked_ip(ip_str):
            raise ExternalDataError("Không được phép truy cập địa chỉ mạng nội bộ")
    return resolved_ips[0]


def _pin_url_to_ip(url: str, ip: str) -> str:
    """Rewrites url's host to ip, preserving path/query/port. IPv6 literals get bracketed
    (required in a URL netloc)."""
    parsed = urlparse(url)
    host = f"[{ip}]" if ":" in ip else ip
    netloc = host if parsed.port is None else f"{host}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


async def fetch_external_json(url: str) -> dict:
    """Validates url (SSRF guard) then fetches it, enforcing a timeout and a response
    size cap, and returns the parsed JSON body. Any failure raises ExternalDataError
    with a friendly message — network/parse exceptions never escape.

    Connects to the exact IP validate_external_url() checked (Host header and TLS SNI are
    pinned to the original hostname) rather than letting httpx resolve the hostname again,
    and never follows redirects — both would otherwise let a validated URL bounce the real
    connection to an internal address after the check passed.
    """
    hostname = urlparse(url).hostname
    safe_ip = validate_external_url(url)
    pinned_url = _pin_url_to_ip(url, safe_ip)

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET", pinned_url,
                timeout=FETCH_TIMEOUT_SECONDS,
                follow_redirects=False,
                headers={"Host": hostname},
                extensions={"sni_hostname": hostname},
            ) as resp:
                if resp.is_redirect:
                    raise ExternalDataError("Không cho phép URL chuyển hướng (redirect)")
                resp.raise_for_status()
                body = b""
                async for chunk in resp.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ExternalDataError("Dữ liệu trả về quá lớn (giới hạn 1MB)")
    except httpx.TimeoutException:
        raise ExternalDataError("Hết thời gian chờ phản hồi")
    except httpx.HTTPStatusError as e:
        raise ExternalDataError(f"Máy chủ trả về lỗi {e.response.status_code}")
    except httpx.HTTPError:
        raise ExternalDataError("Không thể kết nối tới URL này")

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise ExternalDataError("Dữ liệu trả về không phải JSON hợp lệ")


@router.post("/fetch")
async def fetch_external_data(
    payload: ExternalDataRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        data = await fetch_external_json(payload.url)
        return {"ok": True, "data": data}
    except ExternalDataError as e:
        return {"ok": False, "error": str(e)}


def _build_summarize_prompt(data: dict) -> str:
    return (
        f"Đây là dữ liệu JSON người dùng cung cấp: {json.dumps(data, ensure_ascii=False)}. "
        "Tóm tắt ngắn gọn bằng tiếng Việt (1-2 câu) và đưa 1 gợi ý hành động liên quan đến việc "
        "dùng điện trong nhà/doanh nghiệp NẾU dữ liệu cho phép.\n\n"
        "ĐƯỢC PHÉP: áp dụng kiến thức phổ thông đã được công nhận rộng rãi (vd thang phân loại "
        "chỉ số AQI chuẩn quốc tế, khuyến cáo an toàn điện thông dụng) để diễn giải ý nghĩa của "
        "số liệu và đưa ra gợi ý.\n"
        "KHÔNG ĐƯỢC PHÉP: tự thêm SỐ LIỆU, ĐỊA ĐIỂM, THỜI GIAN, hay bất kỳ TRƯỜNG DỮ LIỆU nào "
        "không có trong JSON được cung cấp.\n\n"
        "Nếu JSON không chứa đủ ngữ cảnh để liên hệ tới bất kỳ kiến thức phổ thông nào liên quan "
        "đến việc dùng điện, trả lời đúng câu 'Không đủ thông tin để đưa gợi ý cụ thể.'"
    )


@router.post("/summarize")
def summarize_external_data(
    payload: SummarizeRequest,
    current_user: User = Depends(get_current_user),
):
    """Best-effort Gemini summary of already-fetched external JSON. Any failure (no key,
    quota, timeout, bad response) returns {"ok": False} — the caller falls back to showing
    only the raw JSON, so this must never raise or block that display."""
    if not GEMINI_API_KEY:
        return {"ok": False}
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            _build_summarize_prompt(payload.data),
            request_options={"timeout": SUMMARIZE_TIMEOUT_SECONDS},
        )
        summary = (response.text or "").strip()
        if not summary:
            return {"ok": False}
        return {"ok": True, "summary": summary}
    except Exception:
        return {"ok": False}
