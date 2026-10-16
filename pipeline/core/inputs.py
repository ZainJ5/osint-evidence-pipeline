"""Validated input models used at every module entry point. Invalid input fails here, at the boundary."""

import math
import re
from dataclasses import dataclass, field

from pipeline.core.errors import ValidationError
from pipeline.core.models import SOURCES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HANDLE_RULES = {
    "github": re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$"),
    "codeforces": re.compile(r"^[A-Za-z0-9_.\-]{3,24}$"),
    "leetcode": re.compile(r"^[A-Za-z0-9_\-]{1,30}$"),
}
MAX_RESUME_CHARS = 50_000  # long CVs with project sections exceed 20 000 characters


@dataclass(frozen=True)
class CandidateInput:
    """Validated candidate submission."""

    name: str
    email: str
    resume_text: str
    handles: dict = field(default_factory=dict)  # source -> handle

    def __post_init__(self):
        if not self.name or not self.name.strip() or len(self.name) > 200:
            raise ValidationError("name must be 1-200 characters", context={"field": "name"})
        if not EMAIL_RE.match(self.email or ""):
            raise ValidationError("email is not a valid address", context={"field": "email"})
        if not self.resume_text or len(self.resume_text) > MAX_RESUME_CHARS:
            raise ValidationError(
                f"resume_text must be 1-{MAX_RESUME_CHARS} characters", context={"field": "resume_text"}
            )
        for source, handle in self.handles.items():
            if source not in SOURCES:
                raise ValidationError(f"unknown source '{source}'", context={"field": "handles"})
            if not HANDLE_RULES[source].match(handle or ""):
                raise ValidationError(f"invalid {source} handle", context={"field": f"handles.{source}"})


@dataclass(frozen=True)
class JobRequirementInput:
    """Validated job requirement submission."""

    id: str
    title: str
    text: str
    required_skills: tuple[str, ...]

    def __post_init__(self):
        if not (self.id or "").strip() or not (self.title or "").strip():
            raise ValidationError("job id and title are required", context={"field": "id"})
        if not self.required_skills or len(self.required_skills) > 50:
            raise ValidationError("required_skills must contain 1-50 skills", context={"field": "required_skills"})
        if any(not s or not s.strip() for s in self.required_skills):
            raise ValidationError("required_skills cannot contain blanks", context={"field": "required_skills"})


@dataclass(frozen=True)
class RunConfig:
    """Validated tuning parameters for one pipeline run."""

    link_threshold: float = 0.50
    max_requests_per_source: int = 2
    min_interval_seconds: float = 0.5
    max_retries: int = 3
    extraction_workers: int = 4
    max_repos: int = 50

    def __post_init__(self):
        _check_number("link_threshold", self.link_threshold, 0.0, 1.0)
        _check_number("min_interval_seconds", self.min_interval_seconds, 0.0)
        _check_int("max_requests_per_source", self.max_requests_per_source, 1)
        _check_int("max_retries", self.max_retries, 0, 3)
        _check_int("extraction_workers", self.extraction_workers, 1)
        _check_int("max_repos", self.max_repos, 0, 100)  # one GitHub page holds 100 repos


def _check_int(name: str, value, low: int, high: int | None = None) -> None:
    """Whole numbers only: a float count would crash range() or loosen a semaphore later (BB-DEF-01/03)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < low or (high is not None and value > high):
        bounds = f"[{low}, {high}]" if high is not None else f">= {low}"
        raise ValidationError(f"{name} must be an integer {bounds}", context={"field": name})


def _check_number(name: str, value, low: float, high: float = math.inf) -> None:
    """Finite numbers only: NaN compares false with everything and would disable the check (BB-DEF-02)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number", context={"field": name})
    if not low <= value <= high:
        raise ValidationError(f"{name} must be in [{low}, {high}]", context={"field": name})
