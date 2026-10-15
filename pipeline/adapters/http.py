"""HttpClient adapter over httpx: library exceptions are translated into CollectionError."""

import os
from urllib.parse import urlsplit

import httpx

from pipeline.core.errors import CollectionError
from pipeline.core.ports import HttpClient, HttpResponse

USER_AGENT = "osint-evidence-pipeline"
TIMEOUT_SECONDS = 15.0


class HttpAdapter(HttpClient):
    """Adapter: wraps one httpx.AsyncClient behind the HttpClient port."""

    def __init__(self, token: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        """`token` defaults to $GITHUB_TOKEN; `transport` is for tests (httpx.MockTransport)."""
        self._token = os.environ.get("GITHUB_TOKEN", "") if token is None else token
        self._client = httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}, transport=transport
        )

    async def get(self, url: str, params: dict | None = None) -> HttpResponse:
        return await self._send("GET", url, params=params)

    async def post(self, url: str, json: dict) -> HttpResponse:
        return await self._send("POST", url, json=json)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _send(self, method: str, url: str, **kwargs) -> HttpResponse:
        try:
            response = await self._client.request(method, url, headers=self._auth_headers(url), **kwargs)
        except httpx.TimeoutException as exc:
            raise CollectionError("request timed out", code="TIMEOUT", context={"url": url}) from exc
        except httpx.HTTPError as exc:
            raise CollectionError(f"network error: {type(exc).__name__}", code="NETWORK", context={"url": url}) from exc
        return HttpResponse(response.status_code, response.content, url)

    def _auth_headers(self, url: str) -> dict:
        if self._token and urlsplit(url).hostname == "api.github.com":
            return {"Authorization": f"Bearer {self._token}"}
        return {}
