"""
Main pipeline for mapping institutions from CGSpace → CLARISA
Reads an Excel file, searches for each institution in CLARISA using hybrid search
(vector embeddings + RapidFuzz) and generates a report with the results
"""
import os
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from rapidfuzz import fuzz

# Import project modules
from src.embeddings import get_embedding, embedding_to_list, cosine_similarity
from src.supabase_client import search_by_name_embedding, search_combined, count_institutions
from src.utils import clean_text_for_matching

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
THRESHOLD_EMBEDDINGS = 0.3  # Threshold for vector search (lower = more candidates)
THRESHOLD_FINAL = 0.5       # Threshold to consider a valid match (final score)
NAME_WEIGHT = 0.7           # Weight of name in combined search (0-1)
ACRONYM_WEIGHT = 0.3        # Weight of acronym in combined search (0-1)
COSINE_WEIGHT = 0.50        # Weight of cosine similarity in final score
FUZZ_NAME_WEIGHT = 0.40     # Weight of RapidFuzz name in final score
FUZZ_ACRONYM_WEIGHT = 0.10  # Weight of RapidFuzz acronym in final score


# ============================================================================
# HYBRID SEARCH FUNCTION
# ============================================================================

def search_institution_for_excel(partner_name, acronym=None):
    """
    Search for an institution using hybrid search (embeddings + RapidFuzz)
    Optimized for batch processing from Excel
    
    Args:
        partner_name: Institution name
        acronym: Optional acronym
        
    Returns:
        dict: Result with best match and scores, or None if no match
    """
    # Validate input
    if not partner_name or str(partner_name).lower() in ['nan', 'none', '']:
        return None
    
    partner_name = str(partner_name).strip()
    acronym = str(acronym).strip() if acronym and str(acronym).lower() not in ['nan', 'none', ''] else None
    
    # STEP 1: Generate query embeddings
    name_embedding = get_embedding(partner_name)
    name_embedding_list = embedding_to_list(name_embedding)
    
    # STEP 2: Vector search in Supabase (Top 5)
    if acronym:
        # Combined search (name + acronym)
        acronym_embedding = get_embedding(acronym)
        acronym_embedding_list = embedding_to_list(acronym_embedding)
        
        candidates = search_combined(
            name_embedding=name_embedding_list,
            acronym_embedding=acronym_embedding_list,
            name_weight=NAME_WEIGHT,
            acronym_weight=ACRONYM_WEIGHT,
            threshold=THRESHOLD_EMBEDDINGS,
            limit=5
        )
    else:
        # By name only
        candidates = search_by_name_embedding(
            query_embedding=name_embedding_list,
            threshold=THRESHOLD_EMBEDDINGS,
            limit=5
        )
    
    if not candidates:
        return None
    
    # STEP 3: Tiebreak with RapidFuzz
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        # Cosine similarity (already calculated by Supabase)
        cosine_sim = candidate.get('similarity', candidate.get('combined_similarity', 0))
        
        # Text similarity with RapidFuzz (normalized)
        normalized_query = clean_text_for_matching(partner_name)
        normalized_candidate = clean_text_for_matching(candidate['name'])
        fuzz_name = fuzz.ratio(normalized_query, normalized_candidate) / 100
        
        # If there's an acronym, compare it too
        fuzz_acronym = 0
        if acronym and candidate.get('acronym'):
            normalized_query_acronym = clean_text_for_matching(acronym)
            normalized_candidate_acronym = clean_text_for_matching(candidate['acronym'])
            fuzz_acronym = fuzz.ratio(normalized_query_acronym, normalized_candidate_acronym) / 100
        
        # Combined final score
        combined_score = (
            COSINE_WEIGHT * cosine_sim +
            FUZZ_NAME_WEIGHT * fuzz_name +
            FUZZ_ACRONYM_WEIGHT * fuzz_acronym
        )
        
        if combined_score > best_score:
            best_score = combined_score
            best_match = {
                'clarisa_id': candidate['clarisa_id'],
                'name': candidate['name'],
                'acronym': candidate.get('acronym', ''),
                'website': candidate.get('website', ''),
                'countries': candidate.get('countries', []),
                'institution_type': candidate.get('institution_type', ''),
                'cosine_similarity': cosine_sim,
                'fuzz_name_score': fuzz_name,
                'fuzz_acronym_score': fuzz_acronym,
                'final_score': combined_score
            }
    
    return best_match if best_score >= THRESHOLD_FINAL else None


# ============================================================================
# MAIN PIPELINE
# ============================================================================


