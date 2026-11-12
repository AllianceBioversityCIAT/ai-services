import gzip
import json
from datetime import UTC, datetime

import boto3
import pytest
from botocore.stub import ANY, Stubber

from app.contract.fields import AI_FIELDS
from app.contract.items import AiSuggestionItem, suggestion_pk, suggestion_sk
from app.contract.messages import AiJobMessage
from app.evidence.extractor import EvidenceSource, summarize
from app.handlers.worker import handler
from app.llm.output_schema import SuggestionOutputV2
from app.llm.provider import LlmUsage, RetryableLlmError, SuggestionResult
from app.worker.process import JobDeps, RetryLater, process_job
from app.worker.snapshot import DynamoSnapshotReader, read_field_input
from app.worker.store import DynamoSuggestionStore
from tests.fakes import FakeLlmProvider

GENDER = "general.gender_tag"
SNAP = "2026#000012#00000003#0000000042"
QUOTE = "The project trained 1,200 women farmers in seed business management in 2025."
VALUES = {
    "general.title": "Women-led seed enterprises",
    "general.description": {"value": "Seed businesses run by women's groups."},
    GENDER: {"value": 3},
    "evidence.items": [
        {"source": 0, "link": "https://example.org/report", "gender_related": True},
        {"source": 0, "link": "https://example.org/other"},
        {"source": 1, "file_url": "https://example.org/file.pdf", "gender_related": {"value": True}},
    ],
}


class FakeSnapshots:
    def __init__(self, values=VALUES):
        self.data = {(1001, SNAP): values}

    def values(self, result_code, snap_key):
        return self.data.get((result_code, snap_key))


class FakeStore:
    def __init__(self):
        self.items: dict[tuple[str, str], AiSuggestionItem] = {}
        self.runs: dict[str, dict[str, int]] = {}

    def lookup(self, pk, sk):
        item = self.items.get((pk, sk))
        if item is None:
            return "absent"
        return "failed" if item.unavailableReason == "failed" else "done"

    def write(self, item, counter, replaces_failed=False):
        key = (item.pk, item.sk)
        current = self.items.get(key)
        if replaces_failed:
            if current is None or current.unavailableReason != "failed":
                return False
        elif current is not None:
            return False
        self.items[key] = item
        run = self.runs.setdefault(item.runId, {"produced": 0, "unavailable": 0, "failed": 0})
        run[counter] += 1
        if replaces_failed and counter != "failed":
            run["failed"] -= 1
        return True


class FakeExtractor:
    def __init__(self, sources):
        self.sources = sources
        self.cache = None
        self.calls: list[list[str]] = []

    def extract(self, urls):
        self.calls.append(urls)
        return summarize([s for s in self.sources if s.url in urls])


def text_source(i, url, text=QUOTE):
    return EvidenceSource(i, url, "text", text=text)


def ok(value=2, quote=QUOTE, index=0):
    out = SuggestionOutputV2(
        reasoning="r", value=value, component="Gender Equality", evidence_quote=quote,
        evidence_source_index=index, explanation="Women-led enterprises are the result's main objective.",
    )
    return SuggestionResult("ok", "anthropic.claude-haiku-5-5", LlmUsage(100, 20, 80, 0), out)


def deps(llm=None, sources=None, store=None, snapshots=None):
    return JobDeps(
        snapshots=snapshots or FakeSnapshots(),
        store=store or FakeStore(),
        extractor=FakeExtractor(sources if sources is not None else [text_source(0, "https://example.org/report")]),
        provider=llm or FakeLlmProvider(),
        effort="medium",
        max_tokens=4000,
        clock=lambda: datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
    )


def job(field=GENDER, version="v2-1.0.0", run="run-1"):
    return AiJobMessage(runId=run, resultCode="1001", snapKey=SNAP, fieldKey=field, promptVersion=version)


def stored(d, field=GENDER, version="v2-1.0.0") -> AiSuggestionItem:
    return d.store.items[(suggestion_pk(1001), suggestion_sk(SNAP, field, version))]


# ---- snapshot reading ----

def test_field_input_uses_flagged_links_and_maps_the_tag_level():
    fi = read_field_input(VALUES, GENDER, AI_FIELDS[GENDER])
    assert fi.title == "Women-led seed enterprises" and fi.description.startswith("Seed businesses")
    assert fi.reported == 2  # tag_levels id 3 = Principal
    assert fi.links == ["https://example.org/report", "https://example.org/file.pdf"]
    assert fi.evidence_scope == "field"


