"""
Módulo para generar embeddings usando Amazon Bedrock Titan
"""
import os
import json
import boto3
import numpy as np
from typing import Union, List
from config.config_util import BR


# Cliente de Bedrock
bedrock = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)

MODEL_EMBED = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024  # Titan v2 genera vectores de 1024 dimensiones


def get_embedding(text: str, normalize: bool = False) -> np.ndarray:
    """
    Genera embedding usando Amazon Bedrock Titan
    
    Args:
        text: Texto para generar embedding
        normalize: Si True, aplica limpieza básica (espacios). 
                   Default False para mantener texto original.
        
    Returns:
        np.ndarray: Vector de embedding (1024 dimensiones)
    """
    if not text or not isinstance(text, str) or text.strip() == "":
        # Retorna un vector cero si el texto está vacío
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    
    # Limpieza básica: solo espacios múltiples y trim
    # NO removemos acentos ni lowercase para embeddings semánticos
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
        print(f"❌ Error generando embedding: {e}")
        return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)


def get_embeddings_batch(texts: List[str]) -> List[np.ndarray]:
    """
    Genera embeddings para múltiples textos
    
    Args:
        texts: Lista de textos
        
    Returns:
        List[np.ndarray]: Lista de vectores de embedding
    """
    embeddings = []
    
    for text in texts:
        embedding = get_embedding(text)
        embeddings.append(embedding)
    
    return embeddings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcula similitud coseno entre dos vectores
    
    Args:
        a: Primer vector
        b: Segundo vector
        
    Returns:
        float: Similitud coseno (0.0 - 1.0)
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))


def embedding_to_list(embedding: np.ndarray) -> List[float]:
    """
    Convierte un embedding numpy a lista de Python para guardar en DB
    
    Args:
        embedding: Vector numpy
        
    Returns:
        List[float]: Lista de floats
    """
    return embedding.tolist()


def list_to_embedding(embedding_list: Union[List[float], str]) -> np.ndarray:
    """
    Convierte una lista o string JSON a vector numpy
    
    Args:
        embedding_list: Lista de floats o string JSON
        
    Returns:
        np.ndarray: Vector de embedding
    """
    if isinstance(embedding_list, str):
        embedding_list = json.loads(embedding_list)
    
    return np.array(embedding_list, dtype=np.float32)
