import re
# import pyodbc
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import MYSQL_DATABASE_URL, SQL_SERVER
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3, s3_file_exists

logger = get_logger()

server = SQL_SERVER['server']
database = SQL_SERVER['database']
client_id = SQL_SERVER['client_id']
client_secret = SQL_SERVER['client_secret']


def load_data(table_name):
    try:
        logger.info("📂 Loading data from MySQL...")

        ## SQL Server
        # conn_str = (
        #     "DRIVER={ODBC Driver 18 for SQL Server};"
        #     f"SERVER={server};"
        #     f"DATABASE={database};"
        #     "Encrypt=yes;"
        #     "TrustServerCertificate=yes;"
        #     "Authentication=ActiveDirectoryServicePrincipal;"
        #     f"UID={client_id};"
        #     f"PWD={client_secret};"
        # )

        # logger.info(f"🔍 Inspecting the table: {table_name}")
        # conn = pyodbc.connect(conn_str, timeout=10)

        # cur = conn.cursor()
        # result = cur.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
        # count = result.scalar()
        # logger.info(f"📊 Number of records: {count}")

        # df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        
        # cur.close()
        # conn.close()

        ## MySQL
        engine = create_engine(MYSQL_DATABASE_URL)
        
        logger.info(f"🔍 Inspecting the table: {table_name}")
        
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            logger.info(f"📊 Number of records: {count}")

        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        ## General processing
        logger.info(f"Columns in {table_name}: {df.columns.tolist()}")

        if table_name == "vw_ai_project_contribution":
            df.rename(columns={'Phase name': 'phase_name', 'Phase year': 'year'}, inplace=True)
            df.drop(['Milestone expected unit', 'Outcome Comunication', 'pk', 'contribution_pk'], axis=1, inplace=True)
        elif table_name == "vw_ai_questions":
            df.rename(columns={'project_id': 'cluster_id'}, inplace=True)
            df.drop('contribution_pk', axis=1, inplace=True)
        else:
            df.drop(['contribution_pk', 'Indicator', 'indicator_code', 'DLV_planned', 'image_small', 'updated_date'], axis=1, inplace=True)

        df.to_json(f'{table_name}.jsonl', orient='records', lines=True, force_ascii=False)
        df.to_csv(f'{table_name}.csv', index=False)

        file_key = f'aiccra/{table_name}.jsonl'
        if not s3_file_exists(file_key):
            upload_file_to_s3(file_key, f"{table_name}.jsonl")
        else:
            logger.info(f"⏭️  The file already exists in S3, it was not necessary to upload it: {file_key}")
                        
        return df

    except Exception as e:
        logger.error(f"❌ Error while loading data from table {table_name}: {e}")
        return pd.DataFrame()