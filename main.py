from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.document_router import router as document_router
from routers.chat_router import router as chat_router
from routers.auth_router import router as auth_router
from routers.ai_router import router as ai_router
from core.logging_config import logger
from core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title="Document ChatBot API",
    description="""
    Chatbot RAG (Retrieval-Augmented Generation) basado en documentos.
    
    ## Funcionamiento
    1. Sube documentos PDF vía `/documents/ingest`
    2. Haz preguntas sobre el contenido vía `/chat/ask`
    3. El bot responde basándose EXCLUSIVAMENTE en los documentos indexados
    
    ## Endpoints principales
    - **Autenticación**: `/auth/*` - Registro y login
    - **Chat**: `/chat/*` - Preguntas y respuestas sobre documentos
    - **Documentos**: `/documents/*` - Gestión de PDFs
    - **Búsqueda**: `/search/*` - Búsqueda directa en Qdrant
    """,
    version="1.0.0",
)

# Configure CORS
# Allow frontend running on localhost:5500 (Live Server) or localhost:3000
# IMPORTANT: Cannot use '*' with credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",  # Live Server default
        "http://127.0.0.1:5500",
        "http://localhost:3000",  # Common React/Vue dev server
        "http://localhost:8000",  # Same origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(document_router)
app.include_router(chat_router)

logger.info("Application started successfully")


@app.get("/")
async def root():
    return {
        "message": "Welcome to ChatBot API",
        "qdrant": "http://localhost:6333/dashboard",
        "docs": "/docs",
        "redoc": "/redoc",
    }
