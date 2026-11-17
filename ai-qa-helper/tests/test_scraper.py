from app.evidence.scraper import (
    CGSPACE_API,
    CROSSREF_API,
    SHORT_HTML_MAX_CHARS,
    EvidenceScraper,
    shared_download_url,
    validate_content,
)
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
    # The DOI is resolved first (here it does not land on CGSpace), then Crossref.
    assert http.requested == ["https://doi.org/10.1000/xyz", f"{CROSSREF_API}/10.1000/xyz"]


def test_doi_without_abstract_tries_the_landing_page():
    page = f"<html><head><title>Paper</title></head><body><article><p>{LONG_TEXT} {LONG_TEXT}</p></article></body></html>"
    http = FakeHttp({
        f"{CROSSREF_API}/10.1000/xyz": as_json({"message": {"title": ["Paper"]}}),
        "https://doi.org/10.1000/xyz": html(page),
    })
    r = EvidenceScraper(http).scrape_url("https://doi.org/10.1000/xyz")
    assert r.type == "web_page" and r.is_valid


# ---- DOI resolving to CGSpace (shape of result 10105: an IWMI DOI landing on a CGSpace item) ----

DOI_10105 = "https://doi.org/10.5337/2024.201"
ITEM_URL = f"https://cgspace.cgiar.org/items/{UUID}"
SPA_SHELL = "<html><head><title>CGSpace</title></head><body><main><p>Loading...</p></main></body></html>"


def doi_to_cgspace_routes(final_url: str, with_pdf: bool = True):
    routes = cgspace_routes(with_pdf)
    routes[DOI_10105] = html(SPA_SHELL, url=final_url)  # what plain HTTP gets after the redirects
    routes[f"{CGSPACE_API}/core/items/{UUID}"] = as_json(ITEM)
    return routes


def test_doi_landing_on_a_cgspace_item_reads_its_public_pdf_through_the_api():
    http = FakeHttp(doi_to_cgspace_routes(ITEM_URL))
    r = EvidenceScraper(http).scrape_url(DOI_10105)
    assert r.is_valid and r.type == "cgspace_pdf_pdf" and "women farmers" in r.content
    assert not any(u.startswith(CROSSREF_API) for u in http.requested)


def test_doi_landing_on_a_cgspace_handle_uses_the_same_path():
    http = FakeHttp(doi_to_cgspace_routes("https://cgspace.cgiar.org/handle/10568/132132"))
    r = EvidenceScraper(http).scrape_url(DOI_10105)
    assert r.type == "cgspace_pdf_pdf" and r.is_valid


def test_doi_landing_on_a_cgspace_item_without_public_pdf_gives_the_metadata_record():
    routes = doi_to_cgspace_routes(ITEM_URL, with_pdf=False)
    routes[f"{CGSPACE_API}/core/bitstreams/f1/content"] = resp(status=401, content_type="text/html")
    r = EvidenceScraper(FakeHttp(routes)).scrape_url(DOI_10105)
    assert r.type == "cgspace_metadata" and r.is_valid and "Abstract:" in r.content


def test_doi_on_another_site_keeps_crossref_then_landing():
    page = f"<html><head><title>Paper</title></head><body><article><p>{LONG_TEXT} {LONG_TEXT}</p></article></body></html>"
    http = FakeHttp({
        DOI_10105: html(page, url="https://publisher.example.org/paper"),
        f"{CROSSREF_API}/10.5337/2024.201": as_json({"message": {"title": ["Paper"]}}),
    })
    r = EvidenceScraper(http).scrape_url(DOI_10105)
    assert r.type == "web_page" and r.is_valid
    assert http.requested.count(DOI_10105) == 1  # the landing page is fetched once


# ---- likely_auth_page only on short HTML ----

MANY_INDICATORS = "Please log in to the portal. Sign in required. Unauthorized access is logged."


def test_short_html_login_page_is_still_rejected():
    page = f"{MANY_INDICATORS} {LONG_TEXT} {LONG_TEXT} {LONG_TEXT}"  # 500-5000 chars
    assert 500 <= len(page) < SHORT_HTML_MAX_CHARS
    assert validate_content(page, "Portal")[:2] == (False, "likely_auth_page")


def test_long_html_or_documents_with_login_words_are_content():
    long_page = (LONG_TEXT + " ") * (SHORT_HTML_MAX_CHARS // len(LONG_TEXT) + 1) + MANY_INDICATORS
    assert len(long_page) >= SHORT_HTML_MAX_CHARS
    assert validate_content(long_page, "Report")[0] is True
    short_doc = f"{MANY_INDICATORS} {LONG_TEXT}"
    assert validate_content(short_doc, "report.pdf", "document")[0] is True
    assert validate_content(short_doc, "Item", "record")[0] is True


def test_pdf_mentioning_login_several_times_is_read():
    text = f"{LONG_TEXT} Users log in to the app. Farmers sign in weekly. Unauthorized use is tracked."
    routes = cgspace_routes(False)
    routes[CONTENT] = resp(make_pdf(text), content_type="application/pdf")
    r = EvidenceScraper(FakeHttp(routes)).scrape_url("https://hdl.handle.net/10568/132132")
    assert r.is_valid and r.type == "cgspace_pdf_pdf"


def test_title_checks_still_apply_to_documents():
    assert validate_content(LONG_TEXT, "Access denied", "document")[:2] == (False, "authentication_required")
