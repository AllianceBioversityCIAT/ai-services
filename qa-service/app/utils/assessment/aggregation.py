"""
Traffic light aggregation for W3/Bilateral result assessment (P2-3150).

Implements the "Traffic light at submission" rule from the QA criteria document:

    RED    - at least one CORE FIELD is flagged
    AMBER  - one or more non-core fields are flagged (and no core field flag)
    GREEN  - no flag on any field (US AC2: "the result meets the quality criteria")

The criteria document states the rule at submission level, over field flags.
AC2 asks for the overall verdict to be derived from the section verdicts. The two
are equivalent when sections use the same rule, and `assert_rule_equivalence`
below checks that property rather than assuming it.

Outcomes that are NOT flags and never darken a verdict:
    NOT_EVALUATED  - nothing to assess (confidential evidence; Capacity Sharing
                     evidence when no impact area scores 2)
    NOT_VERIFIABLE - needs a data source we do not have (predatory journal lists,
                     WoS indexing). Never guessed: those criteria are core, so a
                     false positive would produce a false RED.
"""

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from app.utils.assessment.criteria_catalog import Section, CATALOG_BY_ID


class Verdict(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    NOT_EVALUATED = "not_evaluated"


class Outcome(str, Enum):
    PASSED = "passed"
    FLAGGED = "flagged"
    NOT_EVALUATED = "not_evaluated"
    NOT_VERIFIABLE = "not_verifiable"


# Only this one darkens a verdict.
FLAGGING_OUTCOMES = {Outcome.FLAGGED}


@dataclass
class Finding:
    """The result of evaluating one criterion against one submitted result."""
    criterion_id: str
    outcome: Outcome
    comment: str = ""
    # Resolved at evaluation time. Defaults to the catalog value; overridden for
    # conditional-core criteria (Capacity Sharing evidence when IA score = 2).
    core: Optional[bool] = None
    evidence_url: Optional[str] = None

    def __post_init__(self):
        if self.criterion_id not in CATALOG_BY_ID:
            raise KeyError(f"Unknown criterion id: {self.criterion_id}")
        if self.core is None:
            self.core = CATALOG_BY_ID[self.criterion_id].core

    @property
    def section(self) -> Section:
        return CATALOG_BY_ID[self.criterion_id].section

    @property
    def mds_field(self) -> str:
        return CATALOG_BY_ID[self.criterion_id].mds_field

    @property
    def is_flag(self) -> bool:
        return self.outcome in FLAGGING_OUTCOMES


@dataclass
class SectionResult:
    section: Section
    verdict: Verdict
    findings: List[Finding] = field(default_factory=list)

    @property
    def flags(self) -> List[Finding]:
        return [f for f in self.findings if f.is_flag]


@dataclass
class AssessmentResult:
    overall: Verdict
    sections: List[SectionResult]
    findings: List[Finding]

    @property
    def flags(self) -> List[Finding]:
        return [f for f in self.findings if f.is_flag]


def _verdict_from_flags(flags: List[Finding], has_any_evaluated: bool) -> Verdict:
    """The documented rule, applied to one bucket of findings."""
    if any(f.core for f in flags):
        return Verdict.RED
    if flags:
        return Verdict.AMBER
    if not has_any_evaluated:
        return Verdict.NOT_EVALUATED
    return Verdict.GREEN


def aggregate(findings: List[Finding], sections: List[Section]) -> AssessmentResult:
    """
    Roll findings up to per-section verdicts and one overall verdict.

    `sections` is the ordered list of sections shown to the user for this result
    type, so a section with no applicable criteria still renders as NOT_EVALUATED
    instead of silently disappearing from the review window.
    """
    by_section: Dict[Section, List[Finding]] = {s: [] for s in sections}
    for f in findings:
        by_section.setdefault(f.section, []).append(f)

    section_results = []
    for section in sections:
        bucket = by_section.get(section, [])
        evaluated = [f for f in bucket if f.outcome in (Outcome.PASSED, Outcome.FLAGGED)]
        flags = [f for f in bucket if f.is_flag]
        section_results.append(
            SectionResult(
                section=section,
                verdict=_verdict_from_flags(flags, has_any_evaluated=bool(evaluated)),
                findings=bucket,
            )
        )

    all_flags = [f for f in findings if f.is_flag]
    any_evaluated = any(
        f.outcome in (Outcome.PASSED, Outcome.FLAGGED) for f in findings
    )
    overall = _verdict_from_flags(all_flags, has_any_evaluated=any_evaluated)

    return AssessmentResult(
        overall=overall, sections=section_results, findings=findings
    )


def overall_from_sections(section_results: List[SectionResult]) -> Verdict:
    """
    AC2's formulation: derive the overall verdict from the section verdicts.
    Kept separate so the equivalence with the document's field-level rule is
    testable rather than assumed.
    """
    verdicts = [s.verdict for s in section_results]
    if Verdict.RED in verdicts:
        return Verdict.RED
    if Verdict.AMBER in verdicts:
        return Verdict.AMBER
    if any(v == Verdict.GREEN for v in verdicts):
        return Verdict.GREEN
    return Verdict.NOT_EVALUATED


def assert_rule_equivalence(result: AssessmentResult) -> None:
    """The document derives the overall verdict from field flags; AC2 derives it
    from section verdicts. Guard that they never disagree."""
    from_sections = overall_from_sections(result.sections)
    if from_sections != result.overall:
        raise AssertionError(
            f"Traffic light rule mismatch: fields -> {result.overall}, "
            f"sections -> {from_sections}"
        )
