from pipeline.core.intake import detect_email, detect_handles, extract_links, guess_name

RESUME = """Jane Doe
Backend Engineer | Berlin
jane.doe@example.org | +49 30 1234567
https://github.com/janedoe · leetcode.com/u/jane_lc/ · https://codeforces.com/profile/jane_d.
Portfolio: www.janedoe.dev

Experience
Acme GmbH (2021-2024): 3 years of Python, Docker and PostgreSQL.
Contributed to https://github.com/orgs/acme/projects (see github.com/acme/api).
"""


def test_extract_links_finds_full_and_bare_urls_without_trailing_punctuation():
    links = extract_links(RESUME)

    assert links == [
        "https://github.com/janedoe",
        "https://leetcode.com/u/jane_lc/",
        "https://codeforces.com/profile/jane_d",
        "https://www.janedoe.dev",
        "https://github.com/orgs/acme/projects",
        "https://github.com/acme/api",
    ]


def test_extract_links_ignores_email_domains_and_deduplicates():
    text = "mail me: jane@github.com or see github.com/janedoe and https://github.com/janedoe"
    assert extract_links(text) == ["https://github.com/janedoe"]


def test_detect_handles_takes_profile_links_only():
    assert detect_handles(RESUME) == {"github": "janedoe", "codeforces": "jane_d", "leetcode": "jane_lc"}


def test_detect_handles_skips_reserved_paths_and_invalid_handles():
    text = "https://github.com/features github.com/settings leetcode.com/problems/two-sum https://github.com/-bad"
    assert detect_handles(text) == {}


def test_detect_handles_accepts_short_leetcode_profile_url():
    assert detect_handles("LeetCode: https://leetcode.com/octo-dev") == {"leetcode": "octo-dev"}


def test_detect_email_returns_first_address_or_none():
    assert detect_email(RESUME) == "jane.doe@example.org"
    assert detect_email("no contact here") is None


def test_guess_name_uses_the_first_name_like_line():
    assert guess_name(RESUME) == "Jane Doe"
    assert guess_name("\n  CURRICULUM VITAE\nMARIA DEL CARMEN LOPEZ\nmaria@example.org") == "Maria Del Carmen Lopez"
    assert guess_name("Résumé\nJean-Luc O'Neil — Data Scientist") == "Jean-Luc O'Neil"


def test_guess_name_returns_none_when_no_line_looks_like_a_name():
    assert guess_name("Python developer since 2015\nhttps://github.com/x\nme@example.org") is None
    assert guess_name("") is None
