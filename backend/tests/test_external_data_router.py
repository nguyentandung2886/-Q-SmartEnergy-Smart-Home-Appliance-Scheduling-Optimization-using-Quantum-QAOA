"""
Tests for external_data_router.py — user-supplied URL fetch with SSRF guarding.

Verifies:
1. validate_external_url() rejects non-https URLs.
2. validate_external_url() rejects loopback/private/link-local IP literals and "localhost".
3. validate_external_url() rejects hostnames that resolve to a private/loopback IP.
4. validate_external_url() accepts a public IP literal / a hostname resolving to a public IP.
5. fetch_external_json() returns parsed JSON on a valid https response.
6. fetch_external_json() raises a friendly ExternalDataError for non-JSON bodies, oversized
   bodies, HTTP error statuses, and timeouts — never lets the underlying exception escape.
7. POST /api/external-data/fetch requires auth (401 without token) and returns a clean
   {"ok": False, "error": ...} (never 500) for a blocked internal URL.
"""
import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest

from api import external_data_router
from api.external_data_router import (
    ExternalDataError,
    fetch_external_json,
    validate_external_url,
)


class TestValidateExternalUrl:
    def test_rejects_non_https_scheme(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("http://example.com/data")

    def test_rejects_loopback_ip_literal(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("https://127.0.0.1/data")

    def test_rejects_link_local_metadata_ip(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("https://169.254.169.254/latest/meta-data")

    def test_rejects_private_10_range(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("https://10.0.0.5/data")

    def test_rejects_private_192_168_range(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("https://192.168.1.1/data")

    def test_rejects_localhost_hostname(self):
        with pytest.raises(ExternalDataError):
            validate_external_url("https://localhost:8000/data")

    def test_rejects_hostname_resolving_to_private_ip(self, monkeypatch):
        monkeypatch.setattr(
            "api.external_data_router.socket.getaddrinfo",
            lambda host, port: [(2, 1, 6, "", ("10.1.2.3", 0))],
        )
        with pytest.raises(ExternalDataError):
            validate_external_url("https://internal.example.test/data")

    def test_accepts_public_ip_literal(self):
        validate_external_url("https://8.8.8.8/data")  # must not raise

    def test_accepts_hostname_resolving_to_public_ip(self, monkeypatch):
        monkeypatch.setattr(
            "api.external_data_router.socket.getaddrinfo",
            lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
        )
        validate_external_url("https://public.example.test/data")  # must not raise

    def test_unresolvable_hostname_raises_friendly_error(self, monkeypatch):
        import socket as socket_module

        def _raise(host, port):
            raise socket_module.gaierror("not found")

        monkeypatch.setattr("api.external_data_router.socket.getaddrinfo", _raise)
        with pytest.raises(ExternalDataError):
            validate_external_url("https://nonexistent.example.test/data")


_RealAsyncClient = httpx.AsyncClient


def _mock_client_factory(handler):
    def _factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler))
    return _factory


class TestFetchExternalJson:
    def test_returns_parsed_json_on_success(self, monkeypatch):
        def handler(request):
            return httpx.Response(200, json={"solar_forecast_kwh": 12.3})

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        data = asyncio.run(fetch_external_json("https://8.8.8.8/data"))
        assert data == {"solar_forecast_kwh": 12.3}

    def test_non_json_body_raises_friendly_error(self, monkeypatch):
        def handler(request):
            return httpx.Response(200, text="not json")

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://8.8.8.8/data"))

    def test_oversized_body_raises_friendly_error(self, monkeypatch):
        big = b"[" + b"1," * 600_000 + b"1]"

        def handler(request):
            return httpx.Response(200, content=big)

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://8.8.8.8/data"))

    def test_http_error_status_raises_friendly_error(self, monkeypatch):
        def handler(request):
            return httpx.Response(500, text="boom")

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://8.8.8.8/data"))

    def test_timeout_raises_friendly_error(self, monkeypatch):
        def handler(request):
            raise httpx.TimeoutException("timed out", request=request)

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://8.8.8.8/data"))

    def test_blocked_url_raises_before_any_network_call(self):
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://127.0.0.1/data"))

    def test_redirect_is_rejected_even_with_a_valid_json_body(self, monkeypatch):
        # A redirect response can carry any body it likes (attacker-controlled). If the code
        # only relied on "JSON parse fails" to reject 3xx, a redirect with a JSON body would
        # slip through as if it were the real answer. It must be rejected explicitly instead.
        call_count = {"n": 0}

        def handler(request):
            call_count["n"] += 1
            return httpx.Response(
                302,
                headers={"location": "https://169.254.169.254/latest/meta-data"},
                json={"looks": "like a valid answer"},
            )

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )
        with pytest.raises(ExternalDataError):
            asyncio.run(fetch_external_json("https://8.8.8.8/data"))
        assert call_count["n"] == 1  # the redirect target was never followed/requested

    def test_connects_to_the_validated_ip_directly_no_second_dns_lookup(self, monkeypatch):
        # If validate_external_url() resolves the hostname once and fetch_external_json()
        # lets the HTTP client resolve it again to connect, a DNS server that answers the two
        # lookups differently (public IP first, private IP second) bypasses the SSRF check
        # entirely. Connecting to the exact IP that was validated closes that gap.
        call_count = {"n": 0}

        def _getaddrinfo(host, port):
            call_count["n"] += 1
            return [(2, 1, 6, "", ("93.184.216.34", 0))]

        monkeypatch.setattr("api.external_data_router.socket.getaddrinfo", _getaddrinfo)

        captured = {}

        def handler(request):
            captured["host"] = request.url.host
            captured["host_header"] = request.headers.get("host")
            captured["sni"] = request.extensions.get("sni_hostname")
            return httpx.Response(200, json={"ok": True})

        monkeypatch.setattr(
            "api.external_data_router.httpx.AsyncClient", _mock_client_factory(handler)
        )

        data = asyncio.run(fetch_external_json("https://public.example.test/data"))

        assert call_count["n"] == 1  # only the validation lookup — none during connect
        assert captured["host"] == "93.184.216.34"  # connected to the validated IP
        assert captured["host_header"] == "public.example.test"  # Host header preserved
        assert captured["sni"] == "public.example.test"  # TLS SNI preserved
        assert data == {"ok": True}


class TestFetchEndpoint:
    def test_requires_auth(self, client):
        response = client.post("/api/external-data/fetch", json={"url": "https://8.8.8.8/data"})
        assert response.status_code == 401

    def test_blocked_internal_url_returns_clean_error_not_500(self, client, auth_headers):
        headers = auth_headers("dave-uid")
        response = client.post(
            "/api/external-data/fetch",
            json={"url": "http://169.254.169.254/latest/meta-data"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert "error" in body


class TestBuildSummarizePrompt:
    def test_permits_common_knowledge_interpretation_of_aqi(self):
        # Regression: the prompt must let Gemini apply widely-recognized general knowledge
        # (e.g. the standard AQI scale) to interpret a bare number like {"aqi": 180} — an
        # earlier, stricter wording caused Gemini to refuse any suggestion for this case.
        prompt = external_data_router._build_summarize_prompt({"aqi": 180})
        assert "ĐƯỢC PHÉP" in prompt
        assert "kiến thức phổ thông" in prompt
        assert "180" in prompt

    def test_still_forbids_fabricating_fields_not_in_the_json(self):
        prompt = external_data_router._build_summarize_prompt({"aqi": 180})
        assert "KHÔNG ĐƯỢC PHÉP" in prompt
        assert "TRƯỜNG DỮ LIỆU" in prompt

    def test_instructs_plain_text_no_markdown(self):
        prompt = external_data_router._build_summarize_prompt({"aqi": 180})
        assert "KHÔNG dùng markdown" in prompt


class TestStripMarkdown:
    def test_strips_inline_bold_label(self):
        # The exact case observed in production: Gemini bolds an inline label while leaving
        # the rest of the sentence plain.
        text = "Chất lượng không khí rất tốt. **Gợi ý hành động:** hãy mở cửa sổ thông gió."
        result = external_data_router._strip_markdown(text)
        assert "*" not in result
        assert "Gợi ý hành động:" in result
        assert "hãy mở cửa sổ thông gió." in result

    def test_strips_heading_and_bullet_markers(self):
        text = "## Tóm tắt\n- Chỉ số AQI là 40\n* Mức tốt, an toàn để dùng điện bình thường"
        result = external_data_router._strip_markdown(text)
        assert "#" not in result
        assert not result.startswith("- ")
        assert "Tóm tắt" in result
        assert "Chỉ số AQI là 40" in result

    def test_plain_text_passes_through_unchanged(self):
        text = "Chỉ số chất lượng không khí là 40, ở mức tốt."
        assert external_data_router._strip_markdown(text) == text


class TestSummarizeEndpoint:
    def test_requires_auth(self, client):
        response = client.post("/api/external-data/summarize", json={"data": {"aqi": 180}})
        assert response.status_code == 401

    def test_markdown_in_gemini_response_is_stripped_before_reaching_client(
        self, client, auth_headers, monkeypatch
    ):
        monkeypatch.setattr(external_data_router, "GEMINI_API_KEY", "fake-key-for-test")

        mock_response = MagicMock()
        mock_response.text = (
            "Chất lượng không khí rất tốt. **Gợi ý hành động:** hãy mở cửa sổ thông gió."
        )

        with patch("api.external_data_router.genai.GenerativeModel") as mock_cls:
            mock_model = MagicMock()
            mock_cls.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            headers = auth_headers("summarizeuser4")
            response = client.post(
                "/api/external-data/summarize",
                json={"data": {"aqi": 40}},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "*" not in body["summary"]
        assert "Gợi ý hành động:" in body["summary"]

    def test_returns_summary_from_mocked_gemini(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(external_data_router, "GEMINI_API_KEY", "fake-key-for-test")

        mock_response = MagicMock()
        mock_response.text = "Chỉ số AQI ở mức 180, cân nhắc hạn chế dùng thiết bị ngoài trời."

        with patch("api.external_data_router.genai.GenerativeModel") as mock_cls:
            mock_model = MagicMock()
            mock_cls.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            headers = auth_headers("summarizeuser1")
            response = client.post(
                "/api/external-data/summarize",
                json={"data": {"aqi": 180}},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "180" in body["summary"]

    def test_missing_gemini_key_returns_ok_false_not_500(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(external_data_router, "GEMINI_API_KEY", None)

        headers = auth_headers("summarizeuser2")
        response = client.post(
            "/api/external-data/summarize",
            json={"data": {"foo": "bar"}},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() == {"ok": False}

    def test_gemini_exception_returns_ok_false_not_500(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(external_data_router, "GEMINI_API_KEY", "fake-key-for-test")

        with patch("api.external_data_router.genai.GenerativeModel") as mock_cls:
            mock_model = MagicMock()
            mock_cls.return_value = mock_model
            mock_model.generate_content.side_effect = TimeoutError("timed out")

            headers = auth_headers("summarizeuser3")
            response = client.post(
                "/api/external-data/summarize",
                json={"data": {"foo": "bar"}},
                headers=headers,
            )

        assert response.status_code == 200
        assert response.json() == {"ok": False}
