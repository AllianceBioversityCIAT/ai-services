"""Reads every evidence link of a result and decides whether the model can be called.

No readable evidence -> ``EvidenceOutcome(readable=False, unavailable_reason=...)`` and the worker
stores ``unavailable`` without calling the model.
"""

import base64
import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol

import requests

from app.evidence.http import DeadlineExceeded, TooLargeError
from app.evidence.scraper import EvidenceScraper, ScrapeResult, remove_references_section
from app.evidence.url_guard import BlockedUrlError
from app.utils.logger.logger_util import get_logger

logger = get_logger()

SourceStatus = Literal["text", "pdf_ocr", "private", "unreadable", "error"]
"""text: readable text; pdf_ocr: scanned PDF sent as a document block; private: login/401/403;
unreadable: reached but nothing usable; error: transient failure (not cached, retried next run)."""

MAX_SOURCE_CHARS = 40_000
"""Per-source cap, the qa-service ``max_content_length`` default. The prompt builder applies the
final input budget (v1 reproduces the previous helper's ~32,767-character cap)."""
OCR_MAX_BYTES = 10 * 1024 * 1024

_PRIVATE_REASONS = {"authentication_required", "likely_auth_page"}


@dataclass(frozen=True)
class EvidenceSource:
    index: int
    url: str
    status: SourceStatus
    kind: str = ""
    title: str = ""
    text: str | None = None
    pdf_base64: str | None = None
    reason: str = ""
    """Machine-readable reason for non-text statuses. Never contains page content."""


@dataclass(frozen=True)
class EvidenceOutcome:
    sources: list[EvidenceSource]
    readable: bool
    partial: bool = False
    evidence_hash: str | None = None
    unavailable_reason: Literal["no_readable_evidence", "private_link"] | None = None
    counts: dict[str, int] = field(default_factory=dict)


class EvidenceCache(Protocol):
    def get(self, url: str) -> EvidenceSource | None: ...
    def put(self, url: str, source: EvidenceSource) -> None: ...


class NoopEvidenceCache:
    """Used until the S3 bucket exists (blocked on infra)."""

    def get(self, url: str) -> EvidenceSource | None:
        return None

    def put(self, url: str, source: EvidenceSource) -> None:
        return None


class MemoryEvidenceCache:
    """Per-invocation cache: links shared by the fields of one result are fetched once."""

    def __init__(self) -> None:
        self._items: dict[str, EvidenceSource] = {}

    def get(self, url: str) -> EvidenceSource | None:
        return self._items.get(cache_key(url))

    def put(self, url: str, source: EvidenceSource) -> None:
        self._items[cache_key(url)] = source


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class EvidenceExtractor:
    def __init__(self, scraper: EvidenceScraper, cache: EvidenceCache | None = None):
        self.scraper = scraper
        self.cache = cache or NoopEvidenceCache()

    def extract(self, urls: list[str]) -> EvidenceOutcome:
        sources = [replace(self._read_cached(url), index=i) for i, url in enumerate(urls)]
        outcome = summarize(sources)
        logger.info(
            "evidence: %d links, readable=%s, counts=%s, reason=%s",
            len(urls), outcome.readable, outcome.counts, outcome.unavailable_reason,
        )
        return outcome

    def _read_cached(self, url: str) -> EvidenceSource:
        hit = self.cache.get(url)
        if hit:
            return hit
        source = self._read(url)
        if source.status != "error":
            self.cache.put(url, source)
        return source

    def _read(self, url: str) -> EvidenceSource:
        try:
            return to_source(url, self.scraper.scrape_url(url.strip()))
        except BlockedUrlError as err:
            return EvidenceSource(0, url, "unreadable", reason=f"blocked_{err.reason}")
        except TooLargeError:
            return EvidenceSource(0, url, "unreadable", reason="too_large")
        except (DeadlineExceeded, requests.Timeout):
            return EvidenceSource(0, url, "error", reason="timeout")
        except requests.RequestException:
            return EvidenceSource(0, url, "error", reason="fetch_failed")
        except Exception as err:  # noqa: BLE001 - a bad link must never fail the job
            return EvidenceSource(0, url, "unreadable", reason=f"parse_failed_{type(err).__name__}")


def to_source(url: str, r: ScrapeResult) -> EvidenceSource:
    if r.pdf_bytes is not None:
        if len(r.pdf_bytes) > OCR_MAX_BYTES:
            return EvidenceSource(0, url, "unreadable", r.type, r.title, reason="scanned_pdf_too_large")
        return EvidenceSource(0, url, "pdf_ocr", r.type, r.title, pdf_base64=base64.b64encode(r.pdf_bytes).decode())
    if r.is_valid and r.content.strip():
        text = remove_references_section(r.content)[:MAX_SOURCE_CHARS]
        return EvidenceSource(0, url, "text", r.type, r.title, text=text)
    if r.validation_reason in _PRIVATE_REASONS:
        return EvidenceSource(0, url, "private", r.type, reason=r.validation_reason)
    if r.validation_reason == "download_failed" and r.validation_message.startswith("HTTP 5"):
        return EvidenceSource(0, url, "error", r.type, reason="http_5xx")
    return EvidenceSource(0, url, "unreadable", r.type, reason=r.validation_reason or "unknown")


def summarize(sources: list[EvidenceSource]) -> EvidenceOutcome:
    counts: dict[str, int] = {}
    for s in sources:
        counts[s.status] = counts.get(s.status, 0) + 1
    readable = [s for s in sources if s.status in ("text", "pdf_ocr")]
    if not readable:
        reason = "private_link" if any(s.status == "private" for s in sources) else "no_readable_evidence"
        return EvidenceOutcome(sources, readable=False, unavailable_reason=reason, counts=counts)
    digest = [
        [s.index, s.status, hashlib.sha256((s.text or s.pdf_base64 or "").encode()).hexdigest()] for s in readable
    ]
    return EvidenceOutcome(
        sources,
        readable=True,
        partial=len(readable) < len(sources),
        evidence_hash=hashlib.sha256(json.dumps(digest).encode()).hexdigest(),
        counts=counts,
    )
