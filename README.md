# Document ChatBot API (RAG)

A FastAPI-based **RAG (Retrieval-Augmented Generation)** chatbot that answers questions exclusively from uploaded PDF documents using Qdrant vector search and OpenRouter LLM.

## How It Works

1. **Upload PDFs** → Documents are split into chunks and indexed in Qdrant with embeddings
2. **Ask Questions** → The bot searches relevant document chunks using semantic similarity
3. **Get Answers** → LLM generates responses based ONLY on the retrieved document context

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for Qdrant)
- OpenRouter API key

### Setup

```bash
# 1. Clone and setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create .env file
cat > .env << EOF
OPENROUTER_API_KEY=sk-or-v1-...
SECRET_KEY=your-secret-key-for-jwt
EOF

# 3. Start Qdrant (vector database)
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage qdrant/qdrant

# 4. Start the API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage Flow

```bash
# 1. Register/Login
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","username":"user","password":"password123"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123"}' \
  -c cookies.txt

# 2. Upload a PDF
curl -X POST http://localhost:8000/documents/ingest \
  -b cookies.txt \
  -F "file=@document.pdf"

# 3. Ask questions about the document
curl -X POST http://localhost:8000/chat/ask \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"content":"What does the document say about X?"}'
```

## Key Endpoints

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Login (sets httpOnly cookies)
- `POST /auth/logout` - Clear session
- `GET /auth/me` - Current user info

### Chat (RAG)
- `POST /chat/ask` - Ask question about documents
- `POST /chat/sessions` - Create chat session
- `GET /chat/sessions/{id}/messages` - Chat history

### Documents
- `POST /documents/ingest` - Upload PDF
- `GET /documents/list` - List indexed documents
- `DELETE /documents/{source}` - Remove document

### Search
- `GET /search/knowledge?q=...` - Direct Qdrant search

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │──────▶│  FastAPI     │──────▶│   SQLite    │
│  (cookies)  │◀──────│   (RAG)      │◀──────│  (sessions,│
└─────────────┘      └──────┬───────┘      │   messages) │
                            │               └─────────────┘
                     ┌──────▼───────┐
                     │   Qdrant     │
                     │  (vectors)   │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │  OpenRouter  │
                     │(embeddings + │
                     │     LLM)     │
                     └──────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `services/vector_service.py` | Qdrant operations + OpenRouter embeddings |
| `services/document_processor.py` | PDF text extraction + chunking |
| `services/ai_service.py` | RAG logic (search + LLM generation) |
| `routers/ai_router.py` | Chat endpoints with auth |
| `routers/auth_router.py` | JWT cookie-based auth |
| `core/rate_limit.py` | Rate limiting middleware |

## Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...      # For embeddings and LLM
SECRET_KEY=your-secret-key           # For JWT signing

# Optional (with defaults)
OPENAI_MODEL=openai/gpt-3.5-turbo    # LLM model via OpenRouter
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=aprendizaje
SQLALCHEMY_DATABASE_URL=sqlite:///./sql_app.db
RATE_LIMIT_REQUESTS=100              # Per hour
RATE_LIMIT_WINDOW=3600
```

## Tech Stack

- **FastAPI** - Web framework
- **Qdrant** - Vector database (1536 dims, cosine similarity)
- **OpenRouter** - Embeddings + LLM API
- **SQLite** - Relational data (users, sessions, messages)
- **pdfplumber** - PDF parsing
- **Pydantic v2** - Data validation

## Important Notes

- **RAG-only**: The bot only answers from uploaded documents, not general knowledge
- **Authentication required**: All chat/document endpoints need login (httpOnly cookies)
- **UUID document IDs**: Documents use UUIDs, not sequential numbers
- **Threshold 0.5**: Minimum 50% similarity for context retrieval
- **PostgreSQL disabled**: Uses SQLite by default

## License

MIT
