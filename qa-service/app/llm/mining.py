import time
import json
import boto3
import asyncio
import traceback
from typing import List, Optional
from pydantic import ValidationError
from app.utils.config.config_util import AWS
from app.llm.schemas import validate_output_schema
from app.utils.logger.logger_util import get_logger
from app.utils.prompt.main_prompt import build_main_prompt
from app.web_scraping.evidence_scraper import EvidenceEnhancer
from app.utils.prompt.innov_use_prompt import build_use_level_prompt
from app.utils.prompt.innov_read_prompt import build_readiness_prompt
from app.utils.prompt.impact_area_prompt import build_impact_area_prompt
from app.utils.interactions.interaction_client import interaction_client


BEDROCK_SEMAPHORE = asyncio.Semaphore(2)
SCRAPING_SEMAPHORE = asyncio.Semaphore(3)

logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)


async def invoke_model_async(prompt, max_tokens=2000, prompt_name="unknown"):
    """Async version of invoke_model for parallel execution with semaphore control and retry logic."""
    async with BEDROCK_SEMAPHORE:
        logger.info(f"🚀 Invoking Bedrock for {prompt_name}...")
        
        max_retries = 5
        base_delay = 0.5  # Start with 0.5 seconds
        
        for attempt in range(max_retries):
            try:
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                    "top_k": 250,
                    "top_p": 0.999,
                    "stop_sequences": [],
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"{prompt}"}
                            ]
                        }
                    ]
                }
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: bedrock_runtime.invoke_model(
                        modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
                        body=json.dumps(request_body),
                        contentType="application/json",
                        accept="application/json"
                    )
                )
                
                result = json.loads(response['body'].read())['content'][0]['text']
                logger.info(f"✅ Model response received for {prompt_name}")
                return result

            except Exception as e:
                error_msg = str(e)
                is_throttling = "ThrottlingException" in error_msg or "Too many tokens" in error_msg
                
                if is_throttling and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⏱️ Throttled for {prompt_name}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Error invoking the model for {prompt_name}: {error_msg}")
                    raise


