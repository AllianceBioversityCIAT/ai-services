"""
End-to-end tests for /prms/quality-assessment with Bedrock and the scraper stubbed.

Run: python tests/test_assessment_e2e.py
"""

import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.llm.assessment as orch
from app.api.assessment_models import QualityAssessmentRequest

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


print("\n--- Camino feliz ---")
r = run(payload())
check("todo pasa -> green", r.overall.verdict.value == "green", r.overall.verdict.value)
check("status completed", r.status.value == "completed", r.status.value)
check("score 100", r.overall.score == 100, str(r.overall.score))
check("las 5 secciones vienen", len(r.sections.model_dump()) == 5)
check("evidencia [0] con veredicto", r.evidence[0].verdict.value == "green")

print("\n--- Un flag core -> rojo ---")
async def flag_core(system, user, tool, **kw):
    ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
    out = {"findings": [{"criterion_id": i,
                         "outcome": "flagged" if i == "innovdev.irl.supported" else "passed",
                         "comment": "The evidence does not show the innovation in use."} for i in ids]}
    if tool["name"] == "report_evidence_assessment":
        out["evidence"] = [{"index": 0, "verdict": "amber", "reason": "partially related"}]
    return out
r = run(payload(), llm=flag_core)
check("IRL flaggeado -> overall red", r.overall.verdict.value == "red", r.overall.verdict.value)
# El criterio es sobre el campo IRL, así que pinta Type-Specific -- aunque para
# juzgarlo haya que leer la evidencia. La sección la define el campo, no el input.
check("sección type_specific en red", r.sections.type_specific.verdict.value == "red",
      r.sections.type_specific.verdict.value)
check("score en banda roja (0-49)", 0 <= r.overall.score <= 49, str(r.overall.score))
check("el issue llega al usuario", bool(r.sections.type_specific.issues))

print("\n--- Degradación ---")
r = run(payload(), llm=stub_llm(fail_on=("report_evidence_assessment",)))
check("falla la llamada de evidencia -> partial", r.status.value == "partial", r.status.value)
check("degraded_reason explica qué falló", "evidence" in (r.degraded_reason or ""))
check("no revienta: sigue habiendo veredicto", r.overall.verdict is not None)

# Si el modelo no corrió en absoluto, no hay veredicto que dar: es un error.
import app.llm.assessment as _orch_mod
try:
    run(payload(), llm=stub_llm(fail_on=("report_evidence_assessment", "report_metadata_assessment")))
    check("fallan ambas -> lanza AssessmentUnavailable", False, "no lanzó")
except _orch_mod.AssessmentUnavailable as e:
    check("fallan ambas -> lanza AssessmentUnavailable", True)
    check("el error dice qué falló", "metadata" in str(e) and "evidence" in str(e), str(e))

r = run(payload(), scrape=stub_scrape(status="timeout"))
check("scraping con timeout -> partial", r.status.value == "partial", r.status.value)
check("evidencia queda gris", r.evidence[0].verdict.value == "grey", r.evidence[0].verdict.value)

print("\n--- Evidencia privada ---")
r = run(payload(**{"sections.evidence": [
    {"description": "Internal", "link": None, "source": "prms_repository",
     "visibility": "private", "tags": []}]}))
check("privada -> grey", r.evidence[0].verdict.value == "grey")
check("razón explícita", "not evaluated" in r.evidence[0].reason.lower(), r.evidence[0].reason)
check("no penaliza el global", r.overall.verdict.value == "green", r.overall.verdict.value)

print("\n--- Evidencia adjunta que no se pudo leer ---")

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
check("6 adjuntas, 0 leídas -> sección Evidence en gris",
      r.sections.evidence.verdict.value == "grey", r.sections.evidence.verdict.value)
check("el comentario lo dice claro",
      "None of the attached evidence could be read" in r.sections.evidence.comments,
      r.sections.evidence.comments)
check("el gris de sección no arrastra el global",
      r.overall.verdict.value == "green", r.overall.verdict.value)

blocked = six_evidence()
blocked.sections.evidence[0].link = "https://cgiar.sharepoint.com/:b:/s/x/doc.pdf"
r = run(blocked, scrape=read_none)
check("un flag real gana sobre el gris (dominio bloqueado -> rojo)",
      r.sections.evidence.verdict.value == "red", r.sections.evidence.verdict.value)

