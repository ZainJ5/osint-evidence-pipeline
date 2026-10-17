"""Read the text of an uploaded resume file (.pdf, .docx, .txt, .md)."""

import io
import re
import zipfile
from pathlib import PurePath

import docx
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.opc.exceptions import PackageNotFoundError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from pipeline.core.errors import ValidationError

MAX_BYTES = 5 * 1024 * 1024


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _pdf_links(page) -> list[str]:
    links = []
    for annot in page.get("/Annots") or []:
        action = annot.get_object().get("/A") or {}
        if action.get("/URI"):
            links.append(str(action["/URI"]))
    return links


def _pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    links = [link for page in reader.pages for link in _pdf_links(page)]
    return "\n".join([*pages, *links])


def _docx(data: bytes) -> str:
    document = docx.Document(io.BytesIO(data))
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.extend(cell.text for cell in row.cells)
    # Link text such as "GitHub" hides the URL; it lives only in the document's relationships.
    lines.extend(r.target_ref for r in document.part.rels.values() if r.reltype == RELATIONSHIP_TYPE.HYPERLINK)
    return "\n".join(lines)


READERS = {".pdf": _pdf, ".docx": _docx, ".txt": _text, ".md": _text}


def _clean(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def read_resume(filename: str, data: bytes) -> str:
    """Extracted plain text. Raises ValidationError UNSUPPORTED_FILE, EMPTY_RESUME or FILE_TOO_LARGE."""
    if len(data) > MAX_BYTES:
        raise ValidationError("resume file is larger than 5 MB", code="FILE_TOO_LARGE")
    reader = READERS.get(PurePath(filename or "").suffix.lower())
    if reader is None:
        raise ValidationError("resume must be a .pdf, .docx, .txt or .md file", code="UNSUPPORTED_FILE")
    try:
        text = _clean(reader(data))
    except (PyPdfError, PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise ValidationError("resume file could not be read", code="UNSUPPORTED_FILE") from exc
    if not text:
        raise ValidationError("no text found in the resume file", code="EMPTY_RESUME")
    return text
