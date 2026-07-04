"""Tests for POST /appliances/recognize (Gemini Vision + catalog match)."""
import base64
import json
from unittest.mock import MagicMock, patch

# ảnh giả 1 byte, chỉ cần base64 hợp lệ (Gemini được mock nên nội dung không quan trọng)
_FAKE_IMG = base64.b64encode(b"x").decode()


def _mock_gemini(payload: dict):
    """Trả về context manager patch GenerativeModel để generate_content trả JSON payload."""
    resp = MagicMock()
    resp.text = json.dumps(payload)
    ctx = patch("api.recognize_router.genai.GenerativeModel")
    mock_cls = ctx.start()
    mock_model = MagicMock()
    mock_cls.return_value = mock_model
    mock_model.generate_content.return_value = resp
    return ctx


def test_recognize_matches_catalog_verified(client, auth_headers, monkeypatch):
    """Gemini nhận ra 'Tủ lạnh' → khớp catalog → verified=True, dùng công suất catalog."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    ctx = _mock_gemini({"device_type": "Tủ lạnh", "brand": "Panasonic",
                        "power_w": 40, "voltage": 220, "confidence": 0.95})
    try:
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG, "mime_type": "image/jpeg"},
                          headers=auth_headers("recog1"))
    finally:
        ctx.stop()
    assert res.status_code == 200
    body = res.json()
    assert body["verified"] is True
    assert body["suggested_name"] == "Tủ lạnh"
    assert body["suggested_power_w"] == 33.75  # số catalog, KHÔNG phải số Gemini (40)
    assert body["note"] is None


def test_recognize_ambiguous_picks_closest_power(client, auth_headers, monkeypatch):
    """'Điều hòa' khớp 2 mục → chọn mục có power gần số Gemini nhất (18000 BTU = 1670W)."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    ctx = _mock_gemini({"device_type": "Điều hòa", "power_w": 1600, "confidence": 0.9})
    try:
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG},
                          headers=auth_headers("recog2"))
    finally:
        ctx.stop()
    body = res.json()
    assert body["verified"] is True
    assert body["suggested_power_w"] == 1670


def test_recognize_no_match_unverified(client, auth_headers, monkeypatch):
    """Thiết bị không có trong catalog → verified=False, giữ số Gemini + note [CẦN XÁC MINH]."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    ctx = _mock_gemini({"device_type": "Máy sấy quần áo", "power_w": 1800, "confidence": 0.8})
    try:
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG},
                          headers=auth_headers("recog3"))
    finally:
        ctx.stop()
    body = res.json()
    assert body["verified"] is False
    assert body["estimated"] is False
    assert body["suggested_power_w"] == 1800
    assert body["note"] == "[CẦN XÁC MINH]"


def test_recognize_no_power_estimates_from_type(client, auth_headers, monkeypatch):
    """Ảnh không lộ tem (power_w=null) nhưng nhận ra loại → lấy công suất điển hình từ catalog,
    estimated=True (badge ước tính), KHÔNG phải verified."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    ctx = _mock_gemini({"device_type": "Tivi", "power_w": None, "confidence": 0.9})
    try:
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG},
                          headers=auth_headers("recog_est"))
    finally:
        ctx.stop()
    body = res.json()
    assert body["verified"] is False
    assert body["estimated"] is True
    assert body["suggested_name"] == "Tivi"
    assert body["suggested_power_w"] == 100  # công suất điển hình từ catalog
    assert "Ước tính" in body["note"]


def test_recognize_no_power_no_type_falls_back_to_manual(client, auth_headers, monkeypatch):
    """Không đọc được công suất và cũng không nhận ra loại → power=null để frontend nhập tay."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    ctx = _mock_gemini({"device_type": None, "power_w": None, "confidence": 0.2})
    try:
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG},
                          headers=auth_headers("recog_none"))
    finally:
        ctx.stop()
    body = res.json()
    assert body["verified"] is False
    assert body["estimated"] is False
    assert body["suggested_power_w"] is None


def test_recognize_missing_key_returns_error(client, auth_headers, monkeypatch):
    """Thiếu GEMINI_API_KEY → trả {error} (HTTP 200), không crash, để frontend fallback nhập tay."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", None)
    res = client.post("/appliances/recognize",
                      json={"image_base64": _FAKE_IMG},
                      headers=auth_headers("recog4"))
    assert res.status_code == 200
    assert "GEMINI_API_KEY" in res.json()["error"]


def test_recognize_gemini_failure_returns_error(client, auth_headers, monkeypatch):
    """Gemini ném lỗi → bắt gọn, trả {error}, không crash."""
    from api import recognize_router
    monkeypatch.setattr(recognize_router, "GEMINI_API_KEY", "fake-key")
    with patch("api.recognize_router.genai.GenerativeModel") as mock_cls:
        mock_cls.return_value.generate_content.side_effect = RuntimeError("429 quota")
        res = client.post("/appliances/recognize",
                          json={"image_base64": _FAKE_IMG},
                          headers=auth_headers("recog5"))
    assert res.status_code == 200
    assert "error" in res.json()


def test_recognize_requires_auth(client):
    res = client.post("/appliances/recognize", json={"image_base64": _FAKE_IMG})
    assert res.status_code == 401
