import csv
import json

import pytest

from app.evidence.extractor import EvidenceSource, summarize
from app.llm.output_schema import SuggestionOutputV2, V1ImpactAreaOutput
from app.llm.provider import LlmUsage, SuggestionResult
from eval.compare import main
from eval.dataset import COLUMNS, DatasetError, allocate, load_rows, stratified_sample
from eval.metrics import compute, load_jose, render
from eval.pricing import usd
from eval.runner import DiskEvidenceCache, RunConfig, load_records, run

QUOTE = "The cooperative trained 300 women in seed business management during 2025."


def write_export(path, n=30):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(n):
            final = i % 3
            field_links = "https://example.org/a | https://example.org/b" if i % 2 else ""
            all_links = "https://example.org/a | https://example.org/b | https://example.org/c" if i % 5 else ""
            w.writerow([1000 + i, "gender", "innovation_development", (final + i % 2) % 3, final,
                        f"Result {i}", "Description", field_links, all_links])
        w.writerow([2000, "innovation_readiness_level", "innovation_development", 4, "", "T", "D", "", ""])


class Extractor:
    def __init__(self):
        self.calls = []

    def extract(self, urls):
        self.calls.append(urls)
        return summarize([EvidenceSource(i, u, "text", text=QUOTE) for i, u in enumerate(urls)])


class Provider:
    """Answers 1 with a verified quote; v1 or v2 schema according to the request."""

    def __init__(self):
        self.calls = 0

    def suggest(self, request):
        self.calls += 1
        if request.output_model is V1ImpactAreaOutput:
            out = V1ImpactAreaOutput(reasoning="r", short_justification="j", score=1, component="N/A", evidence_quote=QUOTE)
        else:
            out = SuggestionOutputV2(reasoning="r", value=1, component=None, evidence_quote=QUOTE,
                                     evidence_source_index=0, explanation="e")
        return SuggestionResult("ok", "anthropic.claude-haiku-5-5", LlmUsage(10_000, 1_000, 0, 0), out)


@pytest.fixture
def export(tmp_path):
    p = tmp_path / "prms_2025_final.csv"
    write_export(p)
    return p


def test_load_rows_parses_levels_links_and_evidence_status(export):
    rows = load_rows(export)
    r1 = next(r for r in rows if r.result_code == 1001)
    assert r1.final == 1 and r1.links_field == ("https://example.org/a", "https://example.org/b")
    assert r1.evidence_status == "field" and r1.field_key == "general.gender_tag"
    r0 = next(r for r in rows if r.result_code == 1000)
    assert r0.evidence_status == "none" and r0.links == []
    assert next(r for r in rows if r.result_code == 2000).final is None


