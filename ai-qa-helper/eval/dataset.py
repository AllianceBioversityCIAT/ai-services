"""The 2025 PRMS export (prepared by Reporting) and the stratified sample.

Expected file: ``eval/.data/prms_2025_final.csv`` (gitignored), one row per (result, field):

    result_code, field, result_type, reported_value, final_qa_value, title, description,
    evidence_urls_field, evidence_urls_all

``field`` is one of FIELD_KEYS; values are levels (Impact Areas 0-2, IRL/IUL 0-9), empty when
missing; URL lists are separated by `` | ``. No personal data.
"""

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

FIELD_KEYS = {
    "gender": "general.gender_tag",
    "climate": "general.climate_tag",
    "nutrition": "general.nutrition_tag",
    "environment_biodiversity": "general.environment_tag",
    "poverty": "general.poverty_tag",
    "innovation_readiness_level": "innovation_dev.readiness_level",
    "innovation_use_level": "innovation_use.use_level.innovation_use_level",
}
COLUMNS = (
    "result_code", "field", "result_type", "reported_value", "final_qa_value", "title", "description",
    "evidence_urls_field", "evidence_urls_all",
)
MAX_LINKS = 5
"""Same cap as the worker (``app/worker/snapshot.py``)."""

EvidenceStatus = Literal["field", "result", "none"]


@dataclass(frozen=True)
class EvalRow:
    result_code: int
    field: str
    result_type: str
    reported: int | None
    final: int | None
    title: str
    description: str
    links_field: tuple[str, ...]
    links_all: tuple[str, ...]

    @property
    def field_key(self) -> str:
        return FIELD_KEYS[self.field]

    @property
    def key(self) -> str:
        return f"{self.result_code}|{self.field}"

    @property
    def evidence_status(self) -> EvidenceStatus:
        """Mirrors the worker: links flagged for the field, else all the result's links."""
        if self.links_field:
            return "field"
        return "result" if self.links_all else "none"

    @property
    def links(self) -> list[str]:
        return list((self.links_field or self.links_all)[:MAX_LINKS])


class DatasetError(ValueError):
    pass


def load_rows(path: Path) -> list[EvalRow]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise DatasetError(f"missing columns: {', '.join(missing)}")
        rows = []
        for n, r in enumerate(reader, start=2):
            field = r["field"].strip()
            if field not in FIELD_KEYS:
                raise DatasetError(f"line {n}: unknown field {field!r}")
            rows.append(
                EvalRow(
                    result_code=int(r["result_code"]),
                    field=field,
                    result_type=r["result_type"].strip(),
                    reported=_level(r["reported_value"]),
                    final=_level(r["final_qa_value"]),
                    title=r["title"].strip(),
                    description=r["description"].strip(),
                    links_field=_links(r["evidence_urls_field"]),
                    links_all=_links(r["evidence_urls_all"]),
                )
            )
    return rows


def stratified_sample(rows: list[EvalRow], per_field: int, seed: int = 2025) -> list[EvalRow]:
    """Per field, strata = final QA value x evidence status; proportional allocation with at least
    one row per stratum (when ``per_field`` allows). Deterministic for a given seed and file."""
    by_field: dict[str, list[EvalRow]] = defaultdict(list)
    for r in rows:
        if r.final is not None:
            by_field[r.field].append(r)
    sample: list[EvalRow] = []
    for field in sorted(by_field):
        strata: dict[tuple[int, str], list[EvalRow]] = defaultdict(list)
        for r in sorted(by_field[field], key=lambda x: x.result_code):
            strata[(r.final, r.evidence_status)].append(r)
        sizes = allocate({k: len(v) for k, v in strata.items()}, per_field)
        rng = random.Random(f"{seed}:{field}")
        for k in sorted(strata):
            members = strata[k][:]
            rng.shuffle(members)
            sample.extend(members[: sizes[k]])
    return sample


def allocate(counts: dict, total: int) -> dict:
    """Largest-remainder proportional allocation, min 1 per stratum, never above its size."""
    available = sum(counts.values())
    if total >= available:
        return dict(counts)
    keys = sorted(counts)
    alloc = {k: 0 for k in keys}
    if total >= len(keys):
        alloc = {k: 1 for k in keys}
    remaining = total - sum(alloc.values())
    while remaining > 0:
        room = {k: counts[k] - alloc[k] for k in keys if counts[k] > alloc[k]}
        pool = sum(room.values())
        quotas = {k: remaining * room[k] / pool for k in room}
        step = {k: min(room[k], int(q)) for k, q in quotas.items()}
        if sum(step.values()) == 0:
            best = max(room, key=lambda k: (quotas[k], k))
            step = {best: 1}
        for k, v in step.items():
            alloc[k] += v
        remaining -= sum(step.values())
    return alloc


def write_sample(rows: list[EvalRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["result_code", "field"])
        for r in rows:
            w.writerow([r.result_code, r.field])


def read_sample(path: Path, rows: list[EvalRow]) -> list[EvalRow]:
    index = {r.key: r for r in rows}
    with path.open(newline="", encoding="utf-8") as f:
        keys = [f"{int(r['result_code'])}|{r['field']}" for r in csv.DictReader(f)]
    missing = [k for k in keys if k not in index]
    if missing:
        raise DatasetError(f"{len(missing)} sampled rows not in the export, e.g. {missing[0]}")
    return [index[k] for k in keys]


def _level(value: str) -> int | None:
    v = (value or "").strip()
    if not v:
        return None
    return int(float(v))


def _links(value: str) -> tuple[str, ...]:
    out: list[str] = []
    for part in (value or "").split("|"):
        url = part.strip()
        if url.lower().startswith(("http://", "https://")) and url not in out:
            out.append(url)
    return tuple(out)
