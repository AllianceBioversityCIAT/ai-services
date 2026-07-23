"""PRMS multisource mining orchestration."""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Union
from app.llm.shared.models import ModelUsage
from app.utils.logger.logger_util import get_logger
from app.llm.providers import DEFAULT_MODEL_ID, invoke_model
from app.llm.shared.reference_cache import get_reference_data
from app.llm.shared.map_fields import map_fields_with_opensearch
from app.utils.interactions.interaction_client import interaction_client
from app.llm.shared.cgiar_centers import format_cgiar_centers_for_prompt
from app.llm.shared.organization_fields import clean_prms_institution_fields
from app.llm.prms_mining.corpus import build_context_excerpts, estimate_tokens
from app.llm.shared.json_parser import extract_json_from_markdown, is_valid_json
from app.utils.config.config_util import (
    MAPPING_URL,
    PRMS_BUCKET_KEY_NAME,
    PRMS_CONTEXT_TOKEN_BUDGET,
    PRMS_EXTRACTION_MAX_WORKERS,
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
    format_prms_geo_reference_for_prompt,
)
from app.llm.prms_mining.source_extraction import (
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
                reference_section = format_prms_geo_reference_for_prompt(reference_data)
                processing_steps.append("reference_catalogs")
            except Exception as ref_exc:
                logger.warning("⚠️ PRMS reference catalog load failed: %s", ref_exc)

        context_start = time.time()
        reference_parts = [reference_section] if reference_section else []
        reference_parts.append(format_cgiar_centers_for_prompt())
        reference_for_prompt = "\n\n".join(part for part in reference_parts if part)
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

        validation_prompt = build_final_validation_prompt(
            candidates=json_content,
        )
        val_start = time.time()
        validation_result = invoke_model(validation_prompt)
        stages.final_validation = time.time() - val_start
        validation_usage = validation_result.usage
        response_text = validation_result.text
        json_content = _parse_model_json(response_text)
        processing_steps.append("final_validation")

        map_start = time.time()
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
                    "chunks_processed": context_result.chunks_processed,
                    "context_estimated_tokens": context_result.estimated_tokens,
                    "prompt_estimated_tokens": prompt_estimated_tokens,
                    "context_trimmed": context_result.trimmed,
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
            "✅ PRMS mining complete results_count=%s sources=%s duration=%.2fs "
            "extraction_tokens=%s/%s validation_tokens=%s/%s estimated_prompt_tokens=%s "
            "context_trimmed=%s",
            results_count,
            counts.model_dump(),
            elapsed_time,
            extraction_usage.input_tokens,
            extraction_usage.output_tokens,
            validation_usage.input_tokens,
            validation_usage.output_tokens,
            prompt_estimated_tokens,
            context_result.trimmed,
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
