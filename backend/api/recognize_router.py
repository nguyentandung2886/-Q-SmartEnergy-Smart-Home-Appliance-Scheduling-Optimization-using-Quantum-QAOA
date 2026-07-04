"""POST /appliances/recognize: nhận ảnh nhãn thông số thiết bị, dùng Gemini Vision trích xuất
loại thiết bị + công suất, rồi đối chiếu với catalog đã xác minh nguồn (core.appliance_catalog).

Dùng LẠI cùng credential/config Gemini như explain_router (GEMINI_API_KEY, model gemini-2.5-flash).
Không tạo key mới, không thêm biến môi trường mới. Nếu thiếu key hoặc Gemini lỗi/timeout → trả về
{"error": "..."} (HTTP 200) để frontend hiện thông báo và fallback nhập tay, KHÔNG crash.
"""
import base64
import json
import os
import unicodedata

import google.generativeai as genai
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import get_current_user
from core.appliance_catalog import HOUSEHOLD_APPLIANCES
from db.models import User

# Cùng guard như explain_router: thiếu key KHÔNG được crash app — degrade gracefully.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(prefix="/appliances", tags=["appliances"])

_UNVERIFIED_NOTE = "[CẦN XÁC MINH]"
_ESTIMATED_NOTE = ("Ước tính theo loại thiết bị — không đọc được công suất từ ảnh, "
                   "vui lòng kiểm tra lại nếu có tem")

_VISION_PROMPT = (
    "Bạn là trợ lý nhận diện thiết bị điện gia dụng. Ảnh có thể là NHÃN thông số (label/rating "
    "plate) HOẶC ảnh mặt ngoài của thiết bị. Hãy trích xuất thông tin và CHỈ trả về JSON đúng "
    "schema sau, không giải thích thêm.\n"
    "QUY TẮC QUAN TRỌNG — 2 field độc lập:\n"
    "  1. device_type: LUÔN cố nhận diện loại thiết bị dựa vào HÌNH DÁNG / KIỂU MÁY, kể cả khi "
    "KHÔNG thấy tem công suất (vd ảnh mặt trước TV, laptop, quạt...).\n"
    "  2. power_w: CHỈ điền nếu ĐỌC ĐƯỢC RÕ con số trên text/tem trong ảnh. TUYỆT ĐỐI KHÔNG "
    "được suy đoán/ước lượng công suất từ trí nhớ. Không thấy số công suất trên ảnh → power_w = null.\n"
    "Schema:\n"
    '{"device_type": <tên loại thiết bị bằng tiếng Việt, vd "Tủ lạnh", "Điều hòa", "Máy giặt", '
    '"Nồi cơm điện", "Lò vi sóng", "Bình nước nóng", "Quạt điện", "Bếp điện", "Tivi", hoặc null '
    "nếu không nhận ra là thiết bị điện>, "
    '"brand": <hãng nếu thấy, vd "Panasonic", "Daikin", ngược lại null>, '
    '"power_w": <công suất WATT dạng số CHỈ khi đọc được từ ảnh. Nhãn ghi kW thì nhân 1000; chỉ '
    "có điện áp (V) và dòng (A) thì power_w = V * A. Không đọc được → null. KHÔNG đoán bừa>, "
    '"voltage": <điện áp danh định dạng số, vd 220, hoặc null>, '
    '"confidence": <độ tin cậy nhận diện device_type, 0..1>}'
)


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _normalize(s: str) -> str:
    """Bỏ dấu, thường hoá, bỏ phần trong ngoặc, gom khoảng trắng — để so khớp từ khóa."""
    s = _strip_accents(s or "").lower()
    # bỏ phần trong ngoặc (vd "(12000 BTU)") để tách token lõi
    out, depth = [], 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())


# Vài alias tiếng Anh → token tiếng Việt, phòng khi Gemini trả tên tiếng Anh.
_ALIASES = {
    "refrigerator": "tu lanh", "fridge": "tu lanh",
    "air conditioner": "dieu hoa", "aircon": "dieu hoa", "air-conditioner": "dieu hoa",
    "washing machine": "may giat", "washer": "may giat",
    "water heater": "binh nuoc nong",
    "fan": "quat dien",
    "microwave": "lo vi song",
    "rice cooker": "noi com dien",
    "television": "tivi", "tv": "tivi",
    "stove": "bep dien", "cooktop": "bep dien", "induction": "bep dien",
    "light": "bong dien", "lamp": "bong dien", "bulb": "bong dien",
}


# Token phân loại chung ("máy", "điện"...) — chỉ trùng mấy token này KHÔNG đủ để coi là khớp
# (vd "máy sấy" vs "máy giặt" đều có "máy"). Phải trùng ít nhất 1 token ĐẶC TRƯNG.
_GENERIC_TOKENS = {"may", "dien", "binh", "lo", "noi"}


