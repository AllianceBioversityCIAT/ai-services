from app.llm.prms_mining.mining import format_mining_response
from app.schemas.prms_mining_schemas import (
    InnovationUseResult,
    MiningResponse,
    OtherOutputOutcomeResult,
)


def test_innovation_use_schema():
    result = InnovationUseResult(
        indicator="Innovation Use",
        title="Adoption of drought-tolerant maize",
        description="Farmers adopted the variety in two districts.",
        keywords=["adoption", "maize"],
        geoscope_level="National",
        innovation_use_type="Variety adoption",
        adoption_stage="Scaling",
        adoption_scale="District",
        beneficiary_count=1200,
    )
    assert result.indicator == "Innovation Use"
    assert result.beneficiary_count == 1200


def test_other_output_schema():
    result = OtherOutputOutcomeResult(
        indicator="Other Output / Other Outcome",
        title="Network synthesis report",
        description="Cross-center synthesis of learning outcomes.",
        keywords=["synthesis"],
        geoscope_level="Global",
        output_type="Synthesis",
        outcome_description="Shared learning outcome",
        contribution_evidence="Cited in workshop report",
    )
    assert result.output_type == "Synthesis"


def test_mining_response_discriminated_union():
    payload = {
        "results": [
            {
                "indicator": "Innovation Use",
                "title": "Use case",
                "description": "desc",
                "keywords": ["use"],
                "geoscope_level": "Global",
            },
            {
                "indicator": "Other Output / Other Outcome",
                "title": "Other",
                "description": "desc",
                "keywords": ["other"],
                "geoscope_level": "Global",
            },
        ]
    }
    response = MiningResponse.model_validate(payload)
    assert len(response.results) == 2
    assert response.results[0].indicator == "Innovation Use"
    assert response.results[1].indicator == "Other Output / Other Outcome"


def test_format_mining_response_drops_knowledge_product():
    formatted = format_mining_response(
        {
            "results": [
                {
                    "indicator": "Knowledge Product",
                    "title": "KP",
                    "description": "d",
                    "keywords": ["kp"],
                    "geoscope_level": "Global",
                }
            ]
        }
    )
    assert formatted["results"] == []


def test_format_mining_response_empty():
    assert format_mining_response({"results": []})["results"] == []
