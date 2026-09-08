import httpx
import pytest

from backend.services.web_risk_client import WebRiskClient, WebRiskError


@pytest.mark.asyncio
async def test_clear_url_returns_false():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "webrisk.googleapis.com"
        assert request.url.path == "/v1/uris:search"
        assert request.url.params["uri"] == "https://example.com"

        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        result = await client.is_flagged("https://example.com")

    assert result is False


@pytest.mark.asyncio
async def test_flagged_url_returns_true():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "threat": {
                    "threatTypes": ["MALWARE"],
                    "expireTime": "2030-01-01T00:00:00Z",
                }
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        result = await client.is_flagged("https://example.com")

    assert result is True


@pytest.mark.asyncio
async def test_timeout_raises_web_risk_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Simulated timeout",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        with pytest.raises(WebRiskError, match="Web Risk request timed out"):
            await client.is_flagged("https://example.com")


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"unexpected": "value"},
        {"threat": None},
        {"threat": {}},
        {"threat": {"threatTypes": []}},
        {"threat": {"threatTypes": "MALWARE"}},
        {"threat": {"threatTypes": ["UNKNOWN"]}},
    ],
)
@pytest.mark.asyncio
async def test_malformed_response_raises_web_risk_error(payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        with pytest.raises(WebRiskError):
            await client.is_flagged("https://example.com")


@pytest.mark.asyncio
async def test_invalid_json_raises_web_risk_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="this is not JSON")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        with pytest.raises(WebRiskError, match="invalid JSON"):
            await client.is_flagged("https://example.com")


@pytest.mark.parametrize("status_code", [403, 429, 500, 503])
@pytest.mark.asyncio
async def test_http_error_raises_web_risk_error(status_code):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WebRiskClient(http_client, api_key="test-key")

        with pytest.raises(WebRiskError, match="Web Risk request failed"):
            await client.is_flagged("https://example.com")