def test_without_flagged_links_all_result_links_are_used():
    fi = read_field_input(VALUES, "general.climate_tag", AI_FIELDS["general.climate_tag"])
    assert fi.evidence_scope == "result" and len(fi.links) == 3
    assert fi.reported is None  # not reported


def test_control_list_ids_map_to_levels_and_unknown_ids_are_not_guessed():
    irl, iul = "innovation_dev.readiness_level", "innovation_use.use_level.innovation_use_level"
    assert read_field_input({irl: {"value": 11}}, irl, AI_FIELDS[irl]).reported == 0
    assert read_field_input({irl: 20}, irl, AI_FIELDS[irl]).reported == 9
    assert read_field_input({iul: {"value": 1}}, iul, AI_FIELDS[iul]).reported == 0
    assert read_field_input({iul: {"value": 10}}, iul, AI_FIELDS[iul]).reported == 9
    fi = read_field_input({irl: {"value": 7}}, irl, AI_FIELDS[irl])  # 7 is not a readiness_levels id
    assert fi.reported is None and fi.links == [] and fi.evidence_scope == "none"


def test_dynamo_snapshot_reader_handles_plain_and_gzipped_values():
    client = boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
    reader = DynamoSnapshotReader("cgiar-qa-test", client)
    with Stubber(client) as stub:
        key = {"pk": {"S": "RESULT#1001"}, "sk": {"S": f"SNAP#{SNAP}"}}
        expected = {"TableName": "cgiar-qa-test", "Key": key, "ProjectionExpression": ANY, "ExpressionAttributeNames": ANY}
        stub.add_response("get_item", {"Item": {"values": {"S": json.dumps({"a": 1})}}}, expected)
        stub.add_response("get_item", {"Item": {"valuesGz": {"B": gzip.compress(b'{"b": 2}')}}}, expected)
        stub.add_response("get_item", {}, expected)
        assert reader.values(1001, SNAP) == {"a": 1}
        assert reader.values(1001, SNAP) == {"b": 2}
        assert reader.values(1001, SNAP) is None


# ---- one job ----

def test_available_suggestion_is_stored_with_signal_and_counted():
    d = deps(FakeLlmProvider().enqueue(ok()))
    rep = process_job(job(), d, final_attempt=False)
    item = stored(d)
    assert rep.outcome == "produced" and rep.signal == "green"
    assert item.status == "available" and item.signal == "green" and item.quoteVerified is True
    assert item.suggestedValue == 2 and item.reportedValue == 2
    assert item.evidenceSource == "https://example.org/report" and item.evidenceSourceIndex == 0
    assert item.keys_consistent() and item.createdAt == "2026-11-20T12:00:00Z"
    assert d.store.runs["run-1"] == {"produced": 1, "unavailable": 0, "failed": 0}
    assert d.extractor.calls == [["https://example.org/report", "https://example.org/file.pdf"]]


def test_duplicate_delivery_neither_calls_the_model_nor_counts_twice():
    llm = FakeLlmProvider().enqueue(ok())
    d = deps(llm)
    process_job(job(), d, final_attempt=False)
    rep = process_job(job(), d, final_attempt=False)
    assert rep.outcome == "duplicate" and len(llm.calls) == 1
    assert d.store.runs["run-1"]["produced"] == 1


def test_suggestion_id_is_deterministic():
    a, b = deps(FakeLlmProvider().enqueue(ok())), deps(FakeLlmProvider().enqueue(ok()))
    process_job(job(), a, False)
    process_job(job(), b, False)
    assert stored(a).suggestionId == stored(b).suggestionId


def test_unverified_quote_is_amber():
    d = deps(FakeLlmProvider().enqueue(ok(quote="A sentence that is not in the evidence at all.")))
    process_job(job(), d, False)
    assert stored(d).signal == "amber" and stored(d).quoteVerified is False


