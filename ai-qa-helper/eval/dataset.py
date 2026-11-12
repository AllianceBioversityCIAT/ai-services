"""The 2025 PRMS export (prepared by Reporting) and the stratified sample.

Expected file: ``eval/.data/prms_2025_final.csv`` (gitignored), one row per (result, field):

    result_code, field, result_type, reported_value, final_qa_value, title, description,
    evidence_urls_field, evidence_urls_all

``field`` is one of FIELD_KEYS; values are levels (Impact Areas 0-2, IRL/IUL 0-9), empty when
missing; URL lists are separated by `` | ``. No personal data.

``reported_value`` may be empty in the export. ``eval.compare fill-reported`` then derives it by
Result Code from the previous helper's pre-QA 2025 reference (``reported_2025.csv``), which
``load_rows`` merges when the export leaves the value empty.
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


REFERENCE_COLUMNS = {
    "gender": "Gender Tag Level",
    "climate": "Climate Tag Level",
    "nutrition": "Nutrition Tag Level",
    "environment_biodiversity": "Environment and/or biodiversity Tag Level",
    "poverty": "Poverty Tag Level",
    "innovation_readiness_level": "Readiness Level",
    "innovation_use_level": "Innovation Use Level",
}
TAG_LABELS = {"not targeted": 0, "significant": 1, "principal": 2}


def reference_levels(path: Path) -> dict[str, int]:
    """``result_code|field`` -> reported level from the previous helper's pre-QA 2025 labels
    (``reference_prms_2025_subset_labels.csv``). Read as data only."""
    out: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            code = (r.get("Result Code") or "").strip()
            if not code.isdigit():
                continue
            for field, column in REFERENCE_COLUMNS.items():
                raw = (r.get(column) or "").strip()
                level = TAG_LABELS.get(raw.lower()) if field in IMPACT_AREAS else _level(raw) if raw else None
                if level is not None:
                    out[f"{int(code)}|{field}"] = level
    return out


IMPACT_AREAS = {"gender", "climate", "nutrition", "environment_biodiversity", "poverty"}


def write_reported(levels: dict[str, int], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["result_code", "field", "reported_value"])
        for key in sorted(levels):
            code, field = key.split("|")
            w.writerow([code, field, levels[key]])


def read_reported(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as f:
        return {f"{int(r['result_code'])}|{r['field']}": int(r["reported_value"]) for r in csv.DictReader(f)}


def load_rows(path: Path, reported: dict[str, int] | None = None) -> list[EvalRow]:
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
                    reported=_level(r["reported_value"])
                    if r["reported_value"].strip() or not reported
                    else reported.get(f"{int(r['result_code'])}|{field}"),
                    final=_level(r["final_qa_value"]),
                    title=r["title"].strip(),
                    description=r["description"].strip(),
                    links_field=_links(r["evidence_urls_field"]),
                    links_all=_links(r["evidence_urls_all"]),
                )
            )
    return rows


MIN_PER_CLASS = {"impact_area": 8, "level": 2}
"""Minimum rows per final value, so every class (notably Principal = 2) can be measured."""


def stratified_sample(rows: list[EvalRow], per_field: int, seed: int = 2025) -> list[EvalRow]:
    """Two levels, per field: first across final QA values (proportional, with MIN_PER_CLASS rows per
    value when ``per_field`` allows it), then, inside each value, across evidence status x result type
    (proportional, no minimum), so result types keep their population share in every field.
    Deterministic for a given seed and file. Classes are balanced on purpose: pooled accuracy over
    the sample is not the population accuracy; compare versions on the same rows."""
    by_field: dict[str, list[EvalRow]] = defaultdict(list)
    for r in rows:
        if r.final is not None:
            by_field[r.field].append(r)
    sample: list[EvalRow] = []
    for field in sorted(by_field):
        classes: dict[int, list[EvalRow]] = defaultdict(list)
        for r in sorted(by_field[field], key=lambda x: x.result_code):
            classes[r.final].append(r)
        minimum = MIN_PER_CLASS["impact_area" if field in IMPACT_AREAS else "level"]
        per_class = allocate({k: len(v) for k, v in classes.items()}, per_field, minimum)
        rng = random.Random(f"{seed}:{field}")
        for final in sorted(classes):
            strata: dict[tuple[str, str], list[EvalRow]] = defaultdict(list)
            for r in classes[final]:
                strata[(r.evidence_status, r.result_type)].append(r)
            sizes = allocate({k: len(v) for k, v in strata.items()}, per_class[final], 0)
            for k in sorted(strata):
                members = strata[k][:]
                rng.shuffle(members)
                sample.extend(members[: sizes[k]])
    return sample


def allocate(counts: dict, total: int, minimum: int = 1) -> dict:
    """Proportional allocation of ``total`` over strata: first ``minimum`` per stratum (capped by its
    size) when ``total`` allows it, then one row at a time to the stratum furthest below its
    proportional share of ``total``. Never above a stratum's size. Deterministic."""
    available = sum(counts.values())
    if total >= available:
        return dict(counts)
    keys = sorted(counts)
    floor = {k: min(minimum, counts[k]) for k in keys}
    alloc = dict(floor) if minimum and total >= sum(floor.values()) else {k: 0 for k in keys}
    target = {k: total * counts[k] / available for k in keys}
    for _ in range(total - sum(alloc.values())):
        open_keys = [k for k in keys if alloc[k] < counts[k]]
        k = max(open_keys, key=lambda k: (target[k] - alloc[k], counts[k], str(k)))
        alloc[k] += 1
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
