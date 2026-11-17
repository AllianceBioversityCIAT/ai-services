import pytest
from pydantic import TypeAdapter, ValidationError

from app.contract.fields import AI_FIELDS, field_spec
from app.contract.messages import AiJobMessage, AiSuggestionEvent, AiSuggestionView
from app.prompts.loader import get_prompt, production_version

VIEW = TypeAdapter(AiSuggestionView)


def test_job_message_parses_and_rejects_missing_field():
    msg = {"runId": "r1", "resultCode": "1234", "snapKey": "s1", "fieldKey": "general.gender_tag", "promptVersion": "v1"}
    assert AiJobMessage.model_validate(msg).model_dump() == msg
    with pytest.raises(ValidationError):
        AiJobMessage.model_validate({k: v for k, v in msg.items() if k != "fieldKey"})


def test_unavailable_requires_a_reason():
    with pytest.raises(ValidationError):
        VIEW.validate_python({"status": "unavailable", "fieldKey": "x"})
    VIEW.validate_python({"status": "unavailable", "fieldKey": "x", "unavailableReason": "private_link"})


def test_knows_which_fields_have_criteria():
    assert field_spec("general.climate_tag").max == 2
    assert field_spec("innovation_use.use_level.innovation_use_level").max == 9
    assert field_spec("__class__") is None
    assert field_spec("unknown_field") is None


EVENT = TypeAdapter(AiSuggestionEvent)


def test_available_view_carries_the_level_and_quote_flag():
    base = {"status": "available", "fieldKey": "innovation_dev.readiness_level", "suggestionId": "s",
            "signal": "amber", "explanation": "e", "evidenceQuote": "q", "evidenceSource": None,
            "promptVersion": "v2-1.0.0", "modelId": "m", "quoteVerified": True, "valueKind": "level"}
    with pytest.raises(ValidationError):
        VIEW.validate_python(base)
    assert VIEW.validate_python({**base, "suggestedValue": 6}).suggestedValue == 6
    with pytest.raises(ValidationError):
        VIEW.validate_python({**base, "suggestedValue": 11})


def test_usage_events_are_unchanged():
    assert EVENT.validate_python({"action": "copied"}).action == "copied"
    assert EVENT.validate_python({"action": "comment_saved", "commentId": "c1"}).commentId == "c1"


def test_validated_above_ai_event():
    ev = {"action": "validated_above_ai", "aiLevel": 3, "validatedLevel": 5, "reason": "Report shows use at scale."}
    assert EVENT.validate_python(ev).validatedLevel == 5
    for bad in (
        {"validatedLevel": 4},  # only 1 above
        {"validatedLevel": 2},  # below
        {"reason": ""},
        {"reason": "x" * 201},
        {"reason": "two\nlines"},
        {"aiLevel": 10},
    ):
        with pytest.raises(ValidationError):
            EVENT.validate_python({**ev, **bad})
    with pytest.raises(ValidationError):
        EVENT.validate_python({k: v for k, v in ev.items() if k != "reason"})
    assert len(EVENT.validate_python({**ev, "reason": "x" * 200}).reason) == 200


def test_production_versions_per_field():
    assert {k: production_version(k) for k in AI_FIELDS} == {
        **{k: "v2-1.0.0" for k, s in AI_FIELDS.items() if not s.indicative},
        "general.result_type": "v1-1.0.0",
        "innovation_use.current_use.actors": "v1-1.0.0",
    }
    assert all(get_prompt(production_version(k), k) is not None for k in AI_FIELDS) and len(AI_FIELDS) == 9


ROW = {"user": "actors", "user_type": "Researchers", "user_subtype": None, "quantity": 12, "women": 5,
       "youth_women": None, "non_youth_women": None, "men": 7, "youth_men": None, "non_youth_men": None,
       "geolocation": None, "other_quantitative_measures": None}
INDICATIVE = {"status": "available", "fieldKey": "general.result_type", "suggestionId": "s", "signal": "indicative",
              "explanation": "e", "evidenceSource": None, "promptVersion": "v1-1.0.0", "modelId": "m",
              "quoteVerified": False}


def test_indicative_views_carry_a_value_and_no_quote():
    cat = VIEW.validate_python({**INDICATIVE, "valueKind": "category", "suggestedValue": "Knowledge Product"})
    assert cat.suggestedValue == "Knowledge Product" and cat.evidenceQuote is None
    nums = VIEW.validate_python({
        **INDICATIVE, "fieldKey": "innovation_use.current_use.actors", "valueKind": "use_numbers",
        "suggestedValue": [ROW, {**ROW, "user": "other type", "user_type": "hectares", "quantity": 2.5}],
        "coversFieldKeys": ["innovation_use.current_use.organizations", "innovation_use.current_use.measures"],
    })
    assert nums.suggestedValue[1].quantity == 2.5
    for bad in (
        {"valueKind": "category", "suggestedValue": "Banana"},  # not a prompt 06 category
        {"valueKind": "category"},  # value is required
        {"valueKind": "category", "suggestedValue": None},
        {"valueKind": "use_numbers", "suggestedValue": "Innovation"},  # kind mismatch
        {"valueKind": "use_numbers", "suggestedValue": [{**ROW, "extra": 1}]},
        {"valueKind": "level", "suggestedValue": 3},  # indicative signal with a level
    ):
        with pytest.raises(ValidationError):
            VIEW.validate_python({**INDICATIVE, **bad})
    with pytest.raises(ValidationError):  # scored field cannot be indicative-free of colour mismatch
        VIEW.validate_python({**INDICATIVE, "signal": "green", "valueKind": "category", "suggestedValue": "Other"})