def test_load_rows_rejects_missing_columns_and_unknown_fields(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("result_code,field\n1,gender\n")
    with pytest.raises(DatasetError, match="missing columns"):
        load_rows(bad)
    p = tmp_path / "x.csv"
    write_export(p, 1)
    p.write_text(p.read_text().replace("gender", "genre"))
    with pytest.raises(DatasetError, match="unknown field"):
        load_rows(p)


def test_allocation_is_proportional_with_one_per_stratum():
    assert allocate({"a": 80, "b": 15, "c": 5}, 20) == {"a": 16, "b": 3, "c": 1}
    assert allocate({"a": 97, "b": 2, "c": 1}, 10) == {"a": 8, "b": 1, "c": 1}
    assert sum(allocate({"a": 1, "b": 1, "c": 98}, 10).values()) == 10
    assert allocate({"a": 3, "b": 2}, 40) == {"a": 3, "b": 2}
    alloc = allocate({"a": 900, "b": 90, "c": 10}, 40, minimum=8)
    assert alloc["c"] == 8 and alloc["b"] >= 8 and sum(alloc.values()) == 40


def test_stratified_sample_is_deterministic_and_skips_rows_without_final(export):
    rows = load_rows(export)
    a, b = stratified_sample(rows, 12), stratified_sample(rows, 12)
    assert [r.key for r in a] == [r.key for r in b] and len(a) == 12
    assert all(r.final is not None for r in a)
    assert {r.final for r in a} == {r.final for r in rows if r.final is not None}


def test_sample_keeps_a_minimum_per_final_class_and_type_shares():
    from eval.dataset import EvalRow

    rows = [
        EvalRow(i, "poverty", "Knowledge product" if i % 2 else "Innovation development",
                None, 2 if i < 10 else i % 2, "t", "d", ("https://e.org/a",), ("https://e.org/a",))
        for i in range(400)
    ]
    s = stratified_sample(rows, 40)
    assert len(s) == 40 and sum(r.final == 2 for r in s) >= 8
    kp = sum(r.result_type == "Knowledge product" for r in s)
    assert 16 <= kp <= 24  # about half, like the population


def test_pricing_uses_the_short_and_long_rate_cards():
    assert usd(LlmUsage(50_000, 0), multiplier=1) == pytest.approx(0.005)
    assert usd(LlmUsage(0, 1_000_000), multiplier=1) == pytest.approx(0.50)
    assert usd(LlmUsage(0, 0, 50_000, 0), multiplier=1) == pytest.approx(0.0005)
    assert usd(LlmUsage(150_000, 0), multiplier=1) == pytest.approx(0.075)  # long prompt card
    assert usd(LlmUsage(50_000, 0)) == pytest.approx(0.0055)


def test_live_run_records_every_row_and_version_then_resumes(export, tmp_path):
    rows = stratified_sample(load_rows(export), 30)
    out = tmp_path / "run.jsonl"
    provider, extractor = Provider(), Extractor()
    cfg = RunConfig(versions=["v1-1.0.0", "v2-1.0.0"], max_usd=5, workers=3)
    run(rows, cfg, out, extractor, provider)
    recs = load_records(out)
    assert len(recs) == 2 * len(rows)
    no_links = [r for r in recs.values() if r["evidence_status"] == "none"]
    assert no_links and all(r["status"] == "unavailable" and r["reason"] == "no_readable_evidence" for r in no_links)
    ok = [r for r in recs.values() if r["status"] == "ok"]
    assert provider.calls == len(ok) and all(r["quote_verified"] for r in ok)
    assert len(extractor.calls) == sum(1 for r in rows if r.links)  # one extraction per row, both versions

    calls = provider.calls
    run(rows, cfg, out, extractor, provider)
    assert provider.calls == calls  # resumed: nothing paid twice


def test_budget_guard_stops_before_exceeding(export, tmp_path):
    rows = stratified_sample(load_rows(export), 30)
    out = tmp_path / "run.jsonl"
    cfg = RunConfig(versions=["v2-1.0.0"], max_usd=0.01, workers=1)
    summary = run(rows, cfg, out, Extractor(), Provider())
    spent = sum(r.get("usd", 0) for r in load_records(out).values())
    assert summary.stopped_by_budget and spent <= 0.01


def test_live_run_requires_a_budget(export, tmp_path):
    with pytest.raises(ValueError):
        run([], RunConfig(versions=["v2-1.0.0"]), tmp_path / "x.jsonl", Extractor(), Provider())


def test_dry_run_calls_no_model_and_estimates(export, tmp_path):
    rows = stratified_sample(load_rows(export), 30)
    out = tmp_path / "est.jsonl"
    run(rows, RunConfig(versions=["v1-1.0.0", "v2-1.0.0"], dry_run=True, fetch=False), out, None, None)
    recs = load_records(out)
    est = [r for r in recs.values() if r["status"] == "estimate"]
    assert est and all(r["input_tokens"] > 1000 and r["usd"] > 0 for r in est)


def test_metrics_and_report_compare_with_baselines(export, tmp_path):
    rows = load_rows(export)
    sample = stratified_sample(rows, 30)
    out = tmp_path / "run.jsonl"
    run(sample, RunConfig(versions=["v1-1.0.0", "v2-1.0.0"], max_usd=5, workers=2), out, Extractor(), Provider())
    jose_csv = tmp_path / "jose.csv"
    with jose_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["result_code", "dimension", "ai_score_norm", "success"])
        for r in sample:
            w.writerow([r.result_code, "Gender", r.final, "True"])
    cells = compute(load_records(out), rows, load_jose(jose_csv))
    c = cells[("gender", "v2-1.0.0")]
    answered = [r for r in sample if r.links]
    assert c.answered == len(answered) and c.model.n == len(answered)
    assert c.model.exact == sum(1 for r in answered if r.final == 1)
    assert c.jose.exact == c.jose.n == len(answered)
    md = render(cells, "T", ["note"])
    assert "| gender | v2-1.0.0 |" in md and QUOTE not in md  # aggregates only


def test_cli_sample_estimate_and_report(export, tmp_path, capsys):
    data = export.parent
    assert main(["--data", str(data), "sample", "--per-field", "10"]) == 0
    assert (data / "sample.csv").exists()
    assert main(["--data", str(data), "estimate", "--no-fetch"]) == 0
    printed = capsys.readouterr().out
    assert "USD estimated" in printed and "model_calls=" in printed


def test_disk_cache_round_trip(tmp_path):
    cache = DiskEvidenceCache(tmp_path / "c")
    src = EvidenceSource(0, "https://example.org/a", "text", kind="web", title="t", text=QUOTE)
    cache.put(src.url, src)
    assert cache.get(src.url) == src and cache.get("https://example.org/other") is None
    assert json.loads(next((tmp_path / "c").iterdir()).read_text())["url"] == src.url


def test_fill_reported_from_the_pre_qa_reference(export, tmp_path, capsys):
    ref = tmp_path / "reference.csv"
    with ref.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Result Code", "Gender Tag Level", "Climate Tag Level", "Nutrition Tag Level",
                    "Environment and/or biodiversity Tag Level", "Poverty Tag Level", "Readiness Level",
                    "Innovation Use Level"])
        w.writerow([1001, "Principal", "Significant", "", "", "", "", ""])
        w.writerow([1002, "Not Targeted", "", "", "", "", "", ""])
        w.writerow([2000, "", "", "", "", "", "7", ""])
        w.writerow([5555, "Significant", "", "", "", "", "", ""])  # not in the export
    data = export.parent
    # the export used here has reported values; blank them to exercise the merge
    text = export.read_text().splitlines()
    rows = list(csv.reader(text))
    for r in rows[1:]:
        r[3] = ""
    with export.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    assert main(["--data", str(data), "fill-reported", "--reference", str(ref)]) == 0
    out = capsys.readouterr().out
    assert "3 of 31 export rows matched" in out
    from eval.dataset import read_reported
    merged = load_rows(export, read_reported(data / "reported_2025.csv"))
    by_key = {r.key: r.reported for r in merged}
    assert by_key["1001|gender"] == 2 and by_key["1002|gender"] == 0
    assert by_key["2000|innovation_readiness_level"] == 7 and by_key["1003|gender"] is None
