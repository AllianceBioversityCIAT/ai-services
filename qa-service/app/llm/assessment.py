"""
Orchestration for the W3/Bilateral AI quality check (P2-3150).

Shape of a run:

    [code]  deterministic rules on the payload          ~0 ms
       |
       +-- in parallel ------------------------------+
       |                                             |
    [net]  scrape evidence, bounded              [llm] metadata call
       |   (parallel, per-URL timeout)                |  (no evidence text)
       +---------------------+-----------------------+
                             |
                        [llm] evidence call
                             |
    [code]  evidence rules -> aggregate -> score -> response

There is no LLM supervisor and no LLM judge: routing is fixed, and the traffic
light is a pure function of the flags, per the QA criteria document. Every stage
degrades instead of failing - a run that loses a stage reports `partial` rather
than returning nothing, because AC6 says a failed check must never block a
submission.
"""

import time
import json
import asyncio
from typing import List, Dict, Tuple, Optional
from app.utils.logger.logger_util import get_logger
from app.utils.assessment.selection import applicable
from app.llm.bedrock_tools import invoke_with_tool, MODEL_ID
from app.web_scraping.evidence_scraper import EvidenceEnhancer
from app.utils.assessment.scoring import score as compute_score
from app.utils.interactions.interaction_client import interaction_client
from app.utils.prompt.assessment.tool_schemas import metadata_tool, evidence_tool
from app.utils.assessment.rules_engine import run_metadata_rules, run_evidence_rules
from app.utils.assessment.criteria_catalog import Section, Check, Needs, sections_for
from app.utils.prompt.assessment.builders import build_metadata_prompt, build_evidence_prompt
from app.utils.assessment.aggregation import Finding, Outcome, Verdict, aggregate, assert_rule_equivalence

from app.api.models import (
    QualityAssessmentRequest, QualityAssessmentResponse, OverallVerdict,
    SectionVerdict, SectionVerdicts, EvidenceVerdict, Verdict as ApiVerdict,
    CheckStatus, Coverage,
)


logger = get_logger()


class AssessmentUnavailable(Exception):
    """The model never produced an assessment.

    Raised when every LLM call failed, so nothing substantive was evaluated. The
    endpoint turns this into an error rather than a 200 carrying an empty verdict:
    a caller should not have to read a status field to discover the check did not
    run. Partial failures - one call down, or evidence that could not be fetched -
    still return normally, with the gaps reported in `coverage`.
    """


SCRAPE_CONCURRENCY = 6
OVERHEAD_RESERVE_S = 3.0

# Only two things happen in sequence: scraping (which overlaps with the metadata
# call) and then the evidence call. So scraping can take the larger share without
# costing the metadata review anything.
#
# Reading the evidence is the whole point of this endpoint - a CGSpace PDF can
# take tens of seconds to download and extract, and cutting it short produces a
# grey item that helps nobody. The budget is generous by design; Budget.slice()
# clamps every request to whatever is actually left.
SCRAPE_BUDGET_SHARE = 0.65
PER_URL_BUDGET_SHARE = 0.85       # items scrape concurrently, so a single slow
                                  # source may use nearly the whole scrape budget
LLM_BUDGET_SHARE = 0.45           # each call, of the total
MAX_EVIDENCE_CONTENT_CHARS = 12_000   # enough to judge relevance; far below the
                                      # 40k the rewriting endpoint uses


class Budget:
    def __init__(self, total_seconds: float):
        self.total = total_seconds
        self.started = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def remaining(self) -> float:
        return max(0.0, self.total - OVERHEAD_RESERVE_S - self.elapsed)

    def slice(self, share: float) -> float:
        return max(1.0, min(self.remaining, self.total * share))


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #

