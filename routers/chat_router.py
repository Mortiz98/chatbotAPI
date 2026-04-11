from fastapi import APIRouter, Query
from typing import List, Optional

from qdrant_client import QdrantClient
from core.config import settings
from services.vector_service import VectorService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/knowledge")
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Number of results"),
):
    """
    Search in the vector knowledge base.
    """
    vector_service = VectorService()
    results = vector_service.search(q, limit=limit)

    return {"query": q, "results": results, "total": len(results)}


@router.get("/collections")
async def list_collections():
    """
    List available collections in Qdrant.
    """
    client = QdrantClient(url=settings.QDRANT_URL)
    collections = client.get_collections()

    return {"collections": [c.name for c in collections.collections]}


@router.get("/health")
async def health_check():
    """
    Check service status.
    """
    try:
        client = QdrantClient(url=settings.QDRANT_URL)
        collections = client.get_collections()
        qdrant_status = "ok"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    return {"status": "ok", "services": {"qdrant": qdrant_status}}
