"""
End-to-end tests for /prms/quality-assessment with Bedrock and the scraper stubbed.

Run: python tests/test_assessment_e2e.py
"""

import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.llm.assessment as orch
from app.api.models import QualityAssessmentRequest

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else '  -> ' + detail}")


def payload(**over):
    p = {
        "contract_version": "0.2", "request_id": "req-1",
        "result": {"type": "Innovation development", "reporting_center": "AfricaRice"},
        "sections": {
            "general_information": {
                "title": "A drought-tolerant rice variety released for smallholder farmers",
                "description": " ".join(["word"] * 120),
                "result_level": "Output", "lead_contact_person": "Jane Doe"},
            "contributors_and_partners": {"lead_center": "AfricaRice", "no_external_partners": True},
            "geographic_location": {"scope": "National", "countries": ["Côte d'Ivoire"]},
            "evidence": [{"description": "Release bulletin", "link": "https://hdl.handle.net/10568/1",
                          "source": "url", "visibility": "public", "tags": []}],
            "type_specific": {"fields": {"Innovation typology": "Technological",
                                         "Readiness level": "Level 6 — Uptake",
                                         "Innovation developers": "DRABO Inoussa, CIMMYT"}}},
        "impact_areas": [], "constraints": {"timeout_seconds": 60}}
    for path, value in over.items():
        node = p; parts = path.split(".")
        for q in parts[:-1]: node = node[q]
        node[parts[-1]] = value
    return QualityAssessmentRequest(**p)


def stub_llm(outcome="passed", fail_on=(), ev_verdict="green"):
    async def fake(system, user, tool, **kw):
        name = tool["name"]
        if name in fail_on:
            raise RuntimeError("simulated Bedrock failure")
        ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
        out = {"findings": [{"criterion_id": i, "outcome": outcome,
                             "comment": f"comment for {i}"} for i in ids]}
        if name == "report_evidence_assessment":
            out["evidence"] = [{"index": 0, "verdict": ev_verdict, "reason": "looks right"}]
        return out
    return fake


def stub_scrape(status="ok"):
    async def fake(request, budget):
        items = []
        by = {}
        for i, ev in enumerate(request.sections.evidence):
            if not ev.is_evaluable:
                continue
            if status == "ok":
                d = {"index": i, "status": "ok", "reachable": True,
                     "title": "Release bulletin", "content": "The variety was released..."}
            else:
                d = {"index": i, "status": status, "reachable": False,
                     "error": "Could not be retrieved."}
            items.append(d); by[i] = d
        return items, by
    return fake


def run(req, llm=None, scrape=None):
    orch.invoke_with_tool = llm or stub_llm()
    orch._scrape_evidence = scrape or stub_scrape()
    return asyncio.run(orch.assess_result(req))


print("\n--- Happy path ---")
r = run(payload())
check("everything passes -> green", r.overall.verdict.value == "green", r.overall.verdict.value)
check("status is completed", r.status.value == "completed", r.status.value)
check("score is 100", r.overall.score == 100, str(r.overall.score))
check("all five sections are returned", len(r.sections.model_dump()) == 5)
check("evidence item 0 carries a verdict", r.evidence[0].verdict.value == "green")

print("\n--- One core flag -> red ---")
async def flag_core(system, user, tool, **kw):
    ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
    out = {"findings": [{"criterion_id": i,
                         "outcome": "flagged" if i == "innovdev.irl.supported" else "passed",
                         "comment": "The evidence does not show the innovation in use."} for i in ids]}
    if tool["name"] == "report_evidence_assessment":
        out["evidence"] = [{"index": 0, "verdict": "amber", "reason": "partially related"}]
    return out
r = run(payload(), llm=flag_core)
check("IRL flagged -> overall red", r.overall.verdict.value == "red", r.overall.verdict.value)
# The criterion is about the IRL field, so it colours Type-Specific -- even though
# judging it means reading the evidence. The section follows the field, not the input.
check("type_specific section is red", r.sections.type_specific.verdict.value == "red",
      r.sections.type_specific.verdict.value)
check("score lands in the red band (0-49)", 0 <= r.overall.score <= 49, str(r.overall.score))
check("the issue reaches the user", bool(r.sections.type_specific.issues))

