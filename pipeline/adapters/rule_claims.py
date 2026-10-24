"""Deterministic rule-based claim extraction from resume text: an LLMProvider that needs no model."""

import re

from pipeline.core.ports import LLMProvider
from pipeline.core.skills import TECHNOLOGIES, allowed_in_prose, forms_of, mention_regex

RESUME_MARKER = "RESUME:\n"
FORM_TO_DISPLAY = {form: display for display in TECHNOLOGIES for form in forms_of(display)}
MENTION = mention_regex(FORM_TO_DISPLAY)

# Durations: "3 years of Python", "3+ yrs Python", "over 2 years of experience with Django", "5 years experience in
# Java" (before the technology) and "Python (3 years)", "Python - 3 years", "Python: 3 yrs" (after it).
_YEARS = r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\b"
YEARS_BEFORE = re.compile(
    _YEARS + r"(?:\s+of)?(?:\s+[\w-]+)?(?:\s+(?:experience|exp))?(?:\s+(?:with|in|using|on|of))?\s+$", re.I
)
YEARS_AFTER = re.compile(r"\s*[(:\-–—]?\s*" + _YEARS + r"\)?", re.I)

SKILL_HEADING = re.compile(
    r"^(?:[a-z]+[\s/&,]+){0,3}?(?:skills?|skill set|technologies|tech stack|stack|languages|frameworks|libraries|"
    r"tools|tooling|databases|platforms|devops|cloud|competencies|expertise)"
    r"(?:\s*(?:&|and|/|,)\s*[a-z]+)?\s*(?:[:|\-–—]|$)",
    re.I,
)
HEADINGS = {
    "experience", "work experience", "professional experience", "employment", "employment history", "work history",
    "work", "education", "projects", "personal projects", "side projects", "open source", "achievements", "awards",
    "honors", "certifications", "certificates", "summary", "profile", "objective", "about", "about me", "contact",
    "interests", "hobbies", "publications", "research", "volunteering", "competitive programming", "leadership",
    "references", "activities", "courses", "coursework",
}  # fmt: skip
BULLET = re.compile(r"^[\s\-*•·▪●◦>#]+")
LIST_SEPARATORS = re.compile(r"[,;|/:•·]")
MAX_ITEM_WORDS = 4

# Competitive programming. Rank thresholds are each rank's minimum rating; LeetCode badges are approximate: Knight is
# awarded from a contest rating of about 1850 and Guardian from about 2150 (top 25 % and 5 % of contestants).
PLATFORM = re.compile(r"\b(codeforces|leetcode)\b", re.I)
RATING = re.compile(
    r"\b(?:(?:max(?:imum)?|peak|highest|current|contest)\s+)?rating\s*(?:of|is|[:=\-–])?\s*~?\s*(\d{3,4})\b"
    r"|\brated\s+(?:at\s+)?(\d{3,4})\b"
    r"|\b(?:codeforces|leetcode)\s*[:(\-–—]\s*(\d{3,4})\b(?![+\d,])(?!\s*(?:[a-z]+\s+)?(?:problems|questions))",
    re.I,
)
SOLVED = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\s*\+?\s*(?:[a-z]+\s+){0,2}?(?:problems|questions|challenges)\b", re.I)
RANKS = {
    "codeforces": {
        "legendary grandmaster": 3000, "international grandmaster": 2600, "grandmaster": 2400,
        "international master": 2300, "master": 2100, "candidate master": 1900, "expert": 1600,
        "specialist": 1400, "pupil": 1200,
    },
    "leetcode": {"guardian": 2150, "knight": 1850},
}  # fmt: skip
RANK = re.compile(
    r"\b(" + "|".join(sorted({r for ranks in RANKS.values() for r in ranks}, key=len, reverse=True)) + r")\b(?!'s)",
    re.I,
)
MAX_RANK_GAP = 20  # characters between a rank word and its platform name
RATING_RANGE = range(100, 4001)


def _resume(prompt: str) -> str:
    return prompt.split(RESUME_MARKER, 1)[1] if RESUME_MARKER in prompt else prompt


def _is_heading(text: str) -> bool:
    label = text.split(":", 1)[0].strip().lower()
    if label in HEADINGS:
        return True
    return text.isupper() and len(text) <= 40 and not LIST_SEPARATORS.search(text)


