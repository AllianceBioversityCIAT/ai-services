import os
import re
import json
import boto3
import psycopg2
import unicodedata
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger

load_dotenv()
logger = get_logger()

USER = os.getenv("SUPABASE_USER")
PASSWORD = os.getenv("SUPABASE_PASSWORD")
HOST = os.getenv("SUPABASE_HOST")
PORT = os.getenv("SUPABASE_PORT")
DBNAME = os.getenv("SUPABASE_DB")


bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1' 
)


def get_connection():
    return psycopg2.connect(
        dbname=DBNAME,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT
    )


def initialize_supabase_tables():
    try:
        logger.info("🛠️ Checking or creating `reference_embeddings` and `temp_embeddings` tables...")
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS reference_embeddings (
                id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                text TEXT,
                vector VECTOR(1024),
                is_reference BOOLEAN,
                document_name TEXT
            );

            CREATE TABLE IF NOT EXISTS temp_embeddings (
                id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                text TEXT,
                vector VECTOR(1024),
                is_reference BOOLEAN,
                document_name TEXT
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ Supabase tables ready!")

    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise


def get_embedding(text):
    try:
        request_body = {
            "inputText": text
        }
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response['body'].read())
        embeddings = response_body['embedding']
        
        return embeddings
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        raise


def store_reference_embeddings(chunks, embeddings):
    """Check if reference table already exists in the database"""
    try:
        logger.info("💾 Storing reference embeddings in Supabase (PostgreSQL)...")
        conn = get_connection()
        cur = conn.cursor()

        data = [
            (chunks, embeddings, True, None)
        ]
        execute_values(cur, """
            INSERT INTO reference_embeddings (text, vector, is_reference, document_name)
            VALUES %s
        """, data)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error storing reference embeddings: {str(e)}")
        raise


def store_temp_embeddings(chunks, embeddings, file_key):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        s_file_key = normalize_filename(file_key)
        document_name = f"{s_file_key}_{timestamp}"

        logger.info("💾 Storing temporary document embeddings in Supabase (PostgreSQL)...")
        conn = get_connection()
        cur = conn.cursor()

        data = [
            (chunk, embedding, False, document_name)
            for chunk, embedding in zip(chunks, embeddings)
        ]
        
        execute_values(cur, """
            INSERT INTO temp_embeddings (text, vector, is_reference, document_name)
            VALUES %s
        """, data)
        conn.commit()
        cur.close()
        conn.close()

        return document_name
    except Exception as e:
            logger.error(f"❌ Error storing temporary embeddings: {str(e)}")
            raise


def get_all_reference_data():
    try:
        logger.info("📚 Retrieving all reference data from Supabase...")
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT text FROM reference_embeddings WHERE is_reference = TRUE")
        results = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        logger.info(f"✅ Retrieved {len(results)} reference records")
        return results

    except Exception as e:
        logger.error(f"❌ Error retrieving all reference data: {str(e)}")
        raise


def normalize_filename(filename):
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('utf-8')
    filename = filename.lower().replace(" ", "_")
    filename = re.sub(r'[^a-z0-9_\-\.]', '', filename)
    
    return filename


def get_relevant_chunk(query, document_name, top_k=50):
    try:
        logger.info("🔍 Searching for relevant fragment in Supabase...")
        query_embedding = get_embedding(query)
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT text
            FROM temp_embeddings
            WHERE is_reference = FALSE AND document_name = %s
            ORDER BY vector <-> %s
            LIMIT %s
        """, (document_name, f"[{', '.join(map(str, query_embedding))}]", top_k))

        results = [row[0] for row in cur.fetchall()]

        cur.execute("DROP TABLE IF EXISTS temp_embeddings")
        conn.commit()

        cur.close()
        conn.close()

        return results

    except Exception as e:
        logger.error(f"❌ Error retrieving relevant chunk: {str(e)}")
        raise