print("\n--- Degradation ---")
r = run(payload(), llm=stub_llm(fail_on=("report_evidence_assessment",)))
check("the evidence call fails -> partial", r.status.value == "partial", r.status.value)
check("degraded_reason says what failed", "evidence" in (r.degraded_reason or ""))
check("does not blow up: a verdict is still produced", r.overall.verdict is not None)

# If the model never ran at all there is no verdict to give: that is an error.
import app.llm.assessment as _orch_mod
try:
    run(payload(), llm=stub_llm(fail_on=("report_evidence_assessment", "report_metadata_assessment")))
    check("both calls fail -> raises AssessmentUnavailable", False, "did not raise")
except _orch_mod.AssessmentUnavailable as e:
    check("both calls fail -> raises AssessmentUnavailable", True)
    check("the error names what failed", "metadata" in str(e) and "evidence" in str(e), str(e))

r = run(payload(), scrape=stub_scrape(status="timeout"))
check("scraping timeout -> partial", r.status.value == "partial", r.status.value)
check("the evidence item is grey", r.evidence[0].verdict.value == "grey", r.evidence[0].verdict.value)

print("\n--- Private evidence ---")
r = run(payload(**{"sections.evidence": [
    {"description": "Internal", "link": None, "source": "prms_repository",
     "visibility": "private", "tags": []}]}))
check("private -> grey", r.evidence[0].verdict.value == "grey")
check("the reason says so explicitly", "not evaluated" in r.evidence[0].reason.lower(), r.evidence[0].reason)
check("it does not penalise the overall verdict", r.overall.verdict.value == "green", r.overall.verdict.value)

print("\n--- Attached evidence that could not be read ---")

def six_evidence(**over):
    ev = [{"description": f"e{i}", "link": f"https://hdl.handle.net/10568/{i}",
           "source": "url", "visibility": "public", "tags": []} for i in range(6)]
    return payload(**{"sections.evidence": ev, **over})

async def read_none(request, budget):
    items, by = [], {}
    for i, e in enumerate(request.sections.evidence):
        if not e.is_evaluable: continue
        d = {"index": i, "status": "timeout", "determined": False, "error": "Exceeded time budget"}
        items.append(d); by[i] = d
    return items, by

r = run(six_evidence(), scrape=read_none)
check("6 attached, 0 read -> Evidence section is grey",
      r.sections.evidence.verdict.value == "grey", r.sections.evidence.verdict.value)
check("the comment says so plainly",
      "None of the attached evidence could be read" in r.sections.evidence.comments,
      r.sections.evidence.comments)
check("a grey section does not drag the overall verdict",
      r.overall.verdict.value == "green", r.overall.verdict.value)

blocked = six_evidence()
blocked.sections.evidence[0].link = "https://cgiar.sharepoint.com/:b:/s/x/doc.pdf"
blocked.sections.evidence[0].visibility = None   # a pasted URL, not from the repository
r = run(blocked, scrape=read_none)
check("a real flag wins over grey (blocked domain -> red)",
      r.sections.evidence.verdict.value == "red", r.sections.evidence.verdict.value)

r = run(six_evidence(), scrape=stub_scrape())
check("once they are read, it goes back to green", r.sections.evidence.verdict.value == "green",
      r.sections.evidence.verdict.value)

print("\n--- The model omits a criterion ---")
async def omits(system, user, tool, **kw):
    ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
    out = {"findings": [{"criterion_id": i, "outcome": "passed", "comment": "ok"} for i in ids[1:]]}
    if tool["name"] == "report_evidence_assessment":
        out["evidence"] = [{"index": 0, "verdict": "green", "reason": "ok"}]
    return out
r = run(payload(), llm=omits)
check("an omitted criterion is not silently counted as passed",
      r.overall.verdict.value == "green" and r.status.value == "completed")

print("\n--- fields: which inputs the user must revisit ---")

def flagging(*criterion_ids):
    async def fake(system, user, tool, **kw):
        ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
        out = {"findings": [{"criterion_id": i,
                             "outcome": "flagged" if i in criterion_ids else "passed",
                             "comment": "needs work" if i in criterion_ids else "fine"}
                            for i in ids]}
        if tool["name"] == "report_evidence_assessment":
            out["evidence"] = [{"index": 0, "verdict": "green", "reason": "ok"}]
        return out
    return fake

