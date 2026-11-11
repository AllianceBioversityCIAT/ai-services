"""AI-input fields with prompt criteria in v1.

Field keys are the Reporting QA catalog keys (``fields[].key`` in onecgiar_qa
``server/src/admin-config/field-config/fixtures/reporting-qa-catalog-2026.json``, catalog 2026.30),
the same keys the snapshot ``values`` and the field-config ``is_ai_input`` flag use. A field marked
as AI input that is not listed here gets ``unavailableReason = 'no_criteria_for_field'``.

Scales confirmed against the previous helper's ``criteria/assessment-criteria.md``:
Impact Areas 0-2 (sections 1-2), IRL 0-9 (section 3), IUL 0-9 (section 4).

``evidence_flag`` is the boolean subfield of ``evidence.items`` that ties an evidence link to the
field. The catalog shows the Impact Area flags only when the tag is Principal (control-list id 3).
"""

from dataclasses import dataclass
from typing import Literal

FieldKind = Literal["impact_area", "readiness_level"]


@dataclass(frozen=True)
class FieldSpec:
    kind: FieldKind
    min: int
    max: int
    control_list: str = ""
    """Catalog control list of the reported value (single_select)."""
    evidence_flag: str = ""
    """``evidence.items`` subfield that marks a link as evidence for this field."""


def _ia(flag: str) -> FieldSpec:
    return FieldSpec("impact_area", 0, 2, "tag_levels", flag)


AI_FIELDS: dict[str, FieldSpec] = {
    "general.gender_tag": _ia("gender_related"),
    "general.climate_tag": _ia("climate_related"),
    "general.nutrition_tag": _ia("nutrition_related"),
    "general.environment_tag": _ia("environment_related"),
    "general.poverty_tag": _ia("poverty_related"),
    "innovation_dev.readiness_level": FieldSpec(
        "readiness_level", 0, 9, "readiness_levels", "innovation_readiness_related"
    ),
    "innovation_use.use_level.innovation_use_level": FieldSpec(
        "readiness_level", 0, 9, "innovation_use_levels", "innovation_use_related"
    ),
}


def field_spec(field_key: str) -> FieldSpec | None:
    return AI_FIELDS.get(field_key)
