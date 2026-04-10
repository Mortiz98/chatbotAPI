# AGENTS.md - Chatbot con Qdrant

## Development Environment

```bash
cd /home/mortiz/projects/chatbot
source venv/bin/activate
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Qdrant (required)

Qdrant must be running in Docker:
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

Dashboard: http://localhost:6333/dashboard

## Environment Variables (.env)

```bash
OPENROUTER_API_KEY=sk-or-...  # Required for embeddings
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=aprendizaje
# Do not use PostgreSQL - disabled (use SQLite or remove the line)
```

## Key Structure

| File | Purpose |
|------|---------|
| `services/vector_service.py` | Qdrant + OpenRouter embeddings |
| `services/document_processor.py` | PDF → chunks |
| `routers/chat_router.py` | Search endpoints |
| `routers/document_router.py` | Ingestion endpoints |

## Useful Endpoints

- `GET /chat/search?q=...` - Search knowledge base
- `GET /chat/health` - Check Qdrant status
- `GET /documents/list` - List indexed documents
- `POST /documents/ingest` - Upload PDF

## Ingest New PDFs

```python
from services.document_processor import DocumentProcessor
from services.vector_service import VectorService

processor = DocumentProcessor()
chunks = processor.process_pdf("documents/your_pdf.pdf")

vector_service = VectorService()
vector_service.create_collection_if_not_exists()
vector_service.add_documents_batch(chunks)
```

## Important Notes

- Do not use PostgreSQL - not required in current code
- Embeddings use OpenRouter (not direct OpenAI)
- Embedding model is `text-embedding-3-small` (1536 dimensions)
- Qdrant collection is named `aprendizaje` by default