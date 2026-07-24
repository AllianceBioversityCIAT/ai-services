from app.text_mining.prms_mining.mining import format_mining_response
from app.schemas.prms_mining_schemas import (
    CapacitySharingResult,
    InnovationUseResult,
    MiningResponse,
    OtherOutputResult,
    OtherOutcomeResult,
)


def test_geo_focus_accepts_prompt_subnational_areas_shape():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="Department-level training",
        description="Training in two Colombian departments.",
        geo_focus={
            "scope_code": 5,
            "scope_label": "Sub-national",
            "countries": [{"iso_alpha_2": "CO", "subnational_areas": ["CO-CUN", "CO-CAS"]}],
        },
        capacity_sharing={
            "number_people_trained": {"women": 10},
            "length_training": "Short-term",
        },
    )
    country = result.geo_focus.countries[0]
    assert country.iso_alpha_2 == "CO"
    assert country.subnational_areas == ["CO-CUN", "CO-CAS"]
    dumped = country.model_dump(exclude_none=True)
    assert "code" not in dumped
    assert "areas" not in dumped


def test_geo_focus_normalizes_legacy_code_and_areas_aliases():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="Department-level training",
        description="Training in two Colombian departments.",
        geo_focus={
            "scope_code": 5,
            "scope_label": "Sub-national",
            "countries": [{"code": "CO", "areas": ["CO-CUN", "CO-CAS"], "iso_alpha_2": "CO"}],
        },
        capacity_sharing={
            "number_people_trained": {"women": 10},
            "length_training": "Short-term",
        },
    )
    country = result.geo_focus.countries[0]
    assert country.iso_alpha_2 == "CO"
    assert country.subnational_areas == ["CO-CUN", "CO-CAS"]
    dumped = country.model_dump(exclude_none=True)
    assert dumped == {
        "iso_alpha_2": "CO",
        "subnational_areas": ["CO-CUN", "CO-CAS"],
    }


def test_geo_focus_national_strips_subnational_areas():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="National training",
        description="Training in Kenya.",
        geo_focus={
            "scope_label": "National",
            "countries": [{"iso_alpha_2": "KE", "subnational_areas": ["KE-30"]}],
        },
        capacity_sharing={
            "number_people_trained": {"women": 10},
            "length_training": "Short-term",
            "delivery_method": "In person",
        },
    )
    country = result.geo_focus.countries[0]
    assert country.iso_alpha_2 == "KE"
    assert country.subnational_areas is None


def test_geo_focus_global_strips_regions_and_countries():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="Global training",
        description="Global scope.",
        geo_focus={
            "scope_label": "Global",
            "regions": [{"um49code": 2}],
            "countries": [{"iso_alpha_2": "KE"}],
        },
        capacity_sharing={"number_people_trained": {"women": 1}, "length_training": "Short-term"},
    )
    assert result.geo_focus.regions is None
    assert result.geo_focus.countries is None


def test_capacity_sharing_length_training_rejects_legacy_values():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="PhD training",
        description="Degree program.",
        geo_focus={"scope_label": "Global"},
        capacity_sharing={
            "number_people_trained": {"unknown": 3},
            "length_training": "PhD",
        },
    )
    assert result.capacity_sharing.length_training is None


def test_capacity_sharing_subnational_geo_nested_areas():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="Department-level training",
        description="Training in two Colombian departments.",
        geo_focus={
            "scope_code": 5,
            "scope_label": "Sub-national",
            "countries": [{"code": "CO", "areas": ["CO-CUN", "CO-CAS"]}],
        },
        capacity_sharing={
            "number_people_trained": {"women": 10},
            "length_training": "Short-term",
            "delivery_method": "In person",
        },
    )
    country = result.geo_focus.countries[0]
    assert country.iso_alpha_2 == "CO"
    assert country.subnational_areas == ["CO-CUN", "CO-CAS"]
    assert result.geo_focus.scope_code == 5


def test_geo_focus_derives_scope_code_from_label():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="National training",
        description="Training in Kenya.",
        geo_focus={"scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
        capacity_sharing={
            "number_people_trained": {"women": 10},
            "length_training": "Short-term",
            "delivery_method": "In person",
        },
    )
    assert result.geo_focus.scope_code == 4
    assert result.geo_focus.scope_label == "National"


