import json
import shutil

import pytest

from app.contract.fields import AI_FIELDS
from app.evidence.extractor import EvidenceSource
from app.llm.output_schema import SuggestionOutputV2, V1ImpactAreaOutput, V1ReadinessOutput, V1UseOutput
from app.llm.provider import PdfEvidence, TextPart
from app.prompts.builder import V1_CONTENT_CAP, V1_SYSTEM, ResultContext, build_request, v1_context
from app.prompts.loader import (
    PROMPTS_DIR,
    PromptIntegrityError,
    UnknownPromptVersion,
    _manifest,
    get_prompt,
    prompt_versions,
)
from scripts.prompt_manifest import main as check_manifest

RESULT = ResultContext(title="Rice varieties for women farmers", description="Released two varieties.")
QUOTE_TEXT = "Two drought-tolerant rice varieties were released with women farmer groups in 2025."


def sources():
    return [
        EvidenceSource(0, "https://example.org/a", "text", text=QUOTE_TEXT),
        EvidenceSource(1, "https://example.org/b", "private", reason="authentication_required"),
        EvidenceSource(2, "https://example.org/scan.pdf", "pdf_ocr", title="scan", pdf_base64="JVBERi0="),
    ]


def test_manifest_hashes_match_the_files():
    assert check_manifest([]) == 0


def test_both_versions_cover_every_ai_field():
    assert prompt_versions() == ["v1-1.0.0", "v2-1.0.0"]
    for version in prompt_versions():
        for field in AI_FIELDS:
            assert get_prompt(version, field) is not None, (version, field)


def test_v1_keeps_the_previous_helper_text_and_its_empty_placeholders():
    gender = get_prompt("v1-1.0.0", "impact_area_gender").text
    assert gender.startswith("You are an AI assistant tasked with evaluating research results from CGIAR")
    assert '"Component (if Score = 2)": "Gender Equality | Youth | Social Inclusion | N/A"}' in gender
    assert "{core_innovation}" in get_prompt("v1-1.0.0", "innovation_use_level").text
    # The climate prompt was stored with literal backslash-n sequences and escaped quotes.
    assert "\\n\\nYour role is advisory" in get_prompt("v1-1.0.0", "impact_area_climate").text


def test_v1_output_models_follow_the_prompt_keys():
    assert get_prompt("v1-1.0.0", "impact_area_poverty").output_model is V1ImpactAreaOutput
    assert get_prompt("v1-1.0.0", "innovation_readiness_level").output_model is V1ReadinessOutput
    assert get_prompt("v1-1.0.0", "innovation_use_level").output_model is V1UseOutput
    assert get_prompt("v2-1.0.0", "innovation_use_level").output_model is SuggestionOutputV2


def test_v1_request_reproduces_the_previous_input_layout():
    spec = get_prompt("v1-1.0.0", "impact_area_gender")
    built = build_request(spec, RESULT, sources(), "medium", 4000)
    req = built.request
    assert req.system == V1_SYSTEM and req.cache_system is False
    assert isinstance(req.content[0], PdfEvidence) and isinstance(req.content[-1], TextPart)
    user = req.content[-1].text
    context = json.dumps(
        [{"Content": QUOTE_TEXT}, {"Title": RESULT.title}, {"Result Description": RESULT.description}],
        indent=2,
        ensure_ascii=False,
    )
    assert user == f"Context: {context}\n\n{spec.text}"
    assert built.evidence_text == QUOTE_TEXT


def test_v1_context_matches_json_stringify_and_drops_empty_values():
    assert v1_context("Título", "", "x") == '[\n  {\n    "Content": "x"\n  },\n  {\n    "Title": "Título"\n  }\n]'
    assert v1_context("", "", "") == "[]"


def test_v1_content_is_capped_like_the_excel_cell():
    long = [EvidenceSource(0, "u", "text", text="a" * 40_000)]
    built = build_request(get_prompt("v1-1.0.0", "impact_area_gender"), RESULT, long, "low", 4000)
    assert len(built.evidence_text) == V1_CONTENT_CAP


def test_v2_request_has_cached_rubric_tagged_evidence_and_no_reported_value():
    spec = get_prompt("v2-1.0.0", "impact_area_gender")
    assert "{{" not in spec.text and "<criteria>" in spec.text and "Gender Equality; Youth" in spec.text
    built = build_request(spec, RESULT, sources(), "medium", 4000)
    req = built.request
    assert req.system == spec.text and req.cache_system is True
    first = req.content[0]
    assert isinstance(first, TextPart) and first.text.startswith('<evidence index="0" source="https://example.org/a">')
    assert isinstance(req.content[1], PdfEvidence) and req.content[1].source_index == 2
    task = req.content[-1].text
    assert "<title>Rice varieties for women farmers</title>" in task
    assert "reported" not in task.lower()
    assert built.evidence_text == QUOTE_TEXT


def test_v2_criteria_drop_the_previous_input_and_output_instructions():
    for field in AI_FIELDS:
        text = get_prompt("v2-1.0.0", field).text
        for stale in ("Output Format (Strict)", "{core_innovation}", "{context}", "explicity flagged", "\\n"):
            assert stale not in text, (field, stale)


def test_unknown_version_and_missing_field():
    with pytest.raises(UnknownPromptVersion):
        get_prompt("v9-0.0.0", "impact_area_gender")
    assert get_prompt("v1-1.0.0", "is_this_an_innovation") is None


def test_tampered_prompt_is_rejected(tmp_path):
    copy = tmp_path / "prompts"
    shutil.copytree(PROMPTS_DIR, copy)
    target = copy / "impact_area_gender" / "v1.txt"
    target.write_bytes(target.read_bytes() + b" ")
    _manifest.cache_clear()
    try:
        with pytest.raises(PromptIntegrityError):
            get_prompt("v1-1.0.0", "impact_area_gender", prompts_dir=copy)
    finally:
        _manifest.cache_clear()
