"""Compose PRMS extraction and final-validation prompts."""

from __future__ import annotations

import json
from app.text_mining.prms_mining.models import ExtractedPrmsSource
from app.utils.prompt.prompt_prms import DEFAULT_PROMPT_PRMS, FINAL_VALIDATION_RULES


def format_source_block(source: ExtractedPrmsSource) -> str:
    evidence_role = (
        "formal_evidence_eligible"
        if source.eligible_as_formal_evidence
        else "context_only_not_formal_evidence"
    )
    name_attr = f' name="{source.file_name}"' if source.file_name else ""
    return (
        f'<source id="{source.source_id}" type="{source.source_type.value}" '
        f'role="{evidence_role}"{name_attr}>\n'
        f"{source.content}\n"
        f"</source>"
    )


def build_corpus_text(sources: list[ExtractedPrmsSource]) -> str:
    return "\n\n".join(format_source_block(s) for s in sources)


def format_prms_geo_reference_for_prompt(reference_data: dict) -> str:
    """PRMS-specific wrapper — geo_focus field names differ from STAR geoscope."""
    regions_text = "\n".join(reference_data.get("regions", []))
    countries_text = "\n".join(reference_data.get("countries", []))

    return (
        "GEOGRAPHIC REFERENCE DATA - for geo_focus fields only\n"
        "Use the codes below EXCLUSIVELY to fill geo_focus.regions (um49code) and\n"
        "geo_focus.countries (iso_alpha_2 for National; iso_alpha_2 + subnational_areas for Sub-national).\n"
        "Return codes only — never location names.\n"
        "This is a lookup table, NOT document content to be analyzed.\n\n"
        "REGIONS (UN M49 / um49code):\n"
        f"{regions_text}\n\n"
        "COUNTRIES (ISO Alpha-2 / iso_alpha_2):\n"
        f"{countries_text}"
    )


def build_extraction_prompt(
    *,
    excerpts: str,
    reference_section: str,
    extraction_rules: str | None = None,
) -> str:
    rules = extraction_rules if extraction_rules is not None else DEFAULT_PROMPT_PRMS
    return f"""{"=" * 80}
SOURCE EXCERPTS (single source — extract results supported by this source only):
{"=" * 80}
{excerpts}

{"=" * 80}
{reference_section}
{"=" * 80}

{rules}
"""


def build_final_validation_prompt(
    *,
    candidates: dict,
    supporting_excerpts: str = "",
) -> str:
    """
    Compose the final validation prompt.

    ``supporting_excerpts`` holds only the short source window around each
    candidate's verified quote (not the full corpus), keyed by candidate_id.
    """
    candidate_json = json.dumps(candidates, ensure_ascii=False, indent=2)
    excerpts_text = supporting_excerpts.strip() or "(no supporting excerpts available)"
    return f"""{FINAL_VALIDATION_RULES}

{"=" * 80}
CANDIDATE RESULTS JSON:
{"=" * 80}
{candidate_json}

{"=" * 80}
SUPPORTING SOURCE EXCERPTS (one per candidate_id; source text around the verified supporting_quote):
{"=" * 80}
{excerpts_text}
"""