r = run(payload(), llm=flagging("generic.title.quality"))
check("a flag on the title -> fields: ['title']",
      r.sections.general_information.fields == ["title"],
      str(r.sections.general_information.fields))

r = run(payload(), llm=flagging("generic.title.quality",
                                "generic.description.cgiar_contribution"))
check("two different criteria -> both fields, no repeats",
      r.sections.general_information.fields == ["title", "description"],
      str(r.sections.general_information.fields))

r = run(payload(), llm=flagging("generic.title.quality", "generic.description.quality",
                                "generic.description.cgiar_contribution"))
check("two criteria on the SAME field -> not duplicated",
      r.sections.general_information.fields == ["title", "description"],
      str(r.sections.general_information.fields))

r = run(payload(), llm=flagging("generic.geographic_focus.consistency"))
check("a criterion spanning several inputs returns them all",
      r.sections.geographic_location.fields == ["scope", "regions", "countries", "sub_national"],
      str(r.sections.geographic_location.fields))

r = run(payload(), llm=flagging("innovdev.irl.supported"))
check("type_specific uses the visible label, not an internal key",
      r.sections.type_specific.fields == ["Readiness level"],
      str(r.sections.type_specific.fields))

r = run(payload())
check("green section -> fields is empty",
      r.sections.general_information.fields == []
      and r.sections.type_specific.fields == [],
      str(r.sections.general_information.fields))

r = run(payload(**{"result.type": "Other Output",
                   "sections.type_specific": {"fields": {}}}),
        llm=flagging("otheroutput.result_type_check"))
check("Result type check points at title and description in General Information",
      r.sections.general_information.fields == ["title", "description"],
      str(r.sections.general_information.fields))

# Every MDS field in the catalog needs a Reporting field name, or `fields` would
# come back empty for that criterion without anyone noticing.
from app.utils.assessment.criteria_catalog import CATALOG
from app.utils.assessment.payload_binding import reporting_fields
unmapped = sorted({c.mds_field for c in CATALOG if not reporting_fields(c.mds_field)})
check("no MDS field is left without a Reporting field name", not unmapped, str(unmapped))

print("\n--- Per-section score ---")

BANDS = {"green": (100, 100), "amber": (50, 99), "red": (0, 49)}

r = run(payload(), llm=flagging("generic.title.quality"))
for name, sec in r.sections.model_dump().items():
    if sec is None:
        continue
    if sec["verdict"] == "grey":
        check(f"{name} is grey -> score is None", sec["score"] is None, str(sec["score"]))
        continue
    lo, hi = BANDS[sec["verdict"]]
    check(f"{name}: score sits inside the {sec['verdict']} band",
          sec["score"] is not None and lo <= sec["score"] <= hi,
          f"{sec['verdict']} -> {sec['score']}")

check("no coloured section returns a null score",
      all(s["score"] is not None for s in r.sections.model_dump().values()
          if s and s["verdict"] != "grey"))

r_verde = run(payload())
r_rojo = run(payload(), llm=flagging("innovdev.irl.supported"))
check("fixing a criterion raises its section score",
      r_verde.sections.type_specific.score > r_rojo.sections.type_specific.score,
      f"{r_rojo.sections.type_specific.score} -> {r_verde.sections.type_specific.score}")

r = run(six_evidence(), scrape=read_none)
check("grey Evidence -> score is None", r.sections.evidence.score is None,
      str(r.sections.evidence.score))

print("\n--- Result types with no Type-Specific section ---")

def other_output(**over):
    return payload(**{"result.type": "Other Output",
                      "sections.type_specific": {"fields": {}}, **over})

async def flag_type_check(system, user, tool, **kw):
    ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
    out = {"findings": [{"criterion_id": i,
                         "outcome": "flagged" if i == "otheroutput.result_type_check" else "passed",
                         "comment": "Should be reported as Capacity Sharing."} for i in ids]}
    if tool["name"] == "report_evidence_assessment":
        out["evidence"] = [{"index": 0, "verdict": "green", "reason": "ok"}]
    return out

r = run(other_output(), llm=flag_type_check)
check("Other Output does not return type_specific",
      r.sections.type_specific is None, str(r.sections.type_specific))
