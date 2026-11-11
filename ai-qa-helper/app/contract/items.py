"""DynamoDB items written by this worker and read by the QA API through ElectroDB.

Verified against ElectroDB 3.9.3 (the version in onecgiar_qa/server):
  - with ``template`` and ``casing: 'none'`` the pk/sk are written exactly as the template;
    the default casing would lowercase them;
  - ElectroDB adds ``__edb_e__`` (entity name) and ``__edb_v__`` (model version) to every item,
    and a query silently drops items that lack them. Python writers must add both.

Proposed ElectroDB definitions for onecgiar_qa (keys must match these templates byte for byte):

  aiSuggestion  model {entity: 'aiSuggestion', version: '1', service: 'qa'}
    pk: {field: 'pk', casing: 'none', composite: ['resultCode'], template: 'RESULT#${resultCode}'}
    sk: {field: 'sk', casing: 'none', composite: ['snapKey', 'fieldKey', 'promptVersion'],
         template: 'AI#${snapKey}#${fieldKey}#${promptVersion}'}

  aiRun  model {entity: 'aiRun', version: '1', service: 'qa'}
    pk: {field: 'pk', casing: 'none', composite: ['runId'], template: 'AIRUN#${runId}'}
    sk: {field: 'sk', casing: 'none', composite: [], template: 'RUN'}

``fieldKey`` and ``promptVersion`` must not contain ``#`` so a ``begins_with`` query on
``AI#<snapKey>#`` returns exactly the suggestions of one snapshot.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contract.messages import Signal, UnavailableReason

ELECTRODB_ENTITY_SUGGESTION = "aiSuggestion"
ELECTRODB_ENTITY_RUN = "aiRun"
ELECTRODB_VERSION = "1"

_NO_HASH = re.compile(r"^[^#]+$")


def suggestion_pk(result_code: int) -> str:
    return f"RESULT#{result_code}"


def suggestion_sk(snap_key: str, field_key: str, prompt_version: str) -> str:
    if not _NO_HASH.match(field_key) or not _NO_HASH.match(prompt_version):
        raise ValueError("fieldKey and promptVersion must be non-empty and contain no '#'")
    return f"AI#{snap_key}#{field_key}#{prompt_version}"


def snapshot_suggestions_prefix(snap_key: str) -> str:
    return f"AI#{snap_key}#"


def run_pk(run_id: str) -> str:
    return f"AIRUN#{run_id}"


RUN_SK = "RUN"


class AiSuggestionItem(BaseModel):
    """One stored suggestion (status available or unavailable). 'pending' is never stored."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    pk: str = Field(pattern=r"^RESULT#\d+$")
    sk: str = Field(pattern=r"^AI#.+#[^#]+#[^#]+$")
    edb_e: Literal["aiSuggestion"] = Field(alias="__edb_e__")
    edb_v: Literal["1"] = Field(alias="__edb_v__")

    resultCode: int
    snapKey: str
    fieldKey: str = Field(pattern=r"^[^#]+$")
    promptVersion: str = Field(pattern=r"^[^#]+$")
    suggestionId: str
    runId: str
    status: Literal["available", "unavailable"]
    signal: Signal | None = None
    explanation: str | None = None
    evidenceQuote: str | None = None
    evidenceSource: str | None = None
    evidenceSourceIndex: int | None = None
    suggestedValue: int | None = None
    reportedValue: int | None = None
    quoteVerified: bool | None = None
    partialEvidence: bool | None = None
    unavailableReason: UnavailableReason | None = None
    modelId: str | None = None
    evidenceHash: str | None = None
    createdAt: str

    def keys_consistent(self) -> bool:
        return self.pk == suggestion_pk(self.resultCode) and self.sk == suggestion_sk(
            self.snapKey, self.fieldKey, self.promptVersion
        )


class AiRunItem(BaseModel):
    """Run counters. A run is complete only when produced + unavailable == expected and failed == 0."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    pk: str = Field(pattern=r"^AIRUN#.+$")
    sk: Literal["RUN"]
    edb_e: Literal["aiRun"] = Field(alias="__edb_e__")
    edb_v: Literal["1"] = Field(alias="__edb_v__")

    runId: str
    expected: int = Field(ge=0)
    produced: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    failed: int = Field(ge=0)
    createdAt: str

    def is_complete(self) -> bool:
        return self.produced + self.unavailable == self.expected and self.failed == 0
