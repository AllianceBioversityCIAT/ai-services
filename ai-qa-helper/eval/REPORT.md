# AI suggestions: v1 vs v2 on the 2025 sample

Run of 2026-11-12 in TEST: Claude Haiku 5.5 through Bedrock Runtime (`us.anthropic.claude-haiku-5-5`), effort `medium`. 280 sampled rows, 40 per field; 444 model calls; USD 0.73. No call failed and no output was invalid.

## Conclusions

1. **Use v2 for the Impact Areas in December.**
   - Its agreement with the final QA value matches v1: 51.0 % exact for v2 against 52.2 % for v1, n = 157. The per-field differences are 1 to 3 rows, which is within noise at this sample size.
   - Its quotes are verified much more often: 87.9 % against 50.3 %. A verified quote is what lets the signal turn green or red instead of amber.
   - It costs 22 % less, thanks to the cached rubric.
   - It drops the contradictions of the old prompts.
2. **IRL and IUL are not ready.**
   - Both versions underestimate the level by about 2: the mean suggested-minus-final difference is −1.7 to −1.9 for IRL, and −0.7 (v1) or −1.9 (v2) for IUL.
   - Both score below the majority class: 6 % exact and a MAE of 2.5 to 3.8.
   - The suggestion for these two fields should not be shown in December until this is fixed. That is a decision for the PO.
3. **The signal rule needs no change for v2.** At least 73 % of v2 quotes are verified in every field. v1 falls to 30 % in some fields.
4. **QA changed few reported values.**
   - In this sample, QA changed the reported value in only 15 of the 141 rows that had both a reported and a final value. Ten of those 15 are IRL.
   - Accepting the reported value is therefore a very strong baseline. The suggestion helps most as a flag, and the signal-versus-decision table below rests on few changed rows.
5. **Coverage.** The model answered 222 of 280 rows (79 %).
   - 40 rows had only private links, mostly CGIAR SharePoint files that need a login.
   - 18 rows had no readable evidence.
   - Read-only access to those SharePoint files is the largest coverage gain available. It is a decision for after the batch.

## Method and limits

- **Reference.** The final QA value of 2025, from the Reporting export (`eval/README.md`).
- **Sample.**
  - For each field, at least 8 rows per final value for Impact Areas and 2 for IRL and IUL.
  - Result types keep their population share; Knowledge products are about 51 % of the Impact Area rows.
  - Because classes are balanced on purpose, the pooled accuracy over the sample is not the population accuracy. v1 and v2 are compared on the same rows.
- **Reported value.**
  - The export leaves it empty, so it comes from the previous helper's pre-QA 2025 labels of January 2026.
  - 65 % of the export rows match, and 181 of the 280 sampled rows have a reported value.
  - The signal metrics use only the rows that have one.
- **Sample size.** n is 28 to 36 per field, so a difference of 10 points is about 3 rows.
- **Evidence.**
  - The worker's own reader (`app/evidence`): links flagged for the field, otherwise all of the result's links, up to 5.
  - Both versions see the same evidence, cached once.
- **How v1 was reproduced.**
  - v1 is the previous helper's production prompt text, byte for byte.
  - It is sent the way that helper's code sent it: system message `You are a helpful assistant.`, then `Context: <JSON>` followed by the prompt.
  - `{context}` and `{core_innovation}` are left unfilled, as that code left them.
  - Only the mechanics differ: no temperature, and structured output with the same keys plus `Evidence Quote`. See `prompts/README.md`.
- **Previous helper.** Its gpt-5 predictions overlap the sample in only 1 to 2 rows, too few to compare.

- Run `v1-1.0.0,v2-1.0.0-medium`: 560 records over 280 sampled rows.
- Reference: final QA value 2025 (Reporting export). Majority class over the whole export.
- Evidence: links flagged for the field, else all the result's links (max 5), read by `app/evidence`.

## Agreement with the final QA value

Rows where the model answered. Exact and ±1 in %; baselines on the same rows.

| Field | Version | Answered / sample | Exact | ±1 | MAE | Majority exact | Submitter exact | Previous helper exact (n) |
|---|---|---|---|---|---|---|---|---|
| gender | v1-1.0.0 | 36 / 40 | 52.8 | 94.4 | 0.53 | 52.8 | 100.0 | – |
| gender | v2-1.0.0 | 36 / 40 | 61.1 | 94.4 | 0.44 | 52.8 | 100.0 | – |
| climate | v1-1.0.0 | 31 / 40 | 51.6 | 96.8 | 0.52 | 32.3 | 93.8 | – |
| climate | v2-1.0.0 | 31 / 40 | 48.4 | 96.8 | 0.55 | 32.3 | 93.8 | – |
| nutrition | v1-1.0.0 | 28 / 40 | 60.7 | 96.4 | 0.43 | 35.7 | 89.5 | – |
| nutrition | v2-1.0.0 | 28 / 40 | 50.0 | 92.9 | 0.57 | 35.7 | 89.5 | – |
| environment_biodiversity | v1-1.0.0 | 30 / 40 | 66.7 | 100.0 | 0.33 | 40.0 | 93.8 | – |
| environment_biodiversity | v2-1.0.0 | 30 / 40 | 60.0 | 90.0 | 0.50 | 40.0 | 93.8 | – |
| poverty | v1-1.0.0 | 32 / 40 | 31.2 | 90.6 | 0.78 | 46.9 | 94.7 | – |
| poverty | v2-1.0.0 | 32 / 40 | 34.4 | 87.5 | 0.78 | 46.9 | 94.7 | – |
| innovation_readiness_level | v1-1.0.0 | 31 / 40 | 6.5 | 35.5 | 2.52 | 16.1 | 64.3 | 0.0 (1) |
| innovation_readiness_level | v2-1.0.0 | 31 / 40 | 6.5 | 32.3 | 2.74 | 16.1 | 64.3 | 0.0 (1) |
| innovation_use_level | v1-1.0.0 | 34 / 40 | 5.9 | 29.4 | 3.44 | 20.6 | 100.0 | 0.0 (2) |
| innovation_use_level | v2-1.0.0 | 34 / 40 | 5.9 | 20.6 | 3.79 | 20.6 | 100.0 | 0.0 (2) |

