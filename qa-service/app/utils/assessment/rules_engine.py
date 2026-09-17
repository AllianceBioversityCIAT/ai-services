"""
Deterministic evaluation of the `code` criteria.

These never call a model: same payload in, same findings out. Roughly half the
catalog is resolved here, which is what keeps the LLM calls small and the time
budget comfortable.

Rules that need the scraped evidence (HTTP status) run in a second pass once
scraping finishes; everything else runs immediately on the payload.
"""

import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from app.utils.assessment.aggregation import Finding, Outcome
from app.utils.assessment.criteria_catalog import CATALOG_BY_ID, OnAbsent
from app.utils.assessment import vocabularies as vocab

MAX_TITLE_WORDS = 30
MIN_DESCRIPTION_WORDS = 50
# The criteria document says "Max ~300 words"; the tilde is honoured with a 10%
# tolerance so a 305-word description is not flagged against an approximate limit.
MAX_DESCRIPTION_WORDS = 330
MAX_EVIDENCE_ITEMS = 6
IMPLAUSIBLE_PARTICIPANTS = 10_000

FUTURE_TENSE = re.compile(
    r"\b(will\s+be|will|planned\s+to|plans\s+to|is\s+expected\s+to|are\s+expected\s+to)\b",
    re.IGNORECASE,
)
ESTIMATED = re.compile(
    r"\b(estimated|approximately|approx\.?|projected|expected|around|roughly|about)\b",
    re.IGNORECASE,
)

BLOCKED_DOMAINS = (
    "sharepoint.com",
    "onedrive.live.com",
    "1drv.ms",
    "drive.google.com",
    "docs.google.com",
    "dropbox.com",
)


def _words(text: Optional[str]) -> int:
    return len((text or "").split())


def _field(request, label: str) -> Any:
    return (request.sections.type_specific.fields or {}).get(label)


def _score_value(score: Optional[str]) -> Optional[int]:
    """'2 — Principal' -> 2. None when unparseable."""
    if score is None:
        return None
    m = re.match(r"\s*([0-2])\b", str(score))
    return int(m.group(1)) if m else None


def _count(value: Any, key: str) -> Optional[int]:
    if isinstance(value, dict):
        v = value.get(key)
        return v if isinstance(v, (int, float)) else None
    return None


def _f(cid: str, outcome: Outcome, comment: str = "", **kw) -> Finding:
    return Finding(cid, outcome, comment=comment, **kw)


def _ok(cid: str, comment: str = "") -> Finding:
    return _f(cid, Outcome.PASSED, comment)


def _flag(cid: str, comment: str) -> Finding:
    return _f(cid, Outcome.FLAGGED, comment)


# --------------------------------------------------------------------------- #
# General Information
# --------------------------------------------------------------------------- #

def _title_max_words(request) -> Finding:
    cid = "generic.title.max_words"
    title = request.sections.general_information.title
    if not (title or "").strip():
        return _flag(cid, "The title is empty.")
    n = _words(title)
    if n > MAX_TITLE_WORDS:
        return _flag(cid, f"The title is {n} words long; the limit is {MAX_TITLE_WORDS}.")
    return _ok(cid, f"Title length is within the {MAX_TITLE_WORDS}-word limit ({n} words).")


def _description_min_words(request) -> Finding:
    cid = "generic.description.min_words"
    desc = request.sections.general_information.description
    if not (desc or "").strip():
        return _flag(cid, "The result description is empty.")
    n = _words(desc)
    if n < MIN_DESCRIPTION_WORDS:
        return _flag(
            cid,
            f"The description is only {n} words long. Descriptions under "
            f"{MIN_DESCRIPTION_WORDS} words rarely carry enough detail to be assessed.",
        )
    return _ok(cid, f"The description has enough substance to be assessed ({n} words).")


def _description_max_words(request) -> Finding:
    cid = "generic.description.max_words"
    desc = request.sections.general_information.description
    if not (desc or "").strip():
        return _flag(cid, "The result description is empty.")
    n = _words(desc)
    if n > MAX_DESCRIPTION_WORDS:
        return _flag(cid, f"The description is {n} words long; the guideline is about 300.")
    return _ok(cid, f"Description length is within the guideline ({n} words).")


