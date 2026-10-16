"""Extract structured resume claims through an LLMProvider and validate its output (FR-11)."""

import uuid

from pipeline.core.errors import ScoringError
from pipeline.core.models import Claim
from pipeline.core.ports import LLMProvider

CLAIM_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "osint-evidence-pipeline/claims")
CLAIM_KINDS = ("skill", "rating", "solved")
PLATFORMS = ("codeforces", "leetcode")

CLAIM_SCHEMA = {
    "type": "object",
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["text", "kind", "subject"],
                "properties": {
                    "text": {"type": "string"},
                    "kind": {"type": "string", "enum": list(CLAIM_KINDS)},
                    "subject": {"type": "string"},
                    "years": {"type": "number", "minimum": 0},
                    "rating": {"type": "integer", "minimum": 1},
                    "solved": {"type": "integer", "minimum": 1},
                },
            },
        }
    },
}

# Kept free of phrases like "N years" or "Skills:" so rule-based fakes only see the resume's own claims.
PROMPT_TEMPLATE = (
    "Extract verifiable claims from the resume below and answer with JSON that follows the given schema. "
    'Use kind "skill" for a technology (with years when the resume states a duration), kind "rating" '
    'for a competitive programming rating and kind "solved" for a number of solved problems; for those two, '
    'subject is the platform name in lower case ("codeforces" or "leetcode").\n\n'
    "RESUME:\n{resume}"
)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _positive_int(value) -> bool:
    return _is_number(value) and value > 0 and float(value).is_integer()


def _valid(kind: str, subject, years, item: dict) -> bool:
    if not isinstance(subject, str) or not subject.strip():
        return False
    if years is not None and (not _is_number(years) or years < 0):
        return False
    if kind == "skill":
        return True
    if subject.strip().lower() not in PLATFORMS:
        return False
    return _positive_int(item.get(kind))  # item["rating"] or item["solved"]


def _parse_item(candidate_id: str, item) -> Claim | None:
    """Return a Claim, or None when the item is malformed."""
    if not isinstance(item, dict) or item.get("kind") not in CLAIM_KINDS:
        return None
    kind, subject, years = item["kind"], item.get("subject"), item.get("years")
    if not _valid(kind, subject, years, item):
        return None
    subject = subject.strip() if kind == "skill" else subject.strip().lower()
    claim_id = str(uuid.uuid5(CLAIM_NAMESPACE, f"{candidate_id}:{kind}:{subject.lower()}"))
    text = item["text"] if isinstance(item.get("text"), str) and item["text"].strip() else subject
    return Claim(
        id=claim_id,
        candidate_id=candidate_id,
        text=text,
        kind=kind,
        subject=subject,
        years=float(years) if years is not None and kind == "skill" else None,
        rating=int(item["rating"]) if kind == "rating" else None,
        solved=int(item["solved"]) if kind == "solved" else None,
    )


def _adds_years(kept: Claim, duplicate: Claim) -> bool:
    """A later duplicate replaces the kept claim only when it adds a duration."""
    return kept.years is None and duplicate.years is not None


class ClaimExtractor:
    """Extracts claims from resume text with an LLM."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def extract(self, candidate_id: str, resume_text: str) -> list[Claim]:
        output = self._llm.complete(PROMPT_TEMPLATE.format(resume=resume_text), CLAIM_SCHEMA)
        if not isinstance(output, dict) or not isinstance(output.get("claims"), list):
            raise ScoringError("LLM output is not {'claims': [...]}", code="LLM_BAD_OUTPUT")
        claims: dict[str, Claim] = {}
        for item in output["claims"]:
            claim = _parse_item(candidate_id, item)
            if claim and (claim.id not in claims or _adds_years(claims[claim.id], claim)):
                claims[claim.id] = claim
        return list(claims.values())
