# ChatBot API with Qdrant

A FastAPI-based chatbot with vector search knowledge base using Qdrant.

## Features

- **Vector Search**: Semantic search using Qdrant and OpenRouter embeddings
- **PDF Ingestion**: Process and index PDF documents
- **REST API**: FastAPI endpoints for search and document management
- **Knowledge Base**: Search across indexed documents using natural language

## Requirements

- Python 3.10+
- Docker (for Qdrant)
- OpenRouter API key

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install additional packages
pip install qdrant-client python-dotenv requests pdfplumber
```

## Running

### 1. Start Qdrant (Docker)

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 2. Configure environment

Create `.env` file:
```bash
OPENROUTER_API_KEY=sk-or-...  # Get from https://openrouter.ai/keys
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=aprendizaje
```

### 3. Start API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Welcome message |
| `GET /chat/search?q=...` | Search knowledge base |
| `GET /chat/health` | Check Qdrant status |
| `GET /chat/collections` | List Qdrant collections |
| `GET /documents/list` | List indexed documents |
| `POST /documents/ingest` | Upload and index PDF |

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Ingesting Documents

```python
from services.document_processor import DocumentProcessor
from services.vector_service import VectorService

processor = DocumentProcessor()
chunks = processor.process_pdf("documents/your_file.pdf")

vector_service = VectorService()
vector_service.create_collection_if_not_exists()
vector_service.add_documents_batch(chunks)
```

## Tech Stack

- **FastAPI** - Web framework
- **Qdrant** - Vector database
- **OpenRouter** - Embeddings API
- **pdfplumber** - PDF parsing

## License

MIT