r = run(six_evidence(), scrape=stub_scrape())
check("si se leen, vuelve a verde", r.sections.evidence.verdict.value == "green",
      r.sections.evidence.verdict.value)

print("\n--- El modelo omite un criterio ---")
async def omits(system, user, tool, **kw):
    ids = tool["input_schema"]["properties"]["findings"]["items"]["properties"]["criterion_id"]["enum"]
    out = {"findings": [{"criterion_id": i, "outcome": "passed", "comment": "ok"} for i in ids[1:]]}
    if tool["name"] == "report_evidence_assessment":
        out["evidence"] = [{"index": 0, "verdict": "green", "reason": "ok"}]
    return out
r = run(payload(), llm=omits)
check("criterio omitido no cuenta como aprobado en silencio",
      r.overall.verdict.value == "green" and r.status.value == "completed")

print("\n--- Tracking de interacción ---")
import app.llm.assessment as _am
from app.utils.interactions import interaction_client as _ic

tracked = []
def fake_track(**kw):
    tracked.append(kw)
    return {"interaction_id": "int-abc123"}
_am.interaction_client.track_interaction = fake_track

r = run(payload())
check("sin user_id no se trackea", not tracked and r.interaction_id is None,
      f"tracked={len(tracked)} id={r.interaction_id}")

tracked.clear()
p_with_user = payload()
p_with_user.user_id = "user123"
r = run(p_with_user)
check("con user_id sí se trackea", len(tracked) == 1, str(len(tracked)))
check("el interaction_id vuelve en la respuesta", r.interaction_id == "int-abc123",
      str(r.interaction_id))
if tracked:
    kw = tracked[0]
    check("manda user_id y plataforma",
          kw["user_id"] == "user123" and kw["platform"] == "PRMS", str(kw.get("platform")))
    ctx = kw["context"]
    check("el contexto lleva veredicto, cobertura y evidencias",
          ctx["verdict"] == "green"
          and {"criteria_total", "criteria_evaluated", "evidence_total",
               "evidence_read", "model_used", "criteria_version"} <= set(ctx),
          str(sorted(ctx))[:150])
    check("registra el tiempo de respuesta", kw["response_time_seconds"] >= 0,
          str(kw.get("response_time_seconds")))

# El tracking nunca puede tumbar la evaluación.
tracked.clear()
def boom_track(**kw):
    raise RuntimeError("interaction service down")
_am.interaction_client.track_interaction = boom_track
r = run(p_with_user)
check("si el tracking falla, el veredicto sale igual",
      r.overall.verdict.value == "green" and r.interaction_id is None,
      f"{r.overall.verdict.value} {r.interaction_id}")

import time as _t2
def slow_track(**kw):
    _t2.sleep(20)
    return {"interaction_id": "never"}
_am.interaction_client.track_interaction = slow_track
_am.TRACKING_TIMEOUT_S = 1.0

# El tiempo se mide DENTRO de la corrutina: asyncio.run() espera al cierre del
# executor al salir, cosa que uvicorn no hace entre peticiones.
async def _timed():
    _t0 = _t2.monotonic()
    resp = await _am.assess_result(p_with_user)
    return _t2.monotonic() - _t0, resp

_am.invoke_with_tool = stub_llm(); _am._scrape_evidence = stub_scrape()
_el, r = asyncio.run(_timed())
check(f"un tracking colgado no retrasa la evaluación (tardó {_el:.1f}s)",
      _el < 5 and r.overall.verdict.value == "green" and r.interaction_id is None,
      f"{_el:.1f}s id={r.interaction_id}")
_am.interaction_client.track_interaction = fake_track
_am.TRACKING_TIMEOUT_S = 8.0

print("\n--- Endpoint HTTP ---")
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
check("401 sin X-API-Key válida",
      client.post("/prms/quality-assessment", json=payload().model_dump(mode="json")).status_code == 401)
app.dependency_overrides[quality_assessment_auth] = lambda: "PRMS"

body = payload().model_dump(mode="json")
resp = client.post("/prms/quality-assessment", json=body)
check("200 en payload válido", resp.status_code == 200, str(resp.status_code))
check("llaves del contrato",
      set(resp.json()) == {"request_id", "criteria_version", "overall", "sections",
                           "evidence", "status", "degraded_reason", "coverage",
                           "interaction_id"},
      str(sorted(resp.json())))

