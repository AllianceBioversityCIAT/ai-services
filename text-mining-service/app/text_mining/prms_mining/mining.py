"""PRMS multisource mining orchestration."""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Union
from app.text_mining.shared.models import ModelUsage
from app.utils.logger.logger_util import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.text_mining.providers import DEFAULT_MODEL_ID, invoke_model
from app.text_mining.shared.reference_cache import get_reference_data
from app.text_mining.shared.map_fields import map_fields_with_opensearch
from app.utils.interactions.interaction_client import interaction_client
from app.text_mining.shared.cgiar_centers import format_cgiar_centers_for_prompt
from app.text_mining.shared.organization_fields import clean_prms_institution_fields
from app.text_mining.prms_mining.corpus import (
    ContextBuildResult,
    build_single_source_excerpts,
    estimate_tokens,
)
from app.text_mining.shared.json_parser import extract_json_object, is_valid_json
from app.utils.config.config_util import (
    MAPPING_URL,
    PRMS_BUCKET_KEY_NAME,
    PRMS_CONTEXT_TOKEN_BUDGET,
    PRMS_EXTRACTION_MAX_WORKERS,
)

from app.text_mining.prms_mining.models import (
    EmptySourceSetError,
    ExtractedPrmsSource,
    ModelOutputValidationError,
    PrmsSourceType,
    SourceLimitExceededError,
    SourceCounts,
    StageDurations,
    SUPPORTED_INDICATORS,
)
from app.text_mining.prms_mining.prompt_builder import (
    build_extraction_prompt,
    build_final_validation_prompt,
    format_prms_geo_reference_for_prompt,
)
from app.text_mining.prms_mining.source_extraction import (
    build_sources_from_request,
    extract_sources,
)

