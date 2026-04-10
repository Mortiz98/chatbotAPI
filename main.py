from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.document_router import router as document_router
from routers.chat_router import router as chat_router

app = FastAPI(
    title="ChatBot API",
    description="Chatbot with vector knowledge base (Qdrant)",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(document_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to ChatBot API",
        "qdrant": "http://localhost:6333/dashboard",
        "docs": "/docs",
        "redoc": "/redoc",
    }
