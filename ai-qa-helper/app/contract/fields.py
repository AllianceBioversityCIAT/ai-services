"""AI-input fields with prompt criteria in v1.

Field keys are provisional: they must match the ``fieldKey`` values published by the QA
field-config (``is_ai_input``). Confirm with the PO and the published field-config version
before the API integration. A field marked as AI input that is not listed here gets
``unavailableReason = 'no_criteria_for_field'``.

Scales confirmed against the previous helper's ``criteria/assessment-criteria.md``:
Impact Areas 0-2 (sections 1-2), IRL 0-9 (section 3), IUL 0-9 (section 4).
"""

from dataclasses import dataclass
from typing import Literal

FieldKind = Literal["impact_area", "readiness_level"]


@dataclass(frozen=True)
class FieldSpec:
    kind: FieldKind
    min: int
    max: int


IMPACT_AREA = FieldSpec(kind="impact_area", min=0, max=2)
LEVEL = FieldSpec(kind="readiness_level", min=0, max=9)

AI_FIELDS: dict[str, FieldSpec] = {
    "impact_area_gender": IMPACT_AREA,
    "impact_area_climate": IMPACT_AREA,
    "impact_area_nutrition": IMPACT_AREA,
    "impact_area_environment": IMPACT_AREA,
    "impact_area_poverty": IMPACT_AREA,
    "innovation_readiness_level": LEVEL,
    "innovation_use_level": LEVEL,
}


def field_spec(field_key: str) -> FieldSpec | None:
    return AI_FIELDS.get(field_key)
