from app.schemas.prms_policy_reference import (
    normalize_policy_type_ref,
    resolve_policy_stage,
    resolve_policy_type,
    resolve_status_amount,
)
from app.schemas.prms_mining_schemas import PolicyChangeResult
from app.utils.prompt.prompt_prms import compose_extraction_prompt_body


def test_resolve_policy_type_exact_catalog_name():
    resolved = resolve_policy_type(name="Program, budget or investment")
    assert resolved == {"id": 1, "name": "Program, budget or investment"}


def test_resolve_policy_type_policy_or_strategy():
    resolved = resolve_policy_type(name="Policy or strategy")
    assert resolved == {"id": 3, "name": "Policy or strategy"}


def test_resolve_policy_stage_exact_catalog_name():
    resolved = resolve_policy_stage(name="Stage 2")
    assert resolved == {"id": 7, "name": "Stage 2"}


def test_resolve_policy_stage_by_id():
    resolved = resolve_policy_stage(item_id=8)
    assert resolved == {"id": 8, "name": "Stage 3"}


def test_resolve_status_amount_confirmed_estimated_unknown():
    assert resolve_status_amount(name="Confirmed") == {"id": 1, "name": "Confirmed"}
    assert resolve_status_amount(name="Estimated") == {"id": 2, "name": "Estimated"}
    assert resolve_status_amount(name="Unknown") == {"id": 3, "name": "Unknown"}


def test_normalize_policy_type_includes_budget_fields():
    normalized = normalize_policy_type_ref(
        {
            "name": "Program, budget or investment",
            "status_amount": {"name": "Confirmed"},
            "amount": "5000000",
        }
    )
    assert normalized["id"] == 1
    assert normalized["status_amount"] == {"id": 1, "name": "Confirmed"}
    assert normalized["amount"] == 5000000


def test_policy_change_mds_schema():
    result = PolicyChangeResult(
        indicator="Policy Change",
        title="Agricultural budget policy in Kenya",
        description="National budget line for rural development informed by research.",
        geo_focus={"scope_code": 4, "scope_label": "National", "countries": [{"iso_alpha_2": "KE"}]},
        policy_change={
            "policy_type": {
                "id": 1,
                "name": "Program, budget or investment",
                "status_amount": {"id": 1, "name": "Confirmed"},
                "amount": 5000000,
            },
            "policy_stage": {"id": 7, "name": "Stage 2"},
            "implementing_organization": [
                {
                    "institutions_id": 1279,
                    "institutions_acronym": "MOA",
                    "institutions_name": "Ministry of Agriculture Kenya",
                }
            ],
        },
    )
    assert result.policy_change.policy_type.id == 1
    assert result.policy_change.policy_stage.id == 7
    assert result.policy_change.policy_stage.name == "Stage 2"
    assert result.policy_change.implementing_organization[0].institutions_id == 1279


def test_policy_change_schema_accepts_partial_block():
    result = PolicyChangeResult(
        indicator="Policy Change",
        title="Policy uptake in Uganda",
        description="Research taken up by ministry.",
        geo_focus={"scope_code": 4, "scope_label": "National", "countries": [{"iso_alpha_2": "UG"}]},
        policy_change={
            "policy_stage": {"id": 6, "name": "Stage 1"},
            "implementing_organization": [{"institutions_acronym": "MoA-Uganda"}],
        },
    )
    assert result.policy_change.policy_type is None
    assert result.policy_change.policy_stage.id == 6
    assert result.policy_change.policy_stage.name == "Stage 1"


def test_policy_change_prompt_lists_inline_options():
    body = compose_extraction_prompt_body()
    assert 'id 1, name "Program, budget or investment"' in body
    assert 'id 2, name "Legal instrument"' in body
    assert 'id 3, name "Policy or strategy"' in body
    assert 'id 1, name "Confirmed"' in body
    assert 'id 2, name "Estimated"' in body
    assert 'id 3, name "Unknown"' in body
    assert 'id 7, name "Stage 2"' in body
    assert "Policy enacted (provide link to published documents)." in body
    assert "institutions_name" in body
    assert "institutions_acronym" in body
    assert "Policy type guidance:" in body
