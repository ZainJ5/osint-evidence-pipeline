"""Claim extraction with Claude through the official anthropic SDK, using structured outputs (an LLMProvider)."""

import json

import anthropic

from pipeline.core.errors import ScoringError
from pipeline.core.ports import LLMProvider

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
UNSUPPORTED_KEYWORDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf")

SYSTEM_PROMPT = """You extract verifiable claims from a candidate's resume for an evidence-checking pipeline.

Return only claims the resume actually makes; never infer, generalise or add claims of your own.
- kind "skill": a concrete technology the candidate says they use or used (language, framework, library, \
database, cloud or DevOps tool). Skip soft skills, spoken languages and generic topics such as "algorithms". \
subject is the technology's canonical name (PostgreSQL for "Postgres", React for "React.js", Kubernetes for "k8s", \
Go for "Golang"). Set years only when the resume states a duration for that technology ("3 years of Python", \
"Python (3 years)"); otherwise years is null.
- kind "rating": a competitive programming rating on Codeforces or LeetCode. subject is "codeforces" or "leetcode". \
Use the number stated; for a rank without a number use its minimum rating (Codeforces pupil 1200, specialist 1400, \
expert 1600, candidate master 1900, master 2100, international master 2300, grandmaster 2400, international \
grandmaster 2600, legendary grandmaster 3000; LeetCode Knight 1850, Guardian 2150).
- kind "solved": a number of problems solved on Codeforces or LeetCode, with subject as for ratings.
One claim per kind and subject; keep the one with the most information. text is the exact snippet copied verbatim \
from the resume that makes the claim. Fields that do not apply to a claim are null."""


def _nullable(schema: dict) -> dict:
    kind = schema.get("type")
    return {**schema, "type": [kind, "null"]} if isinstance(kind, str) else schema


def strict_schema(schema: dict) -> dict:
    """Structured-output form of a JSON schema: closed objects, every property required, optional ones nullable."""
    out = {key: value for key, value in schema.items() if key not in UNSUPPORTED_KEYWORDS}
    if isinstance(out.get("items"), dict):
        out["items"] = strict_schema(out["items"])
    if out.get("type") == "object":
        required = set(schema.get("required", []))
        properties = {
            name: strict_schema(sub) if name in required else _nullable(strict_schema(sub))
            for name, sub in schema.get("properties", {}).items()
        }
        out.update(properties=properties, required=list(properties), additionalProperties=False)
    return out


class ClaudeClaimProvider(LLMProvider):
    """Claude with JSON-schema structured output. Credentials come from the environment unless a client is given.

    Unlike the rule-based provider the output can vary between calls; replay reuses the stored claims.
    """

    name = "claude"

    def __init__(self, client=None, model: str = DEFAULT_MODEL):
        self._client = client if client is not None else anthropic.Anthropic()
        self._model = model

    def complete(self, prompt: str, schema: dict) -> dict:
        response = self._create(prompt, schema)
        if response.stop_reason == "refusal":
            raise ScoringError("the model declined to extract claims", code="LLM_REFUSED", context=self._context())
        text = next((block.text for block in response.content if block.type == "text"), None)
        try:
            return json.loads(text or "")
        except json.JSONDecodeError as exc:
            context = {**self._context(), "stop_reason": response.stop_reason}
            raise ScoringError("model output is not JSON", code="LLM_BAD_OUTPUT", context=context) from exc

    def _create(self, prompt: str, schema: dict):
        """One Messages API call; vendor exceptions become ScoringError (adapters translate, core never sees them)."""
        try:
            return self._client.beta.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": strict_schema(schema)}},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise self._unavailable("rate limited", exc) from exc
        except anthropic.APIStatusError as exc:
            raise self._unavailable(f"API error {exc.status_code}", exc) from exc
        except anthropic.APIConnectionError as exc:
            raise self._unavailable("cannot reach the API", exc) from exc
        except anthropic.AnthropicError as exc:  # e.g. no credentials configured
            raise self._unavailable("client error", exc) from exc

    def _unavailable(self, reason: str, exc: Exception) -> ScoringError:
        context = {**self._context(), "error": type(exc).__name__}
        return ScoringError(f"Claude is unavailable: {reason}", code="LLM_UNAVAILABLE", context=context)

    def _context(self) -> dict:
        return {"provider": self.name, "model": self._model}
