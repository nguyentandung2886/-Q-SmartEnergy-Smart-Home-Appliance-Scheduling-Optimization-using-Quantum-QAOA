"""POST /explain: stream a Gemini-generated Vietnamese explanation of optimization results."""
import os

import google.generativeai as genai
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user
from models import User

# GEMINI_API_KEY stays optional at startup: a missing key must NOT crash the whole app (the
# rest of the demo — auth, optimize, forecast — has nothing to do with Gemini). When absent,
# /explain degrades gracefully with a friendly message instead of taking the server down.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(tags=["explain"])

_WEATHER_VI = {"sunny": "nắng", "cloudy": "có mây", "rainy": "mưa"}


class ApplianceInfo(BaseModel):
    name: str
    power_w: float
    duration_hours: float
    is_flexible: bool


class ExplainRequest(BaseModel):
    schedule: dict[str, int]
    appliances: list[ApplianceInfo]
    bill_before_vnd: float
    bill_after_vnd: float
    savings_percent: float
    weather_condition: str
    solver_used: str


def _build_prompt(req: ExplainRequest) -> str:
    weather_vi = _WEATHER_VI.get(req.weather_condition, req.weather_condition)
    schedule_lines = "\n".join(
        f"  - {name}: {hour}h00" for name, hour in sorted(req.schedule.items())
    )
    return (
        "Bạn là trợ lý AI phân tích năng lượng của Q-SmartEnergy. "
        "Hãy giải thích kết quả tối ưu hóa sau đây bằng tiếng Việt tự nhiên, "
        "ngắn gọn (4-5 câu). Tập trung vào: tại sao các giờ đó hợp lý "
        "(nắng → solar cao), ý nghĩa tiết kiệm thực tế, và một lời khuyên cụ thể.\n\n"
        f"Thời tiết: {weather_vi}\n"
        f"Solver: {req.solver_used}\n"
        f"Lịch tối ưu:\n{schedule_lines}\n"
        f"Hóa đơn: {req.bill_before_vnd:,.0f}đ → {req.bill_after_vnd:,.0f}đ "
        f"(tiết kiệm {req.savings_percent:.1f}%)"
    )


def _stream_explanation(prompt: str):
    if not GEMINI_API_KEY:
        yield ("data: ❌ Tính năng giải thích chưa khả dụng: chưa cấu hình GEMINI_API_KEY "
               "trong server/.env. Các tính năng khác vẫn hoạt động bình thường.\n\n")
        yield "data: [DONE]\n\n"
        return
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield f"data: {chunk.text.replace(chr(10), ' ')}\n\n"
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
            friendly = "Gemini API đã đạt giới hạn quota. Vui lòng thử lại sau hoặc kiểm tra billing tại https://aistudio.google.com/apikey"
        elif "401" in msg or "403" in msg or "API_KEY" in msg or "invalid" in msg.lower():
            friendly = "API key Gemini không hợp lệ. Vui lòng cập nhật GEMINI_API_KEY trong server/.env"
        else:
            friendly = f"Không thể kết nối Gemini: {msg[:120]}"
        yield f"data: ❌ {friendly}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/explain")
def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
):
    prompt = _build_prompt(payload)
    return StreamingResponse(
        _stream_explanation(prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