def test_capacity_sharing_mds_schema():
    result = CapacitySharingResult(
        indicator="Capacity Sharing for Development",
        title="Extension agent training",
        description="Short-term group training for extension agents.",
        lead_center={
            "institution_id": 1279,
            "acronym": "ICARDA",
            "name": "International Center for Agricultural Research in the Dry Areas",
        },
        geo_focus={"scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
        capacity_sharing={
            "number_people_trained": {"women": 20, "men": 15, "non_binary": 0, "unknown": 2},
            "length_training": "Short-term",
            "delivery_method": "In person",
        },
    )
    assert result.indicator == "Capacity Sharing for Development"
    assert result.geo_focus.scope_code == 4
    assert result.capacity_sharing.delivery_method == "In person"


def test_innovation_use_mds_schema():
    result = InnovationUseResult(
        indicator="Innovation Use",
        title="Adoption of drought-tolerant wheat",
        description="Farmers adopted the variety across two counties.",
        geo_focus={"scope_code": 4, "scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
        innovation_use={
            "current_innovation_use_numbers": {
                "innov_use_to_be_determined": False,
                "actors": [
                    {
                        "actor_type_id": 1,
                        "actor_type_name": "Farmers/ (agro)pastoralist/ herders/ fishers",
                        "sex_and_age_disaggregation": True,
                        "how_many": 1200,
                    }
                ],
            }
        },
    )
    assert result.indicator == "Innovation Use"
    assert result.innovation_use.current_innovation_use_numbers.actors[0].how_many == 1200


def test_other_output_schema():
    result = OtherOutputResult(
        indicator="Other Output",
        title="Network synthesis report",
        description="Cross-center synthesis of learning products.",
        geo_focus={"scope_code": 1, "scope_label": "Global"},
    )
    assert result.indicator == "Other Output"
    assert result.geo_focus.scope_label == "Global"


def test_other_outcome_schema():
    result = OtherOutcomeResult(
        indicator="Other Outcome",
        title="Strengthened national partner capacity",
        description="Partner institutions improved MEL practices.",
        geo_focus={"scope_code": 4, "scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
    )
    assert result.indicator == "Other Outcome"
    assert result.geo_focus.countries[0].iso_alpha_2 == "KE"


def test_mining_response_discriminated_union():
    payload = {
        "results": [
            {
                "indicator": "Innovation Use",
                "title": "Use case",
                "description": "desc",
                "geo_focus": {"scope_label": "Global"},
                "innovation_use": {
                    "current_innovation_use_numbers": {
                        "innov_use_to_be_determined": True,
                    }
                },
            },
            {
                "indicator": "Other Output",
                "title": "Other output",
                "description": "desc",
                "geo_focus": {"scope_label": "Global"},
            },
            {
                "indicator": "Other Outcome",
                "title": "Other outcome",
                "description": "desc",
                "geo_focus": {"scope_label": "Global"},
            },
        ]
    }
    response = MiningResponse.model_validate(payload)
    assert len(response.results) == 3
    assert response.results[0].indicator == "Innovation Use"
    assert response.results[1].indicator == "Other Output"
    assert response.results[2].indicator == "Other Outcome"


def test_innovation_use_tbd_strips_arrays():
    result = InnovationUseResult(
        indicator="Innovation Use",
        title="Pending adoption data",
        description="Use not yet quantified.",
        geo_focus={"scope_label": "Global"},
        innovation_use={
            "current_innovation_use_numbers": {
                "innov_use_to_be_determined": True,
                "actors": [{"actor_type_id": 1, "actor_type_name": "Researchers"}],
                "organization": [{"institution_types_id": 75, "how_many": 1}],
                "measures": [{"unit_of_measure": "hectares", "quantity": "100"}],
            }
        },
    )
    block = result.innovation_use.current_innovation_use_numbers
    assert block.actors is None
    assert block.organization is None
    assert block.measures is None


def test_innovation_readiness_level_from_scaling_level():
    from app.schemas.prms_mining_schemas import InnovationDevelopmentResult

    result = InnovationDevelopmentResult(
        indicator="Innovation Development",
        title="Prototype variety",
        description="Field-tested drought-tolerant wheat.",
        geo_focus={"scope_label": "Global"},
        innovation_development={
            "innovation_readiness_level": {"level": 3},
        },
    )
    irl = result.innovation_development.innovation_readiness_level
    assert irl.id == 14
    assert irl.name == "Proof of Concept"


def test_format_mining_response_drops_knowledge_product():
    payload = {
        "results": [
            {
                "indicator": "Knowledge Product",
                "title": "Should be dropped",
                "description": "desc",
                "keywords": ["kp"],
                "geoscope_level": "Global",
            },
            {
                "indicator": "Other Output",
                "title": "Keep me",
                "description": "desc",
                "geo_focus": {"scope_label": "Global"},
            },
        ]
    }
    formatted = format_mining_response(payload)
    assert len(formatted["results"]) == 1
    assert formatted["results"][0]["indicator"] == "Other Output"
