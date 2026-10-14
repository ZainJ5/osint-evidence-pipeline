"""Abstract collector (Template Method): rate limiting, retries and raw capture shared by every source."""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.models import RawFetch
from pipeline.core.ports import HttpClient, HttpResponse

TRANSIENT_CODES = ("TIMEOUT", "NETWORK")
BACKOFF_BASE = 0.5  # seconds; doubles each retry: 0.5, 1, 2


class Collector(ABC):
    """collect() returns list[RawFetch] or raises CollectionError: never None, never a library exception."""

    source_name: str = ""

    def __init__(self, http: HttpClient, limiter: RateLimiter, config: RunConfig, sleep=asyncio.sleep):
        self._http = http
        self._limiter = limiter
        self._config = config
        self._sleep = sleep

    @property
    def limiter(self) -> RateLimiter:
        return self._limiter

    async def collect(self, handle: str) -> list[RawFetch]:
        return list(await self._collect(handle))

    @abstractmethod
    async def _collect(self, handle: str) -> list[RawFetch]:
        """Fetch every endpoint of this source for one handle."""

    async def _fetch(
        self, handle: str, endpoint: str, url: str, params: dict | None = None, json_body: dict | None = None
    ) -> tuple[RawFetch, object]:
        """One logical request, retried on transient failures. Returns the raw fetch and the parsed JSON."""
        context = {"source": self.source_name, "endpoint": endpoint, "url": url}
        error = None
        for attempt in range(self._config.max_retries + 1):
            if attempt:
                await self._sleep(BACKOFF_BASE * 2 ** (attempt - 1))
            try:
                response = await self._send(url, params, json_body)
            except CollectionError as err:
                if err.code not in TRANSIENT_CODES:
                    raise
                error = err
                continue
            if response.status == 429 or response.status >= 500:
                error = CollectionError(f"HTTP {response.status}", code=f"HTTP_{response.status}", context=context)
                continue
            return self._accept(handle, endpoint, response, context)
        raise error

    async def _send(self, url: str, params: dict | None, json_body: dict | None) -> HttpResponse:
        async with self._limiter:
            if json_body is not None:
                return await self._http.post(url, json=json_body)
            return await self._http.get(url, params=params)

    def _accept(self, handle: str, endpoint: str, response: HttpResponse, context: dict) -> tuple[RawFetch, object]:
        if self._is_not_found(response):
            raise CollectionError(f"{self.source_name} handle not found", code="NOT_FOUND", context=context)
        if self._is_rate_limited(response):
            # Not retried: the quota resets minutes to an hour later, far beyond the back-off window.
            raise CollectionError(f"{self.source_name} rate limit exceeded", code="RATE_LIMITED", context=context)
        if not 200 <= response.status < 300:
            raise CollectionError(f"HTTP {response.status}", code=f"HTTP_{response.status}", context=context)
        try:
            parsed = json.loads(response.body)
        except ValueError as err:
            raise CollectionError("response body is not valid JSON", code="MALFORMED_BODY", context=context) from err
        fetch = RawFetch(self.source_name, handle, endpoint, response.body, datetime.now(timezone.utc))
        return fetch, parsed

    def _is_not_found(self, response: HttpResponse) -> bool:
        return response.status == 404

    def _is_rate_limited(self, response: HttpResponse) -> bool:  # pylint: disable=unused-argument
        return False

    def _malformed(self, endpoint: str, reason: str) -> CollectionError:
        return CollectionError(
            reason, code="MALFORMED_BODY", context={"source": self.source_name, "endpoint": endpoint}
        )
