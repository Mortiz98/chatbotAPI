import asyncio
from services.document_processor import DocumentProcessor, ChunkValidator
from services.vector_service import VectorService


def main():
    pdf_path = "documents/lf_S.pdf"

    print(f"📄 Processing: {pdf_path}\n")

    # 1. Extract text
    processor = DocumentProcessor(chunk_size=500, overlap=50)
    print("1. Extracting text from PDF...")
    text = processor.extract_text_from_pdf(pdf_path)
    print(f"   ✅ Text extracted: {len(text)} characters")

    # 2. Chunking
    print("\n2. Splitting into chunks...")
    chunks_data = processor.process_pdf(pdf_path)
    print(f"   ✅ Total chunks: {len(chunks_data)}")

    # 3. Filter valid
    valid_chunks = [
        {"text": processor.clean_text(c["text"]), "metadata": c["metadata"]}
        for c in chunks_data
        if ChunkValidator.is_valid(c["text"])
    ]
    print(f"   ✅ Valid chunks: {len(valid_chunks)}")

    # 4. Index in Qdrant
    print("\n3. Indexing in Qdrant...")
    vector_service = VectorService()
    vector_service.create_collection_if_not_exists()

    # Clear previous document if exists
    deleted = vector_service.delete_by_source("lf_S.pdf")
    if deleted > 0:
        print(f"   🗑️ Deleted {deleted} previous chunks")

    point_ids = vector_service.add_documents_batch(valid_chunks)
    print(f"   ✅ Indexed: {len(point_ids)} chunks")

    # 5. Verify
    print("\n4. Verifying...")
    all_docs = vector_service.get_all_documents()
    print(f"   📊 Total documents in collection: {len(all_docs)}")

    print("\n✅ Pipeline completed!")


if __name__ == "__main__":
    main()
