import uuid
from typing import List, Optional
import requests
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from core.config import settings
from core.logging_config import logger

# Disable SSL warnings for development (remove in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VectorService:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION

        # Create session with SSL adapter for better connection handling
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10, pool_maxsize=10, max_retries=3
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def create_collection_if_not_exists(self):
        """Creates collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info(f"Collection '{self.collection_name}' created")
        else:
            logger.info(f"Collection '{self.collection_name}' already exists")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding using OpenRouter with retry logic."""
        if not self.openrouter_api_key:
            raise Exception("OPENROUTER_API_KEY not configured")

        logger.info(f"Generating embedding for text: {text[:50]}...")

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Document ChatBot",
        }

        payload = {"model": "openai/text-embedding-3-small", "input": text}

        try:
            response = self.session.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=60,
                verify=True,
            )
            response.raise_for_status()
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL Error, retrying with verify=False: {str(e)}")
            # Fallback without SSL verification (development only)
            response = self.session.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=60,
                verify=False,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter request failed: {str(e)}")
            raise Exception(f"OpenRouter error: {str(e)}")

        return response.json()["data"][0]["embedding"]

    def add_document(self, text: str, metadata: dict) -> str:
        """Adds a single document to the collection."""
        vector = self.get_embedding(text)

        # Use UUID instead of timestamp to avoid collisions
        point_id = str(uuid.uuid4())

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id, vector=vector, payload={"text": text, **metadata}
                )
            ],
        )

        logger.info(f"Added document with ID: {point_id}")
        return point_id

    def add_documents_batch(self, documents: List[dict]) -> List[str]:
        """Adds multiple documents to the collection."""
        points = []

        for doc in documents:
            vector = self.get_embedding(doc["text"])
            point_id = str(uuid.uuid4())  # Unique UUID per document
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": doc["text"], **doc.get("metadata", {})},
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Indexed {len(points)} documents in batch")

        return [str(p.id) for p in points]

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """Searches for similar documents."""
        query_vector = self.get_embedding(query)

        results = self.client.query_points(
            collection_name=self.collection_name, query=query_vector, limit=limit
        ).points

        return [
            {
                "id": r.id,
                "score": r.score,
                "text": r.payload.get("text"),
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]

    def get_all_documents(self, limit: int = 100, offset: str = None) -> List[dict]:
        """Gets all documents with optional pagination."""
        results = self.client.scroll(
            collection_name=self.collection_name, limit=limit, offset=offset
        )[0]

        return [
            {
                "id": r.id,
                "text": r.payload.get("text"),
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]

    def delete_by_source(self, source: str) -> int:
        """Deletes documents by source filename using Qdrant filters."""
        filter_condition = Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source))]
        )

        # First count how many documents match
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_condition,
            limit=10000,
        )[0]

        count = len(results)

        if count > 0:
            self.client.delete(
                collection_name=self.collection_name, points_selector=filter_condition
            )
            logger.info(f"Deleted {count} documents from source: {source}")

        return count
