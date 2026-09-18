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


print("\n--- Delivery method vs geography (el substring trap) ---")
for method, countries, expected, why in [
    ("Virtual / Online", [], Outcome.NOT_EVALUATED, "virtual sin geografía: exenta"),
    ("Blended (in-person and virtual)", [], Outcome.FLAGGED, "blended sin geografía: NO exenta"),
    ("In person", [], Outcome.FLAGGED, "presencial sin geografía"),
]:
    r = build(CS, **{"sections.geographic_location": {"regions": [], "countries": countries,
                                                      "sub_national": []},
                     "sections.type_specific": {"fields": {"Delivery method": method}}})
    got = outcome(run_metadata_rules(r), "generic.geographic_focus.presence")
    check(why, got == expected, f"esperado {expected}, obtenido {got}")


print("\n--- Innovation Use: las partes pueden sumar menos que el total ---")
r = build(IU, **{"sections.type_specific": {"fields": {
    "Number of people using": {"total": 500, "women": 120, "men": 90}}}})
fs = run_metadata_rules(r)
check("total 500 con 120+90 desagregados NO se flaggea",
      outcome(fs, "innovuse.count.gender_disaggregation") == Outcome.PASSED,
      str(outcome(fs, "innovuse.count.gender_disaggregation")))

r = build(IU, **{"sections.type_specific": {"fields": {
    "Number of people using": {"total": 500}}}})
check("sin women ni men SÍ se flaggea",
      outcome(run_metadata_rules(r), "innovuse.count.gender_disaggregation") == Outcome.FLAGGED)


