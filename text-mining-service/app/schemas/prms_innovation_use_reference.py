"""PRMS innovation_use catalogs for schema validation and normalization."""

from __future__ import annotations

from typing import Any

INSTITUTION_TYPE_OTHER_ID = 78

ACTOR_TYPES: tuple[dict[str, Any], ...] = (
    {"id": 1, "name": "Farmers/ (agro)pastoralist/ herders/ fishers"},
    {"id": 2, "name": "Researchers"},
    {"id": 3, "name": "Extension agents"},
    {"id": 4, "name": "Policy actors (public or private)"},
    {"id": 5, "name": "Other"},
)

ORGANIZATION_TYPE_NGO = "NGO"
ORGANIZATION_TYPE_RESEARCH = "Research organizations and universities"
ORGANIZATION_TYPE_OTHER = "Organization (other than financial or research)"
ORGANIZATION_TYPE_GOVERNMENT = "Government"
ORGANIZATION_TYPE_FINANCIAL = "Financial institution"

INSTITUTION_TYPES: tuple[dict[str, Any], ...] = (
    {"id": 39, "name": "NGO International (General)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 40, "name": "NGO International (Farmers)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 42, "name": "NGO Regional (General)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 43, "name": "NGO Regional (Farmers)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 45, "name": "NGO National (General)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 46, "name": "NGO National (Farmers)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 48, "name": "NGO Local (General)", "organization_type": ORGANIZATION_TYPE_NGO},
    {"id": 49, "name": "NGO Local (Farmers)", "organization_type": ORGANIZATION_TYPE_NGO},
    {
        "id": 52,
        "name": "Research organizations and universities International (General)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 53,
        "name": "Research organizations and universities International (Universities)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 54,
        "name": "Research organizations and universities International (CGIAR)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 56,
        "name": "Research organizations and universities Regional (NA)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 57,
        "name": "Research organizations and universities Regional (Universities)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 59,
        "name": "Research organizations and universities National (NARS)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 60,
        "name": "Research organizations and universities National (Universities)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 62,
        "name": "Research organizations and universities Local (NA)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 63,
        "name": "Research organizations and universities Local (Universities)",
        "organization_type": ORGANIZATION_TYPE_RESEARCH,
    },
    {
        "id": 65,
        "name": "Organization (other than financial or research) International",
        "organization_type": ORGANIZATION_TYPE_OTHER,
    },
    {
        "id": 66,
        "name": "Organization (other than financial or research) Regional",
        "organization_type": ORGANIZATION_TYPE_OTHER,
    },
    {"id": 68, "name": "Government (National)", "organization_type": ORGANIZATION_TYPE_GOVERNMENT},
    {"id": 69, "name": "Government (Subnational)", "organization_type": ORGANIZATION_TYPE_GOVERNMENT},
    {"id": 71, "name": "Financial Institution International", "organization_type": ORGANIZATION_TYPE_FINANCIAL},
    {"id": 72, "name": "Financial Institution Regional", "organization_type": ORGANIZATION_TYPE_FINANCIAL},
    {"id": 73, "name": "Financial Institution National", "organization_type": ORGANIZATION_TYPE_FINANCIAL},
    {"id": 74, "name": "Financial Institution Local", "organization_type": ORGANIZATION_TYPE_FINANCIAL},
    {"id": 75, "name": "Private company (other than financial)"},
    {"id": 76, "name": "Public-Private Partnership"},
    {"id": 77, "name": "Foundation"},
    {"id": 78, "name": "Other"},
)

_ACTOR_TYPE_BY_ID = {item["id"]: item for item in ACTOR_TYPES}
_ACTOR_TYPE_BY_NAME = {item["name"].lower(): item for item in ACTOR_TYPES}
_INSTITUTION_TYPE_BY_ID = {item["id"]: item for item in INSTITUTION_TYPES}
_INSTITUTION_TYPE_BY_NAME = {item["name"].lower(): item for item in INSTITUTION_TYPES}


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


def resolve_actor_type(*, item_id: int | str | None = None, name: str | None = None) -> dict[str, Any] | None:
    resolved = _resolve_id_name(
        catalog_by_id=_ACTOR_TYPE_BY_ID,
        catalog_by_name=_ACTOR_TYPE_BY_NAME,
        item_id=item_id,
        name=name,
    )
    if resolved:
        return {"actor_type_id": resolved["id"], "actor_type_name": resolved["name"]}
    return None


