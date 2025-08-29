import os
import vecs
from app.utils.logger.logger_util import get_logger

logger = get_logger()

def setup_supabase():
    try:
        DB_CONNECTION = os.getenv('DB_SUPABASE_CONNECTION')
        COLLECTION_NAME = os.getenv('SUPABASE_COLLECTION')
        
        if not DB_CONNECTION or not COLLECTION_NAME:
            logger.error("Supabase connection variables not set")
            return None
        
        # Crear cliente
        vx = vecs.create_client(DB_CONNECTION)
        collection = vx.get_or_create_collection(
            name=COLLECTION_NAME, 
            dimension=1024
        )
        
        # Verificar si el índice existe, si no crearlo
        try:
            collection.create_index(measure=vecs.IndexMeasure.cosine_distance)
        except:
            # El índice ya puede existir
            pass

        logger.info(f"Collection '{COLLECTION_NAME}' successfully retrieved")
        return collection
        
    except Exception as e:
        logger.error(f"Error con Supabase: {str(e)}")
        return None