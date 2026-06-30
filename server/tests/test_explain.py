"""Tests for POST /explain SSE endpoint."""
import sys
from unittest.mock import MagicMock, patch


def _make_chunk(text: str):
    chunk = MagicMock()
    chunk.text = text
    return chunk


def test_explain_streams_sse(client, auth_headers):
    """POST /explain with mocked Gemini returns text/event-stream with data: lines."""
    headers = auth_headers("explainuser1")
    mock_chunks = [_make_chunk("Hệ thống đã"), _make_chunk(" tối ưu tốt.")]

    with patch("explain_router.genai.GenerativeModel") as mock_cls:
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        mock_model.generate_content.return_value = iter(mock_chunks)

        response = client.post(
            "/explain",
            json={
                "schedule": {"Máy giặt": 9},
                "appliances": [
                    {
                        "name": "Máy giặt",
                        "power_w": 500.0,
                        "duration_hours": 1.0,
                        "is_flexible": True,
                    }
                ],
                "bill_before_vnd": 500000.0,
                "bill_after_vnd": 415000.0,
                "savings_percent": 17.0,
                "weather_condition": "sunny",
                "solver_used": "qaoa",
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data: Hệ thống đã" in body
    assert "data: [DONE]" in body


def test_explain_requires_auth(client):
    """POST /explain without JWT returns 401."""
    response = client.post(
        "/explain",
        json={
            "schedule": {},
            "appliances": [],
            "bill_before_vnd": 0.0,
            "bill_after_vnd": 0.0,
            "savings_percent": 0.0,
            "weather_condition": "sunny",
            "solver_used": "qaoa",
        },
    )
    assert response.status_code == 401


def test_explain_missing_gemini_key_raises_at_startup(monkeypatch):
    """If GEMINI_API_KEY is not set, importing explain_router raises RuntimeError."""
    import pytest

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    sys.modules.pop("explain_router", None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        import explain_router  # noqa: F401
    # Restore module so later tests in this session are unaffected
    monkeypatch.setenv("GEMINI_API_KEY", "restored-fake-key")
    sys.modules.pop("explain_router", None)
    import explain_router  # noqa: F401, F811
