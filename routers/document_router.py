from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
from pathlib import Path

from db.database import get_db
from services.document_processor import DocumentProcessor, ChunkValidator
from services.vector_service import VectorService

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENTS_FOLDER = "documents"


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...), collection: str = "aprendizaje"
):
    """
    Uploads a PDF, processes it and indexes it in Qdrant.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_path = os.path.join(DOCUMENTS_FOLDER, file.filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        processor = DocumentProcessor(chunk_size=500, overlap=50)
        chunks_data = processor.process_pdf(file_path)

        valid_chunks = [
            {"text": processor.clean_text(c["text"]), "metadata": c["metadata"]}
            for c in chunks_data
            if ChunkValidator.is_valid(c["text"])
        ]

        if not valid_chunks:
            raise HTTPException(
                status_code=400,
                detail="No valid chunks could be extracted from the document",
            )

        vector_service = VectorService()
        vector_service.collection_name = collection
        vector_service.create_collection_if_not_exists()

        point_ids = vector_service.add_documents_batch(valid_chunks)

        return {
            "message": "Document processed and indexed successfully",
            "filename": file.filename,
            "chunks_indexed": len(point_ids),
            "collection": collection,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {str(e)}"
        )


@router.get("/list")
async def list_documents(collection: str = "aprendizaje"):
    """
    Lists indexed documents in the collection.
    """
    try:
        vector_service = VectorService()
        vector_service.collection_name = collection
        docs = vector_service.get_all_documents(limit=1000)

        sources = {}
        for doc in docs:
            source = doc.get("metadata", {}).get("source", "unknown")
            if source not in sources:
                sources[source] = {"count": 0, "chunks": []}
            sources[source]["count"] += 1

        return {"total_documents": len(docs), "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source}")
async def delete_document(source: str, collection: str = "aprendizaje"):
    """
    Deletes a document from the collection by filename.
    """
    try:
        vector_service = VectorService()
        vector_service.collection_name = collection
        deleted_count = vector_service.delete_by_source(source)

        return {
            "message": "Document deleted",
            "source": source,
            "chunks_deleted": deleted_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
