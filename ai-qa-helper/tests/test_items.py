"""Item format verified against ElectroDB 3.9.3 (see app/contract/items.py)."""

import pytest
from pydantic import ValidationError

from app.contract.items import (
    AiRunItem,
    AiSuggestionItem,
    run_pk,
    snapshot_suggestions_prefix,
    suggestion_pk,
    suggestion_sk,
)

SNAP = "2025#000012#00000003#0000000042"


def test_keys_are_literal_templates_without_case_changes():
    assert suggestion_pk(4521) == "RESULT#4521"
    assert suggestion_sk(SNAP, "Impact_Area_Gender", "v2+AbC123") == f"AI#{SNAP}#Impact_Area_Gender#v2+AbC123"
    assert snapshot_suggestions_prefix(SNAP) == f"AI#{SNAP}#"
    assert run_pk("R-1") == "AIRUN#R-1"


def test_field_and_prompt_version_cannot_contain_hash():
    with pytest.raises(ValueError):
        suggestion_sk(SNAP, "a#b", "v1")
    with pytest.raises(ValueError):
        suggestion_sk(SNAP, "gender", "v1#x")


def test_item_dumps_electrodb_identifiers():
    item = AiSuggestionItem.model_validate(
        {
            "pk": suggestion_pk(4521),
            "sk": suggestion_sk(SNAP, "impact_area_gender", "v1"),
            "__edb_e__": "aiSuggestion",
            "__edb_v__": "1",
            "resultCode": 4521,
            "snapKey": SNAP,
            "fieldKey": "impact_area_gender",
            "promptVersion": "v1",
            "suggestionId": "s-1",
            "runId": "R-1",
            "status": "unavailable",
            "unavailableReason": "private_link",
            "createdAt": "2026-11-11T00:00:00Z",
        }
    )
    dumped = item.model_dump(by_alias=True, exclude_none=True)
    assert dumped["__edb_e__"] == "aiSuggestion" and dumped["__edb_v__"] == "1"
    assert item.keys_consistent()
    with pytest.raises(ValidationError):
        AiSuggestionItem.model_validate({**dumped, "__edb_e__": "other"})


def test_run_completion_rule():
    base = {"pk": "AIRUN#R", "sk": "RUN", "__edb_e__": "aiRun", "__edb_v__": "1", "runId": "R", "createdAt": "t"}
    assert AiRunItem.model_validate({**base, "expected": 3, "produced": 2, "unavailable": 1, "failed": 0}).is_complete()
    assert not AiRunItem.model_validate({**base, "expected": 3, "produced": 2, "unavailable": 0, "failed": 1}).is_complete()
