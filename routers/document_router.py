from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path

from core.config import settings
from core.logging_config import logger
from services.document_processor import DocumentProcessor, ChunkValidator
from services.vector_service import VectorService

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENTS_FOLDER = "documents"


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...), collection: str = None):
    """
    Uploads a PDF, processes it and indexes it in Qdrant.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Use default collection from settings if not provided
    if collection is None:
        collection = settings.QDRANT_COLLECTION

    file_path = os.path.join(DOCUMENTS_FOLDER, file.filename)

    try:
        # Ensure documents folder exists
        Path(DOCUMENTS_FOLDER).mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Processing PDF: {file.filename}")

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

        logger.info(
            f"Document indexed successfully: {file.filename} ({len(point_ids)} chunks)"
        )

        return {
            "message": "Document processed and indexed successfully",
            "filename": file.filename,
            "chunks_indexed": len(point_ids),
            "collection": collection,
        }

    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {str(e)}"
        )


@router.get("/list")
async def list_documents(collection: str = None):
    """
    Lists indexed documents in the collection.
    """
    # Use default collection from settings if not provided
    if collection is None:
        collection = settings.QDRANT_COLLECTION

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
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source}")
async def delete_document(source: str, collection: str = None):
    """
    Deletes a document from the collection by filename.
    """
    # Use default collection from settings if not provided
    if collection is None:
        collection = settings.QDRANT_COLLECTION

    try:
        vector_service = VectorService()
        vector_service.collection_name = collection
        deleted_count = vector_service.delete_by_source(source)

        logger.info(f"Deleted document: {source} ({deleted_count} chunks)")

        return {
            "message": "Document deleted",
            "source": source,
            "chunks_deleted": deleted_count,
        }
    except Exception as e:
        logger.error(f"Error deleting document {source}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
