#from app.llm.vectorize_os import run_pipeline
from app.llm.knowledge_base import query_knowledge_base

#indicator = "IPI 1.1"

if __name__ == "__main__":
    #run_pipeline(indicator)
    query = "Clearly state the indicator PDO 1 and its purpose."
    response = query_knowledge_base(query)
    print(response)