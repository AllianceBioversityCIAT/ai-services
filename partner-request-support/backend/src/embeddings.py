"""
Module to generate embeddings using Amazon Bedrock Titan
"""
import os
import json
import boto3
import numpy as np
from typing import Union, List
from config.config_util import BR
from logger.logger_util import get_logger

logger = get_logger()

bedrock = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)

MODEL_EMBED = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024


def get_embedding(text: str, normalize: bool = False) -> np.ndarray:
    """
    Generates embedding using Amazon Bedrock Titan
    
    Args:
        text: Text to generate embedding
        normalize: If True, applies basic cleaning (spaces). 
                   Default False to keep original text.
        
    Returns:
        np.ndarray: Embedding vector (1024 dimensions)
    """
    if not text or not isinstance(text, str) or text.strip() == "":
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    cleaned_text = ' '.join(text.split()).strip()
    
    try:
        body = json.dumps({
            "inputText": cleaned_text
        })
        
        response = bedrock.invoke_model(
            modelId=MODEL_EMBED,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        embedding = np.array(response_body["embedding"], dtype=np.float32)
        
        return embedding

    except Exception as e:
        logger.error(f"❌ Error generating embedding: {e}")
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)


def get_embeddings_batch(texts: List[str]) -> List[np.ndarray]:
    """
    Generates embeddings for multiple texts
    
    Args:
        texts: List of texts
        
    Returns:
        List[np.ndarray]: List of embedding vectors
    """
    embeddings = []
    
    for text in texts:
        embedding = get_embedding(text)
        embeddings.append(embedding)
    
    return embeddings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculates cosine similarity between two vectors
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        float: Cosine similarity (0.0 - 1.0)
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))


def embedding_to_list(embedding: np.ndarray) -> List[float]:
    """
    Converts a numpy embedding to a Python list for storing in the DB
    
    Args:
        embedding: Numpy vector
        
    Returns:
        List[float]: List of floats
    """
    return embedding.tolist()


def list_to_embedding(embedding_list: Union[List[float], str]) -> np.ndarray:
    """
    Converts a list or JSON string to a numpy vector
    
    Args:
        embedding_list: List of floats or JSON string
        
    Returns:
        np.ndarray: Embedding vector
    """
    if isinstance(embedding_list, str):
        embedding_list = json.loads(embedding_list)
    
    return np.array(embedding_list, dtype=np.float32)
