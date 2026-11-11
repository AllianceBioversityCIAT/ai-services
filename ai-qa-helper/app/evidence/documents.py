"""Text from downloaded files.

PDF: PyMuPDF, as in qa-service ``WebScraperService._extract_pdf_text`` (read from memory instead
of a temp file). Office files: the text runs are read straight from the OOXML parts with
``zipfile``; qa-service reads xlsx with pandas/openpyxl and does not read docx/pptx, and pandas
alone would add ~100 MB to the Lambda zip.
"""

import html
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import pymupdf

MIN_CHARS_PER_PAGE = 50
"""Below this average the PDF is treated as scanned (no usable text layer)."""
MAX_UNZIPPED_BYTES = 60 * 1024 * 1024
"""Zip-bomb guard for Office files."""

OfficeKind = Literal["docx", "pptx", "xlsx"]


@dataclass(frozen=True)
class PdfText:
    text: str
    pages: int
    scanned: bool


def is_pdf(body: bytes) -> bool:
    return body[:4] == b"%PDF"


def pdf_text(body: bytes) -> PdfText:
    with pymupdf.open(stream=body, filetype="pdf") as doc:
        if doc.needs_pass:
            doc.authenticate("")  # same as the previous helper: try an empty password
        pages = [page.get_text() for page in doc]
        count = doc.page_count
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    return PdfText(text=text, pages=count, scanned=len(text) < MIN_CHARS_PER_PAGE * max(1, count))


_PARTS: dict[str, re.Pattern[str]] = {
    "docx": re.compile(r"^word/(document|footnotes|endnotes)\.xml$"),
    "pptx": re.compile(r"^ppt/slides/slide\d+\.xml$"),
    "xlsx": re.compile(r"^xl/sharedStrings\.xml$"),
}
_RUNS: dict[str, re.Pattern[str]] = {
    "docx": re.compile(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>|</w:p>"),
    "pptx": re.compile(r"<a:t>([^<]*)</a:t>|</a:p>"),
    "xlsx": re.compile(r"<t(?:\s[^>]*)?>([^<]*)</t>|</si>"),
}


def office_kind(body: bytes) -> OfficeKind | None:
    if body[:2] != b"PK":
        return None
    try:
        names = zipfile.ZipFile(BytesIO(body)).namelist()
    except zipfile.BadZipFile:
        return None
    if "word/document.xml" in names:
        return "docx"
    if any(n.startswith("ppt/slides/") for n in names):
        return "pptx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    return None


def office_text(body: bytes, kind: OfficeKind) -> str:
    zf = zipfile.ZipFile(BytesIO(body))
    infos = [i for i in zf.infolist() if _PARTS[kind].match(i.filename)]
    if sum(i.file_size for i in infos) > MAX_UNZIPPED_BYTES:
        raise ValueError("zip_too_large")
    infos.sort(key=lambda i: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", i.filename)])
    parts = []
    for info in infos:
        xml = zf.read(info).decode("utf-8", errors="replace")
        parts.append("".join(html.unescape(m.group(1)) if m.group(1) is not None else "\n" for m in _RUNS[kind].finditer(xml)))
    text = "\n\n".join(p.strip() for p in parts if p.strip())
    return re.sub(r"\n{3,}", "\n\n", text)
