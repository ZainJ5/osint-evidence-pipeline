"""Builders for small resume files (docx, pdf) used by intake tests."""

import io

import docx


def make_docx(paragraphs: list[str], table: list[list[str]] | None = None, link: str | None = None) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table:
        grid = document.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, text in enumerate(row):
                grid.cell(r, c).text = text
    if link:  # a hyperlink whose URL is only in the relationship, as Word stores "GitHub" link text
        document.part.relate_to(link, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")


def make_pdf(lines: list[str], link: str | None = None) -> bytes:
    """A one-page PDF with Helvetica text lines and an optional link annotation."""
    content = "BT /F1 12 Tf 72 720 Td " + " 0 -16 Td ".join(f"({_escape(line)}) Tj" for line in lines) + " ET"
    annots = "/Annots [6 0 R] " if link else ""
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >> {annots}>>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Type /Annot /Subtype /Link /Rect [72 700 200 712] /A << /S /URI /URI ({link}) >> >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out
