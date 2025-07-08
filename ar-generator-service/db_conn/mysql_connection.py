import pymssql
import pandas as pd
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import SQL_SERVER
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3, s3_file_exists

logger = get_logger()

server = SQL_SERVER['server']
database = SQL_SERVER['database']
client_id = SQL_SERVER['client_id']
client_secret = SQL_SERVER['client_secret']


def load_data(table_name):
    try:
        logger.info("📂 Loading data...")

        ## SQL Server
        conn = pymssql.connect(
            server=server,
            user=client_id,
            password=client_secret,
            database=database,
            timeout=30,
            login_timeout=30
        )

        CREATE_VIEW_QUERIES = {
            "vw_aiccra_project_contribution": """
                CREATE OR ALTER VIEW vw_aiccra_project_contribution AS
                SELECT pc.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title
                FROM AICCRA_fact_project_contribution pc
                LEFT JOIN AICCRA_dim_clusters cl ON cl.id = pc.cluster_id
                LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = pc.indicator_pk;
            """,
            "vw_aiccra_question": """
                CREATE OR ALTER VIEW vw_aiccra_question AS
                SELECT fq.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title
                FROM AICCRA_fact_indicator_questions fq
                LEFT JOIN AICCRA_dim_clusters cl ON cl.id = fq.project_id
                LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = fq.indicator_pk;
            """,
            "vw_aiccra_deliverables": """
                CREATE OR ALTER VIEW vw_aiccra_deliverables AS
                SELECT fd.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title, ins.acronym AS institution_acronym, ins.name, ins.typeG AS institution_type, loc.country_name, loc.region_name  
                FROM AICCRA_fact_deliverables fd
                LEFT JOIN AICCRA_dim_clusters cl ON cl.id = fd.cluster_id
                LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = fd.indicator_pk
                LEFT JOIN AICCRA_dim_institutions ins ON ins.id = fd.institution_id 
                LEFT JOIN AICCRA_dim_locations loc ON loc.id = fd.location_id;
            """
        }

        cursor = conn.cursor()
        
        for view_name, view_sql in CREATE_VIEW_QUERIES.items():
            logger.info(f"🛠️ Creating or altering view: {view_name}")
            cursor.execute(view_sql)
        
        conn.commit()
        
        logger.info(f"🔍 Inspecting the table: {table_name}")
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        logger.info(f"📊 Number of records: {count}")
        
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        
        conn.close()

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