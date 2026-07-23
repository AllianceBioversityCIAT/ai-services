"""PRMS prompt composition entrypoint.

Modular sections live under app/utils/prompt/prms/. Runtime extraction uses one
composed prompt covering all six supported result types.
"""

from app.utils.prompt.prms import (
    CAPACITY_SHARING_SECTION,
    COMMON_MDS_FIELDS,
    COMMON_RULES,
    FINAL_VALIDATION_RULES,
    INNOVATION_DEVELOPMENT_SECTION,
    INNOVATION_USE_SECTION,
    OTHER_OUTPUT_SECTION,
    OTHER_OUTCOME_SECTION,
    OUTPUT_SCHEMA_FRAGMENT,
    POLICY_CHANGE_SECTION,
    PRMS_INDICATOR_CONTEXT,
)


def compose_extraction_prompt_body() -> str:
    return "\n".join(
        [
            COMMON_RULES.strip(),
            PRMS_INDICATOR_CONTEXT.strip(),
            COMMON_MDS_FIELDS.strip(),
            CAPACITY_SHARING_SECTION.strip(),
            POLICY_CHANGE_SECTION.strip(),
            INNOVATION_DEVELOPMENT_SECTION.strip(),
            INNOVATION_USE_SECTION.strip(),
            OTHER_OUTPUT_SECTION.strip(),
            OTHER_OUTCOME_SECTION.strip(),
            OUTPUT_SCHEMA_FRAGMENT.strip(),
        ]
    )


DEFAULT_PROMPT_PRMS = compose_extraction_prompt_body()

__all__ = [
    "DEFAULT_PROMPT_PRMS",
    "FINAL_VALIDATION_RULES",
    "compose_extraction_prompt_body",
]
