"""PRMS innovation_development catalogs for schema validation and normalization."""

from __future__ import annotations

from typing import Any

INNOVATION_TYPOLOGIES: tuple[dict[str, Any], ...] = (
    {
        "code": 12,
        "name": "Technological innovation",
        "definition": (
            "Innovations of technical/ material nature, including varieties/ breeds; "
            "crop and livestock management practices; machines; processing technologies; "
            "big data and information systems."
        ),
    },
    {
        "code": 13,
        "name": "Capacity development innovation",
        "definition": (
            "Innovations that strengthen capacity, including farmer, extension or investor "
            "decision-support services; accelerator/ incubator programs; manuals, training "
            "programs and curricula; online courses."
        ),
    },
    {
        "code": 14,
        "name": "Policy, organizational or institutional innovation",
        "definition": (
            "Innovations that create enabling conditions, including policy, legal and regulatory "
            "frameworks; business models; finance mechanisms; partnership models; public/ "
            "private delivery strategies."
        ),
    },
    {
        "code": 15,
        "name": "Other/I’m not sure/This typology does not work for my innovation",
        "definition": "Unknown or the type does not work for the innovation",
    },
)

INNOVATION_READINESS_LEVELS: tuple[dict[str, Any], ...] = (
    {"id": 11, "level": 0, "name": "Idea", "definition": "The innovation is at idea stage."},
    {
        "id": 12,
        "level": 1,
        "name": "Basic Research",
        "definition": (
            "The innovation's basic principles are being researched for their ability "
            "to achieve a specific impact."
        ),
    },
    {
        "id": 13,
        "level": 2,
        "name": "Formulation",
        "definition": "The innovation's key concepts are being formulated or designed.",
    },
    {
        "id": 14,
        "level": 3,
        "name": "Proof of Concept",
        "definition": (
            "The innovation's key concepts have been validated for their ability "
            "to achieve a specific impact."
        ),
    },
    {
        "id": 15,
        "level": 4,
        "name": "Controlled Testing",
        "definition": (
            "The innovation is being tested for its ability to achieve a specific impact "
            "under fully-controlled conditions."
        ),
    },
    {
        "id": 16,
        "level": 5,
        "name": "Model/Early Prototype",
        "definition": (
            "The innovation is validated for its ability to achieve a specific impact "
            "under fully controlled conditions."
        ),
    },
    {
        "id": 17,
        "level": 6,
        "name": "Semi-Controlled Testing",
        "definition": (
            "The innovation is being tested for its ability to achieve a specific impact "
            "under semi-controlled conditions."
        ),
    },
    {
        "id": 18,
        "level": 7,
        "name": "Prototype",
        "definition": (
            "The innovation is validated for its ability to achieve a specific impact "
            "under semi-controlled conditions."
        ),
    },
    {
        "id": 19,
        "level": 8,
        "name": "Uncontrolled Testing",
        "definition": (
            "The innovation is being tested for its ability to achieve a specific impact "
            "under uncontrolled conditions."
        ),
    },
    {
        "id": 20,
        "level": 9,
        "name": "Proven Innovation",
        "definition": (
            "The innovation is validated for its ability to achieve a specific impact "
            "under uncontrolled conditions."
        ),
    },
)

_TYPOLOGY_BY_CODE = {item["code"]: item for item in INNOVATION_TYPOLOGIES}
_TYPOLOGY_BY_NAME = {item["name"].lower(): item for item in INNOVATION_TYPOLOGIES}
_READINESS_BY_ID = {item["id"]: item for item in INNOVATION_READINESS_LEVELS}
_READINESS_BY_NAME = {item["name"].lower(): item for item in INNOVATION_READINESS_LEVELS}
_READINESS_BY_LEVEL = {item["level"]: item for item in INNOVATION_READINESS_LEVELS}


def resolve_innovation_typology(
    *,
    code: int | str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    if code is not None:
        try:
            matched = _TYPOLOGY_BY_CODE.get(int(code))
            if matched:
                return {"code": matched["code"], "name": matched["name"]}
        except (TypeError, ValueError):
            pass

    if isinstance(name, str) and name.strip():
        matched = _TYPOLOGY_BY_NAME.get(name.strip().lower())
        if matched:
            return {"code": matched["code"], "name": matched["name"]}

    return None


def resolve_innovation_readiness_level(
    *,
    item_id: int | str | None = None,
    name: str | None = None,
    level: int | str | None = None,
) -> dict[str, Any] | None:
    if level is not None:
        try:
            matched = _READINESS_BY_LEVEL.get(int(level))
            if matched:
                return {"id": matched["id"], "name": matched["name"]}
        except (TypeError, ValueError):
            pass

    if item_id is not None:
        try:
            matched = _READINESS_BY_ID.get(int(item_id))
            if matched:
                return {"id": matched["id"], "name": matched["name"]}
        except (TypeError, ValueError):
            pass

    if isinstance(name, str) and name.strip():
        matched = _READINESS_BY_NAME.get(name.strip().lower())
        if matched:
            return {"id": matched["id"], "name": matched["name"]}

    return None


def normalize_innovation_typology_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return resolve_innovation_typology(code=value.get("code"), name=value.get("name"))


def normalize_innovation_readiness_level_ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return resolve_innovation_readiness_level(
        item_id=value.get("id"),
        name=value.get("name"),
        level=value.get("level"),
    )
