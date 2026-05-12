import os
import json
import unicodedata
import requests
from typing import List, Dict, Optional
from requests.auth import HTTPBasicAuth
from app.utils.logger.logger_util import get_logger
from app.api.models import MappingEntry, MappingResult
from app.utils.prompts.prompt_staff import prompt_staff
from app.utils.config.config_util import STAR, CLARISA, LLM_API_URL
from app.utils.prompts.prompt_institutions import prompt_institutions

logger = get_logger()


def _normalize(text: str) -> str:
    """Return a version of text with accent marks stripped (NFD decomposition + remove combining chars)."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")


OPENSEARCH_URL = STAR["opensearch_url"]
OPENSEARCH_USERNAME = STAR["opensearch_username"]
OPENSEARCH_PASSWORD = STAR["opensearch_password"]
OPENSEARCH_INDEX = STAR["opensearch_index"]

CL_OPENSEARCH_URL = CLARISA["opensearch_url"]
CL_OPENSEARCH_USERNAME = CLARISA["opensearch_username"]
CL_OPENSEARCH_PASSWORD = CLARISA["opensearch_password"]
CL_OPENSEARCH_PROD_INDEX = CLARISA["opensearch_prod_index"]
CL_OPENSEARCH_TEST_INDEX = CLARISA["opensearch_test_index"]


def call_llm_validation(original_value: str, candidates: List[Dict], entry_type: str) -> Optional[Dict]:
    """Call the LLM API to validate and select the best candidate"""
    try:
        candidates_text = f"Original search: '{original_value}'\n\nCANDIDATES:\n"
        
        for i, candidate in enumerate(candidates, 1):
            if entry_type == "staff":
                candidates_text += f"{i}. ID: {candidate['id']}\n"
                candidates_text += f"   Name: {candidate['name']}\n"
                candidates_text += f"   Email: {candidate.get('email', 'N/A')}\n"
                candidates_text += f"   Center: {candidate.get('center', 'N/A')}\n"
                candidates_text += f"   OpenSearch Score: {candidate['score']}\n\n"
            else:
                candidates_text += f"{i}. ID: {candidate['id']}\n"
                candidates_text += f"   Name: {candidate['name']}\n"
                candidates_text += f"   Acronym: {candidate.get('acronym', 'N/A')}\n"
                candidates_text += f"   Website: {candidate.get('website', 'N/A')}\n"
                candidates_text += f"   OpenSearch Score: {candidate['score']}\n\n"
        
        if entry_type == "staff":
            prompt = prompt_staff
        else:
            prompt = prompt_institutions

        payload = {
            "prompt": prompt,
            "input_text": candidates_text
        }
        
        logger.info(f"🤖 Calling LLM for validation of {len(candidates)} candidates...")
        
        response = requests.post(LLM_API_URL, json=payload, timeout=300)
        response.raise_for_status()
        
        llm_response = response.text.strip()
        
        try:
            api_result = json.loads(llm_response)
            
            if "output" in api_result and "status" in api_result:
                if api_result["status"] == "success":
                    output_text = api_result["output"]

                    result = json.loads(output_text)
                    logger.info(f"🤖 Parsed LLM result: {result}")
                    return result
                else:
                    logger.error(f"❌ LLM API returned error status: {api_result.get('status')}")
                    return None
            else:
                logger.info("🤖 Trying direct JSON parsing...")
                return api_result
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {str(e)}")
            logger.info(f"🤖 Trying to extract JSON from markdown response...")
            
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                if json_end == -1:
                    json_text = llm_response[json_start:].strip()
                else:
                    json_text = llm_response[json_start:json_end].strip()
                
                logger.info(f"🤖 Extracted JSON text: {json_text}")

                json_text = (json_text
                           .replace('\\n', '')           # Remove escaped newlines
                           .replace('\n', '')            # Remove actual newlines
                           .replace('\\"', '"')          # Fix escaped quotes
                           .replace('\\t', '')           # Remove escaped tabs
                           .replace('\t', '')            # Remove actual tabs
                           .strip())                     # Remove leading/trailing whitespace
                
                logger.info(f"🤖 Cleaned JSON text: {json_text}")
                
                try:
                    result = json.loads(json_text)
                    logger.info(f"🤖 Successfully parsed extracted result: {result}")
                    return result
                except json.JSONDecodeError as e2:
                    logger.error(f"❌ Failed to parse extracted JSON: {str(e2)}")
                    logger.error(f"❌ Problematic JSON: {json_text}")
                    
                    try:
                        # Remove any remaining escape characters that might be problematic
                        fixed_json = json_text.replace('\\"', '"').replace('\\', '')
                        logger.info(f"🤖 Attempting to parse fixed JSON: {fixed_json}")
                        result = json.loads(fixed_json)
                        logger.info(f"🤖 Successfully parsed fixed result: {result}")
                        return result
                    except json.JSONDecodeError as e3:
                        logger.error(f"❌ Even fixed JSON failed: {str(e3)}")
                        logger.error(f"🔄 LLM parsing failed completely, will use OpenSearch fallback")
                        return None
            else:
                logger.error(f"❌ No JSON markdown found in response")
                logger.error(f"🔄 LLM parsing failed completely, will use OpenSearch fallback")
                return None
                
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP error calling LLM validation: {str(e)}")
        logger.error(f"🔄 LLM call failed, will use OpenSearch fallback")
        return None
    except Exception as e:
        logger.error(f"❌ Error calling LLM validation: {str(e)}")
        logger.error(f"🔄 LLM call failed, will use OpenSearch fallback")
        return None


def map_entries_to_ids(entries: List[MappingEntry], environment: str = "prod") -> List[MappingResult]:
    results = []

    for entry in entries:
        try:
            # Determine index based on type and environment
            if entry.type == "staff":
                index = OPENSEARCH_INDEX
            elif entry.type == "institution":
                index = CL_OPENSEARCH_TEST_INDEX if environment == "test" else CL_OPENSEARCH_PROD_INDEX
            else:
                raise ValueError(f"Unsupported type '{entry.type}'")

            if entry.type == "staff":
                opensearch_url = OPENSEARCH_URL
                opensearch_username = OPENSEARCH_USERNAME
                opensearch_password = OPENSEARCH_PASSWORD
                search_fields = ["first_name^2", "last_name^2"]
            else:
                opensearch_url = CL_OPENSEARCH_URL
                opensearch_username = CL_OPENSEARCH_USERNAME
                opensearch_password = CL_OPENSEARCH_PASSWORD
                search_fields = ["acronym^2", "name"]

            url = f"{opensearch_url}/{index}/_search"

            normalized_value = _normalize(entry.value)
            # Use a set to avoid duplicate clauses when the value has no accents
            query_values = list(dict.fromkeys([entry.value, normalized_value]))

            should_clauses = []
            for qv in query_values:
                should_clauses.append({
                    "multi_match": {
                        "query": qv,
                        "fields": search_fields,
                        "type": "best_fields",   # Boost docs where terms appear in same field
                        "boost": 2.0
                    }
                })
                should_clauses.append({
                    "multi_match": {
                        "query": qv,
                        "fields": search_fields,
                        "type": "cross_fields",  # Boost docs where terms appear across fields
                        "boost": 1.0
                    }
                })

            # Fuzzy clauses catch residual 1-char differences (e.g. tilde present only in index)
            for field in search_fields:
                clean_field = field.split("^")[0]  # strip boost notation
                should_clauses.append({
                    "fuzzy": {
                        clean_field: {
                            "value": normalized_value,
                            "fuzziness": 1,
                            "boost": 0.5
                        }
                    }
                })

            query_body = {
                "size": 3,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                }
            }

            response = requests.post(
                url,
                json=query_body,
                auth=HTTPBasicAuth(opensearch_username, opensearch_password),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"🔍 Response status: {response.status_code}")
            logger.info(f"🔍 Hits found: {len(data.get('hits', {}).get('hits', []))}")

            hits = data.get("hits", {}).get("hits", [])
            if hits:
                candidates = []
                for hit in hits:
                    source = hit["_source"]
                    score = hit["_score"]

                    if entry.type == "staff":
                        candidate = {
                            "id": source.get("carnet"),
                            "name": f"{source.get('first_name', '')} {source.get('last_name', '')}".strip(),
                            "email": source.get("email"),
                            "center": source.get("center"),
                            "score": round(score, 4)
                        }
                    else:
                        candidate = {
                            "id": str(source.get("code")) if source.get("code") else None,
                            "name": source.get("name"),
                            "acronym": source.get("acronym"),
                            "website": source.get("websiteLink"),
                            "score": round(score, 4)
                        }
                    candidates.append(candidate)

                llm_result = call_llm_validation(entry.value, candidates, entry.type)
                
                logger.info(f"📊 OpenSearch returned {len(candidates)} candidates for '{entry.value}':")
                for i, candidate in enumerate(candidates, 1):
                    if entry.type == "staff":
                        logger.info(f"   {i}. ID: {candidate['id']} | Name: {candidate['name']} | Score: {candidate['score']}")
                    else:
                        logger.info(f"   {i}. ID: {candidate['id']} | Name: {candidate['name']} | Acronym: {candidate.get('acronym')} | Score: {candidate['score']}")

                if llm_result and llm_result.get("selected_candidate") is not None:
                    selected_index = llm_result["selected_candidate"] - 1
                    if 0 <= selected_index < len(candidates):
                        selected_candidate = candidates[selected_index]
                        
                        logger.info(f"🤖 LLM selected candidate {llm_result['selected_candidate']}: {selected_candidate['name']}")
                        logger.info(f"🤖 Confidence score: {llm_result.get('confidence_score', 'N/A')}/100")
                        logger.info(f"🤖 Reasoning: {llm_result.get('reasoning', 'No reasoning provided')}")
                        
                        results.append(MappingResult(
                            original_value=entry.value,
                            type=entry.type,
                            mapped_id=selected_candidate["id"],
                            mapped_name=selected_candidate["name"],
                            mapped_acronym=selected_candidate.get("acronym"),
                            score=llm_result.get("confidence_score")
                        ))
                    else:
                        logger.error(f"❌ LLM selected invalid candidate index: {selected_index}")
                        logger.info(f"🔄 Using OpenSearch fallback - first result")
                        first_candidate = candidates[0]
                        results.append(MappingResult(
                            original_value=entry.value,
                            type=entry.type,
                            mapped_id=first_candidate["id"],
                            mapped_name=first_candidate["name"],
                            mapped_acronym=first_candidate.get("acronym"),
                            score=90
                        ))
                elif llm_result and llm_result.get("selected_candidate") is None:
                    # LLM explicitly said no reliable match
                    logger.info(f"🤖 LLM determined no reliable match for '{entry.value}'")
                    logger.info(f"🤖 Reasoning: {llm_result.get('reasoning', 'No reasoning provided')}")
                    
                    results.append(MappingResult(
                        original_value=entry.value,
                        type=entry.type,
                        mapped_id=None,
                        mapped_name=None,
                        mapped_acronym=None,
                        score=0
                    ))
                else:
                    # LLM call failed completely (parsing errors, network issues, etc.)
                    logger.info(f"🔄 LLM validation failed, using OpenSearch fallback for '{entry.value}'")
                    logger.info(f"🔄 Using first OpenSearch result: {candidates[0]['name']}")
                    
                    first_candidate = candidates[0]
                    results.append(MappingResult(
                        original_value=entry.value,
                        type=entry.type,
                        mapped_id=first_candidate["id"],
                        mapped_name=first_candidate["name"],
                        mapped_acronym=first_candidate.get("acronym"),
                        score=90
                    ))
            else:
                # No OpenSearch results found
                logger.info(f"🔍 No OpenSearch results found for '{entry.value}'")
                results.append(MappingResult(
                    original_value=entry.value,
                    type=entry.type,
                    mapped_id=None,
                    mapped_name=None,
                    mapped_acronym=None,
                    score=0
                ))
            
            logger.info(f"✅ Response generated successfully")

        except Exception as e:
            logger.error(f"❌ Error searching for '{entry.value}': {str(e)}")
            results.append(MappingResult(
                original_value=entry.value,
                type=entry.type,
                mapped_id=None,
                mapped_name=None,
                mapped_acronym=None,
                score=0
            ))

    return results