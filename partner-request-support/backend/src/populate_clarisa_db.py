"""
Script principal para poblar la tabla de instituciones CLARISA en Supabase
con embeddings generados por Amazon Titan
"""
import sys
from tqdm import tqdm
from src.clarisa_api import get_all_parsed_institutions
from src.embeddings import get_embedding, embedding_to_list
from src.supabase_client import insert_institutions_batch, count_institutions


def generate_embeddings_for_institution(institution):
    """
    Genera embeddings para nombre y acrónimo de una institución
    
    Args:
        institution: Diccionario con datos de la institución
        
    Returns:
        Dict: Institución con embeddings agregados
    """
    name = institution.get('name', '')
    acronym = institution.get('acronym', '')
    
    # Generar embedding para el nombre
    if name:
        name_embedding = get_embedding(name)
        institution['name_embedding'] = embedding_to_list(name_embedding)
    else:
        institution['name_embedding'] = None
    
    # Generar embedding para el acrónimo (solo si existe)
    if acronym:
        acronym_embedding = get_embedding(acronym)
        institution['acronym_embedding'] = embedding_to_list(acronym_embedding)
    else:
        institution['acronym_embedding'] = None
    
    return institution


def populate_clarisa_institutions(batch_size=50):
    """
    Proceso principal para poblar la tabla de instituciones CLARISA
    
    Args:
        batch_size: Tamaño de cada batch para inserción
    """
    print("=" * 70)
    print("🚀 INICIANDO POBLACIÓN DE TABLA CLARISA_INSTITUTIONS_V2")
    print("=" * 70)
    print()
    
    # Paso 1: Obtener instituciones de la API de CLARISA
    print("📋 PASO 1: Obteniendo instituciones de CLARISA...")
    institutions = get_all_parsed_institutions()
    
    if not institutions:
        print("❌ No se pudieron obtener instituciones de CLARISA. Abortando.")
        sys.exit(1)
    
    print(f"✅ {len(institutions)} instituciones obtenidas y parseadas")
    print()
    
    # Paso 2: Generar embeddings para cada institución
    print("🧠 PASO 2: Generando embeddings con Amazon Titan...")
    print(f"   Esto puede tardar varios minutos para {len(institutions)} instituciones...")
    print()
    
    institutions_with_embeddings = []
    
    for institution in tqdm(institutions, desc="Generando embeddings"):
        try:
            inst_with_emb = generate_embeddings_for_institution(institution)
            institutions_with_embeddings.append(inst_with_emb)
        except Exception as e:
            print(f"\n⚠️  Error procesando institución {institution.get('clarisa_id')}: {e}")
            continue
    
    print()
    print(f"✅ Embeddings generados para {len(institutions_with_embeddings)} instituciones")
    print()
    
    # Paso 3: Insertar en Supabase
    print("💾 PASO 3: Insertando instituciones en Supabase...")
    stats = insert_institutions_batch(institutions_with_embeddings, batch_size=batch_size)
    
    print()
    print("=" * 70)
    print("📊 RESUMEN DE INSERCIÓN")
    print("=" * 70)
    print(f"✅ Exitosas: {stats['success']}")
    print(f"❌ Fallidas:  {stats['failed']}")
    print()
    
    # Verificar conteo final
    total_in_db = count_institutions()
    print(f"📈 Total de instituciones en la base de datos: {total_in_db}")
    print()
    print("=" * 70)
    print("✅ PROCESO COMPLETADO")
    print("=" * 70)


def main():
    """Función principal"""
    print()
    
    # Verificar conteo actual
    current_count = count_institutions()
    print(f"📊 Instituciones actualmente en la base de datos: {current_count}")
    print()
    
    if current_count > 0:
        response = input("⚠️  La tabla ya contiene datos. ¿Desea continuar? (s/n): ")
        if response.lower() != 's':
            print("❌ Operación cancelada por el usuario")
            sys.exit(0)
        print()
    
    # Ejecutar población
    populate_clarisa_institutions(batch_size=50)


if __name__ == "__main__":
    main()
