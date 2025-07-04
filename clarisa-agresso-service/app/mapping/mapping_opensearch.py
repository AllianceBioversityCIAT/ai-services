import requests
import pandas as pd
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import CLARISA_BEARER_TOKEN

logger = get_logger()


def read_agresso_excel(path):
    try:
        logger.info("📄 Reading Agresso institutions from Excel...")
        df = pd.read_excel(path)
        agresso_institutions = [
            {
                "id": row["agreso_institution_id"],
                "name": row["agreso_institucion_name"]
            }
            for _, row in df.iterrows()
        ]
        return agresso_institutions
    except Exception as e:
        logger.error(f"❌ Error reading Agresso Excel file: {e}")
        raise


def build_text(inst):
    return f"{inst['name']}"


def search_matches_opensearch(agresso_institutions, bearer_token):
    logger.info("🔍 Seeking matches for Agresso's institutions...")
    results = []

    for agresso in agresso_institutions:
        agresso_text = build_text(agresso)

        try:
            response = requests.get(
                "https://api.clarisa.cgiar.org/integration/open-search/institutions/search",
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "accept": "*/*"
                },
                params={
                    "query": agresso_text,
                    "sample-size": 1
                }
            )
            response.raise_for_status()
            result = response.json()

            if result and isinstance(result, list):
                best_match = result[0]
                results.append({
                    "Agresso Institution": agresso_text,
                    "Match CLARISA": best_match.get("name", ""),
                    "Acronym": best_match.get("acronym", ""),
                    "ID CLARISA": best_match.get("code", ""),
                    "Score": round(best_match.get("score", 0), 4)
                })
            else:
                results.append({
                    "Agresso Institution": agresso_text,
                    "Match CLARISA": "",
                    "Acronym": "",
                    "ID CLARISA": "",
                    "Score": ""
                })
        except Exception as e:
            logger.error(f"❌ Error fetching match for '{agresso_text}': {e}")
            results.append({
                "Agresso Institution": agresso_text,
                "Match CLARISA": "ERROR",
                "Acronym": "",
                "ID CLARISA": "",
                "Score": ""
                })

    return results


def save_results_to_excel(df, output_path="app/utils/resources/results_matches_os.xlsx"):
    try:
        df.to_excel(output_path, index=False)
        logger.info(f"\n💾 Results saved as '{output_path}'")
    except Exception as e:
        logger.error(f"❌ Error saving results to Excel: {e}")


def main_opensearch():
    try:
        agresso_institutions = read_agresso_excel("app/utils/resources/agresso_institution_list_20250512_MA.xlsx")
    
        results = search_matches_opensearch(agresso_institutions, CLARISA_BEARER_TOKEN)

        df_matches = pd.DataFrame(results)

        save_results_to_excel(df_matches)

    except Exception as e:
        logger.error(f"❌ Error during main processing: {e}")
        return