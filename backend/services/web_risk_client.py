import httpx


class WebRiskError(Exception):
    """Raised when we cannot get a trustworthy Web Risk result."""


class WebRiskClient:
    def __init__(self, http_client: httpx.AsyncClient, api_key: str):
        self.http_client = http_client
        self.api_key = api_key

    async def _request(self, url: str) -> httpx.Response:
        try:
            response = await self.http_client.get(
                "https://webrisk.googleapis.com/v1/uris:search",
                params={
                    "key": self.api_key,
                    "uri": url,
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                    ],
                },
                timeout=5.0,
                follow_redirects=False,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise WebRiskError("Web Risk request timed out") from exc
        except httpx.HTTPError as exc:
            raise WebRiskError("Web Risk request failed") from exc

        return response

    async def is_flagged(self, url: str) -> bool:
        response = await self._request(url)

        try:
            data = response.json()
        except ValueError as exc:
            raise WebRiskError("Web Risk returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise WebRiskError("Web Risk returned an unexpected response")

        if data == {}:
            return False

        threat = data.get("threat")
        if not isinstance(threat, dict):
            raise WebRiskError("Web Risk returned invalid threat data")

        threat_types = threat.get("threatTypes")
        if not isinstance(threat_types, list) or not threat_types:
            raise WebRiskError("Web Risk returned invalid threat types")

        for threat_type in threat_types:
            if threat_type not in (
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
            ):
                raise WebRiskError("Web Risk returned an unknown threat type")

        return True