@pytest.mark.parametrize(
    ("sources", "reason"),
    [
        ([], "no_readable_evidence"),
        ([EvidenceSource(0, "https://example.org/report", "private", reason="authentication_required")], "private_link"),
        ([EvidenceSource(0, "https://example.org/report", "unreadable", reason="too_short")], "no_readable_evidence"),
    ],
)
def test_no_readable_evidence_is_unavailable_without_a_model_call(sources, reason):
    llm = FakeLlmProvider()
    d = deps(llm, sources=sources)
    rep = process_job(job(), d, False)
    assert rep.outcome == "unavailable" and llm.calls == []
    assert stored(d).unavailableReason == reason and stored(d).reportedValue == 2
    assert d.store.runs["run-1"]["unavailable"] == 1


def test_transient_evidence_errors_retry_until_the_last_attempt():
    sources = [EvidenceSource(0, "https://example.org/report", "error", reason="timeout")]
    d = deps(sources=sources)
    with pytest.raises(RetryLater):
        process_job(job(), d, final_attempt=False)
    assert d.store.items == {}
    process_job(job(), d, final_attempt=True)
    assert stored(d).unavailableReason == "no_readable_evidence"


def test_refusal_truncation_and_out_of_range_values():
    refusal = SuggestionResult("refusal", "m", LlmUsage(10, 0))
    d = deps(FakeLlmProvider().enqueue(refusal))
    process_job(job(), d, False)
    assert stored(d).unavailableReason == "model_declined"

    truncated = SuggestionResult("truncated", "m", LlmUsage(10, 4000))
    llm = FakeLlmProvider().enqueue(truncated, truncated)
    d = deps(llm)
    rep = process_job(job(), d, False)
    assert stored(d).unavailableReason == "invalid_output" and len(llm.calls) == 2
    assert llm.calls[1].max_tokens == 8000 and len(rep.usage) == 2

    d = deps(FakeLlmProvider().enqueue(ok(value=5)))
    process_job(job(), d, False)
    assert stored(d).unavailableReason == "invalid_output"


def test_truncated_then_ok_is_stored():
    llm = FakeLlmProvider().enqueue(SuggestionResult("truncated", "m", LlmUsage(10, 4000)), ok())
    d = deps(llm)
    assert process_job(job(), d, False).outcome == "produced"


def test_field_without_criteria_and_unknown_prompt_version():
    d = deps()
    process_job(job(field="general.title"), d, False)
    assert stored(d, field="general.title").unavailableReason == "no_criteria_for_field"
    process_job(job(version="v9-0.0.0"), d, False)
    assert stored(d, version="v9-0.0.0").unavailableReason == "failed"
    assert d.store.runs["run-1"] == {"produced": 0, "unavailable": 1, "failed": 1}


def test_missing_snapshot_retries_then_fails():
    d = deps(snapshots=FakeSnapshots(values=None))
    d.snapshots.data = {}
    with pytest.raises(RetryLater):
        process_job(job(), d, False)
    assert process_job(job(), d, True).outcome == "failed"


def test_a_failed_job_can_be_replaced_and_counters_move():
    d = deps(FakeLlmProvider().enqueue(RetryableLlmError("throttled", 429)))
    assert process_job(job(), d, final_attempt=True).outcome == "failed"
    assert d.store.runs["run-1"]["failed"] == 1
    d.provider = FakeLlmProvider().enqueue(ok())
    assert process_job(job(), d, final_attempt=False).outcome == "produced"
    assert d.store.runs["run-1"] == {"produced": 1, "unavailable": 0, "failed": 0}


def test_v1_prompt_runs_through_the_same_path():
    from app.llm.output_schema import V1ImpactAreaOutput

    out = V1ImpactAreaOutput(reasoning="r", short_justification="Principal focus on women.", score=2,
                             component="Gender Equality", evidence_quote=QUOTE)
    d = deps(FakeLlmProvider().enqueue(SuggestionResult("ok", "m", LlmUsage(1, 1), out)))
    process_job(job(version="v1-1.0.0"), d, False)
    item = stored(d, version="v1-1.0.0")
    assert item.signal == "green" and item.explanation == "Principal focus on women."
    assert item.evidenceSource == "https://example.org/report"  # found by the quote


# ---- SQS handler ----

def record(message_id, body, attempt=1):
    return {"messageId": message_id, "body": body, "attributes": {"ApproximateReceiveCount": str(attempt)}}


