from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Optional
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class VectorService:
    def __init__(self):
        self.client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "aprendizaje")

    def create_collection_if_not_exists(self):
        """Creates collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            print(f"✅ Collection '{self.collection_name}' created")
        else:
            print(f"ℹ️ Collection '{self.collection_name}' already exists")

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding using OpenRouter."""
        if not self.openrouter_api_key:
            raise Exception("OPENROUTER_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Chatbot",
        }

        payload = {"model": "openai/text-embedding-3-small", "input": text}

        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings", headers=headers, json=payload
        )

        if response.status_code != 200:
            raise Exception(
                f"OpenRouter error: {response.status_code} - {response.text}"
            )

        return response.json()["data"][0]["embedding"]

    def add_document(self, text: str, metadata: dict) -> str:
        """Adds a single document to the collection."""
        vector = self.get_embedding(text)

        import time

        point_id = int(time.time() * 1000)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id, vector=vector, payload={"text": text, **metadata}
                )
            ],
        )
        return str(point_id)

    def add_documents_batch(self, documents: List[dict]) -> List[str]:
        """Adds multiple documents to the collection."""
        import time

        points = []
        for doc in documents:
            vector = self.get_embedding(doc["text"])
            point_id = int(time.time() * 1000) + len(points)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": doc["text"], **doc.get("metadata", {})},
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

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

    def get_all_documents(self, limit: int = 100) -> List[dict]:
        """Gets all documents."""
        results = self.client.scroll(collection_name=self.collection_name, limit=limit)[
            0
        ]

        return [
            {
                "id": r.id,
                "text": r.payload.get("text"),
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]

    def delete_by_source(self, source: str) -> int:
        """Deletes documents by source filename."""
        results = self.client.scroll(collection_name=self.collection_name, limit=10000)[
            0
        ]

        ids_to_delete = []
        for r in results:
            if r.payload.get("source") == source:
                ids_to_delete.append(r.id)

        if ids_to_delete:
            self.client.delete(
                collection_name=self.collection_name, points_selector=ids_to_delete
            )

        return len(ids_to_delete)
