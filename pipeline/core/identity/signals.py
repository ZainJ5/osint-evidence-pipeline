"""Pairwise identity match signals (Strategy pattern, FR-08)."""

import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher

from pipeline.core.models import AccountRef, SignalScore

NEAR_HANDLE_RATIO = 0.85
NEAR_HANDLE_SCORE = 0.6

# Where each source's public profile lives; used to recognise links between accounts.
PROFILE_URLS = {
    "github": ("github.com/{h}",),
    "codeforces": ("codeforces.com/profile/{h}",),
    "leetcode": ("leetcode.com/{h}", "leetcode.com/u/{h}"),
}


class MatchSignal(ABC):
    """Scores how strongly two accounts look like the same person, in [0, 1]."""

    name = "signal"

    @abstractmethod
    def score(self, a: AccountRef, b: AccountRef) -> SignalScore: ...


def _field(ref: AccountRef, key: str) -> str:
    return " ".join(str(ref.profile.get(key) or "").split()).lower()


class EmailSignal(MatchSignal):
    """Matches accounts that publish the same email."""

    name = "email"

    def score(self, a: AccountRef, b: AccountRef) -> SignalScore:
        left, right = _field(a, "email"), _field(b, "email")
        if left and left == right:
            return SignalScore(self.name, 1.0, "same email address (address not stored, NFR-06)")
        return SignalScore(self.name, 0.0, "emails differ or are missing")


class HandleSignal(MatchSignal):
    """Matches accounts with equal or near-equal handles."""

    name = "handle"

    def score(self, a: AccountRef, b: AccountRef) -> SignalScore:
        left, right = a.handle.lower(), b.handle.lower()
        if not left or not right:
            return SignalScore(self.name, 0.0, "handle missing")
        if left == right:
            return SignalScore(self.name, 1.0, f"identical handle {left}")
        left_core, right_core = re.sub(r"[^a-z0-9]", "", left), re.sub(r"[^a-z0-9]", "", right)
        ratio = SequenceMatcher(None, left_core, right_core).ratio()
        if left_core == right_core or ratio >= NEAR_HANDLE_RATIO:
            return SignalScore(self.name, NEAR_HANDLE_SCORE, f"near-identical handles {a.handle} / {b.handle}")
        return SignalScore(self.name, 0.0, f"handles differ (similarity {ratio:.2f})")


def _bare_url(link: str) -> str:
    url = re.sub(r"^[a-z]+://", "", link.strip().lower())
    url = re.sub(r"^www\.", "", url)
    return url.split("?")[0].split("#")[0].rstrip("/")


def _points_to(links: list, target: AccountRef) -> str | None:
    """Return the first link that is target's profile URL, if any."""
    wanted = {pattern.format(h=target.handle.lower()) for pattern in PROFILE_URLS.get(target.source, ())}
    for link in links or []:
        if isinstance(link, str) and _bare_url(link) in wanted:
            return link
    return None


class CrossLinkSignal(MatchSignal):
    """Matches accounts whose profiles link to each other."""

    name = "cross_link"

    def score(self, a: AccountRef, b: AccountRef) -> SignalScore:
        for source, target in ((a, b), (b, a)):
            link = _points_to(source.profile.get("links"), target) if target.handle else None
            if link:
                return SignalScore(self.name, 1.0, f"{source.source}:{source.handle} links to {link}")
        return SignalScore(self.name, 0.0, "no profile links to the other account")


def _name_tokens(ref: AccountRef) -> list[str]:
    return sorted(re.sub(r"[^\w\s]", " ", _field(ref, "name")).split())


class NameSignal(MatchSignal):
    """Matches accounts with similar display names."""

    name = "name"

    def score(self, a: AccountRef, b: AccountRef) -> SignalScore:
        left, right = _name_tokens(a), _name_tokens(b)
        if len(left) >= 2 and left == right:
            return SignalScore(self.name, 1.0, f"same full name '{' '.join(left)}'")
        return SignalScore(self.name, 0.0, "full names differ or are incomplete")