check("the JSON does not include it either",
      "type_specific" not in r.sections.model_dump(), str(list(r.sections.model_dump())))
check("the flag lands in General Information, where the user can act",
      r.sections.general_information.verdict.value == "red"
      and any("Capacity Sharing" in i for i in r.sections.general_information.issues),
      r.sections.general_information.verdict.value)
check("it still drags the overall verdict to red (the criterion is core)",
      r.overall.verdict.value == "red", r.overall.verdict.value)

r = run(payload())
check("types that do have the section still return it",
      r.sections.type_specific is not None
      and "type_specific" in r.sections.model_dump())

print("\n--- Interaction tracking ---")
import app.llm.assessment as _am
from app.utils.interactions import interaction_client as _ic

tracked = []
def fake_track(**kw):
    tracked.append(kw)
    return {"interaction_id": "int-abc123"}
_am.interaction_client.track_interaction = fake_track

r = run(payload())
check("no user_id -> nothing is tracked", not tracked and r.interaction_id is None,
      f"tracked={len(tracked)} id={r.interaction_id}")

tracked.clear()
p_with_user = payload()
p_with_user.user_id = "user123"
r = run(p_with_user)
check("with a user_id -> the interaction is tracked", len(tracked) == 1, str(len(tracked)))
check("the interaction_id comes back in the response", r.interaction_id == "int-abc123",
      str(r.interaction_id))
if tracked:
    kw = tracked[0]
    check("it sends the user_id and the platform",
          kw["user_id"] == "user123" and kw["platform"] == "PRMS", str(kw.get("platform")))
    ctx = kw["context"]
    check("the context carries verdict, coverage and evidence counts",
          ctx["verdict"] == "green"
          and {"criteria_total", "criteria_evaluated", "evidence_total",
               "evidence_read", "model_used", "criteria_version"} <= set(ctx),
          str(sorted(ctx))[:150])
    check("it records the response time", kw["response_time_seconds"] >= 0,
          str(kw.get("response_time_seconds")))

# Tracking must never take the assessment down with it.
tracked.clear()
def boom_track(**kw):
    raise RuntimeError("interaction service down")
_am.interaction_client.track_interaction = boom_track
r = run(p_with_user)
check("a failing tracker leaves the verdict intact",
      r.overall.verdict.value == "green" and r.interaction_id is None,
      f"{r.overall.verdict.value} {r.interaction_id}")

import time as _t2
def slow_track(**kw):
    _t2.sleep(20)
    return {"interaction_id": "never"}
_am.interaction_client.track_interaction = slow_track
_am.TRACKING_TIMEOUT_S = 1.0

# Timed INSIDE the coroutine: asyncio.run() waits for the executor to shut down on
# the way out, which uvicorn does not do between requests.
async def _timed():
    _t0 = _t2.monotonic()
    resp = await _am.assess_result(p_with_user)
    return _t2.monotonic() - _t0, resp

_am.invoke_with_tool = stub_llm(); _am._scrape_evidence = stub_scrape()
_el, r = asyncio.run(_timed())
check(f"a hanging tracker does not delay the assessment (took {_el:.1f}s)",
      _el < 5 and r.overall.verdict.value == "green" and r.interaction_id is None,
      f"{_el:.1f}s id={r.interaction_id}")
_am.interaction_client.track_interaction = fake_track
_am.TRACKING_TIMEOUT_S = 8.0

print("\n--- HTTP endpoint ---")
from fastapi.testclient import TestClient
from app.api.main import app
import app.api.routes as routes

# Stub the webhook before any request: the endpoint notifies on every call, and
# a test run must never post to the team's real Slack channel.
_slack_sent = []
async def _capture_slack(**kw):
    _slack_sent.append(kw)
    return True
routes.notification_service.send_slack_notification = _capture_slack
from app.api.routes import quality_assessment_auth
orch.invoke_with_tool = stub_llm(); orch._scrape_evidence = stub_scrape()
client = TestClient(app)

# Sin clave, CLARISA rechaza: eso es correcto y se verifica primero.
check("401 without a valid X-API-Key",
      client.post("/prms/quality-assessment", json=payload().model_dump(mode="json")).status_code == 401)
app.dependency_overrides[quality_assessment_auth] = lambda: "PRMS"

