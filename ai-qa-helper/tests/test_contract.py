import pytest
from pydantic import TypeAdapter, ValidationError

from app.contract.fields import field_spec
from app.contract.messages import AiJobMessage, AiSuggestionView

VIEW = TypeAdapter(AiSuggestionView)


def test_job_message_parses_and_rejects_missing_field():
    msg = {"runId": "r1", "resultCode": "1234", "snapKey": "s1", "fieldKey": "impact_area_gender", "promptVersion": "v1"}
    assert AiJobMessage.model_validate(msg).model_dump() == msg
    with pytest.raises(ValidationError):
        AiJobMessage.model_validate({k: v for k, v in msg.items() if k != "fieldKey"})


def test_unavailable_requires_a_reason():
    with pytest.raises(ValidationError):
        VIEW.validate_python({"status": "unavailable", "fieldKey": "x"})
    VIEW.validate_python({"status": "unavailable", "fieldKey": "x", "unavailableReason": "private_link"})


def test_knows_which_fields_have_criteria():
    assert field_spec("impact_area_climate").max == 2
    assert field_spec("innovation_use_level").max == 9
    assert field_spec("__class__") is None
    assert field_spec("unknown_field") is None
