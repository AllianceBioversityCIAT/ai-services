"""PRMS multisource mining orchestration."""

from __future__ import annotations

import json
import time
import uuid
from app.llm.shared.models import ModelUsage
from app.utils.logger.logger_util import get_logger
from app.llm.providers import DEFAULT_MODEL_ID, invoke_model
from app.llm.shared.map_fields import map_fields_with_opensearch
from app.utils.interactions.interaction_client import interaction_client
from app.llm.shared.json_parser import extract_json_from_markdown, is_valid_json
from app.llm.star_mining.mining import _clean_organization_fields, format_mining_response
from app.llm.prms_mining.corpus import build_context_excerpts, estimate_tokens
from app.llm.shared.reference_cache import format_reference_for_prompt, get_reference_data
from app.utils.prompt.prompt_prms import EXTRACTION_PROMPT_VERSION, VALIDATION_PROMPT_VERSION
from app.utils.config.config_util import (
    MAPPING_URL,
    PRMS_BUCKET_KEY_NAME,
    PRMS_CONTEXT_TOKEN_BUDGET,
    PRMS_EXTRACTION_MAX_WORKERS,
    PRMS_FINAL_VALIDATION_ENABLED,
)

from app.llm.prms_mining.models import (
    EmptySourceSetError,
    ExtractedPrmsSource,
    ModelOutputValidationError,
    PrmsSourceType,
    SourceLimitExceededError,
    SourceCounts,
    StageDurations,
    SUPPORTED_INDICATORS,
)
from app.llm.prms_mining.prompt_builder import (
    build_extraction_prompt,
    build_final_validation_prompt,
    prompt_versions,
)
from app.llm.prms_mining.source_extraction import (
    build_sources_from_request,
    extract_sources,
)


logger = get_logger()


def _source_counts(extracted: list[ExtractedPrmsSource]) -> SourceCounts:
    counts = SourceCounts()
    for item in extracted:
        if item.source_type == PrmsSourceType.DOCUMENT:
            counts.document += 1
        elif item.source_type == PrmsSourceType.AUDIO:
            counts.audio += 1
        elif item.source_type == PrmsSourceType.FREE_TEXT:
            counts.free_text += 1
    return counts


def _parse_model_json(text: str) -> dict:
    extracted = extract_json_from_markdown(text)
    if not is_valid_json(extracted):
        raise ModelOutputValidationError("Model returned invalid JSON")
    parsed = json.loads(extracted)
    if not isinstance(parsed, dict):
        raise ModelOutputValidationError("Model JSON must be an object")
    if "results" not in parsed or not isinstance(parsed.get("results"), list):
        raise ModelOutputValidationError("Model JSON must contain a results array")
    return parsed


def _preliminary_discriminator_check(payload: dict) -> dict:
    """Keep only candidates with known indicator discriminators before final validation."""
    kept = []
    for index, result in enumerate(payload.get("results") or []):
        indicator = (result or {}).get("indicator")
        if indicator in SUPPORTED_INDICATORS:
            kept.append(result)
        else:
            logger.warning(
                "Dropping candidate index=%s with unsupported/unknown indicator=%s",
                index,
                indicator,
            )
    return {"results": kept}


def _summarize_user_input(extracted: list[ExtractedPrmsSource], counts: SourceCounts) -> str:
    names = []
    for item in extracted:
        if item.source_type == PrmsSourceType.FREE_TEXT:
            names.append("free_text")
        else:
            names.append(item.file_name or item.source_id)
    return (
        f"PRMS multisource mining: documents={counts.document}, "
        f"audio={counts.audio}, free_text={counts.free_text}; "
        f"sources={', '.join(names)}"
    )


