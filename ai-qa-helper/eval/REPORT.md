# AI suggestions: v1 vs v2 on the 2025 sample

Run of 2026-11-12 in TEST: Claude Haiku 5.5 through Bedrock Runtime (`us.anthropic.claude-haiku-5-5`), effort `medium`. 280 sampled rows, 40 per field; 444 model calls; USD 0.73. No call failed and no output was invalid.

## Conclusions

1. **Use v2 for the Impact Areas in December.**
   - Its agreement with the final QA value matches v1: 51.0 % exact for v2 against 52.2 % for v1, n = 157. The per-field differences are 1 to 3 rows, which is within noise at this sample size.
   - Its quotes are verified much more often: 87.9 % against 50.3 %. A verified quote is what lets the signal turn green or red instead of amber.
   - It costs 22 % less, thanks to the cached rubric.
   - It drops the contradictions of the old prompts.
2. **IRL and IUL are not ready.** The diagnosis below finds no technical defect: both versions, and the previous helper on its final batch, underestimate by about 2 levels compared with QA practice.
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

## Reading the signal (v2)

- **Green is reliable.** In 33 of the 35 green rows that had a reported value, QA kept that value.
- **Red is mostly a false alarm.** In 23 of the 28 red rows, QA kept the reported value; QA changed it in only 5.
  - Most red rows are IRL and IUL, where the model underestimates (see below).
- **Proposal for the chip text:**
  - Red reads **"Review"** ("revisar"), never "incorrect". It means "look at the evidence before validating", not "the reported value is wrong".
  - Green and amber keep their meaning: consistent with the evidence, and check.
  - The wording lives in `onecgiar_qa` (`review-ai-note.ts`); the contract only carries `signal`.

## IRL and IUL: diagnosis

The question was why v1 does not reproduce the previous helper's figures (IRL 21 % exact, MAE 1.9) and why both versions come out about 2 levels low. The data below cost nothing: it comes from the run above and the previous helper's own published figures.

- **v1 does reproduce the previous helper.**
  - Its 21.1 % / MAE 1.92 pools 512 innovations from all its production pushes, including earlier prompt versions.
  - For its final batch (V25, the same prompts as our v1), its own figures against the final value are 18.8 % exact, MAE 2.48 and a signed error of −1.94 (n = 48).
  - Our v1 gets MAE 2.45 and −1.92 when weighted by population. The exact rate differs (6.5 % against 18.8 %), but with 2 of 31 rows the 95 % interval is 1.8–20.7 %, so the two overlap.
  - On the 34 IRL rows its batch shares with this export, the previous helper got 11.8 % exact, MAE 3.06 and −2.53.
- **The scales are consistent.**
  - The final value, the reported value and the model output all use levels 0–9; none uses control-list ids or 1–9.
  - The reported value equals the final value in 691 of 832 IRL rows and 157 of 169 IUL rows of the export.
  - The model's suggestions span 0–9 (v1) and 1–8 (v2).
- **The balancing does not explain it.** Weighted by the population's level distribution, the figures hardly change.

  | Field | Version | Exact | ±1 | MAE | Bias |
  |---|---|---|---|---|---|
  | IRL | v1 | 6.2 % | 36.8 % | 2.45 | −1.92 |
  | IRL | v2 | 7.4 % | 32.1 % | 2.72 | −2.14 |
  | IUL | v1 | 5.7 % | 25.5 % | 3.51 | −0.45 |
  | IUL | v2 | 6.1 % | 17.4 % | 3.83 | −1.63 |

  The majority class is level 9: 20.6 % of IRL and 17.1 % of IUL.
- **Confusion matrices** (rows: final value; columns: suggested value).
  - For IRL, final values 6 to 9 are mostly suggested as 2 to 6.
  - For IUL, the errors go both ways: final 3 and 5 are often suggested as 8, and final 8 and 9 as 0 or 2. The spread, not only the bias, drives its MAE.
  - Full matrices: `eval/.data/` diagnosis output (not versioned).
- **The worst underestimations come from little or indirect evidence.** Among the 5 per field and version:
  - CGSpace records with metadata only (381 characters), LinkedIn posts, short web pages (317 characters), spreadsheets;
  - SharePoint files that are partly private, or long PDFs that do not state the maturity explicitly.

  None failed because of a technical error.
- **JavaScript-only pages are a minor factor.**
  - 10 of the 17 web pages read for IRL, and 5 of 16 for IUL, have fewer than 1,500 characters. Some are probably pages that only render with JavaScript.
  - IRL: the bias stays about the same with 8,000 or more characters of evidence (−1.8 for v1, −2.0 for v2) as with less (−1.7, −1.8). More text does not remove it.
  - IUL: the bias depends on the amount of evidence (−0.3 / −1.0 with rich evidence, −2.0 / −4.6 with thin evidence), but the MAE stays above 3 either way.
- **Root cause: the criteria versus QA practice.**
  - The prompts tell the model to assign the lowest level the evidence explicitly supports, and to ignore plans and ambition.
  - QA mostly accepts the level the submitter claims: it kept the reported level in 18 of 28 sampled IRL rows and 17 of 17 IUL rows. The previous helper's metrics show the same, 86 % and 95 %.
  - The model suggests below the reported level in 21–22 of 28 IRL rows and 11–14 of 17 IUL rows.
  - This is a disagreement about criteria, not a defect. It needs expert input on how strict the levels should be, and a prompt revision validated against the final values.

**Proposal to the PO:** do not show IRL and IUL suggestions in the December batch; they would show as "not available: no criteria for this field". Review the IRL and IUL criteria with the innovation experts before the February 2027 cycle.

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
