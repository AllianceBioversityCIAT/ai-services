# v1 vs v2 comparison (2025 sample)

Runs the prompt versions over a stratified sample of 2025 results and measures them against the
final QA values. It uses the worker's own path (`app/worker/suggest.py`: same evidence reader,
prompt builder, model call, quote check and signal) and writes nothing to DynamoDB.

## Input

`eval/.data/prms_2025_final.csv`, prepared by Reporting with no personal data. It has one row per
(result, field):

| Column | Content |
|---|---|
| `result_code` | PRMS result code |
| `field` | `gender`, `climate`, `nutrition`, `environment_biodiversity`, `poverty`, `innovation_readiness_level`, `innovation_use_level` |
| `result_type` | PRMS result type |
| `reported_value` | Level the submitter reported (Impact Areas 0–2, IRL/IUL 0–9) |
| `final_qa_value` | Level after QA 2025: the reference |
| `title`, `description` | As reported |
| `evidence_urls_field` | Links flagged for this field, separated by ` \| ` |
| `evidence_urls_all` | All the result's links, separated by ` \| ` |

Everything under `eval/.data/` is gitignored: the export, the sample, the evidence cache and the
run files. Only the aggregate report may be copied out of it.

## Steps

```bash
uv run python -m eval.compare sample --per-field 40     # stratified: field x final value x evidence status
uv run python -m eval.compare estimate --no-fetch        # cost from row counts, instant
uv run python -m eval.compare estimate                   # reads the evidence (public links), no model call
uv run python -m eval.compare run --max-usd 3 --profile qa-ai-deployer
uv run python -m eval.compare report --jose-csv <previous helper production_ai_outputs CSV>
```

- **Cost.** `run` needs `--max-usd`, which has no default. It stops before a call that would go over it. Running the same command again resumes where it stopped, and nothing is paid twice.
- **Shared evidence.** Each sampled row's evidence is read once and cached on disk. v1 and v2 get the same evidence, and re-runs don't fetch it again.
- **Model ID.** `MODEL_ID` (default `anthropic.claude-haiku-5-5`) and `AWS_REGION` come from the environment, the same as in the worker.

## Report

`runs/<name>.report.md` covers each field and version:

- exact match, within ±1 and MAE against the final value;
- the same metrics for the majority class, the submitter's value and the previous helper (gpt-5, March 2026), all on the same rows;
- coverage and the reasons for unavailable rows;
- the share of verified quotes;
- the signal distribution, and the signal against whether QA kept or changed the reported value;
- tokens and USD.

The report contains no evidence text, quotes or explanations. The run file has them, for review,
and stays in `eval/.data/`.

## Cost

Prices for Haiku 5.5 are in `eval/pricing.py`, with a 10% surcharge for the regional Bedrock
endpoint. A worst-case estimate for 40 rows per field, all with evidence, both versions (560
calls): **≈ USD 1.2**. Confirm the Bedrock price on the AWS pricing page before approving.
