import requests

from app.evidence.extractor import EvidenceExtractor, MemoryEvidenceCache
from app.evidence.scraper import EvidenceScraper, shared_download_url
from app.evidence.url_guard import BlockedUrlError
from tests.evidence_fixtures import LONG_TEXT, FakeHttp, html, make_pdf, resp

PAGE = f"<html><head><title>Project</title></head><body><main><p>{LONG_TEXT}</p></main></body></html>"
SP = "https://cgiar.sharepoint.com/:b:/s/site/private"


def extractor(routes, cache=None):
    http = FakeHttp(routes)
    return EvidenceExtractor(EvidenceScraper(http), cache), http


def test_no_links_means_no_readable_evidence():
    out = extractor({})[0].extract([])
    assert not out.readable and out.unavailable_reason == "no_readable_evidence"


def test_only_private_links_means_private_link():
    out = extractor({shared_download_url(SP): resp(status=403)})[0].extract([SP])
    assert not out.readable and out.unavailable_reason == "private_link"
    assert out.sources[0].status == "private"


def test_mixed_sources_are_partial_and_hashed():
    ex, _ = extractor({"https://example.org/p": html(PAGE), shared_download_url(SP): resp(status=403)})
    out = ex.extract(["https://example.org/p", SP])
    assert out.readable and out.partial and out.evidence_hash
    assert [s.index for s in out.sources] == [0, 1]
    assert out.counts == {"text": 1, "private": 1}


def test_evidence_hash_is_stable_and_content_sensitive():
    a = extractor({"https://example.org/p": html(PAGE)})[0].extract(["https://example.org/p"]).evidence_hash
    b = extractor({"https://example.org/p": html(PAGE)})[0].extract(["https://example.org/p"]).evidence_hash
    c = extractor({"https://example.org/p": html(PAGE.replace("1,200", "1,300"))})[0].extract(["https://example.org/p"]).evidence_hash
    assert a == b != c


def test_scanned_pdf_goes_to_ocr_fallback():
    out = extractor({"https://example.org/scan.pdf": resp(make_pdf(None), content_type="application/pdf")})[0].extract(["https://example.org/scan.pdf"])
    assert out.readable and out.sources[0].status == "pdf_ocr" and out.sources[0].pdf_base64


def test_failures_never_raise_and_transient_ones_are_not_cached():
    cache = MemoryEvidenceCache()
    ex, http = extractor({
        "https://example.org/slow": requests.Timeout(),
        "https://example.org/blocked": BlockedUrlError("private_address"),
        "https://example.org/p": html(PAGE),
    }, cache)
    urls = ["https://example.org/slow", "https://example.org/blocked", "https://example.org/p"]
    out = ex.extract(urls)
    assert [s.status for s in out.sources] == ["error", "unreadable", "text"]
    assert out.sources[1].reason == "blocked_private_address"
    ex.extract(urls)
    assert http.requested.count("https://example.org/slow") == 2
    assert http.requested.count("https://example.org/p") == 1
