from app.utils.prompt.prompt_prms import (
    DEFAULT_PROMPT_PRMS,
    compose_extraction_prompt_body,
)


def test_prompt_includes_six_supported_types():
    body = compose_extraction_prompt_body()
    assert "Capacity Sharing for Development" in body
    assert "Policy Change" in body
    assert "Innovation Development" in body
    assert "Innovation Use" in body
    assert "Other Output" in body
    assert "Other Outcome" in body


def test_prompt_includes_mds_common_and_capacity_sharing():
    body = compose_extraction_prompt_body()
    assert "geo_focus" in body
    assert "lead_center" in body
    assert "contributing_center" in body
    assert "contributing_partners" in body
    assert "capacity_sharing" in body
    assert "number_people_trained" in body
    assert "policy_change" in body
    assert "policy_type" in body
    assert "implementing_organization" in body


def test_prompt_distinguishes_other_output_and_other_outcome():
    body = compose_extraction_prompt_body()
    assert '"Other Output"' in body
    assert '"Other Outcome"' in body
    assert "Other Output / Other Outcome" not in body
    assert body.count("How to distinguish Output vs Outcome") == 1


def test_prompt_output_schema_maps_type_specific_blocks():
    body = compose_extraction_prompt_body()
    assert "Type-specific block (at most one per result" in body
    assert '"Capacity Sharing for Development" → capacity_sharing' in body
    assert '"Other Output" → none' in body
    assert "worked example for its type-specific block" in body


def test_prompt_excludes_knowledge_product_and_toc():
    body = DEFAULT_PROMPT_PRMS
    assert "Do NOT identify or return Knowledge Product" in body
    assert "Do NOT extract Theory of Change" in body
    assert '• "Knowledge Product"' not in body
