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
            "promptVersion": "v2-1.0.0", "modelId": "m", "quoteVerified": True}
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


def test_production_version_covers_the_seven_fields():
    version = production_version()
    assert version == "v2-1.0.0"
    assert all(get_prompt(version, k) is not None for k in AI_FIELDS) and len(AI_FIELDS) == 7
