import pyodbc
import pandas as pd
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import SQL_SERVER
from app.utils.s3.divide_jsonl_files import split_jsonl_to_individual_files

logger = get_logger()

server = SQL_SERVER['server']
database = SQL_SERVER['database']
client_id = SQL_SERVER['client_id']
client_secret = SQL_SERVER['client_secret']


CREATE_VIEW_QUERIES = {
    "vw_ai_project_contribution": """
        CREATE OR ALTER VIEW vw_ai_project_contribution AS
        SELECT pc.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title
        FROM AICCRA_fact_project_contribution pc
        LEFT JOIN AICCRA_dim_clusters cl ON cl.id = pc.cluster_id
        LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = pc.indicator_pk;
    """,
    "vw_ai_questions": """
        CREATE OR ALTER VIEW vw_ai_questions AS
        SELECT fq.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title
        FROM AICCRA_fact_indicator_questions fq
        LEFT JOIN AICCRA_dim_clusters cl ON cl.id = fq.project_id
        LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = fq.indicator_pk;
    """,
    "vw_ai_deliverables": """
        CREATE OR ALTER VIEW vw_ai_deliverables AS
        SELECT fd.*, cl.acronym AS cluster_acronym, cl.title AS cluster_name, ind.acronym AS indicator_acronym, ind.title AS indicator_title, ins.acronym AS institution_acronym, ins.name, ins.typeG AS institution_type, loc.country_name, loc.region_name  
        FROM AICCRA_fact_deliverables fd
        LEFT JOIN AICCRA_dim_clusters cl ON cl.id = fd.cluster_id
        LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = fd.indicator_pk
        LEFT JOIN AICCRA_dim_institutions ins ON ins.id = fd.institution_id 
        LEFT JOIN AICCRA_dim_locations loc ON loc.id = fd.location_id;
    """,
    "vw_ai_oicrs": """
        CREATE OR ALTER VIEW vw_ai_oicrs AS
        SELECT oicrs.*, ind.title AS indicator_title, ind.acronym AS indicator_acronym, loc.country_name AS country_name, ins.name AS institution_name, ins.short_name AS institution_short_name
        FROM AICCRA_aiccrabi_aiccra_oicrs oicrs
        LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = oicrs.indicator_pk
        LEFT JOIN AICCRA_dim_locations loc ON loc.id = oicrs.country_id 
        LEFT JOIN AICCRA_dim_institutions ins ON ins.id = oicrs.institution_id;
    """,
    "vw_ai_innovations": """
        CREATE OR ALTER VIEW vw_ai_innovations AS
        SELECT inno.*, ind.title AS indicator_title, ind.acronym AS indicator_acronym, loc.country_name AS country_name
        FROM AICCRA_aiccrabi_aiccra_innovations inno
        LEFT JOIN AICCRA_dim_indicators ind ON ind.indicator_pk = inno.indicator_pk
        LEFT JOIN AICCRA_dim_locations loc ON loc.id = inno.country_id;
    """
}


def load_full_data(table_name):
    try:
        logger.info("📂 Loading full data...")

        ## SQL Server
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "Authentication=ActiveDirectoryServicePrincipal;"
            f"UID={client_id};"
            f"PWD={client_secret};"
        )

        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
        
            for view_name, view_sql in CREATE_VIEW_QUERIES.items():
                logger.info(f"🛠️ Creating or altering view: {view_name}")
                cursor.execute(view_sql)
            
            conn.commit()
            logger.info("✅ All views created successfully")
            
            logger.info(f"🔍 Inspecting the table: {table_name}")
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"📊 Number of records: {count}")
            
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)

        ## General processing
        logger.info(f"Columns in {table_name}: {df.columns.tolist()}")

        if table_name == "vw_ai_project_contribution":
            df.rename(columns={'Phase name': 'phase_name', 'Phase year': 'year'}, inplace=True)
            df = df.dropna(axis=1, how='all')
            df["table_type"] = "contributions"
        
        elif table_name == "vw_ai_questions":
            df = df.dropna(axis=1, how='all')
            df["table_type"] = "questions"

        elif table_name == "vw_ai_deliverables":
            df = df.dropna(axis=1, how='all')
            id_column = df.columns[0]
            indicator_column = 'indicator_acronym'
            cluster_column = 'cluster_acronym'
            df_grouped = df.groupby([id_column, indicator_column, cluster_column]).agg(
                lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notnull(v) and v != "")))
            )
            df = df_grouped.reset_index()
            df["table_type"] = "deliverables"
        
        elif table_name == "vw_ai_oicrs":
            df.rename(columns={'link_pdf_file': 'link_pdf_oicr', 'oicr_year': 'year'}, inplace=True)
            df = df.dropna(axis=1, how='all')
            id_column = df.columns[0]
            indicator_column = 'indicator_acronym'
            cluster_column = 'cluster_acronym'
            df_grouped = df.groupby([id_column, indicator_column, cluster_column]).agg(
                lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notnull(v) and v != "")))
            )
            df = df_grouped.reset_index()
            df["table_type"] = "oicrs"
        
        else:
            df.rename(columns={'link_pdf_file': 'link_pdf_innovation'}, inplace=True)
            df = df.dropna(axis=1, how='all')
            id_column = df.columns[0]
            indicator_column = 'indicator_acronym'
            cluster_column = 'cluster_acronym'
            df_grouped = df.groupby([id_column, indicator_column, cluster_column]).agg(
                lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notnull(v) and v != "")))
            )
            df = df_grouped.reset_index()
            df["table_type"] = "innovations"

        df.to_json(f'{table_name}.jsonl', orient='records', lines=True, force_ascii=False)
        df.to_csv(f'{table_name}.csv', index=False)

        split_jsonl_to_individual_files(f'{table_name}.jsonl')
        
        return df

    except Exception as e:
        logger.error(f"❌ Error while loading full data from table {table_name}: {e}")
        return pd.DataFrame()