def _is_list_line(text: str) -> bool:
    """Short comma/pipe/bullet separated items, unlike an experience sentence."""
    return all(len(item.split()) <= MAX_ITEM_WORDS for item in LIST_SEPARATORS.split(text))


def classified_lines(resume: str):
    """Yield (line, in_skills_section). A section runs from a skills heading to the next heading or prose line."""
    in_section, has_items = False, False
    for line in resume.splitlines():
        text = BULLET.sub("", line).strip()
        heading = SKILL_HEADING.match(text)
        if heading:
            in_section, has_items = True, bool(text[heading.end() :].strip())
        elif not text:
            in_section = in_section and not has_items
        elif _is_heading(text) or not (in_section and _is_list_line(text)):
            in_section = False
        else:
            has_items = True
        yield line, in_section and bool(text)


def _skill_claim(line: str, match: re.Match, in_section: bool) -> dict | None:
    """'Go', 'C' or lower-case 'rust' count in a skills section or right after a duration, otherwise not."""
    before = YEARS_BEFORE.search(line[: match.start()])
    if not (in_section or before or allowed_in_prose(match.group(1))):
        return None
    claim = {"text": match.group(1), "kind": "skill", "subject": FORM_TO_DISPLAY[match.group(1).lower()]}
    after = YEARS_AFTER.match(line, match.end())
    if before:
        claim.update(text=line[before.start() : match.end()], years=float(before.group(1)))
    elif after:
        claim.update(text=line[match.start() : after.end()], years=float(after.group(1)))
    return claim


def _gap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, b[0] - a[1], a[0] - b[1])


def _nearest_platform(line: str, span: tuple[int, int]) -> re.Match | None:
    platforms = list(PLATFORM.finditer(line))
    return min(platforms, key=lambda p: _gap(p.span(), span)) if platforms else None


def _snippet(line: str, a: re.Match, b: re.Match) -> str:
    return line[min(a.start(), b.start()) : max(a.end(), b.end())].strip()


def _platform_claims(line: str):
    """Rating, solved and rank claims of the platform named nearest to each number on the line."""
    for match in RATING.finditer(line):
        rating = int(match.group(match.lastindex))  # the one alternative that matched
        platform = _nearest_platform(line, match.span())
        if rating in RATING_RANGE and platform:
            yield {"text": _snippet(line, platform, match), "kind": "rating", "subject": platform.group(1).lower(),
                   "rating": rating}  # fmt: skip
    for match in SOLVED.finditer(line):
        platform = _nearest_platform(line, match.span())
        if platform:
            yield {"text": _snippet(line, platform, match), "kind": "solved", "subject": platform.group(1).lower(),
                   "solved": int(match.group(1).replace(",", ""))}  # fmt: skip
    yield from _rank_claims(line)


def _rank_claims(line: str):
    for match in RANK.finditer(line):
        platform = _nearest_platform(line, match.span())
        if not platform or _gap(platform.span(), match.span()) > MAX_RANK_GAP:
            continue
        rating = RANKS[platform.group(1).lower()].get(match.group(1).lower())
        if rating:
            yield {"text": _snippet(line, platform, match), "kind": "rating", "subject": platform.group(1).lower(),
                   "rating": rating, "from_rank": True}  # fmt: skip


def _better(new: dict, old: dict) -> bool:
    """Keep the claim with the most information: a duration, an explicit rating over a rank, the higher number."""
    if new["kind"] == "skill":
        return old.get("years") is None and new.get("years") is not None
    if bool(new.get("from_rank")) != bool(old.get("from_rank")):
        return bool(old.get("from_rank"))
    return new[new["kind"]] > old[old["kind"]]


class RuleBasedClaimProvider(LLMProvider):
    """Extracts skill, rating and solved claims with a curated vocabulary and patterns. Same prompt, same output."""

    name = "rule-based"

    def complete(self, prompt: str, schema: dict) -> dict:
        claims: dict[tuple[str, str], dict] = {}
        for line, in_section in classified_lines(_resume(prompt)):
            found = [_skill_claim(line, m, in_section) for m in MENTION.finditer(line)]
            if PLATFORM.search(line):
                found += _platform_claims(line)
            for claim in filter(None, found):
                key = (claim["kind"], claim["subject"].lower())
                if key not in claims or _better(claim, claims[key]):
                    claims[key] = claim
        return {"claims": [{k: v for k, v in c.items() if k != "from_rank"} for c in claims.values()]}
