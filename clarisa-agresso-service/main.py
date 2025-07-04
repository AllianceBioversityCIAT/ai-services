from app.mapping.mapping_supabase import main_supabase
from app.mapping.mapping_opensearch import main_opensearch

db = "supabase"

if __name__ == "__main__":
    if db == "supabase":
        main_supabase()
    elif db == "opensearch":
        main_opensearch()
    else:
        print("Invalid database choice. Please choose 'supabase' or 'opensearch'.")
        exit(1)