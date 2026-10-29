# How institution matching works

Current implementation: `src/mapping_clarisa_comparison.py`, `src/embeddings.py`, `src/supabase_client.py`, and vector RPCs in `sql/create_clarisa_vector_table.sql`, all relative to the backend directory. This guide replaces an older 50/40/10 scoring description; the executable final weights are 60/30/10.

## Candidate retrieval

1. Prepare the institution name/acronym and detect language. For non-English names, AWS Translate supplies an additional English query; failures fall back to the original text.
2. Generate Titan Text Embeddings V2 vectors with 1,024 dimensions. Semantic text retains its wording rather than being reduced to fuzzy-search normalization.
3. Query Supabase vector RPCs with a semantic threshold of 0.20, up to five candidates per query. With an acronym, retrieval combines name/acronym similarities using weights 0.70/0.30; without one it uses the name path.
4. Combine original/translated results, deduplicate by CLARISA ID using the best semantic candidate, and rerank the retained candidates. Translation metadata identifies the query used.

The retrieval threshold broadens the candidate pool. It is not the accepted-match threshold or the final score formula.

## Final reranking

RapidFuzz compares normalized names/acronyms (including case/accent normalization). Final score:

```text
final_score = 0.60 × cosine_similarity
            + 0.30 × fuzz_name_score
            + 0.10 × fuzz_acronym_score
```

Fuzzy scores are scaled to 0–1. A missing acronym contributes zero; the other weights are not automatically renormalized. For example, cosine 0.90, name 0.80, and acronym 1.00 produce 0.88. This is a combined similarity score, not a calibrated probability.

The search result exposes a best match only at `final_score >= 0.60`; candidates can still be returned below that threshold. Returned score components support review of why a candidate ranked highly.

## Two consumers, different thresholds

| Score | Manual spreadsheet/pending review | Automatic endpoint |
| --- | --- | --- |
| `>0.95` | excellent | excellent: duplicate REJECT |
| `0.85–0.95` inclusive | excellent | very_good: verify same institution |
| `0.70–<0.85` | good | good: verify same institution |
| `0.60–<0.70` | fair | fair: web/rules review |
| `<0.60` / no accepted best match | no_match | no_match: web/rules review |

Manual processing can attach web research for no-match cases when enabled; it does not automatically accept/reject based on its quality label. The frontend displays the manual labels.

The automatic route rejects confirmed duplicates; otherwise web/rules review returns ACCEPT or MANUAL_REVIEW. Completeness information is not an independent acceptance gate in that path. See [API semantics](../../docs/API_GUIDE.md#automated-evaluation), including external creation/response and notification effects.

## Cache, synchronization, and validation

Manual batch processing can reuse results by normalized name, so cache hits may bypass fresh search/model work. Catalog synchronization can invalidate cache. Inspect the cache table constant for the current branch; development and service-main use separate tables.

Candidate quality depends on source catalog data, translations, provider behavior, and thresholds. No latency, cost, accuracy, or live-policy guarantee is established by this guide. Offline checks can verify formulas, boundaries, and routing with synthetic data; live model/search checks require deliberate scope because examples under `test/` call external systems.
