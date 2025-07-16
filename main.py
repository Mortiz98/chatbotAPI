from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ai_router
from db.database import Base, engine

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ChatBot API",
    description="API para chatbot con integración de OpenAI",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(ai_router.router)
@app.get("/")
async def root():
    return {
        "mensaje": "¡Bienvenido a la API del ChatBot!",
        "documentacion": "/docs",
        "redoc": "/redoc"
    }


