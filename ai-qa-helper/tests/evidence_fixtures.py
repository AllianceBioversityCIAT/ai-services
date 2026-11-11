"""Local fixtures for the evidence tests: generated files and an in-memory HTTP client."""

import io
import json
import zipfile
from urllib.parse import urlencode

import pymupdf

from app.evidence.http import Fetched

LONG_TEXT = (
    "This innovation package trained 1,200 women farmers in climate-smart rice practices across three "
    "districts, and the extension service adopted gender-responsive training materials developed with "
    "local partners during the 2025 season."
)


def make_pdf(text: str | None) -> bytes:
    """One-page PDF; None gives a page with no text layer (like a scan)."""
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>' for p in paragraphs)
    return _zip({"[Content_Types].xml": "<Types/>", "word/document.xml": f"<w:document><w:body>{body}</w:body></w:document>"})


def make_pptx(slides: list[str]) -> bytes:
    files = {"[Content_Types].xml": "<Types/>"}
    for i, s in enumerate(slides, 1):
        files[f"ppt/slides/slide{i}.xml"] = f"<p:sld><a:p><a:r><a:t>{s}</a:t></a:r></a:p></p:sld>"
    return _zip(files)


def make_xlsx(strings: list[str]) -> bytes:
    sst = "".join(f"<si><t>{s}</t></si>" for s in strings)
    return _zip({"xl/workbook.xml": "<workbook/>", "xl/sharedStrings.xml": f"<sst>{sst}</sst>"})


def resp(body: bytes | str = b"", status: int = 200, content_type: str = "", url: str = "", headers: dict | None = None) -> Fetched:
    data = body.encode() if isinstance(body, str) else body
    return Fetched(url=url, status=status, content_type=content_type, body=data, headers=headers or {})


def html(body: str, **kw) -> Fetched:
    return resp(body, content_type="text/html; charset=utf-8", **kw)


def as_json(obj: object) -> Fetched:
    return resp(json.dumps(obj), content_type="application/json")


class FakeHttp:
    """Routes keyed by URL (plus encoded params). Unknown URLs answer 404."""

    def __init__(self, routes: dict[str, Fetched | Exception]):
        self.routes = routes
        self.requested: list[str] = []

    def get(self, url: str, *, accept: str = "*/*", params: dict[str, str] | None = None) -> Fetched:
        key = f"{url}?{urlencode(params)}" if params else url
        self.requested.append(key)
        r = self.routes.get(key)
        if isinstance(r, Exception):
            raise r
        if r is None:
            return resp(status=404, content_type="text/plain", url=key)
        return Fetched(url=r.url or key, status=r.status, content_type=r.content_type, body=r.body, headers=r.headers)
