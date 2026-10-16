"""ClaudeClaimProvider with a fake client: request shape, JSON parsing, refusal and error translation (no network)."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from pipeline.adapters.claude_llm import DEFAULT_MODEL, FALLBACK_BETA, ClaudeClaimProvider, strict_schema
from pipeline.core.errors import ScoringError
from pipeline.core.scoring.claims import CLAIM_SCHEMA, PROMPT_TEMPLATE, ClaimExtractor

URL = "https://api.anthropic.com/v1/messages"
OUTPUT = {"claims": [{"text": "3 years of Python", "kind": "skill", "subject": "Python", "years": 3,
                      "rating": None, "solved": None}]}  # fmt: skip


OUTPUT_TEXT = json.dumps(OUTPUT)


def response(text=OUTPUT_TEXT, stop_reason="end_turn"):
    blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


class FakeClient:
    """Stands in for anthropic.Anthropic(): records create() kwargs, returns or raises what it was given."""

    def __init__(self, result):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._result = result

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def status_error(cls, status):
    request = httpx2.Request("POST", URL)
    return cls("error", response=httpx2.Response(status, request=request), body=None)


def test_request_shape():
    client = FakeClient(response())
    ClaudeClaimProvider(client).complete("RESUME:\nPython", CLAIM_SCHEMA)
    (call,) = client.calls
    assert call["model"] == DEFAULT_MODEL == "claude-opus-5-5"
    assert call["max_tokens"] == 16000
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": strict_schema(CLAIM_SCHEMA)},
    }
    assert call["messages"] == [{"role": "user", "content": "RESUME:\nPython"}]
    assert "verbatim" in call["system"]
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(call)


def test_name_and_model_override():
    client = FakeClient(response())
    provider = ClaudeClaimProvider(client, model="claude-sonnet-5-5")
    provider.complete("x", CLAIM_SCHEMA)
    assert provider.name == "claude"
    assert client.calls[0]["model"] == "claude-sonnet-5-5"


def test_strict_schema_closes_objects_and_makes_optional_fields_nullable():
    item = strict_schema(CLAIM_SCHEMA)["properties"]["claims"]["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == ["text", "kind", "subject", "years", "rating", "solved"]
    assert item["properties"]["years"] == {"type": ["number", "null"]}
    assert item["properties"]["solved"] == {"type": ["integer", "null"]}
    assert item["properties"]["kind"] == {"type": "string", "enum": ["skill", "rating", "solved"]}
    top = strict_schema(CLAIM_SCHEMA)
    assert (top["required"], top["additionalProperties"]) == (["claims"], False)


def test_first_text_block_is_parsed_and_feeds_the_extractor():
    claims = ClaimExtractor(ClaudeClaimProvider(FakeClient(response()))).extract("cand-1", "3 years of Python")
    assert [(c.kind, c.subject, c.years, c.text) for c in claims] == [("skill", "Python", 3.0, "3 years of Python")]


def test_prompt_is_the_extractor_prompt():
    client = FakeClient(response())
    ClaimExtractor(ClaudeClaimProvider(client)).extract("cand-1", "I know Go")
    assert client.calls[0]["messages"][0]["content"] == PROMPT_TEMPLATE.format(resume="I know Go")


def test_refusal_raises_llm_refused():
    with pytest.raises(ScoringError) as info:
        ClaudeClaimProvider(FakeClient(response(text="", stop_reason="refusal"))).complete("x", CLAIM_SCHEMA)
    assert info.value.code == "LLM_REFUSED"


@pytest.mark.parametrize("text", ["not json", '{"claims": [', ""])
def test_unparseable_output_raises_bad_output(text):
    with pytest.raises(ScoringError) as info:
        ClaudeClaimProvider(FakeClient(response(text=text, stop_reason="max_tokens"))).complete("x", CLAIM_SCHEMA)
    assert info.value.code == "LLM_BAD_OUTPUT"
    assert info.value.context["stop_reason"] == "max_tokens"


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=httpx2.Request("POST", URL)),
        anthropic.APITimeoutError(request=httpx2.Request("POST", URL)),
        status_error(anthropic.RateLimitError, 429),
        status_error(anthropic.InternalServerError, 500),
        status_error(anthropic.AuthenticationError, 401),
        anthropic.AnthropicError("no credentials"),
    ],
)
def test_vendor_errors_become_llm_unavailable(error):
    with pytest.raises(ScoringError) as info:
        ClaudeClaimProvider(FakeClient(error)).complete("x", CLAIM_SCHEMA)
    assert info.value.code == "LLM_UNAVAILABLE"
    assert info.value.context == {"provider": "claude", "model": DEFAULT_MODEL, "error": type(error).__name__}
    assert isinstance(info.value.__cause__, anthropic.AnthropicError)


def test_default_client_is_built_from_the_environment(monkeypatch):
    built = []
    monkeypatch.setattr(anthropic, "Anthropic", lambda: built.append(True) or FakeClient(response()))
    ClaudeClaimProvider().complete("x", CLAIM_SCHEMA)
    assert built == [True]