def resolve_institution_type(*, item_id: int | str | None = None, name: str | None = None) -> dict[str, Any] | None:
    resolved = _resolve_id_name(
        catalog_by_id=_INSTITUTION_TYPE_BY_ID,
        catalog_by_name=_INSTITUTION_TYPE_BY_NAME,
        item_id=item_id,
        name=name,
    )
    if not resolved:
        return None

    normalized: dict[str, Any] = {
        "institution_types_id": resolved["id"],
        "institution_types_name": resolved["name"],
    }
    organization_type = resolved.get("organization_type")
    if organization_type:
        normalized["organization_type"] = organization_type
    return normalized


def normalize_innovation_use_actor_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    normalized: dict[str, Any] = {}
    resolved_type = resolve_actor_type(
        item_id=value.get("actor_type_id"),
        name=value.get("actor_type_name"),
    )
    if resolved_type:
        normalized.update(resolved_type)
    else:
        actor_type_id = value.get("actor_type_id")
        actor_type_name = value.get("actor_type_name")
        if actor_type_id is not None:
            try:
                normalized["actor_type_id"] = int(actor_type_id)
            except (TypeError, ValueError):
                pass
        if isinstance(actor_type_name, str) and actor_type_name.strip():
            normalized["actor_type_name"] = actor_type_name.strip()

    if not normalized.get("actor_type_id") and not normalized.get("actor_type_name"):
        return None

    for field in (
        "other_actor_type",
        "how_many",
        "women",
        "women_youth",
        "men",
        "men_youth",
    ):
        if field not in value or value[field] is None:
            continue
        if field == "other_actor_type":
            if isinstance(value[field], str) and value[field].strip():
                normalized[field] = value[field].strip()
            continue
        try:
            normalized[field] = int(value[field])
        except (TypeError, ValueError):
            if isinstance(value[field], str) and value[field].strip():
                normalized[field] = value[field].strip()

    if "sex_and_age_disaggregation" in value and value["sex_and_age_disaggregation"] is not None:
        normalized["sex_and_age_disaggregation"] = bool(value["sex_and_age_disaggregation"])

    return normalized


def normalize_innovation_use_organization_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    resolved = resolve_institution_type(
        item_id=value.get("institution_types_id"),
        name=value.get("institution_types_name"),
    )

    normalized: dict[str, Any] = {}
    if resolved:
        normalized.update(resolved)
    else:
        raw_id = value.get("institution_types_id")
        raw_name = value.get("institution_types_name")
        if raw_id is not None:
            try:
                normalized["institution_types_id"] = int(raw_id)
            except (TypeError, ValueError):
                pass
        if isinstance(raw_name, str) and raw_name.strip():
            normalized["institution_types_name"] = raw_name.strip()
        organization_type = value.get("organization_type")
        if isinstance(organization_type, str) and organization_type.strip():
            normalized["organization_type"] = organization_type.strip()

    if not normalized.get("institution_types_id") and not normalized.get("institution_types_name"):
        return None

    institution_types_id = normalized.get("institution_types_id")
    if institution_types_id is not None:
        catalog_entry = _INSTITUTION_TYPE_BY_ID.get(int(institution_types_id))
        if catalog_entry and not catalog_entry.get("organization_type"):
            normalized.pop("organization_type", None)

    other_institution = value.get("other_institution")
    if isinstance(other_institution, str) and other_institution.strip():
        normalized["other_institution"] = other_institution.strip()

    if value.get("how_many") is not None:
        try:
            normalized["how_many"] = int(value["how_many"])
        except (TypeError, ValueError):
            if isinstance(value["how_many"], str) and value["how_many"].strip():
                normalized["how_many"] = value["how_many"].strip()

    return normalized


def normalize_innovation_use_measure_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    unit = value.get("unit_of_measure")
    if not isinstance(unit, str) or not unit.strip():
        return None
    normalized: dict[str, Any] = {"unit_of_measure": unit.strip()}
    quantity = value.get("quantity")
    if quantity is not None:
        if isinstance(quantity, str) and quantity.strip():
            normalized["quantity"] = quantity.strip()
        elif isinstance(quantity, (int, float)):
            normalized["quantity"] = str(int(quantity)) if float(quantity).is_integer() else str(quantity)
    return normalized
