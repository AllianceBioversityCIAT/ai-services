"""Chunking, embedding, and retrieval for a PRMS combined corpus."""

from __future__ import annotations

import lancedb
from typing import Any
from datetime import datetime
from dataclasses import dataclass
from app.text_mining.shared.retrieval import split_text
from app.utils.logger.logger_util import get_logger
from app.text_mining.prms_mining.prompt_builder import build_corpus_text, format_source_block
from app.text_mining.shared.vectorize import DB_PATH, TEMP_TABLE_NAME, get_embedding, normalize_filename
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType, RETRIEVAL_QUERY, RETRIEVAL_QUERY_VERSION
from app.utils.config.config_util import PRMS_CONTEXT_TOKEN_BUDGET, PRMS_FULL_SOURCE_MAX_CHARS, PRMS_RETRIEVAL_TOP_K_PER_SOURCE


logger = get_logger()


@dataclass(frozen=True)
class ContextBuildResult:
    excerpts: str
    retrieval_version: str
    chunks_processed: int
    estimated_tokens: int
    trimmed: bool


def estimate_tokens(text: str) -> int:
    """Conservative approximation used to keep prompts under budget."""
    if not text:
        return 0
    return (len(text) + 2) // 3


def _truncate_block(block: str, max_chars: int) -> str:
    if len(block) <= max_chars:
        return block
    if max_chars <= 120:
        return block[:max_chars]
    marker = "\n\n[TRUNCATED_TO_FIT_PRMS_CONTEXT_BUDGET]"
    return f"{block[: max_chars - len(marker)]}{marker}"


def fit_blocks_to_token_budget(blocks: list[str], token_budget: int) -> tuple[list[str], bool]:
    """Trim context blocks proportionally when the prompt context budget is exceeded."""
    if not blocks:
        return [], False

    separator_chars = len("\n\n---\n\n") * max(0, len(blocks) - 1)
    max_chars = max(0, token_budget * 3 - separator_chars)
    total_chars = sum(len(block) for block in blocks)
    if total_chars <= max_chars:
        return blocks, False

    ratio = max_chars / total_chars
    trimmed_blocks: list[str] = []
    used_chars = 0
    for block in blocks:
        remaining_blocks = len(blocks) - len(trimmed_blocks) - 1
        remaining_chars = max_chars - used_chars
        if remaining_chars <= 0:
            break

        proportional_chars = max(1, int(len(block) * ratio))
        # Leave at least one character for every remaining block.
        allowed_chars = min(proportional_chars, remaining_chars - remaining_blocks)
        if allowed_chars <= 0:
            break

        trimmed = _truncate_block(block, allowed_chars)
        trimmed_blocks.append(trimmed)
        used_chars += len(trimmed)

    logger.warning(
        "PRMS context trimmed from ~%s to ~%s tokens (budget=%s)",
        estimate_tokens("\n\n---\n\n".join(blocks)),
        estimate_tokens("\n\n---\n\n".join(trimmed_blocks)),
        token_budget,
    )
    return trimmed_blocks, True


def chunk_extracted_sources(
    sources: list[ExtractedPrmsSource],
) -> list[dict[str, Any]]:
    """Chunk each source independently; never merge content across sources."""
    rows: list[dict[str, Any]] = []

    for source in sources:
        if len(source.segments) > 1:
            # Pre-segmented content (e.g. Excel rows) — reuse shared excel chunk path
            source_chunks = split_text({"type": "excel", "chunks": source.segments})
        elif source.content:
            source_chunks = split_text(source.content)
        else:
            source_chunks = []

        for chunk_index, chunk in enumerate(source_chunks):
            if not chunk or not str(chunk).strip():
                continue
            prefixed = (
                f"[source_id={source.source_id} type={source.source_type.value} "
                f"chunk={chunk_index} formal_evidence={source.eligible_as_formal_evidence}]\n"
                f"{chunk}"
            )
            rows.append(
                {
                    "text": prefixed,
                    "plain_text": chunk,
                    "source_id": source.source_id,
                    "source_index": source.source_index,
                    "chunk_index": chunk_index,
                    "source_type": source.source_type.value,
                }
            )
    return rows


