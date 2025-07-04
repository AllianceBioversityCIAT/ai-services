from app.llm.vectorize_db import run_pipeline
from app.llm.knowledge_base import query_knowledge_base
from app.llm.vectorize_os import run_pipeline as run_pipeline_os

indicator = "IPI 1.1"
year = "2025"

vector_database = "knowledgebase"  # Options: "knowledgebase", "opensearch", "supabase"

if __name__ == "__main__":
    if vector_database == "knowledgebase":
        query_knowledge_base(indicator, year)
    elif vector_database == "opensearch":
        run_pipeline_os(indicator, year)
    elif vector_database == "supabase":
        run_pipeline(indicator, year)
    else:
        raise ValueError("Invalid vector database option. Choose from 'knowledgebase', 'opensearch', or 'supabase'.")