def run_pipeline(excel_path):
    """
    Main pipeline: processes an Excel file with institutions and maps them to CLARISA
    
    Args:
        excel_path: Path to Excel file
        
    Expected Excel format:
        - Column 0: ID (optional)
        - Column 1: partner_name
        - Column 2: acronym
        - Additional columns are preserved in the output
    """
    print("=" * 80)
    print("🚀 MAPPING PIPELINE: CGSpace → CLARISA")
    print("=" * 80)
    print()
    
    # Verify that the DB has data
    print("🔍 Verifying CLARISA database...")
    total_institutions = count_institutions()
    
    if total_institutions == 0:
        print("❌ Error: The database is empty.")
        print("   Run first: python populate_clarisa_db.py")
        return
    
    print(f"✅ Database ready: {total_institutions:,} institutions in CLARISA")
    print()
    
    # Load Excel
    print(f"📊 Loading Excel file: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
        print(f"✅ {len(df)} rows loaded")
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return
    
    # Verify columns
    if len(df.columns) < 3:
        print(f"❌ Error: Excel must have at least 3 columns")
        print(f"   Format: [ID, Name, Acronym, ...]")
        print(f"   Found: {len(df.columns)} columns")
        return
    
    print()
    print("⚙️  CONFIGURATION:")
    print(f"   - Threshold embeddings: {THRESHOLD_EMBEDDINGS}")
    print(f"   - Threshold final:      {THRESHOLD_FINAL}")
    print(f"   - Name/acronym weight:  {NAME_WEIGHT}/{ACRONYM_WEIGHT}")
    print(f"   - Final score:          {COSINE_WEIGHT*100:.0f}% cosine + {FUZZ_NAME_WEIGHT*100:.0f}% fuzz_name + {FUZZ_ACRONYM_WEIGHT*100:.0f}% fuzz_acronym")
    print()
    
    # Process each row
    print(f"🔄 Processing {len(df)} institutions...")
    print()
    
    results = {
        'match_found': [],
        'clarisa_id': [],
        'clarisa_name': [],
        'clarisa_acronym': [],
        'clarisa_countries': [],
        'clarisa_type': [],
        'clarisa_website': [],
        'cosine_similarity': [],
        'fuzz_name_score': [],
        'fuzz_acronym_score': [],
        'final_score': [],
        'match_quality': []  # 'excellent', 'good', 'fair', 'no_match'
    }
    
    stats = {
        'matched': 0,
        'no_match': 0,
        'errors': 0
    }
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Searching matches"):
        # Read name and acronym from Excel
        # Assuming: column 1 = partner_name, column 2 = acronym
        partner_name = row.iloc[1] if len(row) > 1 else None
        acronym = row.iloc[2] if len(row) > 2 else None
        
        try:
            # Search for match
            match = search_institution_for_excel(partner_name, acronym)
            
            if match:
                # Match found
                results['match_found'].append(True)
                results['clarisa_id'].append(match['clarisa_id'])
                results['clarisa_name'].append(match['name'])
                results['clarisa_acronym'].append(match['acronym'] or '')
                results['clarisa_countries'].append(', '.join(match['countries']) if match['countries'] else '')
                results['clarisa_type'].append(match['institution_type'] or '')
                results['clarisa_website'].append(match['website'] or '')
                results['cosine_similarity'].append(round(match['cosine_similarity'], 4))
                results['fuzz_name_score'].append(round(match['fuzz_name_score'], 4))
                results['fuzz_acronym_score'].append(round(match['fuzz_acronym_score'], 4))
                results['final_score'].append(round(match['final_score'], 4))
                
                # Determine match quality
                score = match['final_score']
                if score >= 0.85:
                    quality = 'excellent'
                elif score >= 0.70:
                    quality = 'good'
                else:
                    quality = 'fair'
                results['match_quality'].append(quality)
                
                stats['matched'] += 1
            else:
                # No match
                results['match_found'].append(False)
                results['clarisa_id'].append('')
                results['clarisa_name'].append('')
                results['clarisa_acronym'].append('')
                results['clarisa_countries'].append('')
                results['clarisa_type'].append('')
                results['clarisa_website'].append('')
                results['cosine_similarity'].append(0)
                results['fuzz_name_score'].append(0)
                results['fuzz_acronym_score'].append(0)
                results['final_score'].append(0)
                results['match_quality'].append('no_match')
                
                stats['no_match'] += 1
                
        except Exception as e:
            # Error processing
            print(f"\n⚠️  Error in row {idx}: {e}")
            results['match_found'].append(False)
            results['clarisa_id'].append('ERROR')
            results['clarisa_name'].append(str(e))
            results['clarisa_acronym'].append('')
            results['clarisa_countries'].append('')
            results['clarisa_type'].append('')
            results['clarisa_website'].append('')
            results['cosine_similarity'].append(0)
            results['fuzz_name_score'].append(0)
            results['fuzz_acronym_score'].append(0)
            results['final_score'].append(0)
            results['match_quality'].append('error')
            
            stats['errors'] += 1
    
    # Add results to DataFrame
    df['MATCH_FOUND'] = results['match_found']
    df['CLARISA_ID'] = results['clarisa_id']
    df['CLARISA_NAME'] = results['clarisa_name']
    df['CLARISA_ACRONYM'] = results['clarisa_acronym']
    df['CLARISA_COUNTRIES'] = results['clarisa_countries']
    df['CLARISA_TYPE'] = results['clarisa_type']
    df['CLARISA_WEBSITE'] = results['clarisa_website']
    df['COSINE_SIMILARITY'] = results['cosine_similarity']
    df['FUZZ_NAME_SCORE'] = results['fuzz_name_score']
    df['FUZZ_ACRONYM_SCORE'] = results['fuzz_acronym_score']
    df['FINAL_SCORE'] = results['final_score']
    df['MATCH_QUALITY'] = results['match_quality']
    
    # Save results
    output_file = "clarisa_mapping_results.xlsx"
    df.to_excel(output_file, index=False)
    
    print()
    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(f"✅ File saved: {output_file}")
    print()
    print(f"📈 Statistics:")
    print(f"   Total processed:      {len(df):,}")
    print(f"   ✅ Successful matches: {stats['matched']:,} ({stats['matched']/len(df)*100:.1f}%)")
    print(f"   ❌ No match:           {stats['no_match']:,} ({stats['no_match']/len(df)*100:.1f}%)")
    print(f"   ⚠️  Errors:             {stats['errors']:,}")
    print()
    
    # Breakdown by quality
    if stats['matched'] > 0:
        excellent = sum(1 for q in results['match_quality'] if q == 'excellent')
        good = sum(1 for q in results['match_quality'] if q == 'good')
        fair = sum(1 for q in results['match_quality'] if q == 'fair')
        
        print(f"🏆 Match quality:")
        print(f"   Excellent (≥0.85): {excellent:,} ({excellent/stats['matched']*100:.1f}%)")
        print(f"   Good (≥0.70):      {good:,} ({good/stats['matched']*100:.1f}%)")
        print(f"   Fair (≥0.50):      {fair:,} ({fair/stats['matched']*100:.1f}%)")
        print()
    
    # Average scores
    if stats['matched'] > 0:
        matched_scores = [s for s, q in zip(results['final_score'], results['match_quality']) if q != 'no_match' and q != 'error']
        avg_score = sum(matched_scores) / len(matched_scores) if matched_scores else 0
        max_score = max(matched_scores) if matched_scores else 0
        min_score = min(matched_scores) if matched_scores else 0
        
        print(f"📊 Similarity scores:")
        print(f"   Average: {avg_score:.4f}")
        print(f"   Maximum: {max_score:.4f}")
        print(f"   Minimum: {min_score:.4f}")
        print()
    
    print("=" * 80)
    print("✅ PROCESS COMPLETED")
    print("=" * 80)
    print()


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    """
    Executes the mapping pipeline CGSpace → CLARISA
    
    Excel format:
        - Column 0: ID (optional)
        - Column 1: partner_name (REQUIRED)
        - Column 2: acronym (optional)
        - Other columns are preserved in the result
    
    Configuration:
        Adjust constants at the beginning of the file:
        - THRESHOLD_EMBEDDINGS: Threshold for vector search (default: 0.3)
        - THRESHOLD_FINAL: Threshold for valid match (default: 0.5)
        - NAME_WEIGHT / ACRONYM_WEIGHT: Weights in combined search
        - COSINE_WEIGHT / FUZZ_NAME_WEIGHT / FUZZ_ACRONYM_WEIGHT: Weights in final score
    """
    # Excel file to process
    excel_file = "File To Dani (1).xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Error: File '{excel_file}' not found")
        print()
        print("📝 Expected Excel format:")
        print("   Column 0: ID (optional)")
        print("   Column 1: partner_name (institution name)")
        print("   Column 2: acronym (acronym, optional)")
        print()
    else:
        run_pipeline(excel_file)