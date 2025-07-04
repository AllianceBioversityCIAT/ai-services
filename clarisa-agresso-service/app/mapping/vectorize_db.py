import re
import json
import vecs
import boto3
import difflib
import numpy as np
import unicodedata
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import BR, SUPABASE_URL

logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1' 
)


def build_text(inst):
    return f"{inst['name']} ({inst.get('acronym', '')}) - {inst.get('url', '')}"


def clean_text(text):
    if not isinstance(text, str):
        return ""

    text = text.lower()

    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    text = re.sub(r"[^\w\s()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def similarity_sequence_matcher(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()
    

def get_embeddings_bedrock(text):
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
        embeddings = np.array(response_body["embedding"], dtype=np.float32)
        return embeddings
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        raise


def generate_batch_embeddings(texts, clarisa_data, start_index):
    batch_records = []

    for j, text in enumerate(texts):
        try:
            emb = get_embeddings_bedrock(text)
            batch_records.append((
                f"ref-{start_index + j}",
                emb,
                {"text": text, "id": clarisa_data[start_index + j]["id"]}
            ))
        except Exception as e:
            logger.error(f"❌ Skipping record {start_index + j} due to error: {e}")
    return batch_records


def insert_batches(collection, clarisa_texts, clarisa_data, batch_size=100):
    for i in range(0, len(clarisa_texts), batch_size):
        batch_texts = clarisa_texts[i:i + batch_size]
        records = generate_batch_embeddings(batch_texts, clarisa_data, i)
        if records:
            try:
                collection.upsert(records)
                logger.info(f"✅ Inserted batch {i}-{i + len(records) - 1}")
            except Exception as e:
                logger.error(f"❌ Error upserting batch {i}-{i + len(records) - 1}: {e}")


def create_collection_supabase(clarisa_texts, clarisa_data):
    try:
        vx = vecs.create_client(SUPABASE_URL)
        collection = vx.get_or_create_collection("clarisa_embeddings", dimension=1024)
        collection.create_index(measure=vecs.IndexMeasure.cosine_distance)

        if collection.query([0.0] * 1024, limit=1):
            logger.info("✅ Vectors already exist in Supabase")
        else:
            logger.info("🔢 Embedding and storing CLARISA vectors in Supabase...")
            insert_batches(collection, clarisa_texts, clarisa_data)
            collection.create_index(measure=vecs.IndexMeasure.cosine_distance)
            logger.info("✅ All vectors stored in Supabase.")
        
        return collection
    except Exception as e:
        logger.error(f"❌ Error creating collection in Supabase: {e}")
        raise


def search_matches_supabase(agresso_institutions, collection):
    try:
        logger.info("🔍 Seeking matches for Agresso's institutions...")
        results = []

        for agresso in agresso_institutions:
            agresso_text = build_text(agresso)
            agresso_emb = get_embeddings_bedrock(agresso_text)

            match = collection.query(agresso_emb, limit=1, include_metadata=True, include_value=True)

            for ref_id, distance, metadata in match:
                clarisa_name = metadata.get("text", "").split(" - ")[0]
                textual_score = similarity_sequence_matcher(
                    clean_text(agresso["name"]),
                    clean_text(clarisa_name)
                )

                results.append({
                    "Agresso Institution": agresso_text.split(" () ")[0],
                    "Match CLARISA": clarisa_name,
                    "ID CLARISA": metadata.get("id", ""),
                    "Cosine Distance": round(distance, 4),
                    "Textual Score": round(textual_score, 4)
                })

        return results
    except Exception as e:
        logger.error(f"❌ Error searching matches in Supabase: {e}")
        raise