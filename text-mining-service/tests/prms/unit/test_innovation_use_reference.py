from app.schemas.prms_innovation_use_reference import resolve_actor_type, resolve_institution_type
from app.schemas.prms_mining_schemas import InnovationUseResult
from app.utils.prompt.prompt_prms import compose_extraction_prompt_body


def test_resolve_actor_type_farmers():
    resolved = resolve_actor_type(item_id=1)
    assert resolved == {
        "actor_type_id": 1,
        "actor_type_name": "Farmers/ (agro)pastoralist/ herders/ fishers",
    }


def test_resolve_institution_type_ngo_subtype():
    resolved = resolve_institution_type(item_id=45)
    assert resolved == {
        "institution_types_id": 45,
        "institution_types_name": "NGO National (General)",
        "organization_type": "NGO",
    }


def test_resolve_institution_type_leaf_only():
    resolved = resolve_institution_type(item_id=75)
    assert resolved == {
        "institution_types_id": 75,
        "institution_types_name": "Private company (other than financial)",
    }


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
                        "how_many": 120,
                        "women": 60,
                        "men": 40,
                    }
                ],
                "organization": [
                    {
                        "organization_type": "NGO",
                        "institution_types_id": 45,
                        "how_many": 3,
                    },
                    {
                        "institution_types_id": 75,
                        "how_many": 2,
                    },
                ],
                "measures": [{"unit_of_measure": "hectares", "quantity": "2500"}],
            }
        },
    )
    assert result.innovation_use.current_innovation_use_numbers.innov_use_to_be_determined is False
    assert result.innovation_use.current_innovation_use_numbers.actors[0].how_many == 120
    orgs = result.innovation_use.current_innovation_use_numbers.organization
    assert orgs[0].organization_type == "NGO"
    assert orgs[0].institution_types_id == 45
    assert orgs[1].organization_type is None
    assert orgs[1].institution_types_id == 75


def test_innovation_use_organization_other_requires_description():
    result = InnovationUseResult(
        indicator="Innovation Use",
        title="Cooperative adoption",
        description="Farmer cooperatives adopted the innovation.",
        geo_focus={"scope_label": "National"},
        innovation_use={
            "current_innovation_use_numbers": {
                "innov_use_to_be_determined": False,
                "organization": [
                    {
                        "institution_types_id": 78,
                        "other_institution": "Farmer cooperatives",
                        "how_many": 4,
                    }
                ],
            }
        },
    )
    assert result.innovation_use.current_innovation_use_numbers.organization[0].other_institution == "Farmer cooperatives"


def test_innovation_use_tbd_requires_no_arrays():
    result = InnovationUseResult(
        indicator="Innovation Use",
        title="Early-stage innovation",
        description="Use not yet reported.",
        geo_focus={"scope_label": "Global"},
        innovation_use={
            "current_innovation_use_numbers": {
                "innov_use_to_be_determined": True,
            }
        },
    )
    assert result.innovation_use.current_innovation_use_numbers.actors is None


def test_innovation_use_prompt_lists_actor_types():
    body = compose_extraction_prompt_body()
    assert "current_innovation_use_numbers" in body
    assert 'id 1, name "Farmers/ (agro)pastoralist/ herders/ fishers"' in body
    assert "innov_use_to_be_determined" in body
    assert "unit_of_measure" in body
    assert 'organization_type "NGO"' in body
    assert 'id 45, name "NGO National (General)"' in body
    assert 'id 75, name "Private company (other than financial)"' in body
