"""Runs prompt versions over the sample: same evidence, same production path, no DynamoDB writes.

Every (row, version) becomes one JSON line in the run file, written as soon as it finishes, so a run
can stop (budget, Ctrl-C) and resume without paying twice. ``dry_run`` reads the evidence and builds
every request but calls no model: it estimates tokens and cost for the approval.
"""

import base64
import dataclasses
import hashlib
import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf

from app.contract.fields import field_spec
from app.evidence.extractor import EvidenceExtractor, EvidenceOutcome, EvidenceSource, summarize
from app.llm.provider import Effort, LlmProvider, LlmUsage, PdfEvidence, RetryableLlmError, TextPart
from app.prompts.builder import ResultContext, build_request
from app.prompts.loader import get_prompt
from app.worker.suggest import SuggestParams, suggest
from eval.dataset import EvalRow
from eval.pricing import usd

CHARS_PER_TOKEN = 3.5
PDF_TOKENS_PER_PAGE = 2_000
SCHEMA_TOKENS = 400
NO_FETCH_INPUT_TOKENS = 10_000
"""Per-call input estimate without reading evidence (the previous helper averaged ~9.7k)."""


@dataclass(frozen=True)
class RunConfig:
    versions: list[str]
    effort: Effort = "medium"
    max_tokens: int = 4000
    max_usd: float | None = None
    dry_run: bool = False
    fetch: bool = True
    """Dry run only: False skips evidence reading and uses NO_FETCH_INPUT_TOKENS per row with links."""
    workers: int = 4
    est_output_tokens: int = 1_500
    """Thinking + JSON per call at medium effort; replaced by measured usage in live runs."""


@dataclass
class RunSummary:
    records: int = 0
    skipped: int = 0
    usd: float = 0.0
    stopped_by_budget: bool = False
    errors: int = 0


class DiskEvidenceCache:
    """URL -> EvidenceSource as JSON under a gitignored folder. Transient errors are not cached."""

    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        return self.folder / f"{hashlib.sha256(url.encode()).hexdigest()}.json"

    def get(self, url: str) -> EvidenceSource | None:
        p = self._path(url)
        if not p.exists():
            return None
        return EvidenceSource(**json.loads(p.read_text(encoding="utf-8")))

    def put(self, url: str, source: EvidenceSource) -> None:
        self._path(url).write_text(json.dumps(dataclasses.asdict(source)), encoding="utf-8")


def load_records(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["key"]] = rec
    return out


def estimate_usage(request, output_tokens: int) -> LlmUsage:
    chars = len(request.system) + sum(len(p.text) for p in request.content if isinstance(p, TextPart))
    pdf = sum(_pdf_pages(p.data_base64) * PDF_TOKENS_PER_PAGE for p in request.content if isinstance(p, PdfEvidence))
    return LlmUsage(input_tokens=int(chars / CHARS_PER_TOKEN) + pdf + SCHEMA_TOKENS, output_tokens=output_tokens)


