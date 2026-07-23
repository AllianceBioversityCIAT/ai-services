from app.llm.prms_mining.prompt_builder import build_extraction_prompt
from app.llm.shared.cgiar_centers import (
    format_cgiar_centers_for_prompt,
    normalize_cgiar_center_ref,
    resolve_cgiar_center,
)
from app.schemas.prms_mining_schemas import CgiarCenterRef


def test_resolve_cgiar_center_by_acronym():
    resolved = resolve_cgiar_center(acronym="ICARDA")
    assert resolved == {
        "institution_id": 1279,
        "acronym": "ICARDA",
        "name": "International Center for Agricultural Research in the Dry Areas",
    }


def test_resolve_cgiar_center_by_id():
    resolved = resolve_cgiar_center(institution_id=115)
    assert resolved["acronym"] == "CIFOR"


def test_normalize_unknown_center_returns_none():
    assert normalize_cgiar_center_ref({"acronym": "NOT-A-CENTER"}) is None


def test_cgiar_center_ref_requires_full_catalog_match():
    center = CgiarCenterRef.model_validate({"acronym": "IWMI"})
    assert center.institution_id == 172
    assert center.acronym == "IWMI"
    assert center.name == "International Water Management Institute"


def test_extraction_prompt_includes_cgiar_centers_catalog():
    prompt = build_extraction_prompt(
        excerpts="sample",
        reference_section=format_cgiar_centers_for_prompt(),
    )
    assert "CGIAR CENTERS REFERENCE DATA" in prompt
    assert "1279 | ICARDA" in prompt
    assert "institution_id, acronym, and name" in prompt


def test_prms_geo_reference_uses_geo_focus_not_geoscope():
    from app.llm.prms_mining.prompt_builder import format_prms_geo_reference_for_prompt

    section = format_prms_geo_reference_for_prompt(
        {"regions": ["UN49 Code: 2, Name: Africa"], "countries": ["ISO Alpha2: KE, Name: Kenya"]}
    )
    assert "geo_focus" in section
    assert "um49code" in section
    assert "geoscope" not in section
