from app.schemas.prms_innovation_reference import (
    normalize_innovation_typology_ref,
    resolve_innovation_readiness_level,
    resolve_innovation_typology,
)
from app.schemas.prms_mining_schemas import InnovationDevelopmentResult
from app.utils.prompt.prompt_prms import compose_extraction_prompt_body


def test_resolve_innovation_typology_technological():
    resolved = resolve_innovation_typology(name="Technological innovation")
    assert resolved == {"code": 12, "name": "Technological innovation"}


def test_resolve_innovation_typology_by_code():
    resolved = resolve_innovation_typology(code=15)
    assert resolved == {
        "code": 15,
        "name": "Other/I’m not sure/This typology does not work for my innovation",
    }


def test_normalize_innovation_typology_ref():
    normalized = normalize_innovation_typology_ref({"name": "Capacity development innovation"})
    assert normalized == {"code": 13, "name": "Capacity development innovation"}


def test_resolve_innovation_readiness_level_proof_of_concept():
    resolved = resolve_innovation_readiness_level(name="Proof of Concept")
    assert resolved == {"id": 14, "name": "Proof of Concept"}


def test_resolve_innovation_readiness_level_by_id():
    resolved = resolve_innovation_readiness_level(item_id=20)
    assert resolved == {"id": 20, "name": "Proven Innovation"}


def test_innovation_development_mds_schema():
    result = InnovationDevelopmentResult(
        indicator="Innovation Development",
        title="Drought-tolerant wheat variety",
        description="New variety validated under semi-controlled conditions.",
        geo_focus={"scope_code": 4, "scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
        innovation_development={
            "innovation_typology": {"code": 12, "name": "Technological innovation"},
            "innovation_developers": "John Doe, john.doe@icarda.org, International Center for Agricultural Research in the Dry Areas",
            "innovation_readiness_level": {"id": 14, "name": "Proof of Concept"},
        },
    )
    assert result.innovation_development.innovation_typology.code == 12
    assert result.innovation_development.innovation_readiness_level.id == 14
    assert result.innovation_development.innovation_developers.startswith("John Doe,")


def test_innovation_development_prompt_lists_catalogs():
    body = compose_extraction_prompt_body()
    assert 'code 12, name "Technological innovation"' in body
    assert 'code 15, name "Other/I’m not sure/This typology does not work for my innovation"' in body
    assert 'id 14, name "Proof of Concept"' in body
    assert 'id 20, name "Proven Innovation"' in body
    assert "innovation_development" in body
