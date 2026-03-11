"""
Module to interact with Supabase
"""
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from logger.logger_util import get_logger
from supabase import create_client, Client

load_dotenv()
logger = get_logger()


supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

TABLE_NAME = "clarisa_institutions_v2"


def insert_institution(institution_data: Dict) -> bool:
    """
    Inserts an institution into Supabase
    
    Args:
        institution_data: Dictionary with institution data
        
    Returns:
        bool: True if inserted successfully, False otherwise
    """
    try:
        response = supabase.table(TABLE_NAME).insert(institution_data).execute()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error inserting institution {institution_data.get('clarisa_id')}: {e}")
        return False


def upsert_institution(institution_data: Dict) -> bool:
    """
    Inserts or updates an institution in Supabase (upsert)
    
    Args:
        institution_data: Dictionary with institution data
        
    Returns:
        bool: True if inserted/updated successfully, False otherwise
    """
    try:
        response = supabase.table(TABLE_NAME).upsert(
            institution_data,
            on_conflict='clarisa_id'
        ).execute()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error in upsert of institution {institution_data.get('clarisa_id')}: {e}")
        return False


def insert_institutions_batch(institutions: List[Dict], batch_size: int = 100) -> Dict[str, int]:
    """
    Inserts multiple institutions in batches
    
    Args:
        institutions: List of institutions to insert
        batch_size: Size of each batch
        
    Returns:
        Dict: Insertion statistics {'success': N, 'failed': M}
    """
    stats = {'success': 0, 'failed': 0}
    
    for i in range(0, len(institutions), batch_size):
        batch = institutions[i:i + batch_size]
        
        try:
            response = supabase.table(TABLE_NAME).upsert(
                batch,
                on_conflict='clarisa_id'
            ).execute()
            
            stats['success'] += len(batch)
            logger.info(f"✅ Batch {i // batch_size + 1}: {len(batch)} institutions inserted")
        
        except Exception as e:
            stats['failed'] += len(batch)
            logger.error(f"❌ Error in batch {i // batch_size + 1}: {e}")
    
    return stats


def get_institution_by_clarisa_id(clarisa_id: int) -> Optional[Dict]:
    """
    Gets an institution by its clarisa_id
    
    Args:
        clarisa_id: CLARISA ID
        
    Returns:
        Dict: Institution data or None if not found
    """
    try:
        response = supabase.table(TABLE_NAME).select("*").eq(
            'clarisa_id', clarisa_id
        ).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    
    except Exception as e:
        logger.error(f"❌ Error getting institution {clarisa_id}: {e}")
        return None


def count_institutions() -> int:
    """
    Counts the total number of institutions in the table
    
    Returns:
        int: Number of institutions
    """
    try:
        response = supabase.table(TABLE_NAME).select(
            "id", count='exact'
        ).execute()
        
        return response.count if response.count else 0
    
    except Exception as e:
        logger.error(f"❌ Error counting institutions: {e}")
        return 0