def store_and_retrieve_chunks(
    chunk_rows: list[dict[str, Any]],
    request_id: str,
    *,
    top_k: int = PRMS_RETRIEVAL_TOP_K_PER_SOURCE,
) -> tuple[list[str], str]:
    """
    Embed chunks into one temporary LanceDB table for the request,
    retrieve with the versioned PRMS query, then delete request rows.
    """
    if not chunk_rows:
        return [], RETRIEVAL_QUERY_VERSION

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    document_name = f"prms_{normalize_filename(request_id)}_{timestamp}"

    texts = [row["text"] for row in chunk_rows]
    logger.info("#️⃣ Generating embeddings for %s PRMS chunk(s)...", len(texts))
    embeddings = [get_embedding(text) for text in texts]

    db = lancedb.connect(DB_PATH)
    # Keep LanceDB columns aligned with the shared temp_documents schema used by STAR.
    data = [
        {
            "text": row["text"],
            "vector": embedding,
            "is_reference": False,
            "document_name": document_name,
        }
        for row, embedding in zip(chunk_rows, embeddings)
    ]

    try:
        if TEMP_TABLE_NAME not in db.table_names():
            table = db.create_table(TEMP_TABLE_NAME, data=data)
        else:
            table = db.open_table(TEMP_TABLE_NAME)
            table.add(data)

        query_embedding = get_embedding(RETRIEVAL_QUERY)
        result = (
            table.search(query_embedding)
            .where(f'document_name == "{document_name}"')
            .limit(top_k)
            .to_pandas()
        )
        retrieved = result["text"].tolist() if not result.empty else texts[:top_k]
    finally:
        try:
            table = db.open_table(TEMP_TABLE_NAME)
            table.delete(f'document_name == "{document_name}"')
        except Exception as cleanup_exc:
            logger.warning("⚠️ PRMS LanceDB cleanup failed: %s", cleanup_exc)

    return retrieved, RETRIEVAL_QUERY_VERSION


def _should_include_full_source(source: ExtractedPrmsSource) -> bool:
    if source.source_type in {PrmsSourceType.FREE_TEXT, PrmsSourceType.AUDIO}:
        return True
    return len(source.content or "") <= PRMS_FULL_SOURCE_MAX_CHARS


def build_context_excerpts(
    sources: list[ExtractedPrmsSource],
    request_id: str,
    *,
    token_budget: int = PRMS_CONTEXT_TOKEN_BUDGET,
    top_k_per_source: int = PRMS_RETRIEVAL_TOP_K_PER_SOURCE,
) -> ContextBuildResult:
    """
    Build PRMS prompt context with guaranteed direct evidence for small/user sources.

    Free text, audio transcripts, and small documents are passed through in full.
    Large documents use per-source retrieval so one long document cannot dominate.
    """
    blocks: list[str] = []
    chunks_processed = 0
    retrieval_version = RETRIEVAL_QUERY_VERSION

    for source in sorted(sources, key=lambda item: item.source_index):
        if _should_include_full_source(source):
            blocks.append(format_source_block(source))
            continue

        source_chunks = chunk_extracted_sources([source])
        chunks_processed += len(source_chunks)
        if not source_chunks:
            continue
        retrieved, retrieval_version = store_and_retrieve_chunks(
            source_chunks,
            request_id=f"{request_id}_{source.source_id}",
            top_k=top_k_per_source,
        )
        blocks.extend(retrieved)

    blocks, trimmed = fit_blocks_to_token_budget(blocks, token_budget)
    excerpts = "\n\n---\n\n".join(blocks)
    return ContextBuildResult(
        excerpts=excerpts,
        retrieval_version=retrieval_version,
        chunks_processed=chunks_processed,
        estimated_tokens=estimate_tokens(excerpts),
        trimmed=trimmed,
    )


def build_excerpts_from_sources(sources: list[ExtractedPrmsSource]) -> str:
    """Build a corpus text from the extracted sources."""
    return build_corpus_text(sources)
