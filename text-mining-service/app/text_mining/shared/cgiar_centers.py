"""PRMS CGIAR / Alliance center reference catalog for lead_center and contributing_center."""

from __future__ import annotations

from typing import Any

CGIAR_CENTERS: tuple[dict[str, Any], ...] = (
    {
        "institution_id": 5,
        "acronym": "IRRI",
        "name": "International Rice Research Institute",
    },
    {
        "institution_id": 45,
        "acronym": "IITA",
        "name": "International Institute of Tropical Agriculture",
    },
    {
        "institution_id": 46,
        "acronym": "CIAT (Alliance)",
        "name": (
            "Alliance of Bioversity and CIAT - Regional Hub "
            "(International Center for Tropical Agriculture / Centro Internacional de Agricultura Tropical)"
        ),
    },
    {
        "institution_id": 49,
        "acronym": "Bioversity (Alliance)",
        "name": "Alliance of Bioversity and CIAT - Headquarter (Bioversity International)",
    },
    {
        "institution_id": 50,
        "acronym": "CIMMYT",
        "name": (
            "International Maize and Wheat Improvement Center / "
            "Centro Internacional de Mejoramiento de Maíz y Trigo"
        ),
    },
    {
        "institution_id": 52,
        "acronym": "AfricaRice",
        "name": "Africa Rice Center",
    },
    {
        "institution_id": 66,
        "acronym": "ILRI",
        "name": "International Livestock Research Institute",
    },
    {
        "institution_id": 67,
        "acronym": "CIP",
        "name": "International Potato Center / Centro Internacional de la Papa",
    },
    {
        "institution_id": 88,
        "acronym": "ICRAF",
        "name": "World Agroforestry Centre",
    },
    {
        "institution_id": 89,
        "acronym": "IFPRI",
        "name": "International Food Policy Research Institute",
    },
    {
        "institution_id": 99,
        "acronym": "WorldFish",
        "name": "WorldFish",
    },
    {
        "institution_id": 115,
        "acronym": "CIFOR",
        "name": "Center for International Forestry Research",
    },
    {
        "institution_id": 172,
        "acronym": "IWMI",
        "name": "International Water Management Institute",
    },
    {
        "institution_id": 221,
        "acronym": "SMO",
        "name": "CGIAR System Organization",
    },
    {
        "institution_id": 1273,
        "acronym": "ICRISAT",
        "name": "International Crops Research Institute for the Semi-Arid Tropics",
    },
    {
        "institution_id": 1279,
        "acronym": "ICARDA",
        "name": "International Center for Agricultural Research in the Dry Areas",
    },
)

_BY_ID = {center["institution_id"]: center for center in CGIAR_CENTERS}
_BY_ACRONYM = {center["acronym"].lower(): center for center in CGIAR_CENTERS}
_BY_NAME = {center["name"].lower(): center for center in CGIAR_CENTERS}


def resolve_cgiar_center(
    *,
    institution_id: int | str | None = None,
    acronym: str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    """Return canonical center dict when id, acronym, or exact name matches the catalog."""
    if institution_id is not None:
        try:
            matched = _BY_ID.get(int(institution_id))
            if matched:
                return dict(matched)
        except (TypeError, ValueError):
            pass

    if isinstance(acronym, str) and acronym.strip():
        matched = _BY_ACRONYM.get(acronym.strip().lower())
        if matched:
            return dict(matched)

    if isinstance(name, str) and name.strip():
        matched = _BY_NAME.get(name.strip().lower())
        if matched:
            return dict(matched)

    return None


def normalize_cgiar_center_ref(value: Any) -> dict[str, Any] | None:
    """Normalize a lead_center / contributing_center item against the CGIAR catalog."""
    if not isinstance(value, dict):
        return None
    return resolve_cgiar_center(
        institution_id=value.get("institution_id"),
        acronym=value.get("acronym"),
        name=value.get("name"),
    )


def format_cgiar_centers_for_prompt() -> str:
    lines = [
        "CGIAR CENTERS REFERENCE DATA - for lead_center and contributing_center only",
        "Use ONLY centers from this list. When sources mention a CGIAR/Alliance center,",
        "return institution_id, acronym, and name exactly as listed below.",
        "Do not invent centers or return partial objects.",
        "",
        "institution_id | acronym | name",
    ]
    for center in CGIAR_CENTERS:
        lines.append(
            f'{center["institution_id"]} | {center["acronym"]} | {center["name"]}'
        )
    return "\n".join(lines)