## Knowledge products vs other result types

Model agreement with the final QA value on each group (exact % / ±1 % / n).

| Field | Version | Knowledge product | Other types |
|---|---|---|---|
| gender | v1-1.0.0 | 38.1 / 90.5 / 21 | 73.3 / 100.0 / 15 |
| gender | v2-1.0.0 | 61.9 / 90.5 / 21 | 60.0 / 100.0 / 15 |
| climate | v1-1.0.0 | 55.6 / 94.4 / 18 | 46.2 / 100.0 / 13 |
| climate | v2-1.0.0 | 50.0 / 100.0 / 18 | 46.2 / 92.3 / 13 |
| nutrition | v1-1.0.0 | 55.6 / 94.4 / 18 | 70.0 / 100.0 / 10 |
| nutrition | v2-1.0.0 | 55.6 / 88.9 / 18 | 40.0 / 100.0 / 10 |
| environment_biodiversity | v1-1.0.0 | 70.6 / 100.0 / 17 | 61.5 / 100.0 / 13 |
| environment_biodiversity | v2-1.0.0 | 64.7 / 88.2 / 17 | 53.8 / 92.3 / 13 |
| poverty | v1-1.0.0 | 33.3 / 88.9 / 18 | 28.6 / 92.9 / 14 |
| poverty | v2-1.0.0 | 27.8 / 83.3 / 18 | 42.9 / 92.9 / 14 |
| innovation_readiness_level | v1-1.0.0 | – / – / 0 | 6.5 / 35.5 / 31 |
| innovation_readiness_level | v2-1.0.0 | – / – / 0 | 6.5 / 32.3 / 31 |
| innovation_use_level | v1-1.0.0 | – / – / 0 | 5.9 / 29.4 / 34 |
| innovation_use_level | v2-1.0.0 | – / – / 0 | 5.9 / 20.6 / 34 |

## Coverage, quotes and signal

| Field | Version | Unavailable (reason: n) | Errors | Verified quotes | Green | Amber | Red |
|---|---|---|---|---|---|---|---|
| gender | v1-1.0.0 | no_readable_evidence: 2, private_link: 2 | 0 | 30.6% | 2 | 34 | 0 |
| gender | v2-1.0.0 | no_readable_evidence: 2, private_link: 2 | 0 | 86.1% | 9 | 26 | 1 |
| climate | v1-1.0.0 | no_readable_evidence: 3, private_link: 6 | 0 | 67.7% | 4 | 27 | 0 |
| climate | v2-1.0.0 | no_readable_evidence: 3, private_link: 6 | 0 | 96.8% | 6 | 25 | 0 |
| nutrition | v1-1.0.0 | no_readable_evidence: 4, private_link: 8 | 0 | 53.6% | 7 | 21 | 0 |
| nutrition | v2-1.0.0 | no_readable_evidence: 4, private_link: 8 | 0 | 78.6% | 8 | 19 | 1 |
| environment_biodiversity | v1-1.0.0 | no_readable_evidence: 3, private_link: 7 | 0 | 30.0% | 2 | 28 | 0 |
| environment_biodiversity | v2-1.0.0 | no_readable_evidence: 3, private_link: 7 | 0 | 80.0% | 6 | 24 | 0 |
| poverty | v1-1.0.0 | no_readable_evidence: 3, private_link: 5 | 0 | 71.9% | 5 | 24 | 3 |
| poverty | v2-1.0.0 | no_readable_evidence: 3, private_link: 5 | 0 | 96.9% | 6 | 23 | 3 |
| innovation_readiness_level | v1-1.0.0 | no_readable_evidence: 2, private_link: 7 | 0 | 41.9% | 0 | 24 | 7 |
| innovation_readiness_level | v2-1.0.0 | no_readable_evidence: 2, private_link: 7 | 0 | 77.4% | 0 | 19 | 12 |
| innovation_use_level | v1-1.0.0 | no_readable_evidence: 1, private_link: 5 | 0 | 47.1% | 0 | 27 | 7 |
| innovation_use_level | v2-1.0.0 | no_readable_evidence: 1, private_link: 5 | 0 | 73.5% | 0 | 23 | 11 |

## Signal against the final decision

Kept: QA kept the reported value. Changed: QA changed it. A useful signal is mostly green on kept rows and red or amber on changed ones.

| Version | Green kept | Green changed | Amber kept | Amber changed | Red kept | Red changed |
|---|---|---|---|---|---|---|
| v1-1.0.0 | 19 | 1 | 94 | 10 | 13 | 4 |
| v2-1.0.0 | 33 | 2 | 70 | 8 | 23 | 5 |

## Tokens and cost

| Version | Input | Cache read | Output | USD |
|---|---|---|---|---|
| v1-1.0.0 | 2,473,832 | 0 | 255,874 | 0.41 |
| v2-1.0.0 | 2,059,459 | 777,235 | 138,475 | 0.32 |