print("\n--- Impact areas: la asimetría pilar/tag ---")
r = build(ID, **{
    "impact_areas": [{"name": "Climate adaptation and mitigation", "score": "2 — Principal",
                      "subcomponents": ["Adaptation"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": []}]})
check("Climate=2 sin tag posible NO se flaggea (no existe tag de Climate)",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.PASSED)

r = build(ID, **{
    "impact_areas": [{"name": "Gender equality, youth and social inclusion",
                      "score": "2 — Principal", "subcomponents": ["Youth"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": ["Youth"]}]})
check("Gender=2 con evidencia tag 'Youth' pasa (Youth mapea a Gender)",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.PASSED)

r = build(ID, **{
    "impact_areas": [{"name": "Poverty reduction, livelihoods and jobs",
                      "score": "2 — Principal", "subcomponents": ["Jobs"]}],
    "sections.evidence": [{"description": "e", "link": "https://x.org/a", "source": "url",
                           "visibility": "public", "tags": ["Gender"]}]})
check("Poverty=2 con solo evidencia Gender SÍ se flaggea",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") == Outcome.FLAGGED)

r = build(ID)
check("sin impact areas el criterio se omite (no aparece)",
      outcome(run_metadata_rules(r), "generic.impact_area.score2_evidence") is None)


print("\n--- Evidencia: dominios bloqueados y repositorio ---")
r = build(ID, **{"sections.evidence": [
    {"description": "a", "link": "https://cgiar.sharepoint.com/:b:/s/x", "source": "url",
     "tags": []}]})   # sin visibility: URL pegada, no viene del repositorio
check("SharePoint pegado como URL se flaggea",
      outcome(run_metadata_rules(r), "generic.evidence.blocked_domain") == Outcome.FLAGGED)

r = build(ID, **{"sections.evidence": [
    {"description": "a", "link": None, "source": "prms_repository",
     "visibility": "private", "tags": []}]})
check("repositorio PRMS sin link NO se flaggea (es la vía sancionada)",
      outcome(run_metadata_rules(r), "generic.evidence.blocked_domain") == Outcome.PASSED)

r = build(ID, **{"sections.evidence": [
    {"description": f"e{i}", "link": f"https://x.org/{i}", "source": "url",
     "visibility": "public", "tags": []} for i in range(7)]})
check("7 evidencias se flaggea (máximo 6)",
      outcome(run_metadata_rules(r), "generic.evidence.max_items") == Outcome.FLAGGED)


print("\n--- Futuro y falsos positivos ---")
for desc, expected, why in [
    ("The team will deliver the toolkit next year.", Outcome.FLAGGED, "'will' se detecta"),
    ("The project generated goodwill among farmers in Williams county.",
     Outcome.PASSED, "'goodwill'/'Williams' NO son falsos positivos"),
    ("The variety was released and adopted by 200 farmers.", Outcome.PASSED, "pasado limpio"),
]:
    r = build(ID, **{"sections.general_information": {
        "title": "T", "description": desc + " " + " ".join(["word"] * 60)}})
    got = outcome(run_metadata_rules(r), "generic.description.future_tense")
    check(why, got == expected, f"esperado {expected}, obtenido {got}")


print("\n--- Capacity Sharing: evidencia condicionada a IA=2 ---")
r = build(CS, **{"sections.type_specific": {"fields": {
    "Delivery method": "In person", "Length of training": "Short-term",
    "Number of people trained": {"total": 40, "female": 20, "male": 20}}}})
check("sin IA=2 la evidencia queda NOT_EVALUATED (gris)",
      outcome(run_metadata_rules(r), "capsharing.evidence.ia_score2_required") == Outcome.NOT_EVALUATED)

r = build(CS, **{
    "impact_areas": [{"name": "Gender equality, youth and social inclusion",
                      "score": "2 — Principal", "subcomponents": ["Gender equality"]}],
    "sections.type_specific": {"fields": {
        "Delivery method": "In person", "Length of training": "Short-term",
        "Number of people trained": {"total": 40, "female": 20, "male": 20}}}})
check("con IA=2 y sin evidencia SÍ se flaggea (core -> RED)",
      outcome(run_metadata_rules(r), "capsharing.evidence.ia_score2_required") == Outcome.FLAGGED)


print("\n--- Integración: un resultado limpio sale verde ---")
r = build(ID, **{"sections.type_specific": {"fields": {
    "Innovation typology": "Technological", "Readiness level": "Level 6 — …",
    "Innovation developers": "DRABO Inoussa, CIMMYT"}}})
fs = run_metadata_rules(r) + run_evidence_rules(r, {})
res = aggregate(fs, sections_for("Innovation development"))
code_flags = [f.criterion_id for f in fs if f.is_flag]
check("ningún criterio de código se dispara sobre un payload correcto",
      not code_flags, f"flags: {code_flags}")

print("\n--- Bloqueo de dominios: el flag de visibilidad manda ---")
PRMS_LINK = ("https://cgiar.sharepoint.com/:b:/s/OneCGIARPRMSRepository/"
             "IQDguq1lCiU8QZH-XvEUh1OuAYQYI")
OTRO_SP = "https://cgiar.sharepoint.com/:x:/s/MiEquipo/a.xlsx"

def blocked_outcome(item):
    r = build(ID, **{"sections.evidence": [item]})
    return outcome(run_metadata_rules(r), "generic.evidence.blocked_domain")

# Con flag de visibilidad -> viene del repositorio PRMS -> nunca se bloquea.
for link, vis, label in [
    (PRMS_LINK, "public",  "repositorio PRMS público"),
    (PRMS_LINK, "private", "repositorio PRMS privado"),
    (OTRO_SP,   "public",  "otro SharePoint pero CON flag"),
]:
    check(f"con flag ({label}) -> no se bloquea",
          blocked_outcome({"description": "d", "link": link, "source": "url",
                           "visibility": vis, "tags": []}) == Outcome.PASSED)

# Sin flag -> URL pegada por el usuario -> se aplica la lista del documento.
check("sin flag, SharePoint ajeno -> se bloquea",
      blocked_outcome({"description": "d", "link": OTRO_SP, "source": "url",
                       "tags": []}) == Outcome.FLAGGED)
check("sin flag, Google Drive -> se bloquea",
      blocked_outcome({"description": "d", "link": "https://drive.google.com/file/d/a/view",
                       "source": "url", "tags": []}) == Outcome.FLAGGED)
check("sin flag, CGSpace -> no se bloquea",
      blocked_outcome({"description": "d", "link": "https://hdl.handle.net/10568/1",
                       "source": "url", "tags": []}) == Outcome.PASSED)

r = build(ID, **{"sections.evidence": [
    {"description": "d", "link": OTRO_SP, "source": "url", "tags": []}]})
msg = [f.comment for f in run_metadata_rules(r)
       if f.criterion_id == "generic.evidence.blocked_domain"][0]
check("el mensaje ya no dice 'usa el repositorio' a quien lo está usando",
      "personal file-sharing" in msg and "(item" not in msg, msg[:70])

print(f"\n{'='*60}\n{len(PASSED)} pasaron, {len(FAILED)} fallaron")
if FAILED:
    for f in FAILED: print("  FALLÓ:", f)
    sys.exit(1)
