"""Evidence scraper, copied from qa-service without the browser paths.

Source: qa-service/app/web_scraping/web_scraping.py (WebScraperService) and
evidence_scraper.py (_remove_references_section), branch dev-qa, commit 4959345.

Kept as in qa-service:
  - routing order: YouTube -> DOI -> CGSpace handle -> SharePoint/OneDrive/Drive -> web page;
  - CGSpace REST API (pid/find, ORIGINAL bundle PDF, metadata record when there is no PDF);
  - Crossref for DOIs, accepted when it has an abstract of 200+ characters;
  - SharePoint ``download=1`` rewrite;
  - _validate_content (minimum length, login and error indicators);
  - main-content selection for HTML pages and the references-section trimming.

Changed, and why:
  - No Playwright: the worker ships as a zip Lambda, where Chromium does not fit. Web pages and
    DOI landing pages are fetched with plain HTTP; JavaScript-only pages end up unreadable.
  - Every request goes through GuardedHttp (SSRF guard per redirect hop, size cap, deadline).
  - Files are read in memory; nothing is written to disk.
  - File type is taken from the content (magic bytes, content type), not the filename, so direct
    PDF links and SharePoint downloads without a filename work.
  - Scanned PDFs are kept as bytes for the OCR fallback (the model reads them as a document block).
  - Private links are told apart: 401/403 and Microsoft/Google login pages -> authentication_required.
  - Google Drive/Docs links are rewritten to their export URL (qa-service appended download=1).
  - CGSpace ``/items/<uuid>`` links use the API too (qa-service sent them to the browser).
  - Docx and pptx are read (qa-service supported only pdf and xlsx).
"""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from app.evidence.documents import is_pdf, office_kind, office_text, pdf_text
from app.evidence.http import Fetched, HttpClient

MIN_CONTENT_LENGTH = 100

AUTH_INDICATORS = [
    "sign in", "log in", "login", "authenticate", "auth0",
    "access denied", "unauthorized", "forbidden",
    "authentication required", "please log in",
    "iniciar sesión", "autenticación requerida",
]

ERROR_INDICATORS = [
    "404", "not found", "page not found",
    "403", "forbidden", "401", "unauthorized",
    "500", "internal server error", "error occurred",
    "no encontrada", "error del servidor",
    "problem providing the content", "content you requested",
    "content not available", "page unavailable",
    "support team", "contact support",
]

CGSPACE_API = "https://cgspace.cgiar.org/server/api"
CROSSREF_API = "https://api.crossref.org/works"
LOGIN_HOSTS = ("login.microsoftonline.com", "login.live.com", "accounts.google.com")


@dataclass
class ScrapeResult:
    url: str
    type: str
    title: str
    content: str
    is_valid: bool
    validation_reason: str
    validation_message: str = ""
    pdf_bytes: bytes | None = None
    """Set for a scanned PDF (no text layer): input for the OCR fallback."""


def validate_content(content: str, title: str) -> tuple[bool, str, str]:
    """qa-service ``_validate_content``; warnings are dropped (they were only logged)."""
    if not content or not content.strip():
        return False, "empty_content", "No content extracted from the page"
    if len(content.strip()) < MIN_CONTENT_LENGTH:
        return False, "insufficient_content", f"Content too short ({len(content.strip())} chars)"
    content_lower, title_lower = content.lower(), title.lower()
    warnings = 0
    for indicator in AUTH_INDICATORS:
        if indicator in title_lower:
            return False, "authentication_required", f'Title contains "{indicator}"'
        if indicator in content_lower:
            warnings += 1
    for indicator in ERROR_INDICATORS:
        if indicator in title_lower:
            return False, "error_page", f'Title contains "{indicator}"'
        if indicator in content_lower:
            if len(content.strip()) < 500:
                return False, "error_page", f'Short content contains "{indicator}"'
            warnings += 1
    if warnings >= 3:
        return False, "likely_auth_page", "Multiple authentication indicators found in content"
    return True, "valid", "Content appears valid"