def process_document_prms(
    *,
    bucket_name: str | None = None,
    keys: list[str] | None = None,
    text: str | None = None,
    audio_keys: list[str] | None = None,
    user_id: str | None = None,
) -> dict:
    """
    Multisource PRMS pipeline:
    parallel source extraction → one extraction model call → optional final validation → mapping.
    """
    start_time = time.time()
    stages = StageDurations()
    processing_steps: list[str] = []
    extraction_usage = ModelUsage()
    validation_usage = ModelUsage()
    response_text = ""
    request_id = uuid.uuid4().hex[:12]

    sources = build_sources_from_request(
        bucket=bucket_name,
        keys=keys,
        audio_keys=audio_keys,
        text=text,
    )
    if not sources:
        raise EmptySourceSetError(
            "Please provide at least one source to process: a document, an audio file, or free text."
        )

    processing_steps.append("source_descriptors")

    try:
        extraction_start = time.time()
        extracted = extract_sources(sources, max_workers=PRMS_EXTRACTION_MAX_WORKERS)
        stages.source_extraction = time.time() - extraction_start
        stages.slowest_source_extraction = max(
            (item.extraction_seconds for item in extracted), default=0.0
        )
        processing_steps.append("source_extraction")
        counts = _source_counts(extracted)

        # Reference catalogs require a bucket; use request bucket or fail soft for text-only.
        reference_section = ""
        if bucket_name and PRMS_BUCKET_KEY_NAME:
            reference_file_regions = f"{PRMS_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
            reference_file_countries = f"{PRMS_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
            try:
                reference_data = get_reference_data(
                    bucket_name,
                    PRMS_BUCKET_KEY_NAME,
                    reference_file_regions,
                    reference_file_countries,
                )
                reference_section = format_reference_for_prompt(reference_data)
                processing_steps.append("reference_catalogs")
            except Exception as ref_exc:
                logger.warning("⚠️ PRMS reference catalog load failed: %s", ref_exc)

        context_start = time.time()
        reference_for_prompt = reference_section or "REFERENCE CATALOGS: (none loaded)"
        prompt_overhead = estimate_tokens(
            build_extraction_prompt(excerpts="", reference_section=reference_for_prompt)
        )
        context_budget = max(1, PRMS_CONTEXT_TOKEN_BUDGET - prompt_overhead)
        context_result = build_context_excerpts(
            extracted,
            request_id=request_id,
            token_budget=context_budget,
        )
        stages.chunking = time.time() - context_start
        stages.embedding = stages.chunking
        stages.retrieval = stages.embedding
        processing_steps.append("context_building")

        excerpts = context_result.excerpts
        extraction_prompt = build_extraction_prompt(
            excerpts=excerpts,
            reference_section=reference_for_prompt,
        )
        prompt_estimated_tokens = estimate_tokens(extraction_prompt)
        if prompt_estimated_tokens > PRMS_CONTEXT_TOKEN_BUDGET:
            raise SourceLimitExceededError(
                "The combined source content is too large to process in one request, "
                "even after selecting the most relevant excerpts. Please reduce the "
                "number or size of the sources and try again."
            )

        model_start = time.time()
        extraction_result = invoke_model(extraction_prompt)
        stages.model_extraction = time.time() - model_start
        extraction_usage = extraction_result.usage
        response_text = extraction_result.text
        processing_steps.append("model_extraction")

        json_content = _preliminary_discriminator_check(_parse_model_json(response_text))

        if PRMS_FINAL_VALIDATION_ENABLED:
            validation_prompt = build_final_validation_prompt(
                candidates=json_content,
                supporting_excerpts=excerpts,
            )
            val_start = time.time()
            validation_result = invoke_model(validation_prompt)
            stages.final_validation = time.time() - val_start
            validation_usage = validation_result.usage
            response_text = validation_result.text
            json_content = _parse_model_json(response_text)
            processing_steps.append("final_validation")
        else:
            processing_steps.append("final_validation_skipped")

        map_start = time.time()
        if isinstance(json_content, dict) and "results" in json_content:
            mapped_results = []
            for result in json_content["results"]:
                try:
                    mapped_result = map_fields_with_opensearch(result, MAPPING_URL)
                    _clean_organization_fields(mapped_result)
                    mapped_results.append(mapped_result)
                except Exception as map_error:
                    logger.warning("⚠️ Field mapping failed for result: %s", str(map_error))
                    mapped_results.append(result)
            json_content["results"] = mapped_results
        stages.field_mapping = time.time() - map_start
        processing_steps.append("field_mapping")

        formatted_response = format_mining_response(json_content)
        results_count = len(formatted_response.get("results") or [])
        processing_steps.append("schema_validation")

        elapsed_time = time.time() - start_time
        stages.total = elapsed_time

        interaction_id = None
        if user_id:
            try:
                versions = prompt_versions()
                tracking_context = {
                    "source_counts": counts.model_dump(),
                    "chunks_processed": context_result.chunks_processed,
                    "context_estimated_tokens": context_result.estimated_tokens,
                    "prompt_estimated_tokens": prompt_estimated_tokens,
                    "context_trimmed": context_result.trimmed,
                    "results_count": results_count,
                    "supported_indicators": SUPPORTED_INDICATORS,
                    "model_used": DEFAULT_MODEL_ID,
                    "extraction_prompt_version": versions["extraction_prompt_version"],
                    "validation_prompt_version": versions["validation_prompt_version"],
                    "extraction_input_tokens": extraction_usage.input_tokens,
                    "extraction_output_tokens": extraction_usage.output_tokens,
                    "validation_input_tokens": validation_usage.input_tokens,
                    "validation_output_tokens": validation_usage.output_tokens,
                    "stage_durations_seconds": stages.model_dump(),
                    "processing_steps": processing_steps,
                    "final_validation_enabled": PRMS_FINAL_VALIDATION_ENABLED,
                }
                interaction_response = interaction_client.track_interaction(
                    user_id=user_id,
                    user_input=_summarize_user_input(extracted, counts),
                    ai_output=json.dumps(formatted_response, indent=2, ensure_ascii=False),
                    service_name="text-mining",
                    display_name="PRMS Text Mining Service",
                    service_description=(
                        "Multisource PRMS mining across documents, free text, and audio."
                    ),
                    context=tracking_context,
                    response_time_seconds=elapsed_time,
                    platform="PRMS",
                )
                if interaction_response:
                    interaction_id = interaction_response.get("interaction_id")
                    logger.info("📊 PRMS interaction tracked: %s", interaction_id)
            except Exception as tracking_error:
                logger.error("❌ PRMS interaction tracking failed: %s", tracking_error)

        logger.info(
            "✅ PRMS mining complete results_count=%s sources=%s duration=%.2fs "
            "extraction_tokens=%s/%s validation_tokens=%s/%s estimated_prompt_tokens=%s "
            "context_trimmed=%s prompt=%s validation=%s",
            results_count,
            counts.model_dump(),
            elapsed_time,
            extraction_usage.input_tokens,
            extraction_usage.output_tokens,
            validation_usage.input_tokens,
            validation_usage.output_tokens,
            prompt_estimated_tokens,
            context_result.trimmed,
            EXTRACTION_PROMPT_VERSION,
            VALIDATION_PROMPT_VERSION,
        )

        result = {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": formatted_response,
            "project": "PRMS",
            "source_counts": counts.model_dump(),
            "context_estimated_tokens": context_result.estimated_tokens,
            "prompt_estimated_tokens": prompt_estimated_tokens,
            "context_trimmed": context_result.trimmed,
            "stage_durations_seconds": stages.model_dump(),
            "failure_stage": None,
        }
        if interaction_id:
            result["interaction_id"] = interaction_id
        return result

    except Exception as exc:
        stages.total = time.time() - start_time
        logger.error("❌ PRMS Error: %s", str(exc))
        raise
