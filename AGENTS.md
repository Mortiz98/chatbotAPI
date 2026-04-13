# AGENTS.md - Document ChatBot (RAG)

## Quick Start

```bash
cd /home/mortiz/projects/chatbot
source venv/bin/activate
uvicorn main:app --reload
```

**Required: Qdrant must be running**
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

## Architecture

**RAG Flow**: Question → Search Qdrant → Get context → LLM generates answer (ONLY from context)

```
/chat/ask → AIService.process_message() → VectorService.search() → OpenRouter LLM
```

## Critical Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-v1-...      # Required for embeddings + LLM
SECRET_KEY=your-secret-key           # Required for JWT
# OPENAI_MODEL defaults to "openai/gpt-3.5-turbo"
# QDRANT_COLLECTION defaults to "aprendizaje"
```

## Key Endpoints (require auth cookie)

| Endpoint | What it does |
|----------|--------------|
| `POST /auth/login` | Returns httpOnly cookie with JWT |
| `POST /chat/ask` | **Main RAG endpoint** - ask questions about documents |
| `POST /documents/ingest` | Upload PDF → auto chunks + indexes in Qdrant |
| `GET /documents/list` | Show indexed documents |
| `GET /search/knowledge?q=...` | Direct Qdrant search (no LLM) |

## Router Prefixes (don't collide)

- `/auth/*` - Authentication
- `/chat/*` - RAG chat endpoints
- `/documents/*` - PDF management
- `/search/*` - Direct vector search

## Key Files

| File | Purpose |
|------|---------|
| `services/ai_service.py` | RAG logic: search Qdrant + query OpenRouter LLM |
| `services/vector_service.py` | Qdrant ops + OpenRouter embeddings (UUIDs, retry logic) |
| `services/document_processor.py` | PDF → chunks with validation |
| `routers/ai_router.py` | Chat endpoints, session ownership checks |
| `core/rate_limit.py` | 100 req/hour per IP |
| `core/security.py` | JWT from httpOnly cookies |
| `frontend/` | Simple HTML/CSS/JS frontend (runs on Live Server at :5500) |

## Frontend

Simple frontend located in `frontend/` folder:
```bash
cd frontend
python -m http.server 5500
# Open http://localhost:5500
```

Features: Login/Register, PDF upload, chat interface, document list.

## Testing

```bash
# Quick test
./test_simple.sh

# Or manual:
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -d '{"email":"test@test.com","password":"password123"}'

curl -b cookies.txt -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"content":"What does the document say about X?"}'
```

## Important Constraints

- **RAG-only**: Bot ONLY answers from uploaded documents (not general knowledge)
- **Auth required**: All chat/document endpoints need valid cookie
- **Threshold 0.3**: Minimum similarity score for context retrieval (changed from 0.5)
- **Cookie secure=False**: Set for local HTTP dev (change to True in production)
- **UUID document IDs**: Not sequential numbers
- **SQLite default**: No PostgreSQL setup needed
- **Conversational mode**: Bot maintains chat history and responds in conversational tone

## Common Gotchas

1. **401 Unauthorized**: Cookie expired or not sent. Re-login.
2. **"No information" response**: Document not indexed OR similarity < 0.3
3. **Rate limited**: 100 requests/hour per IP
4. **Qdrant connection refused**: Start Docker container first
5. **SSL errors with OpenRouter**: May need retry or verify=False in development

## Models

- **Embeddings**: `openai/text-embedding-3-small` (1536 dims)
- **LLM**: Configurable via `OPENAI_MODEL` (default: `openai/gpt-3.5-turbo`)
- **Provider**: OpenRouter (base_url: https://openrouter.ai/api/v1)

## Recent Changes

- Similarity threshold lowered from 0.5 → 0.3 for better context matching
- Bot now maintains conversation history within sessions
- More conversational/perspicacious responses when info is missing
- Fixed datetime issues by using `default=datetime.utcnow` instead of `server_default`