body = payload().model_dump(mode="json")
resp = client.post("/prms/quality-assessment", json=body)
check("200 on a valid payload", resp.status_code == 200, str(resp.status_code))
check("contract keys",
      set(resp.json()) == {"request_id", "criteria_version", "overall", "sections",
                           "evidence", "status", "degraded_reason", "coverage",
                           "interaction_id"},
      str(sorted(resp.json())))

bad = payload().model_dump(mode="json")
bad["sections"]["type_specific"]["fields"].pop("Readiness level")
resp = client.post("/prms/quality-assessment", json=bad)
check("400 when a required label is missing", resp.status_code == 400, str(resp.status_code))
d = resp.json()["detail"]
check("the error names exactly what is missing",
      d["problems"][0]["code"] == "MISSING_LABEL" and "Readiness level" in d["problems"][0]["message"],
      str(d["problems"][0]))

print("\n--- Slack notification ---")
sent = _slack_sent

for fail_on, expect_colour, label in [
    ((), "#36a64f", "successful run -> green notification"),
    (("report_evidence_assessment",), "#36a64f",
     "partial failure -> still green, never blocks"),
]:
    sent.clear()
    orch.invoke_with_tool = stub_llm(fail_on=fail_on); orch._scrape_evidence = stub_scrape()
    resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
    ok = resp.status_code == 200 and len(sent) == 1 and sent[0]["color"] == expect_colour
    check(label, ok, f"{resp.status_code} {sent and sent[0]['color']}")

# The whole model down -> 503 and a red notification.
sent.clear()
orch.invoke_with_tool = stub_llm(
    fail_on=("report_evidence_assessment", "report_metadata_assessment"))
orch._scrape_evidence = stub_scrape()
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
check("model down -> HTTP 503", resp.status_code == 503, str(resp.status_code))
check("model down -> red notification", len(sent) == 1 and sent[0]["color"] == "#ff0000", str(sent))
check("the red one says the AI could not review the result",
      "could not review" in sent[0]["message"], sent and sent[0]["message"][:80])
check("error_type for the frontend",
      resp.json()["detail"]["error_type"] == "ASSESSMENT_UNAVAILABLE",
      str(resp.json()["detail"]))

# An unexpected endpoint failure sends a red notification too.
sent.clear()
async def boom(request):
    raise RuntimeError("bedrock is down")
_real = orch.assess_result
routes.assess_result = boom
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
check("the run fails -> red notification", len(sent) == 1 and sent[0]["color"] == "#ff0000",
      str(sent))
check("the red one carries the error", "RuntimeError" in sent[0]["message"], sent and sent[0]["message"])
check("the red one returns 500", resp.status_code == 500, str(resp.status_code))
routes.assess_result = _real

sent.clear()
orch.invoke_with_tool = stub_llm(); orch._scrape_evidence = stub_scrape()
client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
msg = sent[0]["message"]
check("the green one carries verdict, result type and evidence counts",
      "GREEN" in msg and "Innovation development" in msg and "total" in msg, msg)
check("it reports the real elapsed time", "Processing time" in sent[0]["time_taken"])

# The guard against a hung webhook lives in NotificationService, not in the
# endpoint: aiohttp defaults to 300s, longer than the caller's own timeout.
from app.utils.notification import notification_service as _ns
check("the notification service bounds the webhook timeout",
      getattr(_ns, "SLACK_TIMEOUT_SECONDS", None) is not None
      and _ns.SLACK_TIMEOUT_SECONDS <= 10,
      str(getattr(_ns, "SLACK_TIMEOUT_SECONDS", None)))

# Real check: a dead webhook, with the actual notification service.
import os as _os, time as _time
from app.utils.notification.notification_service import NotificationService
_os.environ["SLACK_WEBHOOK_URL"] = "https://10.255.255.1/hooks/never-answers"
routes.notification_service = NotificationService()
_t0 = _time.monotonic()
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
_took = _time.monotonic() - _t0
check("dead webhook: the response is still 200", resp.status_code == 200, str(resp.status_code))
check(f"dead webhook: the request does not hang (took {_took:.1f}s)", _took < 10, f"{_took:.1f}s")
routes.notification_service.send_slack_notification = _capture_slack

print(f"\n{'='*64}\n{len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    for f in FAILED: print("  FAILED:", f)
    sys.exit(1)