def _description_future_tense(request) -> Finding:
    cid = "generic.description.future_tense"
    desc = request.sections.general_information.description or ""
    hits = sorted({m.group(0).lower() for m in FUTURE_TENSE.finditer(desc)})
    if hits:
        return _flag(
            cid,
            "The description uses future-tense language "
            f"({', '.join(repr(h) for h in hits)}). A reported result must describe "
            "something already completed, not something planned.",
        )
    return _ok(cid, "The description is written as a completed result.")


# --------------------------------------------------------------------------- #
# Impact areas (omitted entirely when none arrive)
# --------------------------------------------------------------------------- #

def _impact_area_score2_evidence(request) -> Optional[Finding]:
    cid = "generic.impact_area.score2_evidence"
    if not request.impact_areas:
        return None
    offenders = []
    for ia in request.impact_areas:
        if _score_value(ia.score) != 2:
            continue
        # No evidence tag points at this pillar, so the requirement can never be
        # met. Skipping is the only correct behaviour.
        if ia.name in vocab.IMPACT_AREAS_WITHOUT_TAG:
            continue
        linked = any(
            vocab.evidence_supports_impact_area(ev.tags, ia.name)
            for ev in request.sections.evidence
        )
        if not linked:
            offenders.append(ia.name)
    if offenders:
        return _flag(
            cid,
            "Scored as a principal contribution without any evidence tagged for "
            f"that area: {'; '.join(offenders)}.",
        )
    return _ok(cid, "Every principal-level impact area has evidence tagged for it.")


def _impact_area_score2_subcomponent(request) -> Optional[Finding]:
    cid = "generic.impact_area.score2_subcomponent"
    if not request.impact_areas:
        return None
    offenders = [
        ia.name for ia in request.impact_areas
        if _score_value(ia.score) == 2 and not ia.subcomponents
    ]
    if offenders:
        return _flag(
            cid,
            "Scored as a principal contribution without selecting a thematic "
            f"subcomponent: {'; '.join(offenders)}.",
        )
    return _ok(cid, "Principal-level impact areas have a thematic subcomponent selected.")


# --------------------------------------------------------------------------- #
# Geographic location
# --------------------------------------------------------------------------- #

def _geographic_presence(request) -> Finding:
    cid = "generic.geographic_focus.presence"
    geo = request.sections.geographic_location
    has_geo = bool(geo.scope or geo.regions or geo.countries or geo.sub_national)
    if has_geo:
        return _ok(cid, "A geographic scope is recorded.")

    delivery = _field(request, "Delivery method")
    if delivery and vocab.waives_geography(delivery):
        return _f(
            cid, Outcome.NOT_EVALUATED,
            "Delivery is fully virtual, so no geographic selection is required.",
        )
    return _flag(cid, "No geographic scope was selected.")


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #

def _evidence_max_items(request) -> Finding:
    cid = "generic.evidence.max_items"
    n = len(request.sections.evidence)
    if n > MAX_EVIDENCE_ITEMS:
        return _flag(cid, f"{n} evidence items were submitted; the maximum is {MAX_EVIDENCE_ITEMS}.")
    return _ok(cid, f"{n} evidence item(s) submitted, within the limit of {MAX_EVIDENCE_ITEMS}.")


def _is_blocked(url: str) -> Optional[str]:
    host = (urlparse(url).hostname or "").lower()
    for blocked in BLOCKED_DOMAINS:
        if host == blocked or host.endswith("." + blocked):
            return blocked
    return None


def _evidence_blocked_domain(request) -> Finding:
    cid = "generic.evidence.blocked_domain"
    offenders = []
    for i, ev in enumerate(request.sections.evidence):
        if not ev.link:
            continue  # repository items carry no link; that is the sanctioned route
        blocked = _is_blocked(ev.link)
        if blocked:
            offenders.append(f"item {i + 1} ({blocked})")
    if offenders:
        return _flag(
            cid,
            "Evidence hosted on a blocked file-sharing service: "
            f"{', '.join(offenders)}. Use the PRMS repository for non-public files.",
        )
    return _ok(cid, "No evidence is hosted on a blocked file-sharing service.")


