"""End-to-end check in TEST: enqueue jobs, wait for the worker, verify suggestions and run counters.

    uv run python -m scripts.e2e_test --profile qa-ai-deployer \\
        --job 1234:2026#000012#00000003#0000000042:general.gender_tag \\
        --job 1234:2026#000012#00000003#0000000042:general.climate_tag ...

    # Optional fixture (needs dynamodb:PutItem/DeleteItem on the table): writes one fictional
    # snapshot RESULT#999001 with public evidence, runs its AI fields, then deletes what it wrote.
    uv run python -m scripts.e2e_test --profile qa-ai-deployer --fixture

Needs: sqs:SendMessage on the queue, dynamodb:GetItem/Query on the table. Prints identifiers,
statuses, signals and counters only; never evidence or model text. Each job costs one model call.
"""

import argparse
import json
import sys
import time
import uuid
from typing import Any

import boto3

from app.contract.items import run_pk, suggestion_pk, suggestion_sk
from app.contract.messages import AiJobMessage

FIXTURE_CODE = 999001
FIXTURE_SNAP = "2026#000000#00000000#0000000001"
FIXTURE_VALUES = {
    "general.title": "E2E fixture: climate-resilient rice varieties released with women farmer groups",
    "general.description": "Fictional result used only to test the AI suggestion worker in TEST.",
    "general.gender_tag": {"value": 3},
    "general.climate_tag": {"value": 2},
    "evidence.items": [
        {"source": 0, "link": "https://www.cgiar.org/research/", "gender_related": True},
    ],
}
FIXTURE_FIELDS = ["general.gender_tag", "general.climate_tag", "general.poverty_tag"]


def parse_job(spec: str) -> tuple[int, str, str]:
    code, rest = spec.split(":", 1)
    snap, field = rest.rsplit(":", 1)
    return int(code), snap, field


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scripts.e2e_test")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--env", default="test")
    p.add_argument("--prompt-version", default="v2-1.0.0")
    p.add_argument("--job", action="append", default=[], help="resultCode:snapKey:fieldKey")
    p.add_argument("--fixture", action="store_true")
    p.add_argument("--timeout", type=int, default=900, help="seconds to wait for the worker")
    a = p.parse_args(argv)

    session = boto3.Session(profile_name=a.profile, region_name=a.region)
    sqs, ddb = session.client("sqs"), session.client("dynamodb")
    table = f"cgiar-qa-{a.env}"
    queue_url = sqs.get_queue_url(QueueName=f"qa-ai-suggestions-{a.env}")["QueueUrl"]

    jobs = [parse_job(j) for j in a.job]
    if a.fixture:
        ddb.put_item(TableName=table, Item=_fixture_item())
        jobs += [(FIXTURE_CODE, FIXTURE_SNAP, f) for f in FIXTURE_FIELDS]
    if not jobs:
        p.error("give --job at least once, or --fixture")

    run_id = f"e2e-{uuid.uuid4().hex[:12]}"
    for code, snap, field in jobs:
        msg = AiJobMessage(runId=run_id, resultCode=str(code), snapKey=snap, fieldKey=field, promptVersion=a.prompt_version)
        sqs.send_message(QueueUrl=queue_url, MessageBody=msg.model_dump_json())
    print(f"run {run_id}: {len(jobs)} jobs enqueued ({a.prompt_version})")

    deadline = time.time() + a.timeout
    found: dict[tuple[int, str, str], dict[str, Any]] = {}
    while time.time() < deadline and len(found) < len(jobs):
        for job in jobs:
            if job in found:
                continue
            code, snap, field = job
            item = ddb.get_item(
                TableName=table,
                Key={"pk": {"S": suggestion_pk(code)}, "sk": {"S": suggestion_sk(snap, field, a.prompt_version)}},
                ConsistentRead=True,
            ).get("Item")
            if item:
                found[job] = item
        if len(found) < len(jobs):
            time.sleep(10)

    rows = []
    for job in jobs:
        item = found.get(job)
        code, _, field = job
        if not item:
            rows.append({"result": code, "field": field, "status": "MISSING"})
            continue
        rows.append({
            "result": code,
            "field": field,
            "status": item["status"]["S"],
            "signal": item.get("signal", {}).get("S"),
            "reason": item.get("unavailableReason", {}).get("S"),
            "suggested": item.get("suggestedValue", {}).get("N"),
            "reported": item.get("reportedValue", {}).get("N"),
            "quoteVerified": item.get("quoteVerified", {}).get("BOOL"),
            "explanationWords": len(item.get("explanation", {}).get("S", "").split()),
        })
    run = ddb.get_item(TableName=table, Key={"pk": {"S": run_pk(run_id)}, "sk": {"S": "RUN"}}, ConsistentRead=True).get("Item", {})
    counters = {k: int(run[k]["N"]) for k in ("produced", "unavailable", "failed") if k in run}
    accounted = sum(counters.values())
    dlq = sqs.get_queue_attributes(
        QueueUrl=sqs.get_queue_url(QueueName=f"qa-ai-suggestions-dlq-{a.env}")["QueueUrl"],
        AttributeNames=["ApproximateNumberOfMessages"],
    )["Attributes"]["ApproximateNumberOfMessages"]

    print(json.dumps({"runId": run_id, "jobs": rows, "counters": counters, "dlq": int(dlq)}, indent=2))
    complete = accounted == len(jobs) and counters.get("failed", 0) == 0 and all(r["status"] != "MISSING" for r in rows)
    print(f"run {'COMPLETE' if complete else 'INCOMPLETE'}: {accounted}/{len(jobs)} accounted, failed={counters.get('failed', 0)}, dlq={dlq}")

    if a.fixture:
        for code, snap, field in jobs:
            if code == FIXTURE_CODE:
                ddb.delete_item(TableName=table, Key={"pk": {"S": suggestion_pk(code)}, "sk": {"S": suggestion_sk(snap, field, a.prompt_version)}})
        ddb.delete_item(TableName=table, Key={"pk": {"S": f"RESULT#{FIXTURE_CODE}"}, "sk": {"S": f"SNAP#{FIXTURE_SNAP}"}})
        print("fixture items deleted")
    return 0 if complete else 1


def _fixture_item() -> dict[str, Any]:
    """Same shape the onecgiar_qa resultSnapshot entity writes (ElectroDB, values as a JSON string)."""
    return {
        "pk": {"S": f"RESULT#{FIXTURE_CODE}"},
        "sk": {"S": f"SNAP#{FIXTURE_SNAP}"},
        "__edb_e__": {"S": "resultSnapshot"},
        "__edb_v__": {"S": "1"},
        "resultCode": {"N": str(FIXTURE_CODE)},
        "snapKey": {"S": FIXTURE_SNAP},
        "values": {"S": json.dumps(FIXTURE_VALUES)},
    }


if __name__ == "__main__":
    sys.exit(main())
