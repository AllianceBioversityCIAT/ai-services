"""
Tests for the deterministic rules of the W3/Bilateral quality assessment.

Run: python tests/test_assessment_rules.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.models import QualityAssessmentRequest
from app.utils.assessment.aggregation import Outcome, aggregate, Verdict
from app.utils.assessment.rules_engine import run_metadata_rules, run_evidence_rules
from app.utils.assessment.criteria_catalog import sections_for

PASSED, FAILED = [], []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{'' if condition else '  -> ' + detail}")


def build(result_type, **over):
    payload = {
        "contract_version": "0.2", "request_id": "t",
        "result": {"type": result_type},
        "sections": {
            "general_information": {
                "title": "A biofortified rice variety released for smallholder farmers",
                "description": " ".join(["word"] * 120),
            },
            "contributors_and_partners": {},
            "geographic_location": {"scope": "National", "countries": ["Côte d'Ivoire"]},
            "evidence": [],
            "type_specific": {"fields": {}},
        },
        "impact_areas": [],
    }
    for path, value in over.items():
        node = payload
        parts = path.split(".")
        for p in parts[:-1]:
            node = node[p]
        node[parts[-1]] = value
    return QualityAssessmentRequest(**payload)


def outcome(findings, cid):
    for f in findings:
        if f.criterion_id == cid:
            return f.outcome
    return None


CS = "Capacity Sharing for Development"
IU = "Innovation Use"
ID = "Innovation development"


print("\n--- Delivery method vs geography (the substring trap) ---")
for method, countries, expected, why in [
    ("Virtual / Online", [], Outcome.NOT_EVALUATED, "fully virtual, no geography: exempt"),
    ("Blended (in-person and virtual)", [], Outcome.FLAGGED, "blended, no geography: NOT exempt"),
    ("In person", [], Outcome.FLAGGED, "in person, no geography: flagged"),
]:
    r = build(CS, **{"sections.geographic_location": {"regions": [], "countries": countries,
                                                      "sub_national": []},
                     "sections.type_specific": {"fields": {"Delivery method": method}}})
    got = outcome(run_metadata_rules(r), "generic.geographic_focus.presence")
    check(why, got == expected, f"expected {expected}, got {got}")


print("\n--- Innovation Use: the parts may sum to less than the total ---")
r = build(IU, **{"sections.type_specific": {"fields": {
    "Number of people using": {"total": 500, "women": 120, "men": 90}}}})
fs = run_metadata_rules(r)
check("total 500 with 120+90 disaggregated is NOT flagged",
      outcome(fs, "innovuse.count.gender_disaggregation") == Outcome.PASSED,
      str(outcome(fs, "innovuse.count.gender_disaggregation")))

r = build(IU, **{"sections.type_specific": {"fields": {
    "Number of people using": {"total": 500}}}})
check("neither women nor men count IS flagged",
      outcome(run_metadata_rules(r), "innovuse.count.gender_disaggregation") == Outcome.FLAGGED)


print("\n--- Impact areas: the pillar/tag asymmetry ---")
r = build(ID, **{
    "impact_areas": [{"name": "Climate adaptation and mitigation", "score": "2 — Principal",
                      "subcomponents": ["Adaptation"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": []}]})
check("Climate=2 is NOT flagged - no evidence tag maps to Climate",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.PASSED)

r = build(ID, **{
    "impact_areas": [{"name": "Gender equality, youth and social inclusion",
                      "score": "2 — Principal", "subcomponents": ["Youth"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": ["Youth"]}]})
check("Gender=2 passes with a Youth-tagged item - Youth maps to Gender",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.PASSED)

r = build(ID, **{
    "impact_areas": [{"name": "Poverty reduction, livelihoods and jobs",
                      "score": "2 — Principal", "subcomponents": ["Jobs"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": ["Gender"]}]})
check("Poverty=2 with only Gender-tagged evidence IS flagged",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.FLAGGED)

r = build(ID)
check("no impact areas: the criterion is omitted entirely",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") is None)


print("\n--- Evidence: blocked domains and the repository ---")
r = build(ID, **{"sections.evidence": [
    {"description": "a", "link": "https://cgiar.sharepoint.com/:b:/s/x", "source": "url",
     "tags": []}]})   # no visibility flag: a pasted URL, not from the repository
check("SharePoint pasted as a URL is flagged",
      outcome(run_metadata_rules(r), "generic.evidence.blocked_domain") == Outcome.FLAGGED)

r = build(ID, **{"sections.evidence": [
    {"description": "a", "link": None, "source": "prms_repository",
     "visibility": "private", "tags": []}]})
check("a repository item with no link is NOT flagged - that is the sanctioned route",
      outcome(run_metadata_rules(r), "generic.evidence.blocked_domain") == Outcome.PASSED)

r = build(ID, **{"sections.evidence": [
    {"description": f"e{i}", "link": f"https://x.org/{i}", "source": "url",
     "visibility": "public", "tags": []} for i in range(7)]})
check("7 evidence items are flagged - the maximum is 6",
      outcome(run_metadata_rules(r), "generic.evidence.max_items") == Outcome.FLAGGED)


print("\n--- Future tense and false positives ---")
for desc, expected, why in [
    ("The team will deliver the toolkit next year.", Outcome.FLAGGED, "'will' is detected"),
    ("The project generated goodwill among farmers in Williams county.",
     Outcome.PASSED, "'goodwill'/'Williams' are NOT false positives"),
    ("The variety was released and adopted by 200 farmers.", Outcome.PASSED, "clean past tense passes"),
]:
    r = build(ID, **{"sections.general_information": {
        "title": "T", "description": desc + " " + " ".join(["word"] * 60)}})
    got = outcome(run_metadata_rules(r), "generic.description.future_tense")
    check(why, got == expected, f"expected {expected}, got {got}")


print("\n--- Capacity Sharing: evidence required only when an impact area scores 2 ---")
r = build(CS, **{"sections.type_specific": {"fields": {
    "Delivery method": "In person", "Length of training": "Short-term",
    "Number of people trained": {"total": 40, "female": 20, "male": 20}}}})
check("no impact area at 2: evidence is NOT_EVALUATED (grey)",
      outcome(run_metadata_rules(r), "capsharing.evidence.ia_score2_required") == Outcome.NOT_EVALUATED)

r = build(CS, **{
    "impact_areas": [{"name": "Gender equality, youth and social inclusion",
                      "score": "2 — Principal", "subcomponents": ["Gender equality"]}],
    "sections.type_specific": {"fields": {
        "Delivery method": "In person", "Length of training": "Short-term",
        "Number of people trained": {"total": 40, "female": 20, "male": 20}}}})
check("impact area at 2 with no evidence IS flagged (core -> RED)",
      outcome(run_metadata_rules(r), "capsharing.evidence.ia_score2_required") == Outcome.FLAGGED)


print("\n--- Integration: a clean result comes out green ---")
r = build(ID, **{"sections.type_specific": {"fields": {
    "Innovation typology": "Technological", "Readiness level": "Level 6 — …",
    "Innovation developers": "DRABO Inoussa, CIMMYT"}}})
fs = run_metadata_rules(r) + run_evidence_rules(r, {})
res = aggregate(fs, sections_for("Innovation development"))
code_flags = [f.criterion_id for f in fs if f.is_flag]
check("no code criterion fires on a well-formed payload",
      not code_flags, f"flags: {code_flags}")

print("\n--- Blocked domains: the visibility flag decides ---")
PRMS_LINK = ("https://cgiar.sharepoint.com/:b:/s/OneCGIARPRMSRepository/"
             "IQDguq1lCiU8QZH-XvEUh1OuAYQYI")
OTRO_SP = "https://cgiar.sharepoint.com/:x:/s/MiEquipo/a.xlsx"

def blocked_outcome(item):
    r = build(ID, **{"sections.evidence": [item]})
    return outcome(run_metadata_rules(r), "generic.evidence.blocked_domain")

# With a visibility flag -> came through the PRMS repository -> never blocked.
for link, vis, label in [
    (PRMS_LINK, "public",  "PRMS repository, public"),
    (PRMS_LINK, "private", "PRMS repository, private"),
    (OTRO_SP,   "public",  "another SharePoint site, but WITH the flag"),
]:
    check(f"with the flag ({label}) -> not blocked",
          blocked_outcome({"description": "d", "link": link, "source": "url",
                           "visibility": vis, "tags": []}) == Outcome.PASSED)

# No flag -> a URL the user pasted -> the document's blocked list applies.
check("no flag, another SharePoint site -> blocked",
      blocked_outcome({"description": "d", "link": OTRO_SP, "source": "url",
                       "tags": []}) == Outcome.FLAGGED)
check("no flag, Google Drive -> blocked",
      blocked_outcome({"description": "d", "link": "https://drive.google.com/file/d/a/view",
                       "source": "url", "tags": []}) == Outcome.FLAGGED)
check("no flag, CGSpace -> not blocked",
      blocked_outcome({"description": "d", "link": "https://hdl.handle.net/10568/1",
                       "source": "url", "tags": []}) == Outcome.PASSED)

r = build(ID, **{"sections.evidence": [
    {"description": "d", "link": OTRO_SP, "source": "url", "tags": []}]})
msg = [f.comment for f in run_metadata_rules(r)
       if f.criterion_id == "generic.evidence.blocked_domain"][0]
check("the message no longer tells a repository user to use the repository",
      "personal file-sharing" in msg and "(item" not in msg, msg[:70])

print(f"\n{'='*60}\n{len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    for f in FAILED: print("  FAILED:", f)
    sys.exit(1)
