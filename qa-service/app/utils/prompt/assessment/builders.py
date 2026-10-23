"""
Prompt builders for the two assessment calls.

The split is by INPUT, not by output section: call A gets everything that needs
the scraped evidence text, call B everything answerable from the payload alone.
That keeps the large evidence context out of one of the two calls.

Both prompts render the criteria straight from the catalog, so the criteria
document stays the single source of truth and the prompt cannot drift from it.
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from app.utils.assessment.criteria_catalog import Criterion
from app.utils.assessment import vocabularies as vocab

@dataclass(frozen=True)
class PromptParts:
    """Split so the stable half can carry a cache breakpoint.

    `system` holds the role and the criteria - identical for every result of the
    same type - and `user` holds this result's data. Keeping the volatile half
    out of the prefix is what makes prompt caching actually hit.
    """
    system: str
    user: str


SHARED_ROLE = """\
You are a quality assessor for CGIAR result reporting. You review W3/Bilateral \
results the way a human QA assessor would, applying the criteria you are given \
and nothing else.

How to judge:
- Assess ONLY the criteria listed below. Do not raise issues outside that list, \
however reasonable they seem. The list is the full scope of this review.
- Report exactly one finding per criterion, using its id.
- Base every judgement on the information provided. Never assume facts that are \
not in the metadata or the evidence.
- When the evidence for a flag is ambiguous, pass the criterion. A false flag \
sends a reporting user to fix something that was not broken, which costs more \
than a missed nuance.

How to write comments:
- Write for the person who reported the result, not for a QA specialist.
- Plain language. No jargon, no criterion ids, no scores, no internal terminology.
- When you flag something, say what is missing or weak and what would fix it.
- When a criterion passes, say briefly what the result does well.
"""


def render_criteria(criteria: List[Criterion]) -> str:
    lines = []
    for c in criteria:
        lines.append(f"### {c.id}")
        lines.append(f"Field: {c.mds_field}")
        lines.append(f"What to check: {c.criterion}")
        lines.append(f"Flag when: {c.flag_when}")
        lines.append("")
    return "\n".join(lines)


def _result_context(request) -> str:
    gi = request.sections.general_information
    cp = request.sections.contributors_and_partners
    geo = request.sections.geographic_location
    ts = request.sections.type_specific

    payload = {
        "result_type": request.result.type,
        "reporting_center": request.result.reporting_center,
        "primary_science_program": request.result.primary_science_program,
        "general_information": {
            "title": gi.title,
            "description": gi.description,
            "result_level": gi.result_level,
            "lead_contact_person": gi.lead_contact_person,
        },
        "contributors_and_partners": cp.model_dump(),
        "geographic_location": geo.model_dump(),
        "type_specific_fields": ts.fields,
    }
    if request.impact_areas:
        payload["impact_areas"] = [ia.model_dump() for ia in request.impact_areas]
    return json.dumps(payload, indent=2, ensure_ascii=False)


SUGGESTION_GUIDANCE = """\
## Replacement title and description

When you flag something about the title or the description, also write a
replacement the user can apply with one click.

- Write the finished text, not advice about it. "Name the crop and the country"
  is a comment; the suggestion is the rewritten title itself.
- Use ONLY what is in the result above. Do not invent a figure, a place, a
  partner, a date or an outcome that is not already there. The user may apply
  your text without checking it, so anything you add becomes a false claim in
  their report.
- Where the metadata is too thin to write a good replacement, leave that field
  null rather than padding it with invention. A missing suggestion is fine; a
  fabricated one is not.
- Address what you flagged. If the finding is that the title names the activity
  instead of the result, the replacement must name the result.
- Keep the author's meaning. You are rewriting their result, not reporting a
  different one.
- Plain text only: one line for the title, 30 words or fewer; 300 words or fewer
  for the description, paragraphs separated by a newline. No markdown, no HTML,
  no surrounding quotes.
"""


def build_metadata_prompt(request, criteria: List[Criterion],
                          known_issues: Optional[List[str]] = None) -> PromptParts:
    """Call B: everything answerable without reading the evidence documents.

    `known_issues` carries the General Information findings the deterministic
    rules already raised - word counts, future tense. The model does not assess
    those, but a replacement it writes has to satisfy them too, so it needs to
    see them.
    """
    labels_note = ""
    no_criteria = vocab.LABELS_WITHOUT_CRITERIA.get((request.result.type or "").lower(), ())
    if no_criteria:
        labels_note = (
            "\nSome fields are shown for context only and have no criterion of their "
            f"own - do not raise findings about them: {', '.join(no_criteria)}.\n"
        )

    system = f"""{SHARED_ROLE}
## Criteria to assess

{render_criteria(criteria)}
{SUGGESTION_GUIDANCE}"""

    already = ""
    if known_issues:
        already = (
            "\n## Already found by the automated checks\n\n"
            "You are not asked to judge these - they are settled. Any replacement "
            "you write must satisfy them as well:\n"
            + "".join(f"- {i}\n" for i in known_issues)
        )

    user = f"""## The result

This is what the user reported. Treat it as the factual record.
{labels_note}
```json
{_result_context(request)}
```
{already}
## Your task

Call `report_metadata_assessment` with exactly one finding per criterion you were \
given ({len(criteria)} findings), in the same order, plus a replacement title or \
description if either needs one.
"""
    return PromptParts(system=system, user=user)


def build_evidence_prompt(request, criteria: List[Criterion], scraped: List[dict]) -> PromptParts:
    """Call A: everything that requires reading the evidence documents."""
    gi = request.sections.general_information

    blocks = []
    for item in scraped:
        i = item["index"]
        ev = request.sections.evidence[i]
        header = [
            f"### Evidence item {i}",
            f"User's description: {ev.description or '(none)'}",
            f"Source: {ev.source or 'unknown'} | Tags: {', '.join(ev.tags) or '(none)'}",
            f"URL: {ev.link or '(no link — repository item)'}",
        ]
        if item.get("status") != "ok":
            header.append(
                f"NOT RETRIEVED ({item.get('status')}): {item.get('error', 'unavailable')}. "
                "Do not judge this item; it is handled separately."
            )
            blocks.append("\n".join(header))
            continue
        header.append(f"Document title: {item.get('title') or '(untitled)'}")
        header.append("")
        header.append("Extracted content:")
        header.append(item.get("content") or "(empty)")
        blocks.append("\n".join(header))

    evidence_block = ("\n\n" + "-" * 70 + "\n\n").join(blocks) if blocks else \
        "No evidence content could be retrieved."

    system = f"""{SHARED_ROLE}
## Criteria to assess

{render_criteria(criteria)}"""

    user = f"""## The result being evidenced

Result type: {request.result.type}
Title: {gi.title}
Description: {gi.description}

Type-specific fields:
```json
{json.dumps(request.sections.type_specific.fields, indent=2, ensure_ascii=False)}
```

## Evidence documents

The text below was extracted automatically from the links the user attached. It \
may be partial or noisy — judge what is there, and do not penalise a result for \
extraction artefacts.

{evidence_block}

## Your task

Call `report_evidence_assessment` with:
1. Exactly one finding per criterion above ({len(criteria)} findings), in order.
2. One verdict per evidence item that WAS retrieved. Judge whether the document \
is genuine, whether it is what its description claims, and whether it actually \
supports this result. Items marked NOT RETRIEVED must be omitted.
"""
    return PromptParts(system=system, user=user)
