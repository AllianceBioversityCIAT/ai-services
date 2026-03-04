"""
Módulo para interactuar con Supabase
"""
import os
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Cliente de Supabase
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

TABLE_NAME = "clarisa_institutions_v2"


def insert_institution(institution_data: Dict) -> bool:
    """
    Inserta una institución en Supabase
    
    Args:
        institution_data: Diccionario con datos de la institución
        
    Returns:
        bool: True si se insertó correctamente, False en caso contrario
    """
    try:
        response = supabase.table(TABLE_NAME).insert(institution_data).execute()
        return True
    
    except Exception as e:
        print(f"❌ Error insertando institución {institution_data.get('clarisa_id')}: {e}")
        return False


def upsert_institution(institution_data: Dict) -> bool:
    """
    Inserta o actualiza una institución en Supabase (upsert)
    
    Args:
        institution_data: Diccionario con datos de la institución
        
    Returns:
        bool: True si se insertó/actualizó correctamente, False en caso contrario
    """
    try:
        response = supabase.table(TABLE_NAME).upsert(
            institution_data,
            on_conflict='clarisa_id'
        ).execute()
        return True
    
    except Exception as e:
        print(f"❌ Error en upsert de institución {institution_data.get('clarisa_id')}: {e}")
        return False


def insert_institutions_batch(institutions: List[Dict], batch_size: int = 100) -> Dict[str, int]:
    """
    Inserta múltiples instituciones en batches
    
    Args:
        institutions: Lista de instituciones a insertar
        batch_size: Tamaño de cada batch
        
    Returns:
        Dict: Estadísticas de inserción {'success': N, 'failed': M}
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
            print(f"✅ Batch {i // batch_size + 1}: {len(batch)} instituciones insertadas")
        
        except Exception as e:
            stats['failed'] += len(batch)
            print(f"❌ Error en batch {i // batch_size + 1}: {e}")
    
    return stats


def get_institution_by_clarisa_id(clarisa_id: int) -> Optional[Dict]:
    """
    Obtiene una institución por su clarisa_id
    
    Args:
        clarisa_id: ID de CLARISA
        
    Returns:
        Dict: Datos de la institución o None si no existe
    """
    try:
        response = supabase.table(TABLE_NAME).select("*").eq(
            'clarisa_id', clarisa_id
        ).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    
    except Exception as e:
        print(f"❌ Error obteniendo institución {clarisa_id}: {e}")
        return None


def count_institutions() -> int:
    """
    Cuenta el número total de instituciones en la tabla
    
    Returns:
        int: Número de instituciones
    """
    try:
        response = supabase.table(TABLE_NAME).select(
            "id", count='exact'
        ).execute()
        
        return response.count if response.count else 0
    
    except Exception as e:
        print(f"❌ Error contando instituciones: {e}")
        return 0


def search_by_name_embedding(query_embedding: List[float], 
                             threshold: float = 0.5, 
                             limit: int = 5) -> List[Dict]:
    """
    Busca instituciones por similitud de embedding de nombre usando RPC
    
    Args:
        query_embedding: Vector de embedding de la consulta
        threshold: Umbral mínimo de similitud
        limit: Número máximo de resultados
        
    Returns:
        List[Dict]: Lista de instituciones similares
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
        print(f"❌ Error en búsqueda por nombre: {e}")
        return []


def search_by_acronym_embedding(query_embedding: List[float], 
                                threshold: float = 0.5, 
                                limit: int = 5) -> List[Dict]:
    """
    Busca instituciones por similitud de embedding de acrónimo usando RPC
    
    Args:
        query_embedding: Vector de embedding de la consulta
        threshold: Umbral mínimo de similitud
        limit: Número máximo de resultados
        
    Returns:
        List[Dict]: Lista de instituciones similares
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
        print(f"❌ Error en búsqueda por acrónimo: {e}")
        return []


def search_combined(name_embedding: List[float],
                   acronym_embedding: List[float],
                   name_weight: float = 0.7,
                   acronym_weight: float = 0.3,
                   threshold: float = 0.5,
                   limit: int = 5) -> List[Dict]:
    """
    Busca instituciones combinando similitud de nombre y acrónimo
    
    Args:
        name_embedding: Vector de embedding del nombre
        acronym_embedding: Vector de embedding del acrónimo
        name_weight: Peso del nombre en el score combinado
        acronym_weight: Peso del acrónimo en el score combinado
        threshold: Umbral mínimo de similitud combinada
        limit: Número máximo de resultados
        
    Returns:
        List[Dict]: Lista de instituciones similares con scores
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
        print(f"❌ Error en búsqueda combinada: {e}")
        return []
