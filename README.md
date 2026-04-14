# Document ChatBot API

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Qdrant-FF6B6B?style=for-the-badge" alt="Qdrant">
  <img src="https://img.shields.io/badge/OpenRouter-412991?style=for-the-badge" alt="OpenRouter">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

<p align="center">
  <b>RAG (Retrieval-Augmented Generation) API</b><br>
  AI-powered document Q&A with semantic search and conversational memory
</p>

---

## ⚠️ Project Status: MVP / Proof of Concept

**This is a Minimum Viable Product (MVP) intended for demonstration and development purposes.**

While functional, this project is **NOT production-ready**. It lacks essential production features such as:
- Comprehensive test coverage
- Distributed rate limiting (currently in-memory only)
- CSRF protection for cookie-based auth
- Proper error monitoring and observability
- Horizontal scalability considerations

Use this as a starting point for building a production RAG system, not as a drop-in production solution.

---

## Overview

This project provides a **RAG (Retrieval-Augmented Generation)** system built with FastAPI. It enables users to upload PDF documents and ask questions about their content, receiving AI-generated answers based exclusively on the indexed documents—not general knowledge.

### Key Features

- **Semantic Document Search** — Vector-based similarity search using Qdrant
- **Conversational AI** — Maintains context across chat sessions
- **Secure Authentication** — JWT-based auth with httpOnly cookies
- **Rate Limiting** — Configurable request throttling per IP
- **PDF Processing** — Automatic text extraction and intelligent chunking
- **RESTful API** — Complete OpenAPI documentation with Swagger UI
- **Web Frontend** — Vanilla JS client included

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌─────────────┐
│   Client    │──────▶│   FastAPI    │──────▶│  Qdrant     │──────▶│  OpenRouter │
│  (Browser)  │◀──────│    Server    │◀──────│  (Vectors)  │      │(Embeddings/ │
└─────────────┘      └──────┬───────┘      └─────────────┘      │    LLM)     │
                            │                                    └─────────────┘
                            │
                     ┌──────▼───────┐
                     │    SQLite    │
                     │(Users, Chat  │
                     │ History)     │
                     └──────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | High-performance async web framework |
| **Vector Database** | Qdrant | Semantic search with cosine similarity |
| **LLM Provider** | OpenRouter | Unified API for embeddings and chat |
| **Database** | SQLite | User sessions, chat history, metadata |
| **PDF Processing** | pdfplumber | Text extraction from PDF documents |
| **Authentication** | JWT + bcrypt | Secure user authentication |
| **Validation** | Pydantic v2 | Request/response data validation |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker (for Qdrant vector database)
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Installation

```bash
# Clone repository
cd /home/mortiz/projects/chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY and SECRET_KEY

# Start Qdrant vector database
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Start application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

---

## API Reference

Interactive documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create new user account |
| `POST` | `/auth/login` | Authenticate and receive JWT cookie |
| `POST` | `/auth/logout` | Clear authentication session |
| `GET` | `/auth/me` | Get current user information |

#### Chat (RAG)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/ask` | Ask question about documents |
| `POST` | `/chat/sessions` | Create new chat session |
| `GET` | `/chat/sessions/{id}/messages` | Retrieve chat history |
| `POST` | `/chat/sessions/{id}/end` | Close chat session |

#### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/ingest` | Upload and index PDF document |
| `GET` | `/documents/list` | List all indexed documents |
| `DELETE` | `/documents/{source}` | Remove document from index |

#### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/search/knowledge?q={query}` | Direct vector search (no LLM) |
| `GET` | `/search/health` | Qdrant health check |

---

## Usage Examples

### 1. Authentication

```bash
# Register new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "username",
    "password": "securepassword123"
  }'

# Login (saves cookie)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }' \
  -c cookies.txt
```

### 2. Document Upload

```bash
# Upload PDF document
curl -X POST http://localhost:8000/documents/ingest \
  -b cookies.txt \
  -F "file=@/path/to/document.pdf"
```

### 3. Ask Questions

```bash
# Query your documents
curl -X POST http://localhost:8000/chat/ask \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the main conclusions of the document?"
  }'
```

---

## Frontend

A lightweight web interface is included in the `frontend/` directory.

