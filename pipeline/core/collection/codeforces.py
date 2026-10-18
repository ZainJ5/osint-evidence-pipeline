"""Codeforces public API collector: profile, rating history and submissions (FR-03)."""

import json

from pipeline.core.collection.collector import Collector
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.models import RawFetch
from pipeline.core.ports import HttpResponse

API = "https://codeforces.com/api"
# user.status page size. Measured 2026-11: tourist's full history is 5,519 submissions, 3.2 MB, ~6 s; 10,000 covers
# virtually every account in one call while bounding the payload (~6 MB). A full page is flagged "capped" by the parser.
STATUS_COUNT = 10000


class CodeforcesCollector(Collector):
    """Collects a Codeforces profile and rating."""

    source_name = "codeforces"

    async def _collect(self, handle: str) -> list[RawFetch]:
        requests = [
            ("user.info", {"handles": handle}),
            ("user.rating", {"handle": handle}),
            ("user.status", {"handle": handle, "from": 1, "count": STATUS_COUNT}),
        ]
        fetches = []
        for method, params in requests:
            endpoint = f"codeforces/{method}"
            fetch, body = await self._fetch(handle, endpoint, f"{API}/{method}", params=params)
            if not isinstance(body, dict) or body.get("status") != "OK":
                raise self._malformed(endpoint, "Codeforces envelope without status OK")
            fetches.append(fetch)
        return fetches

    def _is_not_found(self, response: HttpResponse) -> bool:
        # Unknown handle: HTTP 400 {"status": "FAILED", "comment": "handles: User with handle x not found"}.
        # Other FAILED answers (e.g. "count: Field should contain integer value") are not a missing handle.
        if super()._is_not_found(response):
            return True
        try:
            body = json.loads(response.body)
        except ValueError:
            return False
        if not isinstance(body, dict) or body.get("status") != "FAILED":
            return False
        comment = body.get("comment")
        return isinstance(comment, str) and "not found" in comment.lower()


CollectorFactory.register(CodeforcesCollector.source_name, CodeforcesCollector)
