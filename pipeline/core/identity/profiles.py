"""Turn raw source profile payloads into AccountRefs with normalised keys."""

import json

from pipeline.core.errors import ResolutionError
from pipeline.core.models import AccountRef


def _profile(name, email, handle, links) -> dict:
    return {
        "name": name or None,
        "email": email or None,
        "handle": handle or None,
        "links": [link for link in links if isinstance(link, str) and link.strip()],
    }


def _github(data: dict) -> dict:
    twitter = data.get("twitter_username")
    links = [data.get("blog"), data.get("html_url"), f"https://twitter.com/{twitter}" if twitter else None]
    return _profile(data.get("name"), data.get("email"), data.get("login"), links)


def _codeforces(data: dict) -> dict:
    if data.get("status") != "OK" or not data.get("result"):
        raise ResolutionError("codeforces payload has no user", context={"source": "codeforces"})
    user = data["result"][0]
    name = " ".join(part for part in (user.get("firstName"), user.get("lastName")) if part)
    return _profile(name, None, user.get("handle"), [])


def _leetcode(data: dict) -> dict:
    user = (data.get("data") or {}).get("matchedUser")
    if not user:
        raise ResolutionError("leetcode payload has no user", context={"source": "leetcode"})
    profile = user.get("profile") or {}
    links = [user.get("githubUrl"), *(profile.get("websites") or [])]
    return _profile(profile.get("realName"), None, user.get("username"), links)


PARSERS = {"github": _github, "codeforces": _codeforces, "leetcode": _leetcode}


def build_account_ref(source: str, handle: str, payload) -> AccountRef:
    """Accepts the profile payload as a dict or as raw JSON bytes/str."""
    if source not in PARSERS:
        raise ResolutionError(f"unknown source '{source}'", context={"source": source})
    if isinstance(payload, (bytes, str)):
        try:
            payload = json.loads(payload)
        except ValueError as exc:
            raise ResolutionError("profile payload is not JSON", context={"source": source}) from exc
    if not isinstance(payload, dict):
        raise ResolutionError("profile payload is not an object", context={"source": source})
    return AccountRef(source, handle, PARSERS[source](payload))


def anchor_ref(name: str, email: str, links=()) -> AccountRef:
    """What the candidate told us about themselves, incl. profile links in the resume; accounts are compared to it."""
    return AccountRef("resume", "", _profile(name, email, None, list(links)))