def search_by_name_embedding(query_embedding: List[float], 
                             threshold: float = 0.5, 
                             limit: int = 5) -> List[Dict]:
    """
    Searches institutions by name embedding similarity using RPC
    
    Args:
        query_embedding: Query embedding vector
        threshold: Minimum similarity threshold
        limit: Maximum number of results
        
    Returns:
        List[Dict]: List of similar institutions
    """
    try:
        response = supabase.rpc(
            'search_institution_by_name',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        
        return response.data if response.data else []
    
    except Exception as e:
        logger.error(f"❌ Error in name search: {e}")
        return []


def search_by_acronym_embedding(query_embedding: List[float], 
                                threshold: float = 0.5, 
                                limit: int = 5) -> List[Dict]:
    """
    Searches institutions by acronym embedding similarity using RPC
    
    Args:
        query_embedding: Query embedding vector
        threshold: Minimum similarity threshold
        limit: Maximum number of results
        
    Returns:
        List[Dict]: List of similar institutions
    """
    try:
        response = supabase.rpc(
            'search_institution_by_acronym',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        
        return response.data if response.data else []
    
    except Exception as e:
        logger.error(f"❌ Error in acronym search: {e}")
        return []


# ==========================================
# PARTNER REQUEST CACHE FUNCTIONS
# ==========================================

CACHE_TABLE = "partner_request_cache_test"


def get_cached_result(request_id: int) -> Optional[Dict]:
    """
    Gets a cached result for a partner request
    
    Args:
        request_id: Partner request ID from CLARISA API
        
    Returns:
        Dict: Cached partner result or None if not found
    """
    try:
        response = supabase.table(CACHE_TABLE).select("*").eq(
            'request_id', request_id
        ).execute()
        
        if response.data and len(response.data) > 0:
            cache_data = response.data[0]
            # Reconstruct the partner result format
            partner_result = {
                'id': str(cache_data['request_id']),
                'name': cache_data['partner_name'],
                'acronym': cache_data['acronym'] or '',
                'website': cache_data['website'] or '',
                'country': cache_data['country'] or '',
                'match_found': cache_data['match_found'],
                'match_quality': cache_data['match_quality'],
                'clarisa_match': cache_data['clarisa_match'],
                'top_candidates': cache_data['top_candidates'] or [],
                'web_search': cache_data['web_search'],
                'api_data': cache_data['api_data']
            }
            logger.info(f"✅ Cache HIT for request_id {request_id}")
            return partner_result
        
        logger.info(f"⚠️  Cache MISS for request_id {request_id}")
        return None
    
    except Exception as e:
        logger.error(f"❌ Error getting cached result for {request_id}: {e}")
        return None


def get_cached_results(request_ids: List[int]) -> Dict[int, Dict]:
    """
    Gets multiple cached results for partner requests by ID
    
    Args:
        request_ids: List of partner request IDs
        
    Returns:
        Dict: Dictionary mapping request_id -> partner_result for found items
    """
    if not request_ids:
        return {}
    
    try:
        response = supabase.table(CACHE_TABLE).select("*").in_(
            'request_id', request_ids
        ).execute()
        
        cached_results = {}
        if response.data:
            for cache_data in response.data:
                request_id = cache_data['request_id']
                partner_result = {
                    'id': str(cache_data['request_id']),
                    'name': cache_data['partner_name'],
                    'acronym': cache_data['acronym'] or '',
                    'website': cache_data['website'] or '',
                    'country': cache_data['country'] or '',
                    'match_found': cache_data['match_found'],
                    'match_quality': cache_data['match_quality'],
                    'clarisa_match': cache_data['clarisa_match'],
                    'top_candidates': cache_data['top_candidates'] or [],
                    'web_search': cache_data['web_search'],
                    'api_data': cache_data['api_data']
                }
                cached_results[request_id] = partner_result
            
            logger.info(f"✅ Cache: Found {len(cached_results)}/{len(request_ids)} cached results")
        else:
            logger.info(f"⚠️  Cache: No cached results found for {len(request_ids)} requests")
        
        return cached_results
    
    except Exception as e:
        logger.error(f"❌ Error getting cached results: {e}")
        return {}


def get_cached_results_by_name(partner_names: List[str]) -> Dict[str, Dict]:
    """
    Gets multiple cached results for partner requests by NAME (not ID).
    This allows reusing cache for duplicate partner names with different IDs.
    
    Args:
        partner_names: List of partner names to search for
        
    Returns:
        Dict: Dictionary mapping partner_name (lowercase) -> partner_result for found items
    """
    if not partner_names:
        return {}
    
    try:
        # Normalize names for comparison (lowercase, strip whitespace)
        normalized_names = [name.strip().lower() for name in partner_names if name]
        
        if not normalized_names:
            return {}
        
        # Query cache - search for any of these names (case-insensitive)
        response = supabase.table(CACHE_TABLE).select("*").execute()
        
        cached_results = {}
        if response.data:
            for cache_data in response.data:
                cached_name = cache_data.get('partner_name', '').strip().lower()
                
                # Check if this cached name matches any of our search names
                if cached_name in normalized_names:
                    partner_result = {
                        'id': str(cache_data['request_id']),
                        'name': cache_data['partner_name'],
                        'acronym': cache_data['acronym'] or '',
                        'website': cache_data['website'] or '',
                        'country': cache_data['country'] or '',
                        'match_found': cache_data['match_found'],
                        'match_quality': cache_data['match_quality'],
                        'clarisa_match': cache_data['clarisa_match'],
                        'top_candidates': cache_data['top_candidates'] or [],
                        'web_search': cache_data['web_search'],
                        'api_data': cache_data['api_data']
                    }
                    cached_results[cached_name] = partner_result
            
            logger.info(f"✅ Cache by name: Found {len(cached_results)}/{len(normalized_names)} cached results")
        else:
            logger.info(f"⚠️  Cache by name: No cached results found")
        
        return cached_results
    
    except Exception as e:
        logger.error(f"❌ Error getting cached results by name: {e}")
        return {}


def cache_result(partner_result: Dict) -> bool:
    """
    Caches a processed partner request result
    
    Args:
        partner_result: Partner result dictionary from process_partners_to_json
        
    Returns:
        bool: True if cached successfully, False otherwise
    """
    try:
        # Extract request_id from api_data
        api_data = partner_result.get('api_data', {})
        request_id = api_data.get('request_id')
        
        if not request_id:
            logger.warning(f"⚠️  Cannot cache result: missing request_id")
            return False
        
        cache_data = {
            'request_id': request_id,
            'partner_name': partner_result.get('name', ''),
            'acronym': partner_result.get('acronym'),
            'website': partner_result.get('website'),
            'country': partner_result.get('country'),
            'match_found': partner_result.get('match_found', False),
            'match_quality': partner_result.get('match_quality', 'no_match'),
            'clarisa_match': partner_result.get('clarisa_match'),
            'top_candidates': partner_result.get('top_candidates', []),
            'web_search': partner_result.get('web_search'),
            'api_data': api_data
        }
        
        response = supabase.table(CACHE_TABLE).upsert(
            cache_data,
            on_conflict='request_id'
        ).execute()
        
        logger.info(f"✅ Cached result for request_id {request_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error caching result: {e}")
        return False


def cache_results_batch(partners_results: List[Dict]) -> Dict[str, int]:
    """
    Caches multiple partner request results in a batch
    
    Args:
        partners_results: List of partner results from process_partners_to_json
        
    Returns:
        Dict: Statistics {'cached': N, 'failed': M}
    """
    stats = {'cached': 0, 'failed': 0, 'skipped': 0}
    
    cache_batch = []
    for partner_result in partners_results:
        api_data = partner_result.get('api_data', {})
        request_id = api_data.get('request_id')
        
        if not request_id:
            stats['skipped'] += 1
            continue
        
        cache_data = {
            'request_id': request_id,
            'partner_name': partner_result.get('name', ''),
            'acronym': partner_result.get('acronym'),
            'website': partner_result.get('website'),
            'country': partner_result.get('country'),
            'match_found': partner_result.get('match_found', False),
            'match_quality': partner_result.get('match_quality', 'no_match'),
            'clarisa_match': partner_result.get('clarisa_match'),
            'top_candidates': partner_result.get('top_candidates', []),
            'web_search': partner_result.get('web_search'),
            'api_data': api_data
        }
        cache_batch.append(cache_data)
    
    if not cache_batch:
        logger.warning(f"⚠️  No valid results to cache")
        return stats
    
    try:
        response = supabase.table(CACHE_TABLE).upsert(
            cache_batch,
            on_conflict='request_id'
        ).execute()
        
        stats['cached'] = len(cache_batch)
        logger.info(f"✅ Cached {stats['cached']} partner results")
        
    except Exception as e:
        stats['failed'] = len(cache_batch)
        logger.error(f"❌ Error caching batch: {e}")
    
    return stats


def get_cache_stats() -> Dict:
    """
    Gets statistics about the cache
    
    Returns:
        Dict: Cache statistics
    """
    try:
        # Total cached items
        total_response = supabase.table(CACHE_TABLE).select(
            "request_id", count='exact'
        ).execute()
        
        # By match quality
        quality_response = supabase.table(CACHE_TABLE).select(
            "match_quality", count='exact'
        ).execute()
        
        stats = {
            'total_cached': total_response.count if total_response.count else 0,
            'by_quality': {}
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Error getting cache stats: {e}")
        return {'total_cached': 0, 'by_quality': {}}


def search_combined(name_embedding: List[float],
                   acronym_embedding: List[float],
                   name_weight: float = 0.7,
                   acronym_weight: float = 0.3,
                   threshold: float = 0.5,
                   limit: int = 5) -> List[Dict]:
    """
    Searches institutions by combining name and acronym similarity
    
    Args:
        name_embedding: Name embedding vector
        acronym_embedding: Acronym embedding vector
        name_weight: Weight of the name in the combined score
        acronym_weight: Weight of the acronym in the combined score
        threshold: Minimum combined similarity threshold
        limit: Maximum number of results
        
    Returns:
        List[Dict]: List of similar institutions with scores
    """
    try:
        response = supabase.rpc(
            'search_institution_combined',
            {
                'name_query_embedding': name_embedding,
                'acronym_query_embedding': acronym_embedding,
                'name_weight': name_weight,
                'acronym_weight': acronym_weight,
                'match_threshold': threshold,
                'match_count': limit
            }
        ).execute()
        
        return response.data if response.data else []
    
    except Exception as e:
        logger.error(f"❌ Error in combined search: {e}")
        return []