from app.schemas.prms_mining_schemas import (
    MiningResponse,
    InnovationDevelopmentResult,
    PolicyChangeResult,
    CapacitySharingResult,
    InnovationUseResult,
    OtherOutputResult,
    OtherOutcomeResult,
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
    raw = text or ""
    extracted = extract_json_object(raw)
    if extracted != raw.strip() and not is_valid_json(raw.strip()):
        logger.warning(
            "⚠️ PRMS stripped non-JSON wrapper from model response before parsing "
            "(chars_before=%s chars_after=%s)",
            len(raw),
            len(extracted),
        )
    if not is_valid_json(extracted):
        raise ModelOutputValidationError("Model returned invalid JSON")
    parsed = json.loads(extracted)
    if not isinstance(parsed, dict):
        raise ModelOutputValidationError("Model JSON must be an object")
    if "results" not in parsed or not isinstance(parsed.get("results"), list):
        raise ModelOutputValidationError("Model JSON must contain a results array")
    return parsed


def _build_validation_repair_prompt(raw_response: str) -> str:
    return f"""Convert the text below into one valid JSON object with exactly this shape:
{{
  "results": [ ... ]
}}

Rules:
    • Use only result objects already present in the text — do not invent fields or results.
    • Return raw JSON only — no prose, markdown fences, or commentary.
    • The response must start with {{ and end with }}.

TEXT TO CONVERT:
{"=" * 80}
{raw_response}
"""


def _run_final_validation(candidates: dict) -> tuple[dict, ModelUsage, str]:
    """Run final validation with JSON-only constraints and one repair retry."""
    validation_prompt = build_final_validation_prompt(candidates=candidates)
    validation_result = invoke_model(
        validation_prompt,
        temperature=0,
    )

    try:
        payload = _parse_model_json(validation_result.text)
        if not validation_result.text.lstrip().startswith("{"):
            logger.info("🔍 PRMS final validation JSON recovered via parser/extraction")
        return payload, validation_result.usage, validation_result.text
    except ModelOutputValidationError as first_error:
        logger.warning(
            "⚠️ PRMS final validation returned non-strict JSON (%s); retrying repair pass",
            first_error,
        )

    repair_result = invoke_model(
        _build_validation_repair_prompt(validation_result.text),
        temperature=0,
    )
    payload = _parse_model_json(repair_result.text)
    merged_usage = ModelUsage(
        input_tokens=validation_result.usage.input_tokens + repair_result.usage.input_tokens,
        output_tokens=validation_result.usage.output_tokens + repair_result.usage.output_tokens,
    )
    logger.info("🔧 PRMS final validation JSON repair pass succeeded")
    return payload, merged_usage, repair_result.text


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


def _merge_model_usage(usages: list[ModelUsage]) -> ModelUsage:
    return ModelUsage(
        input_tokens=sum(item.input_tokens for item in usages),
        output_tokens=sum(item.output_tokens for item in usages),
    )


def _source_label(source: ExtractedPrmsSource) -> str:
    if source.source_type == PrmsSourceType.FREE_TEXT:
        return "free_text"
    return source.file_name or source.source_id


def _indicator_summary(results: list[dict]) -> str:
    counts: dict[str, int] = {}
    for result in results:
        indicator = (result or {}).get("indicator") or "unknown"
        counts[indicator] = counts.get(indicator, 0) + 1
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


def _context_mode_label(source: ExtractedPrmsSource, context_result: ContextBuildResult) -> str:
    if context_result.chunks_processed > 0:
        return "retrieval"
    if source.source_type in {PrmsSourceType.FREE_TEXT, PrmsSourceType.AUDIO}:
        return "full_transcript"
    return "full_document"


def _extract_results_from_source(
    source: ExtractedPrmsSource,
    *,
    reference_for_prompt: str,
    request_id: str,
    context_budget: int,
) -> tuple[list[dict], ModelUsage, ContextBuildResult]:
    """Run one extraction model call for a single source."""
    label = _source_label(source)
    logger.info(
        "📎 PRMS building context source=%s label=%s type=%s chars=%s budget_tokens=%s",
        source.source_id,
        label,
        source.source_type.value,
        source.character_count,
        context_budget,
    )

    context_result = build_single_source_excerpts(
        source,
        request_id=request_id,
        token_budget=context_budget,
    )
    context_mode = _context_mode_label(source, context_result)
    logger.info(
        "📄 PRMS context ready source=%s mode=%s excerpt_tokens~=%s chunks=%s trimmed=%s",
        source.source_id,
        context_mode,
        context_result.estimated_tokens,
        context_result.chunks_processed,
        context_result.trimmed,
    )

    extraction_prompt = build_extraction_prompt(
        excerpts=context_result.excerpts,
        reference_section=reference_for_prompt,
    )
    prompt_estimated_tokens = estimate_tokens(extraction_prompt)
    if prompt_estimated_tokens > PRMS_CONTEXT_TOKEN_BUDGET:
        logger.error(
            "❌ PRMS source exceeds token budget source=%s label=%s prompt_tokens~=%s limit=%s",
            source.source_id,
            label,
            prompt_estimated_tokens,
            PRMS_CONTEXT_TOKEN_BUDGET,
        )
        raise SourceLimitExceededError(
            f"Source '{label}' is too large to process in one request, "
            "even after selecting the most relevant excerpts. Please reduce the document "
            "size or split it into smaller files."
        )

    logger.info(
        "🤖 PRMS invoking extraction model source=%s label=%s prompt_tokens~=%s model=%s",
        source.source_id,
        label,
        prompt_estimated_tokens,
        DEFAULT_MODEL_ID,
    )
    model_start = time.time()
    extraction_result = invoke_model(extraction_prompt)
    model_duration = time.time() - model_start

    payload = _preliminary_discriminator_check(_parse_model_json(extraction_result.text))
    results = payload.get("results") or []
    logger.info(
        "✅ PRMS per-source extraction complete source=%s label=%s duration=%.2fs "
        "results=%s indicators=[%s] tokens=%s/%s trimmed=%s",
        source.source_id,
        label,
        model_duration,
        len(results),
        _indicator_summary(results),
        extraction_result.usage.input_tokens,
        extraction_result.usage.output_tokens,
        context_result.trimmed,
    )
    return results, extraction_result.usage, context_result


def _parallel_per_source_extraction(
    sources: list[ExtractedPrmsSource],
    *,
    reference_for_prompt: str,
    request_id: str,
    context_budget: int,
    max_workers: int,
) -> tuple[list[dict], ModelUsage, list[ContextBuildResult], int]:
    """Extract PRMS candidates from each source in parallel."""
    if not sources:
        return [], ModelUsage(), [], 0

    ordered_sources = sorted(sources, key=lambda item: item.source_index)

    if len(ordered_sources) == 1:
        logger.info(
            "🤖 PRMS starting single-source model extraction source=%s",
            ordered_sources[0].source_id,
        )
        results, usage, context_result = _extract_results_from_source(
            ordered_sources[0],
            reference_for_prompt=reference_for_prompt,
            request_id=request_id,
            context_budget=context_budget,
        )
        prompt_tokens = estimate_tokens(
            build_extraction_prompt(
                excerpts=context_result.excerpts,
                reference_section=reference_for_prompt,
            )
        )
        return results, usage, [context_result], prompt_tokens

    results_by_source: dict[str, list[dict]] = {}
    usages_by_source: dict[str, ModelUsage] = {}
    context_by_source: dict[str, ContextBuildResult] = {}
    prompt_tokens_by_source: dict[str, int] = {}
    worker_count = max(1, min(max_workers, len(ordered_sources)))
    logger.info(
        "🤖 PRMS starting parallel model extraction sources=%s workers=%s request_id=%s",
        len(ordered_sources),
        worker_count,
        request_id,
    )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_source = {
            executor.submit(
                _extract_results_from_source,
                source,
                reference_for_prompt=reference_for_prompt,
                request_id=request_id,
                context_budget=context_budget,
            ): source
            for source in ordered_sources
        }
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            results, usage, context_result = future.result()
            results_by_source[source.source_id] = results
            usages_by_source[source.source_id] = usage
            context_by_source[source.source_id] = context_result
            prompt_tokens_by_source[source.source_id] = estimate_tokens(
                build_extraction_prompt(
                    excerpts=context_result.excerpts,
                    reference_section=reference_for_prompt,
                )
            )
            logger.info(
                "🔀 PRMS parallel worker finished source=%s label=%s results=%s",
                source.source_id,
                _source_label(source),
                len(results),
            )

    merged_results: list[dict] = []
    usages: list[ModelUsage] = []
    context_results: list[ContextBuildResult] = []
    max_prompt_tokens = 0
    for source in ordered_sources:
        merged_results.extend(results_by_source.get(source.source_id, []))
        if usage := usages_by_source.get(source.source_id):
            usages.append(usage)
        if context_result := context_by_source.get(source.source_id):
            context_results.append(context_result)
        max_prompt_tokens = max(
            max_prompt_tokens,
            prompt_tokens_by_source.get(source.source_id, 0),
        )

    merged_usage = _merge_model_usage(usages)
    logger.info(
        "🔀 PRMS merged per-source candidates sources=%s total_results=%s indicators=[%s] "
        "extraction_tokens=%s/%s max_prompt_tokens~=%s",
        len(ordered_sources),
        len(merged_results),
        _indicator_summary(merged_results),
        merged_usage.input_tokens,
        merged_usage.output_tokens,
        max_prompt_tokens,
    )

    return merged_results, merged_usage, context_results, max_prompt_tokens


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


def format_mining_response(raw_response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format the mining response to ensure consistent structure with indicator-specific fields
    Accepts either raw JSON string or already parsed dict (after field mapping)
    """
    try:
        # If already a dict, use it directly (post field mapping)
        if isinstance(raw_response, dict):
            parsed_response = raw_response
        elif is_valid_json(raw_response):
            parsed_response = json.loads(raw_response)
        else:
            logger.warning(f"Invalid JSON received from LLM: {raw_response[:200]}...")
            return {
                "content": raw_response,
                "status": "partial_success", 
                "error": "LLM returned invalid JSON"
            }

        results = parsed_response.get("results", [])
        if not isinstance(results, list):
            results = []
        
        typed_results = []
        for result in results:
            indicator = result.get("indicator", "")
            
            try:
                if indicator == "Capacity Sharing for Development":
                    typed_results.append(CapacitySharingResult(**result))
                    
                elif indicator == "Policy Change":
                    policy_result = PolicyChangeResult(**result)
                    typed_results.append(policy_result)
                    
                elif indicator == "Innovation Development":
                    innovation_result = InnovationDevelopmentResult(**result)
                    typed_results.append(innovation_result)

                elif indicator == "Innovation Use":
                    typed_results.append(InnovationUseResult(**result))

                elif indicator == "Other Output":
                    typed_results.append(OtherOutputResult(**result))

                elif indicator == "Other Outcome":
                    typed_results.append(OtherOutcomeResult(**result))
                    
                else:
                    logger.warning(f"❌ Unknown indicator type: {indicator}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing result with indicator '{indicator}': {str(e)}")
                continue
        
        total_count = len(results)
        valid_count = len(typed_results)
        failed_count = total_count - valid_count
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} of {total_count} results failed validation and will NOT be returned to PRMS")
        
        if valid_count > 0:
            logger.info(f"✅ {valid_count} of {total_count} results validated successfully")
        elif total_count > 0:
            logger.error(f"❌ All {total_count} results failed validation - returning empty results")
        
        mining_response = MiningResponse(
            results=typed_results
        )
        
        return mining_response.model_dump(exclude_none=True)
        
    except Exception as e:
        logger.error(f"❌ Critical error formatting mining response: {str(e)}")
        
        return {
            "results": [],
            "status": "error",
            "error": f"Critical formatting error: {str(e)}"
        }


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
    parallel source text extraction → parallel per-source model extraction →
    final validation → mapping.
    """
    start_time = time.time()
    stages = StageDurations()
    processing_steps: list[str] = []
    extraction_usage = ModelUsage()
    validation_usage = ModelUsage()
    response_text = ""
    request_id = uuid.uuid4().hex[:12]

    logger.info(
        "🚀 PRMS mining started request_id=%s bucket=%s docs=%s audio=%s free_text=%s",
        request_id,
        bucket_name or "(none)",
        len(keys or []),
        len(audio_keys or []),
        1 if (text or "").strip() else 0,
    )

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
    logger.info(
        "📋 PRMS source descriptors ready count=%s types=%s",
        len(sources),
        ", ".join(sorted({item.source_type.value for item in sources})),
    )

    try:
        logger.info(
            "📥 PRMS extracting source text request_id=%s sources=%s max_workers=%s",
            request_id,
            len(sources),
            PRMS_EXTRACTION_MAX_WORKERS,
        )
        extraction_start = time.time()
        extracted = extract_sources(sources, max_workers=PRMS_EXTRACTION_MAX_WORKERS)
        stages.source_extraction = time.time() - extraction_start
        stages.slowest_source_extraction = max(
            (item.extraction_seconds for item in extracted), default=0.0
        )
        processing_steps.append("source_extraction")
        counts = _source_counts(extracted)
        logger.info(
            "📥 PRMS source text extraction complete duration=%.2fs slowest_source=%.2fs "
            "documents=%s audio=%s free_text=%s chars=%s",
            stages.source_extraction,
            stages.slowest_source_extraction,
            counts.document,
            counts.audio,
            counts.free_text,
            sum(item.character_count for item in extracted),
        )
        for item in extracted:
            logger.info(
                "📄 PRMS source ready id=%s label=%s type=%s chars=%s pages=%s duration=%.2fs",
                item.source_id,
                _source_label(item),
                item.source_type.value,
                item.character_count,
                item.page_count,
                item.extraction_seconds,
            )

        # Reference catalogs require a bucket; use request bucket or fail soft for text-only.
        reference_section = ""
        if bucket_name and PRMS_BUCKET_KEY_NAME:
            reference_file_regions = f"{PRMS_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
            reference_file_countries = f"{PRMS_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
            logger.info(
                "🌍 PRMS loading geo reference catalogs bucket=%s prefix=%s",
                bucket_name,
                PRMS_BUCKET_KEY_NAME,
            )
            try:
                reference_data = get_reference_data(
                    bucket_name,
                    PRMS_BUCKET_KEY_NAME,
                    reference_file_regions,
                    reference_file_countries,
                )
                reference_section = format_prms_geo_reference_for_prompt(reference_data)
                processing_steps.append("reference_catalogs")
                logger.info(
                    "🌍 PRMS geo reference catalogs loaded regions=%s countries=%s",
                    len(reference_data.get("regions") or []),
                    len(reference_data.get("countries") or []),
                )
            except Exception as ref_exc:
                logger.warning("⚠️ PRMS reference catalog load failed: %s", ref_exc)
        else:
            logger.info("🌍 PRMS geo reference catalogs skipped (text-only or missing bucket)")

        context_start = time.time()
        reference_parts = [reference_section] if reference_section else []
        reference_parts.append(format_cgiar_centers_for_prompt())
        reference_for_prompt = "\n\n".join(part for part in reference_parts if part)
        prompt_overhead = estimate_tokens(
            build_extraction_prompt(excerpts="", reference_section=reference_for_prompt)
        )
        context_budget = max(1, PRMS_CONTEXT_TOKEN_BUDGET - prompt_overhead)
        processing_steps.append("context_budgeting")
        logger.info(
            "🧮 PRMS prompt budget ready overhead_tokens~=%s context_budget=%s total_budget=%s",
            prompt_overhead,
            context_budget,
            PRMS_CONTEXT_TOKEN_BUDGET,
        )

        model_start = time.time()
        merged_results, extraction_usage, context_results, prompt_estimated_tokens = (
            _parallel_per_source_extraction(
                extracted,
                reference_for_prompt=reference_for_prompt,
                request_id=request_id,
                context_budget=context_budget,
                max_workers=PRMS_EXTRACTION_MAX_WORKERS,
            )
        )
        stages.model_extraction = time.time() - model_start
        stages.chunking = time.time() - context_start
        stages.embedding = stages.chunking
        stages.retrieval = stages.embedding
        processing_steps.append("per_source_model_extraction")

        chunks_processed = sum(item.chunks_processed for item in context_results)
        context_estimated_tokens = sum(item.estimated_tokens for item in context_results)
        context_trimmed = any(item.trimmed for item in context_results)
        logger.info(
            "🤖 PRMS model extraction stage complete duration=%.2fs sources=%s "
            "merged_candidates=%s context_tokens~=%s chunks=%s trimmed=%s",
            stages.model_extraction,
            len(extracted),
            len(merged_results),
            context_estimated_tokens,
            chunks_processed,
            context_trimmed,
        )

        json_content = {"results": merged_results}
        pre_validation_count = len(merged_results)

        logger.info(
            "🔍 PRMS starting final validation candidates=%s indicators=[%s] model=%s json_mode=strict",
            pre_validation_count,
            _indicator_summary(merged_results),
            DEFAULT_MODEL_ID,
        )
        val_start = time.time()
        json_content, validation_usage, response_text = _run_final_validation(json_content)
        stages.final_validation = time.time() - val_start
        post_validation_count = len(json_content.get("results") or [])
        processing_steps.append("final_validation")
        logger.info(
            "🔍 PRMS final validation complete duration=%.2fs candidates=%s→%s "
            "tokens=%s/%s indicators=[%s]",
            stages.final_validation,
            pre_validation_count,
            post_validation_count,
            validation_usage.input_tokens,
            validation_usage.output_tokens,
            _indicator_summary(json_content.get("results") or []),
        )

        map_start = time.time()
        logger.info(
            "🗺️ PRMS starting field mapping results=%s mapping_url=%s",
            post_validation_count,
            "configured" if MAPPING_URL else "missing",
        )
        if isinstance(json_content, dict) and "results" in json_content:
            mapped_results = []
            for result in json_content["results"]:
                try:
                    mapped_result = map_fields_with_opensearch(result, MAPPING_URL)
                    clean_prms_institution_fields(mapped_result)
                    mapped_results.append(mapped_result)
                except Exception as map_error:
                    logger.warning("⚠️ Field mapping failed for result: %s", str(map_error))
                    mapped_results.append(result)
            json_content["results"] = mapped_results
        stages.field_mapping = time.time() - map_start
        processing_steps.append("field_mapping")
        logger.info(
            "🗺️ PRMS field mapping complete duration=%.2fs mapped_results=%s",
            stages.field_mapping,
            len(json_content.get("results") or []),
        )

        logger.info("📐 PRMS validating response against MDS schemas")
        formatted_response = format_mining_response(json_content)
        results_count = len(formatted_response.get("results") or [])
        processing_steps.append("schema_validation")

        elapsed_time = time.time() - start_time
        stages.total = elapsed_time

        interaction_id = None
        if user_id:
            try:
                tracking_context = {
                    "source_counts": counts.model_dump(),
                    "extraction_mode": "per_source_parallel",
                    "sources_processed": len(extracted),
                    "chunks_processed": chunks_processed,
                    "context_estimated_tokens": context_estimated_tokens,
                    "prompt_estimated_tokens": prompt_estimated_tokens,
                    "context_trimmed": context_trimmed,
                    "results_count": results_count,
                    "supported_indicators": SUPPORTED_INDICATORS,
                    "model_used": DEFAULT_MODEL_ID,
                    "extraction_input_tokens": extraction_usage.input_tokens,
                    "extraction_output_tokens": extraction_usage.output_tokens,
                    "validation_input_tokens": validation_usage.input_tokens,
                    "validation_output_tokens": validation_usage.output_tokens,
                    "stage_durations_seconds": stages.model_dump(),
                    "processing_steps": processing_steps,
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
            "✅ PRMS mining complete request_id=%s results_count=%s sources=%s duration=%.2fs "
            "extraction_tokens=%s/%s validation_tokens=%s/%s max_prompt_tokens~=%s "
            "context_trimmed=%s stages=%s",
            request_id,
            results_count,
            counts.model_dump(),
            elapsed_time,
            extraction_usage.input_tokens,
            extraction_usage.output_tokens,
            validation_usage.input_tokens,
            validation_usage.output_tokens,
            prompt_estimated_tokens,
            context_trimmed,
            stages.model_dump(),
        )

        result = {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": formatted_response,
            "project": "PRMS",
            "source_counts": counts.model_dump(),
            "extraction_mode": "per_source_parallel",
            "sources_processed": len(extracted),
            "context_estimated_tokens": context_estimated_tokens,
            "prompt_estimated_tokens": prompt_estimated_tokens,
            "context_trimmed": context_trimmed,
            "stage_durations_seconds": stages.model_dump(),
            "failure_stage": None,
        }
        if interaction_id:
            result["interaction_id"] = interaction_id
        return result

    except Exception as exc:
        stages.total = time.time() - start_time
        logger.error(
            "❌ PRMS mining failed request_id=%s duration=%.2fs error=%s",
            request_id,
            stages.total,
            exc,
        )
        raise
