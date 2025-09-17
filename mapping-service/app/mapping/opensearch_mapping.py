import os
import requests
from typing import List
from requests.auth import HTTPBasicAuth
from app.utils.logger.logger_util import get_logger
from app.api.models import MappingEntry, MappingResult
from app.utils.config.config_util import STAR, CLARISA

logger = get_logger()

OPENSEARCH_URL = STAR["opensearch_url"]
OPENSEARCH_USERNAME = STAR["opensearch_username"]
OPENSEARCH_PASSWORD = STAR["opensearch_password"]
OPENSEARCH_INDEX = STAR["opensearch_index"]

CL_OPENSEARCH_URL = CLARISA["opensearch_url"]
CL_OPENSEARCH_USERNAME = CLARISA["opensearch_username"]
CL_OPENSEARCH_PASSWORD = CLARISA["opensearch_password"]
CL_OPENSEARCH_INDEX = CLARISA["opensearch_index"]

INDEX_MAPPING = {
    "institution": CL_OPENSEARCH_INDEX,
    "staff": OPENSEARCH_INDEX
}

def map_entries_to_ids(entries: List[MappingEntry]) -> List[MappingResult]:
    results = []

    for entry in entries:
        try:
            index = INDEX_MAPPING.get(entry.type)
            if not index:
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
            
            query_body = {
                "size": 3,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": entry.value,
                                    "fields": search_fields,
                                    "type": "best_fields",  # Boost docs where terms appear in same field
                                    "boost": 2.0
                                }
                            },
                            {
                                "multi_match": {
                                    "query": entry.value,
                                    "fields": search_fields,
                                    "type": "cross_fields",  # Boost docs where terms appear across fields
                                    "boost": 1.0
                                }
                            }
                        ]
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
            logger.info(f"🔍 Total hits: {data.get('hits', {}).get('total', {})}")
            logger.info(f"🔍 Hits found: {len(data.get('hits', {}).get('hits', []))}")

            hits = data.get("hits", {}).get("hits", [])
            if hits:
                for hit in hits:
                    source = hit["_source"]
                    score = hit["_score"]

                    if entry.type == "staff":
                        mapped_id = source.get("carnet")
                        mapped_name = f"{source.get('first_name', '')} {source.get('last_name', '')}".strip()
                        mapped_acronym = None
                    else:
                        mapped_id = str(source.get("code")) if source.get("code") else None
                        mapped_name = source.get("name")
                        mapped_acronym = source.get("acronym")

                    results.append(MappingResult(
                        original_value=entry.value,
                        type=entry.type,
                        mapped_id=mapped_id,
                        mapped_name=mapped_name,
                        mapped_acronym=mapped_acronym,
                        score=round(score, 4)
                    ))
            else:
                results.append(MappingResult(
                    original_value=entry.value,
                    type=entry.type,
                    mapped_id=None,
                    mapped_name=None,
                    mapped_acronym=None,
                    score=None
                ))
            
            logger.info(f"✅ Response generated successfully: {results}")

        except Exception as e:
            logger.error(f"❌ Error searching for '{entry.value}': {str(e)}")
            results.append(MappingResult(
                original_value=entry.value,
                type=entry.type,
                mapped_id=None,
                mapped_name=None,
                mapped_acronym=None,
                score=None
            ))

    return results