bad = payload().model_dump(mode="json")
bad["sections"]["type_specific"]["fields"].pop("Readiness level")
resp = client.post("/prms/quality-assessment", json=bad)
check("400 cuando falta una etiqueta obligatoria", resp.status_code == 400, str(resp.status_code))
d = resp.json()["detail"]
check("el error dice exactamente qué falta",
      d["problems"][0]["code"] == "MISSING_LABEL" and "Readiness level" in d["problems"][0]["message"],
      str(d["problems"][0]))

print("\n--- Notificación de Slack ---")
sent = _slack_sent

for fail_on, expect_colour, label in [
    ((), "#36a64f", "proceso exitoso -> notificación verde"),
    (("report_evidence_assessment",), "#36a64f",
     "falla parcial -> sigue siendo verde, no bloquea"),
]:
    sent.clear()
    orch.invoke_with_tool = stub_llm(fail_on=fail_on); orch._scrape_evidence = stub_scrape()
    resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
    ok = resp.status_code == 200 and len(sent) == 1 and sent[0]["color"] == expect_colour
    check(label, ok, f"{resp.status_code} {sent and sent[0]['color']}")

# El modelo entero caído -> 503 y notificación roja.
sent.clear()
orch.invoke_with_tool = stub_llm(
    fail_on=("report_evidence_assessment", "report_metadata_assessment"))
orch._scrape_evidence = stub_scrape()
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
check("modelo caído -> HTTP 503", resp.status_code == 503, str(resp.status_code))
check("modelo caído -> notificación roja", len(sent) == 1 and sent[0]["color"] == "#ff0000", str(sent))
check("el rojo dice que la IA no pudo revisar",
      "could not review" in sent[0]["message"], sent and sent[0]["message"][:80])
check("error_type para el frontend",
      resp.json()["detail"]["error_type"] == "ASSESSMENT_UNAVAILABLE",
      str(resp.json()["detail"]))

# Un fallo inesperado del endpoint manda rojo también.
sent.clear()
async def boom(request):
    raise RuntimeError("bedrock is down")
_real = orch.assess_result
routes.assess_result = boom
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
check("el proceso falla -> notificación roja", len(sent) == 1 and sent[0]["color"] == "#ff0000",
      str(sent))
check("el rojo lleva el error", "RuntimeError" in sent[0]["message"], sent and sent[0]["message"])
check("el rojo devuelve 500", resp.status_code == 500, str(resp.status_code))
routes.assess_result = _real

sent.clear()
orch.invoke_with_tool = stub_llm(); orch._scrape_evidence = stub_scrape()
client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
msg = sent[0]["message"]
check("el verde lleva veredicto, tipo y conteo de evidencias",
      "GREEN" in msg and "Innovation development" in msg and "total" in msg, msg)
check("reporta el tiempo real", "Processing time" in sent[0]["time_taken"])

# La protección contra un webhook colgado vive en NotificationService, no en el
# endpoint: aiohttp usa 300s por defecto, más que el timeout del propio cliente.
from app.utils.notification import notification_service as _ns
check("el servicio de notificaciones acota el tiempo del webhook",
      getattr(_ns, "SLACK_TIMEOUT_SECONDS", None) is not None
      and _ns.SLACK_TIMEOUT_SECONDS <= 10,
      str(getattr(_ns, "SLACK_TIMEOUT_SECONDS", None)))

# Prueba real: webhook muerto, con el servicio de notificaciones de verdad.
import os as _os, time as _time
from app.utils.notification.notification_service import NotificationService
_os.environ["SLACK_WEBHOOK_URL"] = "https://10.255.255.1/hooks/never-answers"
routes.notification_service = NotificationService()
_t0 = _time.monotonic()
resp = client.post("/prms/quality-assessment", json=payload().model_dump(mode="json"))
_took = _time.monotonic() - _t0
check("webhook muerto: la respuesta sigue siendo 200", resp.status_code == 200, str(resp.status_code))
check(f"webhook muerto: no cuelga la petición (tardó {_took:.1f}s)", _took < 10, f"{_took:.1f}s")
routes.notification_service.send_slack_notification = _capture_slack

print(f"\n{'='*64}\n{len(PASSED)} pasaron, {len(FAILED)} fallaron")
if FAILED:
    for f in FAILED: print("  FALLÓ:", f)
    sys.exit(1)
