"""SQS -> worker Lambda. Partial batch failures: only the failed messages are redelivered.

Requires ``function_response_types = ["ReportBatchItemFailures"]`` on the event source mapping.
Environment: TABLE_NAME, MODEL_ID, LLM_EFFORT, LLM_MAX_TOKENS, MAX_RECEIVE_COUNT (same value as the
queue's redrive ``maxReceiveCount``). Logs carry identifiers, outcomes, reasons and token counts only:
never evidence text, prompts or model output.
"""

import os
from collections import Counter
from typing import Any

import anthropic
from pydantic import ValidationError

from app.contract.messages import AiJobMessage
from app.evidence.extractor import EvidenceExtractor, MemoryEvidenceCache
from app.evidence.http import GuardedHttp
from app.evidence.scraper import EvidenceScraper
from app.prompts.loader import PromptIntegrityError
from app.utils.config.config_util import AWS, LLM
from app.utils.logger.logger_util import get_logger
from app.worker.process import JobDeps, RetryLater, process_job, record_failure

logger = get_logger()

MAX_RECEIVE_COUNT = int(os.getenv("MAX_RECEIVE_COUNT", "3"))

_TERMINAL = (anthropic.BadRequestError, PromptIntegrityError)
"""Errors a redelivery cannot fix: the job is stored as failed at once. Permission and throttling
errors are retried; after the last delivery they are stored as failed too, and a failed item can be
replaced by re-enqueuing the job once the cause is fixed."""


def build_deps() -> JobDeps:  # pragma: no cover - wiring of real clients
    import boto3

    from app.llm.bedrock_mantle import BedrockMantleProvider
    from app.worker.snapshot import DynamoSnapshotReader
    from app.worker.store import DynamoSuggestionStore

    table = os.environ["TABLE_NAME"]
    ddb = boto3.client("dynamodb", region_name=AWS["aws_region"])
    return JobDeps(
        snapshots=DynamoSnapshotReader(table, ddb),
        store=DynamoSuggestionStore(table, ddb),
        extractor=EvidenceExtractor(EvidenceScraper(GuardedHttp()), MemoryEvidenceCache()),
        provider=BedrockMantleProvider(LLM["model_id"], AWS["aws_region"]),
        effort=LLM["effort"],
        max_tokens=LLM["max_tokens"],
    )


_deps: JobDeps | None = None


def handler(event: dict[str, Any], context: Any = None, deps: JobDeps | None = None) -> dict[str, Any]:
    global _deps
    if deps is None:
        _deps = _deps or build_deps()
        deps = _deps
    # Links shared by the fields of one result are fetched once per invocation.
    deps.extractor.cache = MemoryEvidenceCache()

    failures: list[dict[str, str]] = []
    tally: Counter[str] = Counter()
    for record in event.get("Records", []):
        message_id = record["messageId"]
        attempt = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
        final = attempt >= MAX_RECEIVE_COUNT
        try:
            msg = AiJobMessage.model_validate_json(record["body"])
        except ValidationError:
            logger.error("job: invalid message %s, left for the DLQ", message_id)
            failures.append({"itemIdentifier": message_id})
            tally["invalid_message"] += 1
            continue
        ids = f"run={msg.runId} result={msg.resultCode} field={msg.fieldKey} prompt={msg.promptVersion}"
        try:
            rep = process_job(msg, deps, final)
        except RetryLater as err:
            logger.warning("job: retry %s attempt=%d reason=%s", ids, attempt, err)
            failures.append({"itemIdentifier": message_id})
            tally["retry"] += 1
            continue
        except Exception as err:  # noqa: BLE001 - decide retry vs failed per message
            if not (final or isinstance(err, _TERMINAL)):
                logger.warning("job: retry %s attempt=%d error=%s", ids, attempt, type(err).__name__)
                failures.append({"itemIdentifier": message_id})
                tally["retry"] += 1
                continue
            logger.error("job: failed %s attempt=%d error=%s", ids, attempt, type(err).__name__)
            try:
                rep = record_failure(msg, deps, f"error_{type(err).__name__}")
            except Exception:  # noqa: BLE001 - could not even record it: let SQS/DLQ keep it
                failures.append({"itemIdentifier": message_id})
                tally["retry"] += 1
                continue
        tally[rep.outcome] += 1
        tokens_in = sum(u.input_tokens for u in rep.usage)
        tokens_out = sum(u.output_tokens for u in rep.usage)
        cached = sum(u.cache_read_input_tokens for u in rep.usage)
        logger.info(
            "job: %s outcome=%s reason=%s signal=%s calls=%d in=%d out=%d cache_read=%d evidence=%s",
            ids, rep.outcome, rep.reason, rep.signal, len(rep.usage), tokens_in, tokens_out, cached,
            rep.evidence_counts,
        )
    logger.info("batch: %s", dict(tally))
    return {"batchItemFailures": failures}