def remove_references_section(content: str) -> str:
    """qa-service ``EvidenceEnhancer._remove_references_section``."""
    headers = [
        r"\n\s*references?\s*\n", r"\n\s*bibliography\s*\n", r"\n\s*works?\s+cited\s*\n",
        r"\n\s*literatura?\s+citada\s*\n", r"\n\s*bibliograf[ií]a\s*\n",
        r"\n\s*referencias?\s+bibliogr[áa]ficas?\s*\n",
    ]
    cutoff = int(len(content) * 0.6)
    area = content[cutoff:]
    for pattern in headers:
        match = re.search(pattern, area, re.IGNORECASE)
        if not match:
            continue
        pos = cutoff + match.start()
        after = content[pos : pos + 1000]
        score = (
            len(re.findall(r"\b\d{4}\b", after))
            + 2 * len(re.findall(r"doi:", after, re.IGNORECASE))
            + len(re.findall(r"https?://", after))
            + 2 * len(re.findall(r"\bet al\.", after, re.IGNORECASE))
            + 2 * len(re.findall(r"[A-Z][a-z]+\s+[A-Z]{1,3}[,\.].*?\d{4}", after))
            + 2 * len(re.findall(r"\.\s+[A-Z][a-zA-Z\s]+\.\s+\d{4}", after))
            + 3 * sum(1 for line in after.split("\n")[:10] if line.strip() and re.search(r"^[A-Z].*\d{4}", line.strip()))
        )
        if score >= 5:
            return content[:pos].strip()
    return content


