"""Metrics over a run file, and the Markdown report (aggregates only: no evidence, quotes or text).

Reference = the final QA value of 2025. Per field and version, on the rows where the model answered:
exact, within one level, MAE; the same metrics for two baselines on the same rows (majority class of
the field over the whole export, and the value the submitter reported); the previous helper (gpt-5,
production run of March 2026) when its CSV is given. Plus coverage, verified quotes, signal
distribution, signal against the final decision, tokens and cost.
"""

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval.dataset import FIELD_KEYS, EvalRow

JOSE_DIMENSIONS = {
    "Gender": "gender",
    "Climate": "climate",
    "Nutrition": "nutrition",
    "Environment/Biodiversity": "environment_biodiversity",
    "Poverty": "poverty",
    "Innovation Readiness Level": "innovation_readiness_level",
    "Innovation Use": "innovation_use_level",
}


@dataclass
class Agreement:
    n: int = 0
    exact: int = 0
    within1: int = 0
    abs_err: int = 0

    def add(self, predicted: int, final: int) -> None:
        d = abs(predicted - final)
        self.n += 1
        self.exact += d == 0
        self.within1 += d <= 1
        self.abs_err += d

    def pct(self, k: int) -> str:
        return f"{100 * k / self.n:.1f}" if self.n else "–"

    @property
    def mae(self) -> str:
        return f"{self.abs_err / self.n:.2f}" if self.n else "–"


@dataclass
class Cell:
    """One (field, version)."""

    sample: int = 0
    answered: int = 0
    unavailable: Counter = field(default_factory=Counter)
    errors: int = 0
    model: Agreement = field(default_factory=Agreement)
    majority: Agreement = field(default_factory=Agreement)
    submitter: Agreement = field(default_factory=Agreement)
    jose: Agreement = field(default_factory=Agreement)
    quotes_verified: int = 0
    signals: Counter = field(default_factory=Counter)
    signal_vs_final: Counter = field(default_factory=Counter)
    """(signal, 'kept' | 'changed'): did QA keep the reported value?"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    usd: float = 0.0


def majority_classes(rows: list[EvalRow]) -> dict[str, int]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.final is not None:
            counts[r.field][r.final] += 1
    return {f: c.most_common(1)[0][0] for f, c in counts.items()}


def load_jose(path: Path) -> dict[str, int]:
    """``result_code|field`` -> the previous helper's normalised score. Read-only, data only."""
    out: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            field_name = JOSE_DIMENSIONS.get(r.get("dimension", ""))
            score = (r.get("ai_score_norm") or "").strip()
            if field_name and score and r.get("success", "").strip().lower() == "true":
                out[f"{int(r['result_code'])}|{field_name}"] = int(float(score))
    return out


def compute(
    records: dict[str, dict[str, Any]], all_rows: list[EvalRow], jose: dict[str, int] | None = None
) -> dict[tuple[str, str], Cell]:
    majority = majority_classes(all_rows)
    cells: dict[tuple[str, str], Cell] = defaultdict(Cell)
    for rec in records.values():
        cell = cells[(rec["field"], rec["version"])]
        cell.sample += 1
        status = rec["status"]
        cell.input_tokens += rec.get("input_tokens", 0)
        cell.output_tokens += rec.get("output_tokens", 0)
        cell.cache_read += rec.get("cache_read", 0)
        cell.usd += rec.get("usd", 0.0)
        if status == "error":
            cell.errors += 1
            continue
        if status == "unavailable":
            cell.unavailable[rec.get("reason") or "unknown"] += 1
            continue
        if status != "ok":
            continue
        cell.answered += 1
        final, reported = rec["final"], rec["reported"]
        cell.quotes_verified += bool(rec.get("quote_verified"))
        signal = rec.get("signal") or "none"
        cell.signals[signal] += 1
        if final is None:
            continue
        cell.model.add(rec["value"], final)
        if rec["field"] in majority:
            cell.majority.add(majority[rec["field"]], final)
        if reported is not None:
            cell.submitter.add(reported, final)
            cell.signal_vs_final[(signal, "kept" if reported == final else "changed")] += 1
        if jose is not None:
            j = jose.get(f"{rec['result_code']}|{rec['field']}")
            if j is not None:
                cell.jose.add(j, final)
    return cells


def render(cells: dict[tuple[str, str], Cell], title: str, notes: list[str]) -> str:
    versions = sorted({v for _, v in cells})
    fields = [f for f in FIELD_KEYS if any(k[0] == f for k in cells)]
    lines = [f"# {title}", ""]
    lines += [f"- {n}" for n in notes] + [""]

    lines += ["## Agreement with the final QA value", "",
              "Rows where the model answered. Exact and ±1 in %; baselines on the same rows.", "",
              "| Field | Version | Answered / sample | Exact | ±1 | MAE | Majority exact | Submitter exact | Previous helper exact (n) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for f in fields:
        for v in versions:
            c = cells.get((f, v))
            if not c:
                continue
            m = c.model
            jose = f"{c.jose.pct(c.jose.exact)} ({c.jose.n})" if c.jose.n else "–"
            lines.append(
                f"| {f} | {v} | {c.answered} / {c.sample} | {m.pct(m.exact)} | {m.pct(m.within1)} | {m.mae} "
                f"| {c.majority.pct(c.majority.exact)} | {c.submitter.pct(c.submitter.exact)} | {jose} |"
            )

    lines += ["", "## Coverage, quotes and signal", "",
              "| Field | Version | Unavailable (reason: n) | Errors | Verified quotes | Green | Amber | Red |",
              "|---|---|---|---|---|---|---|---|"]
    for f in fields:
        for v in versions:
            c = cells.get((f, v))
            if not c:
                continue
            unav = ", ".join(f"{k}: {n}" for k, n in sorted(c.unavailable.items())) or "–"
            q = f"{100 * c.quotes_verified / c.answered:.1f}%" if c.answered else "–"
            s = c.signals
            lines.append(f"| {f} | {v} | {unav} | {c.errors} | {q} | {s['green']} | {s['amber']} | {s['red']} |")

    lines += ["", "## Signal against the final decision", "",
              "Kept: QA kept the reported value. Changed: QA changed it. A useful signal is mostly green on kept rows and red or amber on changed ones.", "",
              "| Version | Green kept | Green changed | Amber kept | Amber changed | Red kept | Red changed |",
              "|---|---|---|---|---|---|---|"]
    for v in versions:
        t: Counter = Counter()
        for (f, ver), c in cells.items():
            if ver == v:
                t.update(c.signal_vs_final)
        lines.append("| " + v + " | " + " | ".join(str(t[(s, k)]) for s in ("green", "amber", "red") for k in ("kept", "changed")) + " |")

    lines += ["", "## Tokens and cost", "",
              "| Version | Input | Cache read | Output | USD |", "|---|---|---|---|---|"]
    for v in versions:
        cs = [c for (f, ver), c in cells.items() if ver == v]
        lines.append(
            f"| {v} | {sum(c.input_tokens for c in cs):,} | {sum(c.cache_read for c in cs):,} "
            f"| {sum(c.output_tokens for c in cs):,} | {sum(c.usd for c in cs):.2f} |"
        )
    return "\n".join(lines) + "\n"