def run(
    rows: list[EvalRow],
    cfg: RunConfig,
    out_path: Path,
    extractor: EvidenceExtractor | None,
    provider: LlmProvider | None,
    progress: Callable[[str], None] = lambda _: None,
) -> RunSummary:
    if not cfg.dry_run and (provider is None or cfg.max_usd is None):
        raise ValueError("a live run needs a provider and max_usd")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {k for k, r in load_records(out_path).items() if r["status"] != "error"}
    summary = RunSummary(usd=sum(r.get("usd", 0.0) for r in load_records(out_path).values()))
    lock = threading.Lock()
    params = SuggestParams(cfg.effort, cfg.max_tokens)

    def emit(rec: dict[str, Any]) -> None:
        with lock:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            summary.records += 1
            summary.usd += rec.get("usd", 0.0)
            summary.errors += rec["status"] == "error"
            progress(f"{rec['key']} {rec['status']} {rec.get('reason', '')}")

    def reserve(estimate: float) -> bool:
        with lock:
            if summary.stopped_by_budget or summary.usd + estimate > cfg.max_usd:
                summary.stopped_by_budget = True
                return False
            summary.usd += estimate  # released when the record lands with the real cost
            return True

    def release(estimate: float) -> None:
        with lock:
            summary.usd -= estimate

    def one_row(row: EvalRow) -> None:
        todo = [v for v in cfg.versions if f"{row.key}|{v}" not in done]
        if not todo:
            with lock:
                summary.skipped += len(cfg.versions)
            return
        evidence = _evidence(row, cfg, extractor)
        for version in todo:
            base = _base(row, version, cfg, evidence)
            prompt, spec = get_prompt(version, row.field_key), field_spec(row.field_key)
            if not evidence.readable:
                emit({**base, "status": "unavailable", "reason": evidence.unavailable_reason})
                continue
            ctx = ResultContext(row.title, row.description)
            built = build_request(prompt, ctx, evidence.sources, cfg.effort, cfg.max_tokens)
            est = estimate_usage(built.request, cfg.est_output_tokens)
            if cfg.dry_run:
                emit({**base, "status": "estimate", **_usage_fields([est])})
                continue
            est_usd = usd(est)
            if not reserve(est_usd):
                return
            try:
                out = suggest(provider, prompt, spec, ctx, row.reported, evidence, params)
            except RetryableLlmError as err:
                release(est_usd)
                emit({**base, "status": "error", "reason": f"retryable_{err.status}"})
                continue
            except Exception as err:  # noqa: BLE001 - one bad row must not stop the run
                release(est_usd)
                emit({**base, "status": "error", "reason": type(err).__name__})
                continue
            release(est_usd)
            rec = {**base, **_usage_fields(out.usage), "model_id": out.model_id}
            if out.kind != "ok" or out.output is None:
                emit({**rec, "status": "unavailable", "reason": out.kind})
                continue
            n = out.output
            emit({
                **rec, "status": "ok", "value": n.value, "signal": out.signal,
                "quote_verified": out.quote_verified, "component": n.component,
                "explanation": n.explanation, "evidence_quote": n.evidence_quote,
                "evidence_source_index": out.source_index,
            })

    with ThreadPoolExecutor(max_workers=max(1, cfg.workers)) as pool:
        list(pool.map(one_row, rows))
    return summary


def _evidence(row: EvalRow, cfg: RunConfig, extractor: EvidenceExtractor | None) -> EvidenceOutcome:
    if not row.links:
        return summarize([])
    if cfg.dry_run and not cfg.fetch:
        fake = "x" * int((NO_FETCH_INPUT_TOKENS - SCHEMA_TOKENS) * CHARS_PER_TOKEN)
        return summarize([EvidenceSource(0, row.links[0], "text", text=fake)])
    assert extractor is not None
    return extractor.extract(row.links)


def _base(row: EvalRow, version: str, cfg: RunConfig, evidence: EvidenceOutcome) -> dict[str, Any]:
    return {
        "key": f"{row.key}|{version}",
        "result_code": row.result_code,
        "field": row.field,
        "result_type": row.result_type,
        "version": version,
        "effort": cfg.effort,
        "reported": row.reported,
        "final": row.final,
        "evidence_status": row.evidence_status,
        "evidence_counts": evidence.counts,
        "partial": evidence.partial,
    }


def _usage_fields(usage: list[LlmUsage]) -> dict[str, Any]:
    total = LlmUsage(
        sum(u.input_tokens for u in usage),
        sum(u.output_tokens for u in usage),
        sum(u.cache_read_input_tokens for u in usage),
        sum(u.cache_creation_input_tokens for u in usage),
    )
    return {
        "calls": len(usage),
        "input_tokens": total.input_tokens,
        "output_tokens": total.output_tokens,
        "cache_read": total.cache_read_input_tokens,
        "cache_write": total.cache_creation_input_tokens,
        "usd": round(sum(usd(u) for u in usage), 6),
    }


def _pdf_pages(data_base64: str) -> int:
    try:
        with pymupdf.open(stream=base64.b64decode(data_base64), filetype="pdf") as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001 - estimate only
        return 5