class EvidenceScraper:
    def __init__(self, http: HttpClient):
        self.http = http

    # ---- routing (same order as qa-service scrape_url) ----
    def scrape_url(self, url: str) -> ScrapeResult:
        low = url.lower()
        if any(s in low for s in ("youtube.com", "youtu.be")):
            return ScrapeResult(url, "unsupported_content", "YouTube Video", "", False, "unsupported_content_type")
        if "doi.org/" in low:
            return self._scrape_doi(url)
        if "hdl.handle.net" in low or "cgspace.cgiar.org/handle" in low or "cgspace.cgiar.org/items" in low:
            return self._scrape_cgspace(url)
        if any(s in low for s in ("sharepoint.com", "onedrive.live.com", "1drv.ms", "drive.google.com", "docs.google.com")):
            return self._scrape_shared_file(url)
        return self._scrape_web_page(url)

    # ---- CGSpace (API only) ----
    def _scrape_cgspace(self, url: str) -> ScrapeResult:
        handle = re.search(r"(?:hdl\.handle\.net|cgspace\.cgiar\.org/handle)/(\d+/\d+)", url)
        uuid = re.search(r"cgspace\.cgiar\.org/items/([0-9a-f-]{36})", url, re.IGNORECASE)
        if handle:
            r = self.http.get(f"{CGSPACE_API}/pid/find", accept="application/json", params={"id": f"hdl:{handle.group(1)}"})
        elif uuid:
            r = self.http.get(f"{CGSPACE_API}/core/items/{uuid.group(1)}", accept="application/json")
        else:
            return self._scrape_web_page(url)
        if r.status != 200 or "json" not in r.content_type:
            # Handles from other repositories resolve to their own pages.
            return self._scrape_web_page(url) if handle and not handle.group(1).startswith("10568/") else ScrapeResult(
                url, "cgspace_error", "CGSpace item", "", False, "download_failed", f"HTTP {r.status}"
            )
        item = _json(r)
        md = item.get("metadata", {})

        def first(*keys: str) -> str:
            for k in keys:
                if md.get(k):
                    return md[k][0].get("value", "")
            return ""

        title = first("dc.title") or "CGSpace item"
        pdf_url = self._cgspace_pdf(item.get("uuid", ""))
        if pdf_url:
            f = self.http.get(pdf_url, accept="application/pdf")
            if f.status == 200 and f.body:
                return self._from_document(url, "cgspace_pdf", title, f)

        parts = [f"Title: {title}", "=" * 60]
        abstract = first("dcterms.abstract", "dc.description.abstract", "dc.description")
        if abstract:
            parts += ["Abstract:", abstract]
        for label, keys in (
            ("Authors", ("dc.contributor.author", "dcterms.creator")),
            ("Published", ("dcterms.issued", "dc.date.issued")),
            ("Type", ("dcterms.type", "dc.type")),
            ("Publisher", ("dcterms.publisher", "dc.publisher")),
            ("Subjects", ("dcterms.subject", "dc.subject")),
            ("Countries", ("cg.coverage.country",)),
        ):
            for k in keys:
                if md.get(k):
                    parts.append(f"{label}: " + "; ".join(v.get("value", "") for v in md[k]))
                    break
        content = "\n\n".join(parts)
        ok, reason, msg = validate_content(content, title)
        return ScrapeResult(url, "cgspace_metadata", title, content, ok, reason, msg)

    def _cgspace_pdf(self, item_uuid: str) -> str | None:
        if not re.fullmatch(r"[0-9a-f-]{36}", item_uuid or "", re.IGNORECASE):
            return None
        bundles = self.http.get(f"{CGSPACE_API}/core/items/{item_uuid}/bundles", accept="application/json")
        if bundles.status != 200:
            return None
        for bundle in _json(bundles).get("_embedded", {}).get("bundles", []):
            if bundle.get("name") != "ORIGINAL":
                continue
            href = bundle.get("_links", {}).get("bitstreams", {}).get("href", "")
            if not href.startswith(CGSPACE_API + "/"):
                continue
            listing = self.http.get(href, accept="application/json")
            if listing.status != 200:
                continue
            for bs in _json(listing).get("_embedded", {}).get("bitstreams", []):
                content = bs.get("_links", {}).get("content", {}).get("href", "")
                if bs.get("name", "").lower().endswith(".pdf") and content.startswith(CGSPACE_API + "/"):
                    return content
        return None

    # ---- DOI: Crossref, then the landing page over plain HTTP ----
    def _scrape_doi(self, url: str) -> ScrapeResult:
        m = re.search(r"doi\.org/(10\.\S+)", url)
        crossref: ScrapeResult | None = None
        has_abstract = False
        if m:
            try:
                crossref, has_abstract = self._crossref(url, m.group(1).rstrip("/"))
            except Exception:  # noqa: BLE001 - Crossref is best effort, as in qa-service
                crossref = None
        if crossref and has_abstract:
            return crossref
        try:
            page = self._scrape_web_page(url)
            if page.is_valid and (page.pdf_bytes or len(page.content) > len(crossref.content if crossref else "")):
                return page
            if crossref is None:
                return page
        except Exception:  # noqa: BLE001
            if crossref is None:
                raise
        return crossref

    def _crossref(self, url: str, doi: str) -> tuple[ScrapeResult | None, bool]:
        r = self.http.get(f"{CROSSREF_API}/{doi}", accept="application/json")
        if r.status != 200:
            return None, False
        m = _json(r).get("message", {})
        title = (m.get("title") or ["Untitled"])[0]
        abstract = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.get("abstract", "") or "")).strip()
        has_abstract = len(abstract) >= 200
        parts = [f"Title: {title}", "=" * 60]
        if has_abstract:
            parts += ["Abstract:", abstract]
        for label, value in (
            ("Journal", (m.get("container-title") or [""])[0]),
            ("Published", str((m.get("published", {}).get("date-parts") or [["?"]])[0][0])),
            ("Type", m.get("type", "")),
            ("Publisher", m.get("publisher", "")),
        ):
            if value:
                parts.append(f"{label}: {value}")
        authors = m.get("author", [])
        if authors:
            parts.append("Authors: " + "; ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors[:20]))
        _, reason, msg = validate_content("\n\n".join(parts), title)
        return ScrapeResult(url, "doi_article", title, "\n\n".join(parts), True, reason, msg), has_abstract

    # ---- SharePoint / OneDrive / Google Drive ----
    def _scrape_shared_file(self, url: str) -> ScrapeResult:
        f = self.http.get(shared_download_url(url))
        if f.status in (401, 403) or _is_login(f):
            return ScrapeResult(url, "sharepoint_error", "Download Failed", "", False, "authentication_required", f"HTTP {f.status}")
        if f.status != 200:
            return ScrapeResult(url, "sharepoint_error", "Download Failed", "", False, "download_failed", f"HTTP {f.status}")
        if len(f.body) < 100:
            return ScrapeResult(url, "sharepoint_error", "Download Failed", "", False, "authentication_required", "File too small or empty (likely auth required)")
        return self._from_document(url, "shared_file", _filename(f) or "Shared file", f)

    # ---- generic page (plain HTTP instead of Playwright) ----
    def _scrape_web_page(self, url: str) -> ScrapeResult:
        f = self.http.get(url, accept="text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8")
        if f.status in (401, 403) or _is_login(f):
            return ScrapeResult(url, "web_page", "", "", False, "authentication_required", f"HTTP {f.status}")
        if f.status >= 400:
            return ScrapeResult(url, "web_page", "", "", False, "error_page", f"HTTP {f.status}")
        if not _is_html(f):
            return self._from_document(url, "web_document", _filename(f) or url, f)
        soup = BeautifulSoup(f.body, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        for el in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
            el.decompose()
        main = None
        for selector in ["main", "article", '[role="main"]', ".main-content", "#main-content", ".content", "#content"]:
            main = soup.select_one(selector)
            if main:
                break
        main = main or soup.body
        if main:
            texts = [t for el in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"]) if (t := el.get_text(strip=True))]
            content = "\n\n".join(texts)
        else:
            content = soup.get_text(separator="\n\n", strip=True)
        content = re.sub(r"\n{3,}", "\n\n", content)
        ok, reason, msg = validate_content(content, title)
        return ScrapeResult(url, "web_page", title, content, ok, reason, msg)

    # ---- downloaded files ----
    def _from_document(self, url: str, kind: str, title: str, f: Fetched) -> ScrapeResult:
        body = f.body
        if is_pdf(body):
            pdf = pdf_text(body)
            if pdf.scanned:
                return ScrapeResult(url, f"{kind}_scanned_pdf", title, "", True, "scanned_pdf", pdf_bytes=body)
            ok, reason, msg = validate_content(pdf.text, title)
            return ScrapeResult(url, f"{kind}_pdf", title, pdf.text, ok, reason, msg)
        office = office_kind(body)
        if office:
            text = office_text(body, office)
            ok, reason, msg = validate_content(text, title)
            return ScrapeResult(url, f"{kind}_{office}", title, text, ok, reason, msg)
        if f.content_type.startswith("text/plain") or "csv" in f.content_type:
            text = body.decode("utf-8", errors="replace")
            ok, reason, msg = validate_content(text, title)
            return ScrapeResult(url, f"{kind}_text", title, text, ok, reason, msg)
        if _is_html(f):
            return ScrapeResult(url, kind, title, "", False, "authentication_required" if _is_login(f) else "unsupported_format")
        return ScrapeResult(url, "unsupported_format", title, "", False, "unsupported_format", f.content_type or "unknown type")


def shared_download_url(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host in ("drive.google.com", "docs.google.com"):
        file_id = (re.search(r"/d/([A-Za-z0-9_-]{10,})", parts.path) or [None, None])[1] or (parse_qs(parts.query).get("id") or [None])[0]
        if file_id:
            if host == "drive.google.com":
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            if parts.path.startswith("/document/"):
                return f"https://docs.google.com/document/d/{file_id}/export?format=txt"
            if parts.path.startswith("/presentation/"):
                return f"https://docs.google.com/presentation/d/{file_id}/export/pdf"
            if parts.path.startswith("/spreadsheets/"):
                return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        return url
    if "download=" in url:
        return url
    return f"{url}{'&' if '?' in url else '?'}download=1"


def _is_html(f: Fetched) -> bool:
    head = f.body[:512].lstrip().lower()
    return "html" in f.content_type or head.startswith((b"<!doctype html", b"<html"))


def _is_login(f: Fetched) -> bool:
    host = (urlsplit(f.url).hostname or "").lower()
    if host in LOGIN_HOSTS:
        return True
    if not _is_html(f):
        return False
    head = f.body[:200_000].lower()
    return b'name="loginfmt"' in head or b"login.microsoftonline.com/common/oauth2" in head


def _filename(f: Fetched) -> str | None:
    cd = f.headers.get("content-disposition", "")
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd, re.IGNORECASE)
    return m.group(1) if m else None


def _json(f: Fetched) -> dict:
    import json

    data = json.loads(f.body.decode("utf-8", errors="replace"))
    return data if isinstance(data, dict) else {}
