from app.evidence.documents import office_kind, office_text, pdf_text
from tests.evidence_fixtures import LONG_TEXT, make_docx, make_pdf, make_pptx, make_xlsx


def test_pdf_with_text_layer():
    pdf = pdf_text(make_pdf(LONG_TEXT))
    assert not pdf.scanned and "1,200 women farmers" in pdf.text.replace("\n", " ")


def test_pdf_without_text_layer_is_scanned():
    assert pdf_text(make_pdf(None)).scanned


def test_office_formats():
    docx = make_docx(["First paragraph &amp; more", "Second"])
    assert office_kind(docx) == "docx" and office_text(docx, "docx") == "First paragraph & more\nSecond"
    pptx = make_pptx(["Slide one", "Slide two"])
    assert office_kind(pptx) == "pptx" and "Slide one" in office_text(pptx, "pptx")
    xlsx = make_xlsx(["Women trained", "1200"])
    assert office_kind(xlsx) == "xlsx" and "Women trained" in office_text(xlsx, "xlsx")


def test_not_office():
    assert office_kind(b"PK\x03\x04garbage") is None
    assert office_kind(b"%PDF-1.4") is None
