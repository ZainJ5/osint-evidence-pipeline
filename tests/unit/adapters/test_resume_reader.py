from pathlib import Path

import pytest

from pipeline.adapters.resume_reader import MAX_BYTES, read_resume
from pipeline.core.errors import ValidationError
from tests.resume_files import make_docx, make_pdf

SAMPLE_TXT = Path(__file__).resolve().parents[2] / "fixtures" / "resumes" / "sample.txt"


def test_txt_resume_is_read_as_utf8():
    text = read_resume("cv.txt", SAMPLE_TXT.read_bytes())
    assert text.startswith("Octo Developer\n")
    assert "https://github.com/octo-dev" in text


def test_text_that_is_not_utf8_falls_back_to_latin1():
    assert read_resume("cv.md", "# José Núñez\n".encode("latin-1")) == "# José Núñez"


def test_docx_resume_includes_paragraphs_table_cells_and_hyperlinks():
    data = make_docx(
        ["Octo Developer", "3 years of Python."],
        table=[["Skills", "Rust, Docker"]],
        link="https://github.com/octo-dev",
    )

    text = read_resume("CV.DOCX", data)

    assert text.splitlines()[:2] == ["Octo Developer", "3 years of Python."]
    assert "Skills" in text and "Rust, Docker" in text
    assert "https://github.com/octo-dev" in text


def test_pdf_resume_includes_text_and_link_annotations():
    data = make_pdf(["Octo Developer", "Codeforces rating 1600 (Div. 2)"], link="https://leetcode.com/u/octo-dev/")

    text = read_resume("cv.pdf", data)

    assert "Octo Developer" in text
    assert "Codeforces rating 1600 (Div. 2)" in text
    assert "https://leetcode.com/u/octo-dev/" in text


@pytest.mark.parametrize(
    ("filename", "data", "code"),
    [
        ("cv.exe", b"MZ", "UNSUPPORTED_FILE"),
        ("cv", b"text", "UNSUPPORTED_FILE"),
        ("cv.pdf", b"not a pdf", "UNSUPPORTED_FILE"),
        ("cv.docx", b"not a zip", "UNSUPPORTED_FILE"),
        ("cv.txt", b"  \n\t\n", "EMPTY_RESUME"),
        ("cv.txt", b"x" * (MAX_BYTES + 1), "FILE_TOO_LARGE"),
    ],
    ids=["exe", "no-extension", "bad-pdf", "bad-docx", "blank", "too-large"],
)
def test_unreadable_files_are_rejected_with_a_code(filename, data, code):
    with pytest.raises(ValidationError) as err:
        read_resume(filename, data)
    assert err.value.code == code
