from app.utils.prompt.prompt_prms import (
    DEFAULT_PROMPT_PRMS,
    EXTRACTION_PROMPT_VERSION,
    compose_extraction_prompt_body,
)


def test_prompt_includes_five_supported_types():
    body = compose_extraction_prompt_body()
    assert "Capacity Sharing for Development" in body
    assert "Policy Change" in body
    assert "Innovation Development" in body
    assert "Innovation Use" in body
    assert "Other Output / Other Outcome" in body


def test_prompt_excludes_knowledge_product_and_toc():
    body = DEFAULT_PROMPT_PRMS
    assert "Do NOT identify or return Knowledge Product" in body
    assert "Do NOT extract Theory of Change" in body
    # Knowledge Product must not appear as a supported indicator discriminator list item
    assert '• "Knowledge Product"' not in body


def test_extraction_prompt_version_constant():
    assert EXTRACTION_PROMPT_VERSION.startswith("prms-extraction-")
