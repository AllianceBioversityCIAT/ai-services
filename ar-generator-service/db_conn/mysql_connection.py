import pandas as pd
from sqlalchemy import create_engine, inspect, text
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import MYSQL_DATABASE_URL

logger = get_logger()


def load_data(table_name):
    try:
        engine = create_engine(MYSQL_DATABASE_URL)
        
        logger.info(f"🔍 Inspecting the table: {table_name}")
        
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            logger.info(f"📊 Number of records: {count}")

        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        logger.info(f"Columns in {table_name}: {df.columns.tolist()}")
                        
        return df

    except Exception as e:
        logger.error(f"❌ Error while loading data from table {table_name}: {e}")
        return pd.DataFrame()