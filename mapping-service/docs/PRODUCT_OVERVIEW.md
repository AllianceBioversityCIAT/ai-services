# Mapping Service workflows

Mapping resolves staff and institution names supplied by another application to catalog identifiers. It uses STAR staff data and CLARISA institution data available through OpenSearch, with an external LLM API to compare retrieved candidates.

## Caller workflow

1. Send an entries array to `POST /map/fields`, using `staff` or `institution` for each value.
2. Choose `environment:test` for test institution indexing; omission defaults to production indexing. Staff indexing is independent of this selector.
3. Inspect each ordered result's mapped fields and score. Unmapped/error entries can coexist with mapped entries in an HTTP 200 response.

Search requests ask for three text/fuzzy matches. Type-specific prompts ask the model to choose a candidate or return no reliable match. Mapping does not use a vector/embedding pipeline or select a Bedrock model itself.

## Interpreting outcomes

A selected candidate returns model confidence. If validation fails, the implementation can fall back to the first search hit with fixed score 90. That value is not proof of strong evidence or successful LLM validation. Null mapped fields and score 0 can mean no hits, a model rejection, or a caught error; the response does not distinguish these causes.

The prompts describe rejecting low-confidence matches, but code does not independently enforce their threshold. Applications that need a verified acceptance policy must account for the actual [API semantics](API_GUIDE.md#selection-and-scores), rather than inferring such a policy from score alone.

## Operations and continuing work

The service is an API without a dedicated UI, local catalog database, or catalog-write endpoint. Nonempty batches send data to configured search/model services and create logs. An empty batch provides a local route check without those external calls; there is no health route.

Use the [README](../README.md) for setup/architecture, [design](HIGH_LEVEL_DESIGN.md) for implementation flow, and [agent guide](../AGENTS.md) for continuation rules. Preserve service-main's Dockerfile, Lambda dependency, and logging differences during the [branch workflow](BRANCH_DIFFERENCES.md).
