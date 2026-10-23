"""Skill name normalisation through an alias table (FR-10). Shared by M4 and M5."""

import re

from pipeline.core.skills import vocabulary_aliases

EXPLICIT_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "node.js": "javascript",
    "nodejs": "javascript",
    "ts": "typescript",
    "golang": "go",
    "c++": "cpp",
    "gnu c++": "cpp",
    "c#": "csharp",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "reactjs": "react",
    "react.js": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "jupyter notebook": "python",
}


def _default_aliases() -> dict[str, str]:
    """Explicit aliases plus every vocabulary form, mapped to the explicit canonical name where one exists."""
    aliases = dict(EXPLICIT_ALIASES)
    for form, display in vocabulary_aliases().items():
        canonical = EXPLICIT_ALIASES.get(display, display)
        if form != canonical:
            aliases.setdefault(form, canonical)
    return aliases


DEFAULT_ALIASES = _default_aliases()

# Codeforces/LeetCode report compiler names, e.g. "GNU C++17", "Python 3", "PyPy 3-64", "Java 21".
COMPILER_PREFIXES = [
    (re.compile(r"^((gnu|ms)\s+)?(g\+\+|c\+\+|clang\+\+)"), "cpp"),
    (re.compile(r"^(python|pypy)"), "python"),
    (re.compile(r"^java(\s|$|\d)"), "java"),
    (re.compile(r"^kotlin"), "kotlin"),
    (re.compile(r"^(gnu\s+)?c(\s|\d|$)"), "c"),
    (re.compile(r"^((ms|mono)\s+)?c#"), "csharp"),
    (re.compile(r"^(javascript|node\.js)(\s|$)"), "javascript"),
    (re.compile(r"^rust"), "rust"),
    (re.compile(r"^go(\s|$)"), "go"),
]


class SkillNormalizer:
    """Maps skill names and aliases to canonical form."""

    def __init__(self, aliases: dict | None = None):
        self._aliases = {k.lower(): v.lower() for k, v in (aliases or DEFAULT_ALIASES).items()}

    def normalize(self, name: str) -> str:
        key = " ".join((name or "").lower().split())
        if key in self._aliases:
            return self._aliases[key]
        for pattern, canonical in COMPILER_PREFIXES:
            if pattern.match(key):
                return canonical
        return key

    def forms(self, canonical: str) -> set[str]:
        """The canonical name and every alias that normalises to it, e.g. 'postgresql' -> {'postgresql', 'postgres'}."""
        return {canonical} | {alias for alias, target in self._aliases.items() if target == canonical}
