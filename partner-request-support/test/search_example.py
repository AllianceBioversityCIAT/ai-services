"""
Ejemplo de búsqueda híbrida de instituciones
Combina similitud vectorial (Titan embeddings) + RapidFuzz
"""
from src.embeddings import get_embedding, embedding_to_list
from src.supabase_client import search_by_name_embedding, search_combined
from src.utils import clean_text_for_matching
from rapidfuzz import fuzz


def search_institution_hybrid(partner_name, acronym=None, threshold=0.4, verbose=True):
    """
    Búsqueda híbrida: Embeddings (Top 5) → RapidFuzz (desempate)
    
    Args:
        partner_name: Nombre de la institución a buscar
        acronym: Acrónimo opcional
        threshold: Umbral mínimo de similitud para embeddings
        verbose: Mostrar detalles del proceso
        
    Returns:
        Dict: Mejor match con score combinado
    """
    
    if verbose:
        print("=" * 80)
        print(f"🔍 BÚSQUEDA HÍBRIDA: {partner_name}")
        if acronym:
            print(f"   Acrónimo: {acronym}")
        print("=" * 80)
        print()
    
    # PASO 1: Generar embeddings
    if verbose:
        print("🧠 PASO 1: Generando embeddings...")
    
    name_embedding = get_embedding(partner_name)
    name_embedding_list = embedding_to_list(name_embedding)
    
    # PASO 2: Búsqueda vectorial en Supabase (Top 5)
    if verbose:
        print("🔎 PASO 2: Buscando candidatos por similitud vectorial (Top 5)...")
        print()
    
    if acronym:
        # Búsqueda combinada si hay acrónimo
        acronym_embedding = get_embedding(acronym)
        acronym_embedding_list = embedding_to_list(acronym_embedding)
        
        candidates = search_combined(
            name_embedding=name_embedding_list,
            acronym_embedding=acronym_embedding_list,
            name_weight=0.7,
            acronym_weight=0.3,
            threshold=threshold,
            limit=5
        )
    else:
        # Solo por nombre
        candidates = search_by_name_embedding(
            query_embedding=name_embedding_list,
            threshold=threshold,
            limit=5
        )
    
    if not candidates:
        if verbose:
            print("❌ No se encontraron candidatos (similitud < threshold)")
        return None
    
    if verbose:
        print(f"✅ Se encontraron {len(candidates)} candidatos:")
        print()
        for i, cand in enumerate(candidates, 1):
            cosine_sim = cand.get('similarity', cand.get('combined_similarity', 0))
            print(f"   {i}. {cand['name']}")
            print(f"      Acrónimo: {cand['acronym'] or 'N/A'}")
            print(f"      Similitud coseno: {cosine_sim:.4f}")
            print()
    
    # PASO 3: Desempate con RapidFuzz
    if verbose:
        print("🎯 PASO 3: Desempate con RapidFuzz (con normalización completa)...")
        print(f"   Normalizando query: \"{partner_name}\" → \"{clean_text_for_matching(partner_name)}\"")
        print()
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        # Similitud coseno (ya calculada por Supabase)
        cosine_sim = candidate.get('similarity', candidate.get('combined_similarity', 0))
        
        # Similitud de texto con RapidFuzz (con normalización completa)
        normalized_query = clean_text_for_matching(partner_name)
        normalized_candidate = clean_text_for_matching(candidate['name'])
        fuzz_name = fuzz.ratio(normalized_query, normalized_candidate) / 100
        
        # Si hay acrónimo, también compararlo (normalizado)
        fuzz_acronym = 0
        if acronym and candidate.get('acronym'):
            normalized_query_acronym = clean_text_for_matching(acronym)
            normalized_candidate_acronym = clean_text_for_matching(candidate['acronym'])
            fuzz_acronym = fuzz.ratio(normalized_query_acronym, normalized_candidate_acronym) / 100
        
        # Score combinado (ajusta pesos según necesidad)
        # 50% embedding + 40% fuzz name + 10% fuzz acronym
        combined_score = (
            0.50 * cosine_sim +
            0.40 * fuzz_name +
            0.10 * fuzz_acronym
        )
        
        if verbose:
            print(f"   📊 {candidate['name']}")
            print(f"      Coseno:         {cosine_sim:.4f}")
            print(f"      Fuzz Name:      {fuzz_name:.4f}")
            if acronym and candidate.get('acronym'):
                print(f"      Fuzz Acronym:   {fuzz_acronym:.4f}")
            print(f"      Score Final:    {combined_score:.4f}")
            print()
        
        if combined_score > best_score:
            best_score = combined_score
            best_match = candidate
            best_match['final_score'] = combined_score
            best_match['fuzz_name_score'] = fuzz_name
            best_match['fuzz_acronym_score'] = fuzz_acronym
    
    if verbose:
        print("=" * 80)
        print("✅ MEJOR MATCH")
        print("=" * 80)
        print(f"Institución:    {best_match['name']}")
        print(f"Acrónimo:       {best_match['acronym'] or 'N/A'}")
        print(f"Tipo:           {best_match['institution_type'] or 'N/A'}")
        print(f"Países:         {', '.join(best_match['countries']) if best_match['countries'] else 'N/A'}")
        print(f"Website:        {best_match['website'] or 'N/A'}")
        print(f"Score Final:    {best_match['final_score']:.4f}")
        print("=" * 80)
        print()
    
    return best_match


def main():
    """Ejemplos de búsqueda"""
    
    print("\n")
    print("🚀 EJEMPLOS DE BÚSQUEDA HÍBRIDA")
    print("\n")
    
    # Ejemplo 1: Solo nombre
    print("\n" + "=" * 80)
    print("EJEMPLO 1: Búsqueda por nombre")
    print("=" * 80)
    result1 = search_institution_hybrid(
        partner_name="Wageningen University and Research Centre",
        threshold=0.3
    )
    
    # Ejemplo 2: Nombre + acrónimo
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Búsqueda por nombre + acrónimo")
    print("=" * 80)
    result2 = search_institution_hybrid(
        partner_name="World Resources Institute",
        acronym="WRI",
        threshold=0.3
    )
    
    # Ejemplo 3: Nombre parcial
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Búsqueda con nombre parcial")
    print("=" * 80)
    result3 = search_institution_hybrid(
        partner_name="University of Cambridge",
        threshold=0.3
    )
    
    # Ejemplo 4: Búsqueda difícil
    print("\n" + "=" * 80)
    print("EJEMPLO 4: Búsqueda con variación de nombre")
    print("=" * 80)
    result4 = search_institution_hybrid(
        partner_name="MIT",
        acronym="MIT",
        threshold=0.2
    )


if __name__ == "__main__":
    # Verificar que la tabla tenga datos
    from src.supabase_client import count_institutions
    
    count = count_institutions()
    
    if count == 0:
        print("❌ La tabla está vacía. Ejecuta primero: python populate_clarisa_db.py")
    else:
        print(f"✅ Base de datos lista: {count} instituciones")
        main()
