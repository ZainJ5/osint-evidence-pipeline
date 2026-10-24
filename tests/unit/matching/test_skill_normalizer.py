"""SkillNormalizer alias table and compiler-name prefixes (FR-10)."""

import pytest

from pipeline.core.matching.normalizer import SkillNormalizer


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("Py", "python"),
        ("python3", "python"),
        ("Jupyter Notebook", "python"),
        ("JS", "javascript"),
        ("Node.js", "javascript"),
        ("TS", "typescript"),
        ("Golang", "go"),
        ("C++", "cpp"),
        ("C#", "csharp"),
        ("Postgres", "postgresql"),
        ("k8s", "kubernetes"),
        ("  React.JS  ", "react"),
        ("Vue.js", "vue"),
        ("Rust", "rust"),
    ],
)
def test_aliases(raw, canonical):
    assert SkillNormalizer().normalize(raw) == canonical


@pytest.mark.parametrize(
    ("compiler", "canonical"),
    [
        ("GNU C++17", "cpp"),
        ("GNU G++20 13.2 (64 bit, winlibs)", "cpp"),
        ("Clang++20 Diagnostics", "cpp"),
        ("MS C++ 2017", "cpp"),
        ("GNU C11", "c"),
        ("Python 3", "python"),
        ("PyPy 3-64", "python"),
        ("Java 21 64bit", "java"),
        ("Java 8", "java"),
        ("JavaScript V8 4.8.0", "javascript"),
        ("Node.js 15.8.0", "javascript"),
        ("Kotlin 1.9", "kotlin"),
        ("C# 10", "csharp"),
        ("Mono C#", "csharp"),
        ("Rust 2021", "rust"),
        ("Go 1.22.2", "go"),
    ],
)
def test_codeforces_and_leetcode_compiler_names(compiler, canonical):
    assert SkillNormalizer().normalize(compiler) == canonical


@pytest.mark.parametrize(("raw", "canonical"), [("Haskell", "haskell"), ("Machine   Learning", "machine learning")])
def test_unknown_names_are_lowercased_and_whitespace_collapsed(raw, canonical):
    assert SkillNormalizer().normalize(raw) == canonical


@pytest.mark.parametrize("raw", ["", None, "   "])
def test_blank_input_normalises_to_empty_string(raw):
    assert SkillNormalizer().normalize(raw) == ""


def test_custom_alias_table_replaces_defaults():
    normalizer = SkillNormalizer({"ML": "Machine Learning"})
    assert normalizer.normalize("ml") == "machine learning"
    assert normalizer.normalize("py") == "py"
