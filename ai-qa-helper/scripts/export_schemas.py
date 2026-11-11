"""Generate the published contract (JSON Schema + example items) from the Pydantic models.

Run from ai-qa-helper/:  uv run python -m scripts.export_schemas
tests/test_schema_export.py fails when the committed files are stale.
"""

import json
from pathlib import Path

from pydantic import TypeAdapter

from app.contract.items import AiRunItem, AiSuggestionItem, suggestion_pk, suggestion_sk
from app.contract.messages import AiJobMessage, AiSuggestionEvent, AiSuggestionView

ROOT = Path(__file__).resolve().parent.parent / "contract"

SCHEMAS = {
    "ai-job-message": TypeAdapter(AiJobMessage),
    "ai-suggestion-view": TypeAdapter(AiSuggestionView),
    "ai-suggestion-event": TypeAdapter(AiSuggestionEvent),
    "ai-suggestion-item": TypeAdapter(AiSuggestionItem),
    "ai-run-item": TypeAdapter(AiRunItem),
}

_SNAP = "2025#000012#00000003#0000000042"
EXAMPLES = {
    # Fictional values. The onecgiar_qa contract test loads these through its ElectroDB entities.
    "ai-suggestion-item.available": AiSuggestionItem.model_validate(
        {
            "pk": suggestion_pk(1001),
            "sk": suggestion_sk(_SNAP, "general.gender_tag", "v2-1.0.0"),
            "__edb_e__": "aiSuggestion",
            "__edb_v__": "1",
            "resultCode": 1001,
            "snapKey": _SNAP,
            "fieldKey": "general.gender_tag",
            "promptVersion": "v2-1.0.0",
            "suggestionId": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
            "runId": "run-example",
            "status": "available",
            "signal": "green",
            "explanation": "The evidence describes training targeted at women farmers, consistent with the reported score.",
            "evidenceQuote": "trained 1,200 women farmers in climate-smart practices",
            "evidenceSource": "https://example.org/evidence.pdf",
            "evidenceSourceIndex": 0,
            "suggestedValue": 1,
            "reportedValue": 1,
            "quoteVerified": True,
            "partialEvidence": False,
            "modelId": "anthropic.claude-haiku-5-5",
            "evidenceHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "createdAt": "2026-11-20T12:00:00Z",
        }
    ),
    "ai-suggestion-item.unavailable": AiSuggestionItem.model_validate(
        {
            "pk": suggestion_pk(1001),
            "sk": suggestion_sk(_SNAP, "innovation_use.use_level.innovation_use_level", "v2-1.0.0"),
            "__edb_e__": "aiSuggestion",
            "__edb_v__": "1",
            "resultCode": 1001,
            "snapKey": _SNAP,
            "fieldKey": "innovation_use.use_level.innovation_use_level",
            "promptVersion": "v2-1.0.0",
            "suggestionId": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
            "runId": "run-example",
            "status": "unavailable",
            "unavailableReason": "private_link",
            "createdAt": "2026-11-20T12:00:00Z",
        }
    ),
}


def render() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for name, adapter in SCHEMAS.items():
        schema = adapter.json_schema(by_alias=True)
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{name}.schema.json", **schema}
        out[ROOT / "schema" / f"{name}.schema.json"] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    for name, model in EXAMPLES.items():
        out[ROOT / "examples" / f"{name}.json"] = (
            json.dumps(model.model_dump(by_alias=True, exclude_none=True), indent=2, sort_keys=True) + "\n"
        )
    return out


def main() -> None:
    for path, text in render().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
