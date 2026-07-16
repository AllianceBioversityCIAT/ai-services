"""Compose PRMS extraction and final-validation prompts."""

from __future__ import annotations

import json
from app.llm.prms_mining.models import ExtractedPrmsSource
from app.utils.prompt.prompt_prms import DEFAULT_PROMPT_PRMS, EXTRACTION_PROMPT_VERSION, FINAL_VALIDATION_RULES, VALIDATION_PROMPT_VERSION


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


def build_extraction_prompt(
    *,
    excerpts: str,
    reference_section: str,
    extraction_rules: str | None = None,
) -> str:
    rules = extraction_rules if extraction_rules is not None else DEFAULT_PROMPT_PRMS
    return f"""{"=" * 80}
COMBINED SOURCE EXCERPTS:
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
    supporting_excerpts: str,
) -> str:
    candidate_json = json.dumps(candidates, ensure_ascii=False, indent=2)
    return f"""{FINAL_VALIDATION_RULES}

{"=" * 80}
CANDIDATE RESULTS JSON:
{"=" * 80}
{candidate_json}

{"=" * 80}
SUPPORTING SOURCE EXCERPTS:
{"=" * 80}
{supporting_excerpts}
"""


def prompt_versions() -> dict[str, str]:
    return {
        "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
        "validation_prompt_version": VALIDATION_PROMPT_VERSION,
    }