async def _scrape_evidence(request, budget: Budget) -> Tuple[List[dict], Dict[int, dict]]:
    """Scrape the evaluable evidence items. Returns (for the prompt, by index)."""
    evaluable = [(i, ev) for i, ev in enumerate(request.sections.evidence) if ev.is_evaluable]
    if not evaluable:
        logger.info("ℹ️ No evaluable evidence items")
        return [], {}

    total_budget = budget.slice(SCRAPE_BUDGET_SHARE)
    per_url = max(10.0, total_budget * PER_URL_BUDGET_SHARE)
    logger.info(
        f"📚 Scraping {len(evaluable)} evidence item(s), "
        f"budget {total_budget:.1f}s (per URL {per_url:.1f}s)"
    )

    # The batch deadline is handled inside the scraper so that sources which
    # finished in time are kept. Wrapping the whole batch in wait_for discarded
    # completed results along with the stragglers.
    enhancer = EvidenceEnhancer()
    raw = await enhancer.extract_evidence_content(
        [ev.link for _, ev in evaluable],
        max_content_length=MAX_EVIDENCE_CONTENT_CHARS,
        concurrency=SCRAPE_CONCURRENCY,
        per_url_timeout=per_url,
        batch_timeout=total_budget,
    )

    by_index: Dict[int, dict] = {}
    for position, (index, _) in enumerate(evaluable):
        item = raw[position] if position < len(raw) else None
        if item is None:
            by_index[index] = {
                "index": index, "status": "timeout", "determined": False,
                "error": "The link could not be checked within the time available.",
            }
            continue
        kind = item.get("type")
        if kind in ("error", "timeout"):
            # We could not complete the check. That is OUR failure, not a defect in
            # the user's evidence, so accessibility stays undetermined: a broken
            # scraper must never produce a RED that blames the reporting user.
            by_index[index] = {
                "index": index, "status": kind, "determined": False,
                "error": item.get("error", "Could not be retrieved."),
            }
        elif kind == "invalid_content":
            reason = item.get("validation_reason")
            # Only these two are positive determinations about the link itself.
            # Thin or empty extractions say more about our parser than the source.
            dead = reason in ("authentication_required", "error_page")
            by_index[index] = {
                "index": index, "status": "invalid", "determined": dead,
                "reachable": not dead,
                "error": item.get("error", "The page did not contain usable content."),
                "validation_reason": reason,
            }
        else:
            by_index[index] = {
                "index": index, "status": "ok", "determined": True, "reachable": True,
                "title": item.get("title"), "content": item.get("content", ""),
            }

    ok = sum(1 for v in by_index.values() if v["status"] == "ok")
    logger.info(f"📊 Evidence retrieved: {ok}/{len(evaluable)}")
    return [by_index[i] for i, _ in evaluable], by_index


# --------------------------------------------------------------------------- #
# LLM calls
# --------------------------------------------------------------------------- #

def _unevaluated(criteria, reason: str) -> List[Finding]:
    return [Finding(c.id, Outcome.NOT_EVALUATED, comment=reason) for c in criteria]


async def _metadata_call(request, budget: Budget) -> Tuple[List[Finding], Optional[str]]:
    criteria = applicable(request, check=Check.LLM, needs=Needs.METADATA)
    if not criteria:
        return [], None
    parts = build_metadata_prompt(request, criteria)
    try:
        result = await invoke_with_tool(
            parts.system, parts.user, metadata_tool(criteria),
            call_name="metadata", timeout=budget.slice(LLM_BUDGET_SHARE),
        )
        return _to_findings(result.get("findings", []), criteria), None
    except Exception as e:
        logger.error(f"❌ Metadata assessment unavailable: {e}")
        return (
            _unevaluated(criteria, "This part of the check could not be completed."),
            f"metadata assessment unavailable: {type(e).__name__}",
        )


async def _evidence_call(request, scraped, budget: Budget):
    criteria = applicable(request, check=Check.LLM, needs=Needs.EVIDENCE_CONTENT)
    if not criteria:
        return [], [], None
    retrieved = [s for s in scraped if s.get("status") == "ok"]
    if not retrieved:
        return (
            _unevaluated(criteria, "No evidence content was available to review."),
            [], None,
        )
    parts = build_evidence_prompt(request, criteria, scraped)
    try:
        result = await invoke_with_tool(
            parts.system, parts.user,
            evidence_tool(criteria, len(request.sections.evidence)),
            max_tokens=6000, call_name="evidence",
            timeout=budget.slice(LLM_BUDGET_SHARE),
        )
        return (
            _to_findings(result.get("findings", []), criteria),
            result.get("evidence", []),
            None,
        )
    except Exception as e:
        logger.error(f"❌ Evidence assessment unavailable: {e}")
        return (
            _unevaluated(criteria, "This part of the check could not be completed."),
            [],
            f"evidence assessment unavailable: {type(e).__name__}",
        )


def _to_findings(reported: List[dict], criteria) -> List[Finding]:
    """Map the tool call back onto the catalog. Criteria the model skipped come
    back as not evaluated rather than silently counting as passed."""
    by_id = {r.get("criterion_id"): r for r in reported}
    findings = []
    for c in criteria:
        r = by_id.get(c.id)
        if r is None:
            logger.warning(f"⚠️ Model omitted criterion {c.id}")
            findings.append(Finding(c.id, Outcome.NOT_EVALUATED,
                                    comment="This point was not reviewed."))
            continue
        outcome = Outcome.FLAGGED if r.get("outcome") == "flagged" else Outcome.PASSED
        findings.append(Finding(c.id, outcome, comment=(r.get("comment") or "").strip()))
    return findings


