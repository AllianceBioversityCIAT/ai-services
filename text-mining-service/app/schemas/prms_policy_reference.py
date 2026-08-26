"""PRMS policy_change catalogs for schema validation and normalization."""

from __future__ import annotations

from typing import Any

POLICY_TYPES: tuple[dict[str, Any], ...] = (
    {"id": 1, "name": "Program, budget or investment"},
    {"id": 2, "name": "Legal instrument"},
    {"id": 3, "name": "Policy or strategy"},
)

POLICY_STAGES: tuple[dict[str, Any], ...] = (
    {
        "id": 6,
        "name": "Stage 1",
        "definition": "Research taken up by next user, policy change not yet enacted.",
    },
    {
        "id": 7,
        "name": "Stage 2",
        "definition": "Policy enacted (provide link to published documents).",
    },
    {
        "id": 8,
        "name": "Stage 3",
        "definition": "Evidence of impact of policy (provide Key Result Story or evidence link).",
    },
)

STATUS_AMOUNTS: tuple[dict[str, Any], ...] = (
    {"id": 1, "name": "Confirmed"},
    {"id": 2, "name": "Estimated"},
    {"id": 3, "name": "Unknown"},
)

_POLICY_TYPE_BY_ID = {item["id"]: item for item in POLICY_TYPES}
_POLICY_TYPE_BY_NAME = {item["name"].lower(): item for item in POLICY_TYPES}
_POLICY_STAGE_BY_ID = {item["id"]: item for item in POLICY_STAGES}
_POLICY_STAGE_BY_NAME = {item["name"].lower(): item for item in POLICY_STAGES}
_STATUS_AMOUNT_BY_ID = {item["id"]: item for item in STATUS_AMOUNTS}
_STATUS_AMOUNT_BY_NAME = {item["name"].lower(): item for item in STATUS_AMOUNTS}


def _resolve_id_name(
    *,
    catalog_by_id: dict[int, dict[str, Any]],
    catalog_by_name: dict[str, dict[str, Any]],
    item_id: int | str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    if item_id is not None:
        try:
            matched = catalog_by_id.get(int(item_id))
            if matched:
                return dict(matched)
        except (TypeError, ValueError):
            pass

    if isinstance(name, str) and name.strip():
        matched = catalog_by_name.get(name.strip().lower())
        if matched:
            return dict(matched)

    return None


def resolve_policy_type(*, item_id: int | str | None = None, name: str | None = None) -> dict[str, Any] | None:
    return _resolve_id_name(
        catalog_by_id=_POLICY_TYPE_BY_ID,
        catalog_by_name=_POLICY_TYPE_BY_NAME,
        item_id=item_id,
        name=name,
    )


def resolve_policy_stage(*, item_id: int | str | None = None, name: str | None = None) -> dict[str, Any] | None:
    resolved = _resolve_id_name(
        catalog_by_id=_POLICY_STAGE_BY_ID,
        catalog_by_name=_POLICY_STAGE_BY_NAME,
        item_id=item_id,
        name=name,
    )
    if resolved:
        return {"id": resolved["id"], "name": resolved["name"]}
    return None


def resolve_status_amount(*, item_id: int | str | None = None, name: str | None = None) -> dict[str, Any] | None:
    return _resolve_id_name(
        catalog_by_id=_STATUS_AMOUNT_BY_ID,
        catalog_by_name=_STATUS_AMOUNT_BY_NAME,
        item_id=item_id,
        name=name,
    )


def normalize_policy_type_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    resolved = resolve_policy_type(item_id=value.get("id"), name=value.get("name"))
    if not resolved:
        return None
    normalized = dict(resolved)
    if normalized["id"] == 1:
        status_amount = value.get("status_amount")
        if isinstance(status_amount, dict):
            resolved_status = resolve_status_amount(
                item_id=status_amount.get("id"),
                name=status_amount.get("name"),
            )
            if resolved_status:
                normalized["status_amount"] = dict(resolved_status)
        amount = value.get("amount")
        if amount is not None:
            try:
                normalized["amount"] = int(amount)
            except (TypeError, ValueError):
                pass
    return normalized


def normalize_policy_stage_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return resolve_policy_stage(item_id=value.get("id"), name=value.get("name"))


def normalize_implementing_organization_ref(value: Any) -> dict[str, Any] | None:
    """Normalize implementing-organization items from extraction or post-mapping shapes."""
    if not isinstance(value, dict):
        return None
    normalized: dict[str, Any] = {}
    for source_key, target_key in (
        ("institutions_id", "institutions_id"),
        ("institution_id", "institutions_id"),
        ("institutions_acronym", "institutions_acronym"),
        ("acronym", "institutions_acronym"),
        ("institutions_name", "institutions_name"),
        ("name", "institutions_name"),
    ):
        raw = value.get(source_key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        if target_key == "institutions_id":
            try:
                normalized[target_key] = int(raw)
            except (TypeError, ValueError):
                continue
        else:
            normalized[target_key] = str(raw).strip()
    return normalized or None
