import requests
import pandas as pd
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import CLARISA_API_URL
from app.mapping.vectorize_db import create_collection_supabase, search_matches_supabase

logger = get_logger()


def read_agresso_excel(path):
    try:
        logger.info("📄 Reading Agresso institutions from Excel...")
        df = pd.read_excel(path)
        agresso_institutions = [
            {
                "id": row["agreso_institution_id"],
                "name": row["agreso_institucion_name"],
                "acronym": "",
                "url": ""
            }
            for _, row in df.iterrows()
        ]
        return agresso_institutions
    except Exception as e:
        logger.error(f"❌ Error reading Agresso Excel file: {e}")
        raise


def get_clarisa_institutions(api_url):
    try:
        logger.info("🌐 Obtaining data from CLARISA...")

        response = requests.get(api_url)
        response.raise_for_status()
        raw_data = response.json()

        institutions = []
        for inst in raw_data:
            institutions.append({
                "id": inst.get("code", None), 
                "name": inst.get("name", ""),
                "acronym": inst.get("acronym", ""),
                "url": inst.get("websiteLink", "")
            })
        
        return institutions
    except Exception as e:
        logger.error(f"❌ Error fetching CLARISA institutions: {e}")
        raise


def build_text(inst):
    return f"{inst['name']} ({inst.get('acronym', '')}) - {inst.get('url', '')}"


def save_results_to_excel(df, output_path="app/utils/resources/results_matches_sb.xlsx"):
    try:
        df.to_excel(output_path, index=False)
        logger.info(f"\n💾 Results saved as '{output_path}'")
    except Exception as e:
        logger.error(f"❌ Error saving results to Excel: {e}")


def main_supabase():
    try:
        agresso_institutions = read_agresso_excel("app/utils/resources/agresso_institution_list_20250512_MA.xlsx")        
        
        clarisa_data = get_clarisa_institutions(CLARISA_API_URL)
        clarisa_texts = [build_text(inst) for inst in clarisa_data]

        collection = create_collection_supabase(clarisa_texts, clarisa_data)

        results = search_matches_supabase(agresso_institutions, collection)

        df_matches = pd.DataFrame(results)

        save_results_to_excel(df_matches)

    except Exception as e:
        logger.error(f"❌ Error during main processing: {e}")
        return