# --------------------------------------------------------------------------- #
# Response assembly
# --------------------------------------------------------------------------- #

_TO_API = {
    Verdict.GREEN: ApiVerdict.GREEN,
    Verdict.AMBER: ApiVerdict.AMBER,
    Verdict.RED: ApiVerdict.RED,
    Verdict.NOT_EVALUATED: ApiVerdict.GREY,
}

_SECTION_SUMMARY = {
    ApiVerdict.GREEN: "This section meets the quality criteria.",
    ApiVerdict.AMBER: "This section is acceptable, but it could be stronger.",
    ApiVerdict.RED: "This section does not meet the quality criteria.",
    ApiVerdict.GREY: "There was nothing to review in this section.",
}

_OVERALL_SUMMARY = {
    ApiVerdict.GREEN: "This result meets the quality criteria and is ready to submit.",
    ApiVerdict.AMBER: "This result can be submitted, but it is not its best version yet.",
    ApiVerdict.RED: "This result does not meet the quality criteria.",
    ApiVerdict.GREY: "The quality check could not review this result.",
}

MAX_STRENGTHS_PER_SECTION = 3


def _section_payload(section_result, force_grey: bool = False) -> SectionVerdict:
    verdict = ApiVerdict.GREY if force_grey else _TO_API[section_result.verdict]
    issues = [f.comment for f in section_result.findings if f.is_flag and f.comment]
    strengths = [
        f.comment for f in section_result.findings
        if f.outcome == Outcome.PASSED and f.comment
    ][:MAX_STRENGTHS_PER_SECTION]

    unchecked = sum(1 for f in section_result.findings
                    if f.outcome == Outcome.NOT_EVALUATED)

    comments = _SECTION_SUMMARY[verdict]
    if force_grey:
        comments = (
            "None of the attached evidence could be read this time, so the "
            "evidence itself was not reviewed."
        )
    elif issues:
        comments = (
            f"{len(issues)} point{'s' if len(issues) > 1 else ''} to address "
            f"before this section is at its best."
        )
    elif unchecked and verdict == ApiVerdict.GREEN:
        # Never claim a section "meets the quality criteria" when part of it was
        # not looked at. The traffic light follows the documented rule - no flags
        # means green - but the wording must not overstate what was verified.
        comments = (
            f"Nothing was flagged here, but {unchecked} "
            f"{'check' if unchecked == 1 else 'checks'} could not be completed this "
            "time, so this section was only partly reviewed."
        )
    return SectionVerdict(
        verdict=verdict,
        score=None,
        comments=comments,
        strengths=[] if issues else strengths,
        issues=issues,
    )


def _evidence_payload(request, by_index, llm_verdicts) -> List[EvidenceVerdict]:
    reported = {v.get("index"): v for v in llm_verdicts or []}
    out = []
    for i, ev in enumerate(request.sections.evidence):
        if not ev.is_evaluable:
            reason = (
                "Private repository file — not evaluated"
                if ev.source == "prms_repository" or ev.visibility == "private"
                else "No link provided — not evaluated"
            )
            out.append(EvidenceVerdict(index=i, verdict=ApiVerdict.GREY, reason=reason))
            continue

        state = by_index.get(i, {})
        if state.get("status") != "ok":
            out.append(EvidenceVerdict(
                index=i, verdict=ApiVerdict.GREY,
                reason=state.get("error", "Could not be checked — not evaluated"),
            ))
            continue

        judged = reported.get(i)
        if judged is None:
            out.append(EvidenceVerdict(
                index=i, verdict=ApiVerdict.GREY,
                reason="Not reviewed — not evaluated",
            ))
            continue
        out.append(EvidenceVerdict(
            index=i,
            verdict=ApiVerdict(judged.get("verdict", "grey")),
            reason=(judged.get("reason") or "").strip(),
        ))
    return out


CRITERIA_VERSION = "QA-2026-v1"
TRACKING_TIMEOUT_S = 8.0


