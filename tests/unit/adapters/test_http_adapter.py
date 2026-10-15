import json

import httpx
import pytest

from pipeline.adapters.http import HttpAdapter
from pipeline.core.errors import CollectionError


def recording_transport(seen: list, status: int = 200, body: bytes = b"{}"):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, content=body)

    return httpx.MockTransport(handler)


def failing_transport(exc: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return httpx.MockTransport(handler)


async def test_get_returns_response_with_user_agent():
    seen = []
    adapter = HttpAdapter(token="", transport=recording_transport(seen, body=b'{"ok": 1}'))
    response = await adapter.get("https://codeforces.com/api/user.info", params={"handles": "octo-dev"})
    await adapter.aclose()
    assert response.status == 200
    assert response.body == b'{"ok": 1}'
    assert response.url == "https://codeforces.com/api/user.info"
    assert seen[0].url.params["handles"] == "octo-dev"
    assert seen[0].headers["User-Agent"] == "osint-evidence-pipeline"
    assert "Authorization" not in seen[0].headers


async def test_non_2xx_status_is_returned_not_raised():
    adapter = HttpAdapter(token="", transport=recording_transport([], status=404))
    response = await adapter.get("https://api.github.com/users/nobody")
    assert response.status == 404


async def test_github_token_sent_only_to_github():
    seen = []
    adapter = HttpAdapter(token="t0ken", transport=recording_transport(seen))
    await adapter.get("https://api.github.com/users/octo-dev")
    await adapter.get("https://codeforces.com/api/user.info")
    assert seen[0].headers["Authorization"] == "Bearer t0ken"
    assert "Authorization" not in seen[1].headers


async def test_token_defaults_to_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    seen = []
    adapter = HttpAdapter(transport=recording_transport(seen))
    await adapter.get("https://api.github.com/users/octo-dev")
    assert seen[0].headers["Authorization"] == "Bearer from-env"


async def test_post_sends_json():
    seen = []
    adapter = HttpAdapter(token="", transport=recording_transport(seen))
    await adapter.post("https://leetcode.com/graphql", json={"query": "q"})
    assert seen[0].method == "POST"
    assert json.loads(seen[0].content) == {"query": "q"}


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (httpx.ReadTimeout("slow"), "TIMEOUT"),
        (httpx.ConnectError("refused"), "NETWORK"),
    ],
)
async def test_transport_errors_become_collection_errors(exc, code):
    adapter = HttpAdapter(token="", transport=failing_transport(exc))
    with pytest.raises(CollectionError) as err:
        await adapter.get("https://api.github.com/users/octo-dev")
    assert err.value.code == code
    assert err.value.context["url"] == "https://api.github.com/users/octo-dev"
