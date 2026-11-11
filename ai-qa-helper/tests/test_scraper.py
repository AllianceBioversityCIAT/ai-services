from app.evidence.scraper import CGSPACE_API, CROSSREF_API, EvidenceScraper, shared_download_url
from tests.evidence_fixtures import LONG_TEXT, FakeHttp, as_json, html, make_pdf, resp

UUID = "508ee655-9907-4b4c-ab16-a65ac5459d2c"
BUNDLES = f"{CGSPACE_API}/core/items/{UUID}/bundles"
BITSTREAMS = f"{CGSPACE_API}/core/bundles/b1/bitstreams"
CONTENT = f"{CGSPACE_API}/core/bitstreams/f1/content"
ITEM = {"uuid": UUID, "metadata": {"dc.title": [{"value": "Rice package"}], "dcterms.abstract": [{"value": LONG_TEXT}]}}


def cgspace_routes(with_pdf: bool):
    routes = {
        f"{CGSPACE_API}/pid/find?id=hdl%3A10568%2F132132": as_json(ITEM),
        BUNDLES: as_json({"_embedded": {"bundles": [{"name": "ORIGINAL", "_links": {"bitstreams": {"href": BITSTREAMS}}}]}}),
        BITSTREAMS: as_json({"_embedded": {"bitstreams": [{"name": "report.pdf", "_links": {"content": {"href": CONTENT}}}]}}),
    }
    if with_pdf:
        routes[CONTENT] = resp(make_pdf(LONG_TEXT), content_type="application/pdf")
    return routes


def test_cgspace_handle_reads_the_pdf_through_the_api():
    r = EvidenceScraper(FakeHttp(cgspace_routes(True))).scrape_url("https://hdl.handle.net/10568/132132")
    assert r.is_valid and r.type == "cgspace_pdf_pdf" and "women farmers" in r.content


def test_cgspace_without_pdf_falls_back_to_metadata_record():
    routes = cgspace_routes(False)
    routes[BITSTREAMS] = as_json({"_embedded": {"bitstreams": []}})
    r = EvidenceScraper(FakeHttp(routes)).scrape_url("https://hdl.handle.net/10568/132132")
    assert r.is_valid and r.type == "cgspace_metadata" and "Abstract:" in r.content


def test_scanned_cgspace_pdf_is_kept_for_ocr():
    routes = cgspace_routes(False)
    routes[CONTENT] = resp(make_pdf(None), content_type="application/pdf")
    r = EvidenceScraper(FakeHttp(routes)).scrape_url("https://hdl.handle.net/10568/132132")
    assert r.pdf_bytes and r.validation_reason == "scanned_pdf"


def test_sharepoint_private_link():
    url = "https://cgiar.sharepoint.com/:b:/s/site/abc?e=x1"
    login = html("<html><input name=\"loginfmt\"></html>", url="https://login.microsoftonline.com/common/oauth2")
    r = EvidenceScraper(FakeHttp({shared_download_url(url): login})).scrape_url(url)
    assert not r.is_valid and r.validation_reason == "authentication_required"
    r403 = EvidenceScraper(FakeHttp({shared_download_url(url): resp(status=403)})).scrape_url(url)
    assert r403.validation_reason == "authentication_required"


def test_sharepoint_file_detected_by_content_not_name():
    url = "https://cgiar.sharepoint.com/:b:/s/site/abc"
    r = EvidenceScraper(FakeHttp({shared_download_url(url): resp(make_pdf(LONG_TEXT), content_type="application/octet-stream")})).scrape_url(url)
    assert r.is_valid and "women farmers" in r.content


def test_shared_link_rewrites():
    assert shared_download_url("https://cgiar.sharepoint.com/:b:/s/x/abc?e=1") == "https://cgiar.sharepoint.com/:b:/s/x/abc?e=1&download=1"
    assert shared_download_url("https://drive.google.com/file/d/1AbCdEfGhIjK/view?usp=sharing") == "https://drive.google.com/uc?export=download&id=1AbCdEfGhIjK"
    assert shared_download_url("https://docs.google.com/document/d/1AbCdEfGhIjK/edit") == "https://docs.google.com/document/d/1AbCdEfGhIjK/export?format=txt"


def test_web_page_main_content_and_short_page():
    page = f"<html><head><title>Project</title></head><body><nav>menu</nav><main><h1>Results</h1><p>{LONG_TEXT}</p></main></body></html>"
    r = EvidenceScraper(FakeHttp({"https://example.org/p": html(page)})).scrape_url("https://example.org/p")
    assert r.is_valid and r.content.startswith("Results") and "menu" not in r.content
    short = EvidenceScraper(FakeHttp({"https://example.org/s": html("<html><body><div id=app></div></body></html>")})).scrape_url("https://example.org/s")
    assert not short.is_valid and short.validation_reason in ("empty_content", "insufficient_content")


def test_direct_pdf_link_is_read_as_document():
    r = EvidenceScraper(FakeHttp({"https://example.org/r.pdf": resp(make_pdf(LONG_TEXT), content_type="application/pdf")})).scrape_url("https://example.org/r.pdf")
    assert r.is_valid and "women farmers" in r.content


def test_youtube_unsupported():
    assert EvidenceScraper(FakeHttp({})).scrape_url("https://www.youtube.com/watch?v=x").validation_reason == "unsupported_content_type"


def test_doi_uses_crossref_abstract():
    http = FakeHttp({f"{CROSSREF_API}/10.1000/xyz": as_json({"message": {"title": ["Paper"], "abstract": f"<jats:p>{LONG_TEXT}</jats:p>"}})})
    r = EvidenceScraper(http).scrape_url("https://doi.org/10.1000/xyz")
    assert r.type == "doi_article" and "Abstract:" in r.content
    assert http.requested == [f"{CROSSREF_API}/10.1000/xyz"]


def test_doi_without_abstract_tries_the_landing_page():
    page = f"<html><head><title>Paper</title></head><body><article><p>{LONG_TEXT} {LONG_TEXT}</p></article></body></html>"
    http = FakeHttp({
        f"{CROSSREF_API}/10.1000/xyz": as_json({"message": {"title": ["Paper"]}}),
        "https://doi.org/10.1000/xyz": html(page),
    })
    r = EvidenceScraper(http).scrape_url("https://doi.org/10.1000/xyz")
    assert r.type == "web_page" and r.is_valid