async def _track_interaction(request, response, findings, elapsed: float,
                             evidence_read: int) -> Optional[str]:
    """Record the assessment with the interaction service.

    interaction_client.track_interaction posts synchronously, so it runs in the
    executor: at this point the verdict is already computed and a blocking call
    would only delay a response that is ready. Failure here is never allowed to
    affect the assessment.
    """
    if not request.user_id:
        return None

    try:
        gi = request.sections.general_information
        user_input = (
            f"W3/Bilateral quality assessment - Result type: {request.result.type}, "
            f"Title: {gi.title}, Level: {gi.result_level}"
        )
        ai_output = json.dumps(
            {
                "overall": response.overall.model_dump(),
                "sections": response.sections.model_dump(),
                "evidence": [e.model_dump() for e in response.evidence],
            },
            indent=2, ensure_ascii=False,
        )
        tracking_context = {
            "criteria_version": CRITERIA_VERSION,
            "result_type": request.result.type,
            "verdict": response.overall.verdict.value,
            "score": response.overall.score,
            "flags": sum(1 for f in findings if f.is_flag),
            "criteria_total": response.coverage.criteria_total,
            "criteria_evaluated": response.coverage.criteria_evaluated,
            "llm_calls": 2,
            "model_used": MODEL_ID,
            "evidence_total": len(request.sections.evidence),
            "evidence_read": evidence_read,
            "check_status": response.status.value,
        }

        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(
            loop.run_in_executor(
                None,
                lambda: interaction_client.track_interaction(
                    user_id=request.user_id,
                    user_input=user_input,
                    ai_output=ai_output,
                    service_name="qa-ai-traffic-light",
                    display_name="PRMS Reporting Tool - Bilateral QA Assessment",
                    service_description="W3/Bilateral quality assessment with "
                                        "traffic-light verdicts and evidence review",
                    context=tracking_context,
                    response_time_seconds=elapsed,
                    platform="PRMS",
                ),
            )
        )

        done, _ = await asyncio.wait([future], timeout=TRACKING_TIMEOUT_S)
        if not done:
            logger.warning(
                f"⏱️ Interaction tracking exceeded {TRACKING_TIMEOUT_S}s; "
                "returning without the interaction id"
            )
            return None

        result = future.result()
        if result:
            interaction_id = result.get("interaction_id")
            logger.info(f"📊 Interaction tracked with ID: {interaction_id}")
            return interaction_id
        logger.warning("⚠️ Failed to track interaction with interaction service")
    except Exception as e:
        logger.error(f"❌ Error tracking interaction: {e}")
    return None


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

async def assess_result(request: QualityAssessmentRequest) -> QualityAssessmentResponse:
    budget = Budget(float(request.constraints.timeout_seconds or 60))
    logger.info(
        f"🔍 Quality assessment {request.request_id} | type={request.result.type} | "
        f"budget={budget.total}s"
    )

    code_findings = run_metadata_rules(request)

    # Scraping and the metadata call have no dependency on each other.
    (scraped, by_index), (meta_findings, meta_error) = await asyncio.gather(
        _scrape_evidence(request, budget),
        _metadata_call(request, budget),
    )

    ev_findings, ev_verdicts, ev_error = await _evidence_call(request, scraped, budget)
    code_findings += run_evidence_rules(request, by_index)

    findings = code_findings + meta_findings + ev_findings
    result = aggregate(findings, sections_for(request.result.type))
    assert_rule_equivalence(result)

    overall = _TO_API[result.overall]

    # Evidence attached but nothing readable: the two structural checks (item
    # count, blocked domains) would otherwise carry the section to green without
    # a single document having been opened. A reviewer must not see a green light
    # on evidence that was never read.
    submitted = len(request.sections.evidence)
    read = sum(1 for v in by_index.values() if v.get("status") == "ok")

    sections = {}
    for s in result.sections:
        blind = (
            s.section == Section.EVIDENCE
            and submitted > 0
            and read == 0
            and not s.flags
        )
        sections[s.section.value] = _section_payload(s, force_grey=blind)

    errors = [e for e in (meta_error, ev_error) if e]
    if len(errors) == 2:
        raise AssessmentUnavailable("; ".join(errors))
    if errors:
        status, reason = CheckStatus.PARTIAL, "; ".join(errors)
    elif any(v.get("status") != "ok" for v in by_index.values()):
        status = CheckStatus.PARTIAL
        reason = "one or more evidence items could not be retrieved"
    else:
        status, reason = CheckStatus.COMPLETED, None

    evaluated = sum(1 for f in result.findings
                    if f.outcome in (Outcome.PASSED, Outcome.FLAGGED))

    logger.info(
        f"✅ {request.request_id}: {overall.value} in {budget.elapsed:.1f}s "
        f"({status.value}) | flags={len(result.flags)} | "
        f"criteria {evaluated}/{len(result.findings)}"
    )

    response = QualityAssessmentResponse(
        request_id=request.request_id,
        overall=OverallVerdict(
            verdict=overall,
            score=compute_score(result.findings, result.overall),
            summary=_OVERALL_SUMMARY[overall],
        ),
        sections=SectionVerdicts(**sections),
        evidence=_evidence_payload(request, by_index, ev_verdicts),
        status=status,
        degraded_reason=reason,
        coverage=Coverage(criteria_total=len(result.findings),
                          criteria_evaluated=evaluated),
    )

    response.interaction_id = await _track_interaction(
        request, response, result.findings, budget.elapsed, read
    )
    return response