```bash
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500 in your browser.

**Features:**
- User registration and login
- PDF upload with drag-and-drop
- Real-time chat interface
- Document management
- Chat session history

---

## Configuration

Environment variables (configured in `.env`):

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...        # Your OpenRouter API key
SECRET_KEY=your-secret-key-here        # JWT signing secret

# Optional (with sensible defaults)
OPENAI_MODEL=openai/gpt-3.5-turbo      # LLM model via OpenRouter
QDRANT_URL=http://localhost:6333       # Qdrant connection URL
QDRANT_COLLECTION=aprendizaje          # Vector collection name
SQLALCHEMY_DATABASE_URL=sqlite:///./chatbot.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=1440
RATE_LIMIT_REQUESTS=100                # Per hour per IP
RATE_LIMIT_WINDOW=3600
```

---

## How RAG Works

### Document Ingestion Flow

1. **Upload** — PDF uploaded via `/documents/ingest`
2. **Extraction** — Text extracted using pdfplumber with page metadata
3. **Chunking** — Content split into 500-character chunks with 50-character overlap
4. **Validation** — Chunks filtered by size and content quality
5. **Embedding** — Each chunk converted to 1536-dimension vector using OpenRouter
6. **Storage** — Vectors and metadata stored in Qdrant with UUID-based IDs

### Query Flow

1. **Question Embedding** — User query converted to vector
2. **Semantic Search** — Qdrant retrieves top 5 most similar chunks (cosine similarity)
3. **Threshold Filtering** — Results filtered by minimum similarity score (0.3)
4. **Context Assembly** — Relevant chunks combined with recent chat history
5. **LLM Generation** — OpenRouter LLM generates answer from context only
6. **Response Storage** — Q&A pair saved to SQLite for conversation continuity

---

## Project Structure

```
chatbot/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration
│
├── core/                      # Core infrastructure
│   ├── config.py             # Application settings (Pydantic)
│   ├── security.py           # JWT and password hashing
│   ├── rate_limit.py         # Request throttling middleware
│   └── logging_config.py     # Structured JSON logging
│
├── db/                        # Database layer
│   ├── database.py           # SQLAlchemy engine & sessions
│   └── models.py             # ORM models (User, Message, ChatSession)
│
├── models/                    # Pydantic schemas
│   └── schemas.py            # Request/response DTOs
│
├── routers/                   # API route handlers
│   ├── auth_router.py        # Authentication endpoints
│   ├── ai_router.py          # Chat/RAG endpoints
│   ├── document_router.py    # Document management
│   └── chat_router.py        # Direct search endpoints
│
├── services/                  # Business logic
│   ├── ai_service.py         # RAG orchestration
│   ├── vector_service.py     # Qdrant operations & embeddings
│   ├── document_processor.py # PDF parsing & chunking
│   └── auth_service.py       # User management
│
└── frontend/                  # Web client
    ├── index.html
    ├── app.js
    └── styles.css
```

---

## Security Considerations

### Implemented
- **Authentication**: JWT tokens stored in httpOnly cookies (XSS protection)
- **Passwords**: Bcrypt hashing with automatic salt
- **Rate Limiting**: 100 requests/hour per IP address (configurable)
- **Input Validation**: Pydantic schemas validate all requests
- **CORS**: Configured for specific origins only
- **File Uploads**: MIME type validation for PDF files

### ⚠️ Missing for Production
- **CSRF Protection**: Not implemented for cookie-based authentication
- **Rate Limiting Distribution**: Currently in-memory only (won't scale across multiple workers)
- **HTTPS Enforcement**: `secure=False` on cookies for local development
- **Input Sanitization**: Limited protection against malicious PDF content
- **Audit Logging**: No security event logging

---

## Performance Notes

- **Embeddings**: `text-embedding-3-small` (1536 dimensions) provides optimal speed/quality
- **Chunking**: 500-character chunks with overlap balance context vs. precision
- **Similarity Threshold**: 0.3 threshold balances recall and precision
- **Session History**: Last 10 messages included for conversational context
- **Async Operations**: FastAPI async handlers for I/O-bound operations

---

## Development

```bash
# Run with auto-reload
uvicorn main:app --reload

# Run with custom port
uvicorn main:app --host 0.0.0.0 --port 8080

# View Qdrant dashboard
open http://localhost:6333/dashboard
```

---

## License

This project is licensed under the MIT License.

---

## Support

For detailed developer documentation, see [AGENTS.md](./AGENTS.md).

For API issues or questions, check the interactive documentation at `/docs` when running the server.
