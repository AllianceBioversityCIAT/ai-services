import boto3
from typing import Any
from botocore.exceptions import ClientError
from app.utils.config.config_util import S3_VECTORS
from app.utils.logger.logger_util import get_logger
from app.vector_store.schemas import NON_FILTERABLE_METADATA_KEYS, chunk_from_vector_metadata

logger = get_logger()

_client_instance = None


class S3VectorsClient:
    def __init__(self, bucket: str, index: str, region: str):
        self.bucket = bucket
        self.index = index
        self.region = region
        self._client = boto3.client("s3vectors", region_name=region)

    def get_index(self) -> dict | None:
        try:
            return self._client.get_index(
                vectorBucketName=self.bucket,
                indexName=self.index,
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "NotFoundException":
                return None
            raise

    def create_index(self, dimension: int = 1024) -> None:
        logger.info(f"📦 Creating S3 Vectors index: {self.index}")
        self._client.create_index(
            vectorBucketName=self.bucket,
            indexName=self.index,
            dataType="float32",
            dimension=dimension,
            distanceMetric="cosine",
            metadataConfiguration={
                "nonFilterableMetadataKeys": NON_FILTERABLE_METADATA_KEYS,
            },
        )

    def delete_index(self) -> None:
        try:
            logger.info(f"🗑️ Deleting S3 Vectors index: {self.index}")
            self._client.delete_index(
                vectorBucketName=self.bucket,
                indexName=self.index,
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "NotFoundException":
                logger.info(f"📦 Index {self.index} does not exist. Skipping delete.")
                return
            raise

    def recreate_index(self, dimension: int = 1024) -> None:
        self.delete_index()
        self.create_index(dimension=dimension)

    def put_vectors_batch(self, vectors: list[dict], batch_size: int = 500) -> int:
        inserted = 0
        for start in range(0, len(vectors), batch_size):
            batch = vectors[start:start + batch_size]
            self._client.put_vectors(
                vectorBucketName=self.bucket,
                indexName=self.index,
                vectors=batch,
            )
            inserted += len(batch)
        return inserted

    def query_vectors(
        self,
        query_vector: list[float],
        top_k: int,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "vectorBucketName": self.bucket,
            "indexName": self.index,
            "queryVector": {"float32": [float(value) for value in query_vector]},
            "topK": top_k,
            "returnMetadata": True,
        }
        if metadata_filter:
            params["filter"] = metadata_filter

        chunks = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = self._client.query_vectors(**params)
            for vector in response.get("vectors", []):
                chunk = chunk_from_vector_metadata(vector.get("metadata"))
                if chunk is not None:
                    chunks.append(chunk)

            next_token = response.get("nextToken")
            if not next_token:
                break

        return chunks


def get_vector_store_client() -> S3VectorsClient:
    global _client_instance

    if _client_instance is None:
        if not S3_VECTORS.get("bucket"):
            raise ValueError(
                "S3_VECTORS_BUCKET_NAME environment variable is required. "
                "Please configure it in Lambda environment variables."
            )
        if not S3_VECTORS.get("index"):
            raise ValueError(
                "S3_VECTORS_INDEX_NAME environment variable is required. "
                "Please configure it in Lambda environment variables."
            )

        _client_instance = S3VectorsClient(
            bucket=S3_VECTORS["bucket"],
            index=S3_VECTORS["index"],
            region=S3_VECTORS.get("region", "us-east-1"),
        )

    return _client_instance
