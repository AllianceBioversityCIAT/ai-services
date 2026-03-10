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
