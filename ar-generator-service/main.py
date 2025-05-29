from app.llm.vectorize_os import run_pipeline
#from db_conn.mysql_connection import load_data

indicator = "IPI 1.1"

if __name__ == "__main__":
    #load_data()
    run_pipeline(indicator)