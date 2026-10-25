"""RuleBasedClaimProvider: sections, durations, vocabulary, ambiguity and competitive programming patterns."""

import pytest

from pipeline.adapters.rule_claims import RuleBasedClaimProvider
from pipeline.core.scoring.claims import CLAIM_SCHEMA, PROMPT_TEMPLATE

PROVIDER = RuleBasedClaimProvider()


def claims(resume: str) -> list[dict]:
    return PROVIDER.complete(PROMPT_TEMPLATE.format(resume=resume), CLAIM_SCHEMA)["claims"]


def skills(resume: str) -> dict:
    return {c["subject"]: c.get("years") for c in claims(resume) if c["kind"] == "skill"}


def platform(resume: str, kind: str) -> dict:
    return {c["subject"]: c[kind] for c in claims(resume) if c["kind"] == kind}


def test_name_and_only_the_resume_part_of_the_prompt_is_read():
    assert PROVIDER.name == "rule-based"
    prompt = 'Use kind "skill" for Python and Docker.\n\nRESUME:\nI write Rust.'
    assert [c["subject"] for c in PROVIDER.complete(prompt, CLAIM_SCHEMA)["claims"]] == ["Rust"]


def test_prompt_without_marker_is_read_whole():
    assert [c["subject"] for c in PROVIDER.complete("Built with Django", CLAIM_SCHEMA)["claims"]] == ["Django"]


@pytest.mark.parametrize(
    "heading",
    [
        "Skills:",
        "Technical Skills",
        "TECHNOLOGIES",
        "Tech Stack:",
        "Languages:",
        "Frameworks & Libraries:",
        "## Skills",
    ],
)
def test_skill_headings_start_a_multi_line_section(heading):
    resume = f"{heading}\n- Go, C\n- R / Python\n\nExperience\nGo to market lead"
    assert skills(resume) == {"Go": None, "C": None, "R": None, "Python": None}


@pytest.mark.parametrize(
    "line", ["Skills: Go, C, R", "Skills | Go | C | R", "Skills - Go • C • R", "Languages: Go; C; R"]
)
def test_inline_skill_lists_with_any_separator(line):
    assert set(skills(line)) == {"Go", "C", "R"}


def test_section_ends_at_a_prose_line():
    resume = "Skills: Python\nLed the migration and was ready to go live within a week with a C grade."
    assert skills(resume) == {"Python": None}


@pytest.mark.parametrize(
    ("text", "years", "snippet"),
    [
        ("I have 3 years of Python.", 3.0, "3 years of Python"),
        ("3+ yrs Python in production", 3.0, "3+ yrs Python"),
        ("Python (3 years)", 3.0, "Python (3 years)"),
        ("Python - 3 years", 3.0, "Python - 3 years"),
        ("Python: 2.5 yrs", 2.5, "Python: 2.5 yrs"),
        ("over 2 years of experience with Python", 2.0, "2 years of experience with Python"),
        ("5 years experience in Python", 5.0, "5 years experience in Python"),
        ("4 years of hands-on experience with Python", 4.0, "4 years of hands-on experience with Python"),
    ],
)
def test_durations_before_and_after_the_technology(text, years, snippet):
    (claim,) = claims(text)
    assert (claim["subject"], claim["years"], claim["text"]) == ("Python", years, snippet)


def test_duration_belongs_to_the_adjacent_technology_only():
    assert skills("3 years of Python and Django") == {"Python": 3.0, "Django": None}


def test_aliases_map_to_canonical_display_names():
    found = skills("APIs on Postgres, React.js, k8s, sklearn, Golang and Node.js; C language course")
    assert found == {
        "PostgreSQL": None, "React": None, "Kubernetes": None, "scikit-learn": None, "Go": None, "Node.js": None,
        "C": None,
    }  # fmt: skip


def test_longest_form_wins():
    assert set(skills("Spring Boot, React Native, Ruby on Rails, Tailwind CSS")) == {
        "Spring Boot", "React Native", "Ruby on Rails", "Tailwind CSS"
    }  # fmt: skip


@pytest.mark.parametrize(
    "prose",
    [
        "Ready to go live; got a C grade; R&D budget",
        "love swift iterations and the spring release, react quickly",
        "JavaScriptish and pythonic code",
    ],
)
def test_ambiguous_words_in_prose_are_not_claims(prose):
    assert skills(prose) == {}


def test_ambiguous_words_count_right_after_a_duration_and_in_exact_case():
    assert skills("2 years of Go. Wrote Swift and Rust apps") == {"Go": 2.0, "Swift": None, "Rust": None}


def test_duplicates_keep_the_claim_with_years():
    found = [c for c in claims("Skills: Python\nBuilt tools in Python.\nPython (4 years)") if c["kind"] == "skill"]
    assert found == [{"text": "Python (4 years)", "kind": "skill", "subject": "Python", "years": 4.0}]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Codeforces rating 1650", {"codeforces": 1650}),
        ("rated 1650 on Codeforces", {"codeforces": 1650}),
        ("Codeforces: 1650", {"codeforces": 1650}),
        ("Codeforces (max rating 1820)", {"codeforces": 1820}),
        ("Codeforces rating 1650, max rating 1820", {"codeforces": 1820}),
        ("LeetCode rating 1900", {"leetcode": 1900}),
        ("LeetCode contest rating: 2010; Codeforces 1500", {"leetcode": 2010}),
        ("Codeforces rating 1650 and LeetCode rating 2000", {"codeforces": 1650, "leetcode": 2000}),
    ],
)
def test_numeric_ratings(text, expected):
    assert platform(text, "rating") == expected


@pytest.mark.parametrize(
    ("text", "rating"),
    [
        ("Codeforces Expert", 1600),
        ("Candidate Master on Codeforces", 1900),
        ("Codeforces International Grandmaster", 2600),
        ("Codeforces Pupil", 1200),
        ("Knight on LeetCode", 1850),
        ("LeetCode Guardian", 2150),
    ],
)
def test_ranks_map_to_their_minimum_rating(text, rating):
    assert list(platform(text, "rating").values()) == [rating]


def test_numeric_rating_beats_rank_and_unrelated_rank_words_are_ignored():
    assert platform("Codeforces Expert\nCodeforces rating 1750", "rating") == {"codeforces": 1750}
    assert platform("Master's degree in CS; mastered tools. My Codeforces handle is x", "rating") == {}
    assert platform("Codeforces newbie", "rating") == {}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("solved 500+ problems on LeetCode", {"leetcode": 500}),
        ("400+ LeetCode problems", {"leetcode": 400}),
        ("solved 300 problems on Codeforces", {"codeforces": 300}),
        ("LeetCode: 1,200 questions solved", {"leetcode": 1200}),
        ("Solved 250 problems", {}),
    ],
)
def test_solved_counts(text, expected):
    assert platform(text, "solved") == expected
    assert platform(text, "rating") == {}


def test_output_follows_the_claim_schema():
    output = PROVIDER.complete(PROMPT_TEMPLATE.format(resume="Codeforces Expert; 3 years of Python"), CLAIM_SCHEMA)
    allowed = set(CLAIM_SCHEMA["properties"]["claims"]["items"]["properties"])
    assert all(set(c) <= allowed and {"text", "kind", "subject"} <= set(c) for c in output["claims"])


def test_deterministic():
    resume = "Skills: Python, Docker\nCodeforces rating 1650"
    assert claims(resume) == claims(resume)
