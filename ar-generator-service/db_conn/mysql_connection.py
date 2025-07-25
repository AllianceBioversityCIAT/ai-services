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
        logger.info("📂 Loading data...")

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
            id_column = df.columns[0]
            indicator_column = 'indicator_acronym'
            cluster_column = 'cluster_acronym'

            df_grouped = df.groupby([id_column, indicator_column, cluster_column]).agg(
                lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notnull(v) and v != "")))
            )
            df = df_grouped.reset_index()
                        
        return df

    except Exception as e:
        logger.error(f"❌ Error while loading data from table {table_name}: {e}")
        return pd.DataFrame()