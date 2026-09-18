"""
Which criteria actually apply to one specific submitted result.

`criteria_catalog.criteria_for()` answers "which criteria exist for this result
type". This module answers the narrower question: of those, which ones can be
evaluated given what the payload actually contains.

Criteria marked OnAbsent.OMIT are dropped when their field did not arrive, so an
optional field the user was never required to fill is never rendered and never
penalised. This runs before both the rules engine and the prompt builders, so the
two can never disagree about what is in scope.
"""

import re
from typing import List

from app.utils.assessment.criteria_catalog import (
    Criterion, OnAbsent, criteria_for, Check, Needs,
)

IRL_CONTEXT_SPECIFIC_FROM = 5


def _field(request, label: str):
    return (request.sections.type_specific.fields or {}).get(label)


def _level_number(value) -> int:
    """'Level 6 — Uptake by users' -> 6. Returns -1 when unparseable."""
    m = re.search(r"\b(\d+)\b", str(value or ""))
    return int(m.group(1)) if m else -1


def _is_present(request, criterion: Criterion) -> bool:
    """Whether the field an OMIT criterion depends on arrived in the payload."""
    cid = criterion.id

    if cid.startswith("generic.impact_area."):
        return bool(request.impact_areas)

    if cid == "generic.toc_link.coherence":
        toc = request.sections.contributors_and_partners.theory_of_change
        if toc is None:
            return False
        return any([toc.result, toc.indicator, toc.contribution, toc.why_reported])

    if cid == "innovuse.usd_spend.coherence":
        return _field(request, "Investment (USD)") is not None

    if cid == "innovdev.evidence.geolocation_irl5":
        return _level_number(_field(request, "Readiness level")) >= IRL_CONTEXT_SPECIFIC_FROM

    return True


def applicable(request, check: Check = None, needs: Needs = None) -> List[Criterion]:
    """Criteria in scope for this result, with OMIT criteria already dropped."""
    out = []
    for c in criteria_for(request.result.type, check=check, needs=needs):
        if c.on_absent == OnAbsent.OMIT and not _is_present(request, c):
            continue
        out.append(c)
    return out


def omitted(request) -> List[Criterion]:
    """Criteria dropped for this result. Useful for logging and debugging."""
    in_scope = {c.id for c in applicable(request)}
    return [c for c in criteria_for(request.result.type) if c.id not in in_scope]