def match_catalog(device_type: str | None, power_w: float | None):
    """Fuzzy-match device_type với HOUSEHOLD_APPLIANCES theo trùng token (đã bỏ dấu). Chỉ coi là
    khớp khi trùng ít nhất một token ĐẶC TRƯNG (không phải token phân loại chung). Khi nhiều mục
    cùng số token trùng (vd 2 loại điều hòa / 2 loại bình nước nóng), chọn mục có power_w gần với
    số Gemini trích nhất. Trả về Appliance khớp hoặc None."""
    if not device_type:
        return None
    norm = _normalize(device_type)
    for eng, vi in _ALIASES.items():
        if eng in norm:
            norm = f"{norm} {vi}"

    query_tokens = set(norm.split())
    best = None  # ((num_overlap, -power_gap), appliance)
    for appliance in HOUSEHOLD_APPLIANCES:
        name_tokens = _normalize(appliance.name).split()
        overlap = [t for t in name_tokens if t in query_tokens]
        if not any(t not in _GENERIC_TOKENS for t in overlap):
            continue  # chỉ trùng token chung → chưa đủ để khớp
        gap = abs(appliance.power_w - power_w) if power_w else 0.0
        key = (len(overlap), -gap)
        if best is None or key > best[0]:
            best = (key, appliance)
    return best[1] if best else None


class RecognizeRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    mime_type: str = "image/jpeg"


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return ("Gemini API đã đạt giới hạn quota. Vui lòng thử lại sau hoặc nhập tay công suất.")
    if "401" in msg or "403" in msg or "API_KEY" in msg or "invalid" in msg.lower():
        return "API key Gemini không hợp lệ. Vui lòng kiểm tra GEMINI_API_KEY trong server/.env"
    return f"Không thể nhận diện ảnh: {msg[:120]}"


def _parse_gemini_json(text: str) -> dict:
    """Gemini có thể bọc JSON trong ```json ... ``` — bóc fence rồi json.loads."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
    return json.loads(t.strip())


@router.post("/recognize")
def recognize_appliance(
    payload: RecognizeRequest,
    current_user: User = Depends(get_current_user),
):
    if not GEMINI_API_KEY:
        return {"error": ("Tính năng nhận diện chưa khả dụng: chưa cấu hình GEMINI_API_KEY "
                          "trong server/.env. Vui lòng nhập tay thông số thiết bị.")}
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception:
        return {"error": "Ảnh không hợp lệ (không giải mã được base64). Vui lòng chọn ảnh khác."}

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            [_VISION_PROMPT, {"mime_type": payload.mime_type, "data": image_bytes}],
            generation_config={"response_mime_type": "application/json"},
        )
        extracted = _parse_gemini_json(response.text)
    except Exception as exc:  # lỗi mạng/quota/parse — bắt gọn, không crash
        return {"error": _friendly_error(exc)}

    device_type = extracted.get("device_type")
    power_w = extracted.get("power_w")
    if isinstance(power_w, str):
        try:
            power_w = float(power_w.replace(",", "").strip() or 0) or None
        except ValueError:
            power_w = None

    gemini = {
        "device_type": device_type,
        "brand": extracted.get("brand"),
        "power_w": power_w,
        "voltage": extracted.get("voltage"),
        "confidence": extracted.get("confidence"),
    }

    has_power = isinstance(power_w, (int, float))
    match = match_catalog(device_type, power_w if has_power else None)

    if has_power and match is not None:
        # Case XANH (đã test thật): đọc được công suất + khớp catalog → dùng số ĐÃ XÁC MINH.
        return {
            "gemini": gemini,
            "verified": True,
            "estimated": False,
            "suggested_name": match.name,
            "suggested_power_w": match.power_w,
            "catalog_match": {
                "name": match.name,
                "power_w": match.power_w,
                "duration_hours": match.duration_hours,
                "is_flexible": match.is_flexible,
                "verified": True,
            },
            "note": None,
        }

    if has_power:
        # Case VÀNG (đã test thật): đọc được công suất nhưng không khớp catalog → giữ số Gemini.
        return {
            "gemini": gemini,
            "verified": False,
            "estimated": False,
            "suggested_name": device_type,
            "suggested_power_w": power_w,
            "catalog_match": None,
            "note": _UNVERIFIED_NOTE,
        }

    if match is not None:
        # Case MỚI (ước tính): không đọc được công suất từ ảnh nhưng nhận diện được LOẠI thiết bị
        # → lấy công suất điển hình từ catalog (KHÔNG phải LLM đoán), badge riêng "ước tính".
        return {
            "gemini": gemini,
            "verified": False,
            "estimated": True,
            "suggested_name": match.name,
            "suggested_power_w": match.power_w,
            "catalog_match": {
                "name": match.name,
                "power_w": match.power_w,
                "duration_hours": match.duration_hours,
                "is_flexible": match.is_flexible,
                "verified": False,
            },
            "note": _ESTIMATED_NOTE,
        }

    # Không đọc được công suất và cũng không nhận ra loại → fallback nhập tay như cũ.
    return {
        "gemini": gemini,
        "verified": False,
        "estimated": False,
        "suggested_name": device_type,
        "suggested_power_w": None,
        "catalog_match": None,
        "note": _UNVERIFIED_NOTE,
    }
