"""v1 vs v2 comparison on the 2025 sample. Nothing here writes to DynamoDB.

    uv run python -m eval.compare fill-reported --reference PATH   # reported_value from the pre-QA labels
    uv run python -m eval.compare sample   --per-field 40
    uv run python -m eval.compare estimate --no-fetch            # cost from row counts only
    uv run python -m eval.compare estimate                       # reads the evidence, no model call
    uv run python -m eval.compare run --max-usd 3 --profile qa-ai-deployer
    uv run python -m eval.compare report [--jose-csv PATH]

Files live in ``eval/.data/`` (gitignored): the export, ``sample.csv``, ``evidence-cache/`` and
``runs/<name>.jsonl``. A live run needs ``--max-usd`` (no default): it stops before a call that would
exceed it, and resumes where it stopped when run again.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from app.evidence.extractor import EvidenceExtractor
from app.evidence.http import GuardedHttp
from app.evidence.scraper import EvidenceScraper
from app.utils.config.config_util import AWS, LLM
from eval.dataset import (
    FIELD_KEYS,
    load_rows,
    read_reported,
    read_sample,
    reference_levels,
    stratified_sample,
    write_reported,
    write_sample,
)
from eval.metrics import compute, load_jose, render
from eval.runner import DiskEvidenceCache, RunConfig, load_records, run

DATA = Path(__file__).resolve().parent / ".data"
VERSIONS = "v1-1.0.0,v2-1.0.0"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="eval.compare")
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--export", default="prms_2025_final.csv")
    sub = p.add_subparsers(dest="cmd", required=True)

    fr = sub.add_parser("fill-reported")
    fr.add_argument("--reference", type=Path, required=True, help="reference_prms_2025_subset_labels.csv")

    s = sub.add_parser("sample")
    s.add_argument("--per-field", type=int, default=40)
    s.add_argument("--seed", type=int, default=2025)

    for name in ("estimate", "run"):
        r = sub.add_parser(name)
        r.add_argument("--versions", default=VERSIONS)
        r.add_argument("--effort", choices=["low", "medium", "high"], default=LLM["effort"])
        r.add_argument("--max-tokens", type=int, default=LLM["max_tokens"])
        r.add_argument("--workers", type=int, default=4)
        r.add_argument("--name", default=None, help="run file name (default: <versions>-<effort>)")
        if name == "estimate":
            r.add_argument("--no-fetch", action="store_true")
        else:
            r.add_argument("--max-usd", type=float, required=True)
            r.add_argument("--profile", default=None)

    rep = sub.add_parser("report")
    rep.add_argument("--name", default=f"{VERSIONS}-{LLM['effort']}")
    rep.add_argument("--jose-csv", type=Path, default=None)

    a = p.parse_args(argv)
    reported_path = a.data / "reported_2025.csv"

    if a.cmd == "fill-reported":
        levels = reference_levels(a.reference)
        rows = load_rows(a.data / a.export)
        matched = {k: v for k, v in levels.items() if k in {r.key for r in rows}}
        write_reported(matched, reported_path)
        per_field = Counter(k.split("|")[1] for k in matched)
        totals = Counter(r.field for r in rows)
        print(f"reported values: {len(matched)} of {len(rows)} export rows matched -> {reported_path}")
        for f in FIELD_KEYS:
            print(f"  {f:28} {per_field.get(f, 0):6} / {totals.get(f, 0)}")
        return 0

    rows = load_rows(a.data / a.export, read_reported(reported_path) if reported_path.exists() else None)

    if a.cmd == "sample":
        sample = stratified_sample(rows, a.per_field, a.seed)
        write_sample(sample, a.data / "sample.csv")
        print(f"sample: {len(sample)} rows -> {a.data / 'sample.csv'}")
        for f in FIELD_KEYS:
            sub_rows = [r for r in sample if r.field == f]
            if not sub_rows:
                continue
            finals = dict(sorted(Counter(r.final for r in sub_rows).items()))
            ev = dict(Counter(r.evidence_status for r in sub_rows))
            types = dict(Counter(r.result_type for r in sub_rows).most_common())
            reported = sum(r.reported is not None for r in sub_rows)
            print(f"  {f}: n={len(sub_rows)} final={finals} evidence={ev} reported={reported}")
            print(f"    types={types}")
        return 0

    sample = read_sample(a.data / "sample.csv", rows)

    if a.cmd == "report":
        records = load_records(a.data / "runs" / f"{a.name}.jsonl")
        jose = load_jose(a.jose_csv) if a.jose_csv else None
        notes = [
            f"Run `{a.name}`: {len(records)} records over {len(sample)} sampled rows.",
            "Reference: final QA value 2025 (Reporting export). Majority class over the whole export.",
            "Evidence: links flagged for the field, else all the result's links (max 5), read by `app/evidence`.",
        ]
        out = a.data / "runs" / f"{a.name}.report.md"
        out.write_text(render(compute(records, rows, jose), "AI suggestions: v1 vs v2 (2025 sample)", notes), encoding="utf-8")
        print(out)
        return 0

    versions = [v.strip() for v in a.versions.split(",") if v.strip()]
    dry = a.cmd == "estimate"
    name = a.name or f"{','.join(versions)}-{a.effort}" + ("-estimate" + ("-nofetch" if a.no_fetch else "") if dry else "")
    cfg = RunConfig(
        versions=versions, effort=a.effort, max_tokens=a.max_tokens, workers=a.workers,
        dry_run=dry, fetch=not getattr(a, "no_fetch", False), max_usd=getattr(a, "max_usd", None),
    )
    out = a.data / "runs" / f"{name}.jsonl"
    if dry and out.exists():
        out.unlink()  # an estimate is always recomputed
    extractor = None if (dry and not cfg.fetch) else EvidenceExtractor(
        EvidenceScraper(GuardedHttp()), DiskEvidenceCache(a.data / "evidence-cache")
    )
    provider = None
    if not dry:
        from app.llm.bedrock import BedrockProvider

        provider = BedrockProvider(LLM["model_id"], AWS["aws_region"], api=LLM["bedrock_api"], aws_profile=a.profile)

    summary = run(sample, cfg, out, extractor, provider, progress=lambda m: print(m, file=sys.stderr))
    records = load_records(out)
    calls = sum(1 for r in records.values() if r["status"] in ("estimate", "ok"))
    unavailable = Counter(r.get("reason") for r in records.values() if r["status"] == "unavailable")
    label = "estimated" if dry else "spent"
    print(f"{out}")
    print(f"rows={len(sample)} versions={len(versions)} model_calls={calls} unavailable={dict(unavailable)}")
    print(f"USD {label}: {sum(r.get('usd', 0.0) for r in records.values()):.2f}"
          + (" (stopped by --max-usd; run again to resume)" if summary.stopped_by_budget else ""))
    if summary.errors:
        print(f"errors: {summary.errors} (retried on the next run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