def _evidence_accessible(request, scrape_results: Dict[int, dict]) -> Finding:
    """Flag only links we positively determined to be dead or login-gated.

    When the fetch failed on our side - scraper error, timeout, missing browser -
    accessibility is left undetermined. An infrastructure failure must not turn
    into a RED verdict telling the user their evidence is broken. Those runs are
    reported through `status: partial` instead.
    """
    cid = "generic.evidence.accessible"
    dead, undetermined = [], []
    for i, ev in enumerate(request.sections.evidence):
        if not ev.is_evaluable:
            continue
        res = scrape_results.get(i)
        if res is None:
            undetermined.append(i + 1)
            continue
        if not res.get("determined", False):
            undetermined.append(i + 1)
        elif not res.get("reachable", True):
            reason = res.get("validation_reason")
            label = "requires a login" if reason == "authentication_required" else "is not reachable"
            dead.append(f"item {i + 1} {label}")

    if dead:
        return _flag(
            cid,
            "Evidence could not be opened: " + ", ".join(dead) +
            ". Reviewers need to be able to reach the evidence you attach.",
        )
    if undetermined:
        return _f(
            cid, Outcome.NOT_EVALUATED,
            "Some evidence links could not be checked automatically this time.",
        )
    return _ok(cid, "All public evidence links are reachable.")


# --------------------------------------------------------------------------- #
# Innovation Use
# --------------------------------------------------------------------------- #

def _innovuse_count_present(request) -> Finding:
    cid = "innovuse.count.present"
    value = _field(request, "Number of people using")
    total = _count(value, "total")
    if total is None:
        return _flag(cid, "No number of people or actors using the innovation was reported.")
    if total <= 0:
        return _flag(cid, "The number of people or actors using the innovation is zero.")
    return _ok(cid, f"{int(total)} users reported.")


def _innovuse_gender_disaggregation(request) -> Finding:
    cid = "innovuse.count.gender_disaggregation"
    value = _field(request, "Number of people using")
    women, men = _count(value, "women"), _count(value, "men")
    if women is None and men is None:
        return _flag(
            cid,
            "The user count is not disaggregated. Counts of women and men are required.",
        )
    # Deliberately no women + men == total check: rows reported without
    # disaggregation add to the total only, and youth counts are subsets of
    # women/men, so the parts legitimately sum to less than the total.
    return _ok(cid, "The user count is disaggregated by women and men.")


def _innovuse_not_estimated(request) -> Finding:
    cid = "innovuse.count.not_estimated"
    haystack = " ".join(
        str(x) for x in [
            request.sections.general_information.description,
            _field(request, "Other quantitative measures"),
        ] if x
    )
    hits = sorted({m.group(0).lower() for m in ESTIMATED.finditer(haystack)})
    if hits:
        return _flag(
            cid,
            "Usage figures appear to be estimates rather than actual data "
            f"({', '.join(repr(h) for h in hits)}). Reported numbers must be evidence-based.",
        )
    return _ok(cid, "Usage figures are presented as actual data.")


# --------------------------------------------------------------------------- #
# Capacity Sharing
# --------------------------------------------------------------------------- #

def _capsharing_count_present(request) -> Finding:
    cid = "capsharing.trained.count_present"
    value = _field(request, "Number of people trained")
    total = _count(value, "total")
    if total is None:
        return _flag(cid, "No number of people trained was reported.")
    if total <= 0:
        return _flag(cid, "The number of people trained is zero.")
    return _ok(cid, f"{int(total)} people trained reported.")


def _capsharing_gender_disaggregation(request) -> Finding:
    cid = "capsharing.trained.gender_disaggregation"
    value = _field(request, "Number of people trained")
    female, male = _count(value, "female"), _count(value, "male")
    if female is None and male is None:
        return _flag(
            cid,
            "The training count is not disaggregated by gender.",
        )
    return _ok(cid, "The training count is disaggregated by gender.")


def _capsharing_plausible(request) -> Finding:
    cid = "capsharing.trained.plausible"
    value = _field(request, "Number of people trained")
    total = _count(value, "total")
    if total is None:
        return _flag(cid, "No number of people trained was reported.")
    if total > IMPLAUSIBLE_PARTICIPANTS:
        return _flag(
            cid,
            f"{int(total)} participants is unusually high for a single training "
            "and needs supporting detail.",
        )
    return _ok(cid, "The number of participants is plausible for the activity described.")


