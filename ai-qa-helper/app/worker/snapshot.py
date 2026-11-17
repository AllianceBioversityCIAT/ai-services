"""Reads what the worker needs from a QA result snapshot.

The snapshot is written by onecgiar_qa (``resultSnapshot`` ElectroDB entity, pk ``RESULT#<code>``,
sk ``SNAP#<snapKey>``). ``values`` is the Reporting feed's JSON keyed by catalog field key, stored
as a string or, above 256 KB, gzipped in ``valuesGz``.

Value shapes are not documented in onecgiar_qa beyond the catalog ``type``; the only fixture shows
a single_select as ``{"value": 4, "degree": 2}``. ``scalar`` therefore accepts a bare value or an
object with ``value``/``id``. An id outside the control-list maps below is treated as "not reported"
(signal amber), never guessed.
"""

import gzip
import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.contract.fields import USE_NUMBERS_PREFIX, FieldSpec

LEVEL_MAPS: dict[str, dict[int, int]] = {
    # Confirmed by Reporting (2026-11-12): tag_levels from the Reporting code; the other two from
    # its control-list export (level_maps.csv).
    "tag_levels": {1: 0, 2: 1, 3: 2},
    "readiness_levels": {11 + level: level for level in range(10)},  # 11 Idea ... 20 Proven Innovation
    "innovation_use_levels": {1 + level: level for level in range(10)},  # 1 No use ... 10 End-user
}

RESULT_TYPE_KEYS: dict[int, str] = {
    # onecgiar_pr ResultTypeEnum id -> catalog result_types key (qa-catalog/definitions/result-type-ids.ts).
    1: "policy_change",
    2: "innovation_use",
    4: "other_outcome",
    5: "capacity_sharing",
    6: "knowledge_product",
    7: "innovation_development",
    8: "other_output",
    9: "impact_contribution",
    10: "innovation_package",
}

USE_NUMBER_LISTS = ("actors", "organizations", "measures")

MAX_LINKS = 5
"""Same cap as qa-service ``enhance_prms_context(max_evidences=5)``."""

EvidenceScope = Literal["field", "result", "none"]


@dataclass(frozen=True)
class FieldInput:
    title: str
    description: str
    reported: int | str | dict[str, Any] | None
    """level: 0-9; result category: result-type key; use numbers: the three lists. None: not reported."""
    links: list[str]
    evidence_scope: EvidenceScope
    """field: links flagged for this field; result: no flagged link, all the result's links."""


class SnapshotReader(Protocol):
    def values(self, result_code: int, snap_key: str) -> dict[str, Any] | None: ...


def scalar(value: Any) -> Any:
    while isinstance(value, dict):
        for key in ("value", "id"):
            if key in value:
                value = value[key]
                break
        else:
            return None
    return value


def text(values: dict[str, Any], key: str) -> str:
    v = scalar(values.get(key))
    return v.strip() if isinstance(v, str) else ""


def reported_value(values: dict[str, Any], field_key: str, spec: FieldSpec) -> int | str | dict[str, Any] | None:
    if spec.kind == "use_numbers":
        lists = {name: values.get(f"{USE_NUMBERS_PREFIX}.{name}") for name in USE_NUMBER_LISTS}
        lists = {k: v for k, v in lists.items() if isinstance(v, list)}
        return lists or None
    raw = scalar(values.get(field_key))
    if raw is None or isinstance(raw, bool):
        return None
    try:
        control_id = int(raw)
    except (TypeError, ValueError):
        return None
    if spec.kind == "result_category":
        return RESULT_TYPE_KEYS.get(control_id)
    return LEVEL_MAPS.get(spec.control_list, {}).get(control_id)


def evidence_links(values: dict[str, Any], spec: FieldSpec) -> tuple[list[str], EvidenceScope]:
    items = values.get("evidence.items")
    if not isinstance(items, list):
        return [], "none"
    every: list[str] = []
    flagged: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = _url(item)
        if not url:
            continue
        if url not in every:
            every.append(url)
        if scalar(item.get(spec.evidence_flag)) is True and url not in flagged:
            flagged.append(url)
    if flagged:
        return flagged[:MAX_LINKS], "field"
    if every:
        return every[:MAX_LINKS], "result"
    return [], "none"


def read_field_input(values: dict[str, Any], field_key: str, spec: FieldSpec) -> FieldInput:
    links, scope = evidence_links(values, spec)
    return FieldInput(
        title=text(values, "general.title"),
        description=text(values, "general.description"),
        reported=reported_value(values, field_key, spec),
        links=links,
        evidence_scope=scope,
    )


def _url(item: dict[str, Any]) -> str:
    """http(s) links as is; ``www.`` links without a scheme (as submitters often type them) get https://."""
    for key in ("link", "file_url"):
        v = scalar(item.get(key))
        if not isinstance(v, str):
            continue
        v = v.strip()
        if v.lower().startswith(("http://", "https://")):
            return v
        if v.lower().startswith("www.") and " " not in v:
            return f"https://{v}"
    return ""


class DynamoSnapshotReader:
    def __init__(self, table: str, client: Any):
        self._table = table
        self._client = client

    def values(self, result_code: int, snap_key: str) -> dict[str, Any] | None:
        resp = self._client.get_item(
            TableName=self._table,
            Key={"pk": {"S": f"RESULT#{result_code}"}, "sk": {"S": f"SNAP#{snap_key}"}},
            ProjectionExpression="#v, valuesGz",
            ExpressionAttributeNames={"#v": "values"},
        )
        item = resp.get("Item")
        if not item:
            return None
        if "valuesGz" in item:
            raw = item["valuesGz"].get("B")
            data = json.loads(gzip.decompress(raw).decode("utf-8")) if raw else None
        elif "values" in item:
            data = json.loads(item["values"]["S"])
        else:
            data = None
        return data if isinstance(data, dict) else {}
