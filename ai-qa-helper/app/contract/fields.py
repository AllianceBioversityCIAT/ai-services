"""AI-input fields with prompt criteria in v1.

Field keys are the Reporting QA catalog keys (``fields[].key`` in onecgiar_qa
``server/src/admin-config/field-config/fixtures/reporting-qa-catalog-2026.json``, catalog 2026.30),
the same keys the snapshot ``values`` and the field-config ``is_ai_input`` flag use. A field marked
as AI input that is not listed here gets ``unavailableReason = 'no_criteria_for_field'``.

Indicative fields: ``general.result_type`` (single_select, control list ``result_types``, ids of
onecgiar_pr ``ResultTypeEnum``) and ``innovation_use.current_use.{actors,organizations,measures}``
(lists), keys from onecgiar_pr ``onecgiar-pr-server/src/api/qa-catalog/definitions/sections/``
(``general-information.ts``, ``innovation-use.ts``), checked on 2026-11-17.

Scales confirmed against the previous helper's ``criteria/assessment-criteria.md``:
Impact Areas 0-2 (sections 1-2), IRL 0-9 (section 3), IUL 0-9 (section 4).

``evidence_flag`` is the boolean subfield of ``evidence.items`` that ties an evidence link to the
field. The catalog shows the Impact Area flags only when the tag is Principal (control-list id 3).
"""

from dataclasses import dataclass
from typing import Literal

from app.contract.messages import ValueKind

FieldKind = Literal["impact_area", "readiness_level", "result_category", "use_numbers"]


@dataclass(frozen=True)
class FieldSpec:
    kind: FieldKind
    min: int
    max: int
    control_list: str = ""
    """Catalog control list of the reported value (single_select)."""
    evidence_flag: str = ""
    """``evidence.items`` subfield that marks a link as evidence for this field."""
    requires_verified_quote: bool = False
    """Show the suggestion only with a quote found verbatim in the evidence; otherwise it is stored as
    unavailable (``no_supporting_quote``). The assessor UI shows IRL/IUL as "Evidence explicitly
    supports level X" next to the quote, so the quote must exist."""
    covers: tuple[str, ...] = ()
    """Catalog fields the suggestion covers besides its own key (``coversFieldKeys``)."""

    @property
    def indicative(self) -> bool:
        """No green/amber/red and no quote: the value is shown for reference (signal ``indicative``)."""
        return self.kind in ("result_category", "use_numbers")

    @property
    def value_kind(self) -> ValueKind:
        return {"result_category": "category", "use_numbers": "use_numbers"}.get(self.kind, "level")


USE_NUMBERS_PREFIX = "innovation_use.current_use"
USE_NUMBERS_KEY = f"{USE_NUMBERS_PREFIX}.actors"
"""Catalog 2026.30 has no single "use numbers" field: three lists (actors, organizations, measures).
The suggestion is stored under the actors key and covers the three."""


def _ia(flag: str) -> FieldSpec:
    return FieldSpec("impact_area", 0, 2, "tag_levels", flag)


AI_FIELDS: dict[str, FieldSpec] = {
    "general.gender_tag": _ia("gender_related"),
    "general.climate_tag": _ia("climate_related"),
    "general.nutrition_tag": _ia("nutrition_related"),
    "general.environment_tag": _ia("environment_related"),
    "general.poverty_tag": _ia("poverty_related"),
    "innovation_dev.readiness_level": FieldSpec(
        "readiness_level", 0, 9, "readiness_levels", "innovation_readiness_related", requires_verified_quote=True
    ),
    "innovation_use.use_level.innovation_use_level": FieldSpec(
        "readiness_level", 0, 9, "innovation_use_levels", "innovation_use_related", requires_verified_quote=True
    ),
    # Indicative fields (December 2026 batch, scope change approved by the QA coordinator on 2026-11-17):
    # previous helper's prompts 06 and 09 verbatim (promptVersion v1-1.0.0).
    "general.result_type": FieldSpec("result_category", 0, 0, "result_types"),
    USE_NUMBERS_KEY: FieldSpec(
        "use_numbers", 0, 0, "", "innovation_use_related",
        covers=(f"{USE_NUMBERS_PREFIX}.organizations", f"{USE_NUMBERS_PREFIX}.measures"),
    ),
}


def field_spec(field_key: str) -> FieldSpec | None:
    return AI_FIELDS.get(field_key)
