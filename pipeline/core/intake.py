"""Pure helpers that read links, profile handles, an email and a name guess out of resume text."""

import re

from pipeline.core.inputs import HANDLE_RULES

# A full URL, or a bare www./profile-site address that is not part of an email address.
URL_RE = re.compile(
    r"https?://[^\s<>\"'()]+"
    r"|(?<![\w@./])(?:www\.[\w-]+(?:\.[\w-]+)+|(?:github|gitlab|codeforces|leetcode|linkedin)\.com)(?:/[^\s<>\"'()]*)?",
    re.I,
)
TRAILING = ".,;:!?)]}>'\""
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_RESERVED = {
    "about", "apps", "collections", "contact", "enterprise", "explore", "features", "join", "login",
    "marketplace", "notifications", "orgs", "pricing", "search", "security", "settings", "site", "sponsors",
    "topics", "trending",
}  # fmt: skip
LEETCODE_RESERVED = {"accounts", "company", "contest", "discuss", "explore", "interview", "problems", "problemset"}
NAME_WORD_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|['.\-])*$")  # letters, plus ' . - inside the word
NOT_NAMES = {"curriculum", "vitae", "resume", "résumé", "cv", "profile", "contact", "summary", "experience"}
NAME_LINES = 5  # a name is at the top of a resume


def extract_links(text: str) -> list[str]:
    """Every URL in the text, in order and without duplicates; bare addresses get https://."""
    links = []
    for match in URL_RE.finditer(text or ""):
        link = match.group(0).rstrip(TRAILING)
        if not re.match(r"https?://", link, re.I):
            link = f"https://{link}"
        if link not in links:
            links.append(link)
    return links


def _profile_handle(link: str) -> tuple[str, str] | None:
    """(source, handle) when the link is a GitHub, Codeforces or LeetCode profile URL."""
    bare = re.sub(r"^https?://(www\.)?", "", link, flags=re.I).split("?")[0].split("#")[0]
    host, *path = [part for part in bare.split("/") if part]
    host = host.lower()
    if host == "github.com" and len(path) == 1 and path[0].lower() not in GITHUB_RESERVED:
        return "github", path[0]
    if host == "codeforces.com" and len(path) == 2 and path[0] == "profile":
        return "codeforces", path[1]
    if host == "leetcode.com" and len(path) == 2 and path[0] == "u":
        return "leetcode", path[1]
    if host == "leetcode.com" and len(path) == 1 and path[0].lower() not in LEETCODE_RESERVED:
        return "leetcode", path[0]
    return None


def detect_handles(text: str) -> dict:
    """source -> handle for the first valid profile link of each source."""
    handles = {}
    for link in extract_links(text):
        found = _profile_handle(link)
        if found and HANDLE_RULES[found[0]].match(found[1]):
            handles.setdefault(*found)
    return handles


def detect_email(text: str) -> str | None:
    match = EMAIL_RE.search(text or "")
    return match.group(0) if match else None


def _as_name(line: str) -> str | None:
    part = re.split(r"\s+[|·—–-]\s+|,", line.strip())[0].strip()
    words = part.split()
    if not 2 <= len(words) <= 4 or any(w.lower() in NOT_NAMES for w in words):
        return None
    if not all(NAME_WORD_RE.match(w) and w[0].isupper() for w in words):
        return None
    return part.title() if part.isupper() else part


def guess_name(text: str) -> str | None:
    """The first of the top lines that looks like a person's name (2-4 capitalised words), or None."""
    lines = [line for line in (text or "").splitlines() if line.strip()][:NAME_LINES]
    for line in lines:
        name = _as_name(line)
        if name:
            return name
    return None