def test_handler_reports_only_the_failed_messages():
    llm = FakeLlmProvider().enqueue(ok(), RetryableLlmError("throttled", 429))
    d = deps(llm)
    event = {
        "Records": [
            record("m1", job().model_dump_json()),
            record("m2", "{not json"),
            record("m3", job(field="general.poverty_tag").model_dump_json()),
        ]
    }
    out = handler(event, deps=d)
    assert out == {"batchItemFailures": [{"itemIdentifier": "m2"}, {"itemIdentifier": "m3"}]}
    assert d.store.runs["run-1"]["produced"] == 1


def test_handler_stores_failed_on_the_last_attempt_and_acknowledges():
    d = deps(FakeLlmProvider().enqueue(RetryableLlmError("throttled", 429)))
    out = handler({"Records": [record("m1", job().model_dump_json(), attempt=3)]}, deps=d)
    assert out == {"batchItemFailures": []}
    assert stored(d).unavailableReason == "failed" and d.store.runs["run-1"]["failed"] == 1


def test_handler_unexpected_error_retries_then_records_failure():
    class Boom(FakeLlmProvider):
        def suggest(self, request):
            raise KeyError("x")

    d = deps(Boom())
    assert handler({"Records": [record("m1", job().model_dump_json(), 1)]}, deps=d)["batchItemFailures"]
    assert handler({"Records": [record("m1", job().model_dump_json(), 3)]}, deps=d)["batchItemFailures"] == []
    assert stored(d).unavailableReason == "failed"


# ---- DynamoDB adapter ----

def _client():
    return boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")


def _item(**over):
    base = dict(
        pk="RESULT#1001", sk=suggestion_sk(SNAP, GENDER, "v2-1.0.0"), resultCode=1001, snapKey=SNAP,
        fieldKey=GENDER, promptVersion="v2-1.0.0", suggestionId="s", runId="run-1",
        status="unavailable", unavailableReason="no_readable_evidence", createdAt="2026-11-20T12:00:00Z",
    )
    base.update(over)
    return AiSuggestionItem.model_validate({"__edb_e__": "aiSuggestion", "__edb_v__": "1", **base})


def test_store_writes_item_and_counter_in_one_conditional_transaction():
    client = _client()
    calls = []
    client.transact_write_items = lambda **kw: calls.append(kw) or {}
    store = DynamoSuggestionStore("cgiar-qa-test", client)
    assert store.write(_item(), "unavailable") is True
    assert store.write(_item(), "unavailable", replaces_failed=True) is True

    first_put, first_update = calls[0]["TransactItems"][0]["Put"], calls[0]["TransactItems"][1]["Update"]
    assert first_put["ConditionExpression"] == "attribute_not_exists(pk)"
    assert first_put["Item"]["__edb_e__"] == {"S": "aiSuggestion"} and first_put["Item"]["resultCode"] == {"N": "1001"}
    assert "signal" not in first_put["Item"]  # None fields are not written
    assert first_update["Key"] == {"pk": {"S": "AIRUN#run-1"}, "sk": {"S": "RUN"}}
    assert first_update["UpdateExpression"].startswith("ADD #c :one SET")
    assert first_update["ExpressionAttributeNames"]["#c"] == "unavailable"

    put, update = calls[1]["TransactItems"][0]["Put"], calls[1]["TransactItems"][1]["Update"]
    assert put["ConditionExpression"] == "unavailableReason = :failed"
    assert update["UpdateExpression"].startswith("ADD #c :one, #f :minus")
    assert update["ExpressionAttributeValues"][":minus"] == {"N": "-1"}


def test_store_returns_false_when_the_condition_fails():
    client = _client()
    store = DynamoSuggestionStore("cgiar-qa-test", client)
    with Stubber(client) as stub:
        stub.add_client_error(
            "transact_write_items",
            service_error_code="TransactionCanceledException",
            modeled_fields={"CancellationReasons": [{"Code": "ConditionalCheckFailed"}, {"Code": "None"}]},
        )
        assert store.write(_item(), "unavailable") is False


def test_store_lookup_distinguishes_failed_items():
    client = _client()
    store = DynamoSuggestionStore("cgiar-qa-test", client)
    with Stubber(client) as stub:
        stub.add_response("get_item", {})
        stub.add_response("get_item", {"Item": {"pk": {"S": "x"}, "unavailableReason": {"S": "failed"}}})
        stub.add_response("get_item", {"Item": {"pk": {"S": "x"}}})
        assert [store.lookup("p", "s") for _ in range(3)] == ["absent", "failed", "done"]