def _capsharing_length_present(request) -> Finding:
    cid = "capsharing.length.present"
    value = _field(request, "Length of training")
    if not value:
        return _flag(cid, "No training term was selected.")
    if value not in vocab.TRAINING_LENGTHS:
        return _flag(cid, f"{value!r} is not a valid training term.")
    return _ok(cid, f"Training term recorded as {value}.")


def _capsharing_delivery_method(request) -> Finding:
    cid = "capsharing.delivery.method"
    value = _field(request, "Delivery method")
    if not value:
        return _flag(cid, "No delivery method was selected.")
    if value not in vocab.DELIVERY_METHODS:
        return _flag(cid, f"{value!r} is not a valid delivery method.")

    geo = request.sections.geographic_location
    if vocab.waives_geography(value) and (geo.countries or geo.sub_national):
        return _flag(
            cid,
            "Delivery is recorded as fully virtual, but a country-level geographic "
            "scope was also selected. One of the two needs revisiting.",
        )
    return _ok(cid, f"Delivery method recorded as {value}.")


def _capsharing_evidence_required(request) -> Finding:
    cid = "capsharing.evidence.ia_score2_required"
    principal = [ia.name for ia in (request.impact_areas or []) if _score_value(ia.score) == 2]
    if not principal:
        return _f(
            cid, Outcome.NOT_EVALUATED,
            "No impact area is scored as principal, so evidence is not required "
            "for this result type.",
        )
    if not request.sections.evidence:
        return _flag(
            cid,
            "An impact area is scored as a principal contribution "
            f"({'; '.join(principal)}), which requires supporting evidence such as a "
            "syllabus, agenda, or attendance list. No evidence was attached.",
        )
    return _ok(cid, "Evidence is attached to support the principal-level impact area.")


# --------------------------------------------------------------------------- #
# Innovation Development
# --------------------------------------------------------------------------- #

def _innovdev_contact_point(request) -> Finding:
    cid = "innovdev.contact_point.populated"
    value = _field(request, "Innovation developers")
    if not str(value or "").strip():
        return _flag(cid, "No innovation developer was recorded.")
    return _ok(cid, "An innovation developer is recorded.")


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #

METADATA_RULES = {
    "generic.title.max_words": _title_max_words,
    "generic.description.min_words": _description_min_words,
    "generic.description.max_words": _description_max_words,
    "generic.description.future_tense": _description_future_tense,
    "generic.impact_area.score2_evidence": _impact_area_score2_evidence,
    "generic.impact_area.score2_subcomponent": _impact_area_score2_subcomponent,
    "generic.geographic_focus.presence": _geographic_presence,
    "generic.evidence.max_items": _evidence_max_items,
    "generic.evidence.blocked_domain": _evidence_blocked_domain,
    "innovuse.count.present": _innovuse_count_present,
    "innovuse.count.gender_disaggregation": _innovuse_gender_disaggregation,
    "innovuse.count.not_estimated": _innovuse_not_estimated,
    "capsharing.trained.count_present": _capsharing_count_present,
    "capsharing.trained.gender_disaggregation": _capsharing_gender_disaggregation,
    "capsharing.trained.plausible": _capsharing_plausible,
    "capsharing.length.present": _capsharing_length_present,
    "capsharing.delivery.method": _capsharing_delivery_method,
    "capsharing.evidence.ia_score2_required": _capsharing_evidence_required,
    "innovdev.contact_point.populated": _innovdev_contact_point,
}

EVIDENCE_RULES = {
    "generic.evidence.accessible": _evidence_accessible,
}


def run_metadata_rules(request) -> List[Finding]:
    """Everything resolvable from the payload alone, before any scraping."""
    from app.utils.assessment.selection import applicable as _applicable

    applicable = {c.id for c in _applicable(request)}
    findings = []
    for cid, rule in METADATA_RULES.items():
        if cid not in applicable:
            continue
        finding = rule(request)
        if finding is not None:   # None == omitted (optional field absent)
            findings.append(finding)
    return findings


def run_evidence_rules(request, scrape_results: Dict[int, dict]) -> List[Finding]:
    """Rules that need the fetch outcome. Run once scraping finishes."""
    from app.utils.assessment.selection import applicable as _applicable

    applicable = {c.id for c in _applicable(request)}
    findings = []
    for cid, rule in EVIDENCE_RULES.items():
        if cid not in applicable:
            continue
        findings.append(rule(request, scrape_results))
    return findings
