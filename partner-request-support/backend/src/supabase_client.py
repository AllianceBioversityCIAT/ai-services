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


def get_all_institutions_from_db() -> List[Dict]:
    """
    Gets all institutions from the database
    
    Returns:
        List[Dict]: List of all institutions with their data (excluding embeddings)
    """
    try:
        all_data = []
        page_size = 1000
        offset = 0
        
        while True:
            response = supabase.table(TABLE_NAME).select(
                "clarisa_id, name, acronym, website, countries, institution_type, created_at, updated_at"
            ).range(offset, offset + page_size - 1).execute()
            
            if response.data:
                all_data.extend(response.data)
                
                if len(response.data) < page_size:
                    break
                    
                offset += page_size
            else:
                break
        
        return all_data
    
    except Exception as e:
        logger.error(f"❌ Error getting all institutions: {e}")
        return []


def delete_institutions_by_ids(clarisa_ids: List[int]) -> int:
    """
    Deletes institutions by their clarisa_ids
    
    Args:
        clarisa_ids: List of clarisa_ids to delete
        
    Returns:
        int: Number of institutions deleted
    """
    if not clarisa_ids:
        return 0
    
    try:
        response = supabase.table(TABLE_NAME).delete().in_(
            'clarisa_id', clarisa_ids
        ).execute()
        
        deleted_count = len(response.data) if response.data else 0
        logger.info(f"✅ Deleted {deleted_count} institutions from database")
        
        return deleted_count
    
    except Exception as e:
        logger.error(f"❌ Error deleting institutions: {e}")
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


# ==========================================
# PARTNER REQUEST CACHE FUNCTIONS
# ==========================================

CACHE_TABLE = "partner_request_cache_test"


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
        normalized_names = [name.strip().lower() for name in partner_names if name]
        
        if not normalized_names:
            return {}
        
        response = supabase.table(CACHE_TABLE).select("*").execute()
        
        cached_results = {}
        if response.data:
            for cache_data in response.data:
                cached_name = cache_data.get('partner_name', '').strip().lower()
                
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


def clear_all_cache() -> int:
    """
    Clears all cache entries. Used when CLARISA database is updated
    to ensure all matches are reprocessed with fresh data.
    
    Returns:
        int: Number of cache entries deleted
    """
    try:
        count_response = supabase.table(CACHE_TABLE).select(
            "request_id", count='exact'
        ).execute()
        
        count = count_response.count if count_response.count else 0
        
        if count == 0:
            logger.info("📭 Cache is already empty")
            return 0
        
        delete_response = supabase.table(CACHE_TABLE).delete().neq(
            'request_id', -1
        ).execute()
        
        logger.info(f"🗑️  Cleared {count} cache entries")
        return count
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        return 0


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