def is_valid_json(text):
    """Check if the text is a valid JSON string"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


async def improve_prms_result_metadata(
        result_metadata: dict,
        user_id: str = None,
        max_evidences: int = 5
):
    """
    Process PRMS result metadata to generate an improved response using LLM.
    
    Args:
        result_metadata: PRMS result metadata dictionary
        evidence_urls: List of evidence URLs (optional)
        user_id: User ID for tracking
        max_evidences: Maximum number of evidences to process
        max_content_per_evidence: Maximum content length per evidence
    
    Returns:
        Dict with improved results and evidence metadata
    """
    
    start_time = time.time()

    try:
        result_type = result_metadata["result_type_name"].lower()
        result_level = result_metadata["result_level_name"].lower()
        result_title = result_metadata.get("result_name", "")
        result_description = result_metadata.get("result_description", "")

        def normalize_impact_score(value):
            return value if value is not None else "Not Defined"

        def normalize_impact_component(value):
            return value if value is not None else "Not Applicable"
        
        impact_tags = {
            "Gender Equality, Youth and Social Inclusion": {
                "user_score": normalize_impact_score(
                    result_metadata["gender_tag_level_description"]
                ),
                "component": normalize_impact_component(
                    result_metadata.get("gender_impact_area_impact_area", "")
                )
            },
            "Climate Adaptation and Mitigation": {
                "user_score": normalize_impact_score(
                    result_metadata["climate_change_tag_level_description"]
                ),
                "component": normalize_impact_component(
                    result_metadata.get("climate_impact_area_impact_area", "")
                )
            },
            "Nutrition, Health and Food Security": {
                "user_score": normalize_impact_score(
                    result_metadata["nutrition_tag_level_description"]
                ),
                "component": normalize_impact_component(
                    result_metadata.get("nutrition_impact_area_impact_area", "")
                )
            },
            "Environmental Health and Biodiversity": {
                "user_score": normalize_impact_score(
                    result_metadata["environmental_biodiversity_tag_level_description"]
                ),
                "component": normalize_impact_component(
                    result_metadata.get("environmental_biodiversity_impact_area_impact_area", "")
                )
            },
            "Poverty Reduction, Livelihoods and Jobs": {
                "user_score": normalize_impact_score(
                    result_metadata["poverty_tag_level_description"]
                ),
                "component": normalize_impact_component(
                    result_metadata.get("poverty_impact_area_impact_area", "")
                )
            }
        }

        all_evidences = result_metadata.get("evidence", [])
        valid_evidences = []
        
        for evidence in all_evidences:
            is_sharepoint = evidence.get("is_sharepoint", 0) == 1
            is_public = evidence.get("is_public_file", True)
            
            if is_sharepoint and not is_public:
                logger.info(f"⏭️ Skipping private SharePoint file: {evidence.get('link', 'N/A')}")
                continue
            
            valid_evidences.append(evidence)
        
        evidence_urls = [evidence.get("link") for evidence in valid_evidences]
        
        if len(all_evidences) != len(valid_evidences):
            logger.info(f"📋 Filtered evidences: {len(valid_evidences)}/{len(all_evidences)} (skipped {len(all_evidences) - len(valid_evidences)} private SharePoint files)")

        logger.info(f"🔍 Processing PRMS document with result type: {result_type}, result level: {result_level}")

        evidence_context = ""
        evidence_data = None

        if evidence_urls and len(evidence_urls) > 0:
            logger.info(f"📚 Processing {len(evidence_urls)} evidence URLs")
            
            try:
                async with SCRAPING_SEMAPHORE:
                    enhancer = EvidenceEnhancer()
                    
                    evidence_data = await enhancer.enhance_prms_context(
                        result_metadata=result_metadata,
                        evidence_urls=evidence_urls,
                        max_evidences=max_evidences
                    )
                
                evidence_context = evidence_data['formatted_context']
                
                logger.info(f"✅ Evidence processing complete:")
                logger.info(f"   Successful: {evidence_data['evidence_count']}/{evidence_data['total_attempted']}")
                logger.info(f"   Context length: {len(evidence_context)} chars")
                
            except Exception as e:
                logger.error(f"⚠️ Error processing evidences: {str(e)}")
                logger.warning(f"⚠️ Continuing without evidence context")
                evidence_context = ""
        else:
            logger.info("ℹ️  No evidence URLs provided, processing without additional context")
        
        logger.info("📝 Building modular prompts...")
        main_prompt = build_main_prompt(result_type, result_level, result_metadata, evidence_context)
        
        tasks = [
            invoke_model_async(main_prompt, max_tokens=2000, prompt_name="main (title/description)")
        ]
        
        has_evidence = bool(evidence_context and evidence_context.strip())
        if has_evidence:
            impact_area_prompt = build_impact_area_prompt(result_metadata, evidence_context, impact_tags)
            tasks.append(
                invoke_model_async(impact_area_prompt, max_tokens=1000, prompt_name="impact_areas")
            )
            logger.info("➕ Added impact areas prompt (evidence available)")
        else:
            logger.info("⏭️  Skipping impact areas prompt (no evidence available)")
        
        # if result_type == "innovation development":
        #     readiness_prompt = build_readiness_prompt(result_metadata, evidence_context)
        #     tasks.append(
        #         invoke_model_async(readiness_prompt, max_tokens=1000, prompt_name="readiness_level")
        #     )
        #     logger.info("➕ Added readiness level prompt for Innovation Development")
        
        # elif result_type == "innovation use":
        #     use_level_prompt = build_use_level_prompt(result_metadata, evidence_context)
        #     tasks.append(
        #         invoke_model_async(use_level_prompt, max_tokens=1000, prompt_name="use_level")
        #     )
        #     logger.info("➕ Added use level prompt for Innovation Use")
        
        logger.info(f"🚀 Executing {len(tasks)} prompts in parallel...")
        responses = await asyncio.gather(*tasks)
        
        logger.info("📦 Parsing responses...")

        try:
            main_response = json.loads(responses[0])
            
            if has_evidence:
                impact_response = json.loads(responses[1])
                logger.info("✅ Using AI-generated impact areas (evidence available)")
            else:
                impact_response = {
                    "impact_area_scores": {
                        "social_inclusion": "Unable to assess - no evidence provided or evidence could not be accessed to evaluate this impact area",
                        "climate_adaptation": "Unable to assess - no evidence provided or evidence could not be accessed to evaluate this impact area", 
                        "food_security": "Unable to assess - no evidence provided or evidence could not be accessed to evaluate this impact area",
                        "environmental_health": "Unable to assess - no evidence provided or evidence could not be accessed to evaluate this impact area",
                        "poverty_reduction": "Unable to assess - no evidence provided or evidence could not be accessed to evaluate this impact area"
                    }
                }
                logger.info("✅ Using default impact areas (no evidence available)")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        
        json_content = {
            **main_response,
            **impact_response
        }

        try:
            validate_output_schema(json_content, result_type)
            logger.info("✅ Output schema validation succeeded")
        except ValidationError as ve:
            error_msg = f"Output schema validation failed: {ve}"
            logger.error(f"❌ PRMS Schema Error: {error_msg}")
            raise ValueError(error_msg)

        if len(responses) > (2 if has_evidence else 1):
            conditional_index = 2 if has_evidence else 1
            conditional_response = json.loads(responses[conditional_index]) if is_valid_json(responses[conditional_index]) else {"text": responses[conditional_index]}
            json_content.update(conditional_response)
        
        logger.info(f"✅ Combined {len(responses)} responses successfully")

        end_time = time.time()
        elapsed_time = end_time - start_time

        interaction_id = None
        if user_id:
            try:           
                ai_output = json.dumps(json_content, indent=2, ensure_ascii=False)
                user_input = f"PRMS Result Metadata - Result type: {result_type}, Original result title: {result_title}, Original result description: {result_description}"

                tracking_context = {
                    "prompts_executed": len(tasks),
                    "prompt_types": ["main", "impact_areas"] + (["readiness_level"] if result_type == "innovation development" else ["use_level"] if result_type == "innovation use" else []),
                    "model_used": "claude-4-sonnet",
                    "evidence_context_length": len(evidence_context),
                    "evidence_count": evidence_data['evidence_count'] if evidence_data else 0,
                    "evidence_urls": evidence_urls[:5] if evidence_urls else []
                }
                
                interaction_response = interaction_client.track_interaction(
                    user_id=user_id,
                    user_input=user_input,
                    ai_output=ai_output,
                    service_name="qa-ai",
                    display_name="PRMS Reporting Tool - QA Service",
                    service_description="QA service with web scraping evidence support",
                    context=tracking_context,
                    response_time_seconds=elapsed_time,
                    platform="PRMS"
                )

                if interaction_response:
                    interaction_id = interaction_response.get('interaction_id')
                    logger.info(f"📊 Interaction tracked with ID: {interaction_id}")
                else:
                    logger.warning("⚠️ Failed to track interaction with interaction service")

            except Exception as tracking_error:
                logger.error(f"❌ Error tracking interaction: {str(tracking_error)}")
        
        logger.info(f"✅ Successfully generated PRMS response:\n{json.dumps(json_content, indent=2, ensure_ascii=False)}")
        logger.info(f"⏱️ PRMS Response time: {elapsed_time:.2f} seconds")

        result = {
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json_content,
        }

        if interaction_id:
            result["interaction_id"] = interaction_id

        if evidence_data and evidence_data['evidence_count'] > 0:
            result["evidence_metadata"] = {
                "count": evidence_data['evidence_count'],
                "total_attempted": evidence_data['total_attempted'],
                "sources": [
                    {
                        "url": e['url'],
                        "title": e['title'],
                        "type": e['type'],
                        "content_length": e['full_length']
                    }
                    for e in evidence_data['evidence_contents']
                    if e['type'] != 'error'
                ]
            }
        
        return result

    except KeyError as e:
        logger.error(f"❌ PRMS KeyError - Missing key: {str(e)}")
        logger.error(f"📦 DEBUG - Available keys: {list(result_metadata.keys())}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise
    
    except Exception as e:
        logger.error(f"❌ PRMS Error: {str(e)}")
        logger.error(f"📦 DEBUG - Error type: {type(e).__name__}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise