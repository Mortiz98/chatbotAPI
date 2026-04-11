from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from db import models
from services.ai_service import AIService
from models.schemas import ChatRequest, MessageResponse, ChatSession
from core.security import get_current_user
from db.models import User

router = APIRouter(prefix="/chat", tags=["chat"])


def verify_session_ownership(session_id: int, user_id: int, db: Session):
    """Verify that the user owns the session."""
    session = (
        db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada"
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a esta sesión",
        )

    return session


@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva sesión de chat sobre documentos.

    El chatbot responderá preguntas basándose únicamente en los documentos
    indexados en Qdrant (no tiene conocimiento general).
    """
    ai_service = AIService(db)
    return await ai_service.create_chat_session(current_user.id)


@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Finaliza una sesión de chat.
    """
    verify_session_ownership(session_id, current_user.id, db)

    ai_service = AIService(db)
    await ai_service.end_chat_session(session_id)
    return {"message": "Sesión finalizada correctamente"}


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el historial de mensajes de una sesión de chat.
    """
    verify_session_ownership(session_id, current_user.id, db)

    ai_service = AIService(db)
    return await ai_service.get_chat_history(session_id)


@router.post("/ask", response_model=MessageResponse)
async def ask_question(
    message: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Hace una pregunta al chatbot sobre los documentos indexados.

    El bot buscará información relevante en Qdrant y responderá
    basándose únicamente en el contenido de los documentos.

    Si no encuentra información relevante, indicará que no puede responder.
    """
    if message.session_id:
        verify_session_ownership(message.session_id, current_user.id, db)

    ai_service = AIService(db)
    return await ai_service.process_message(
        user_id=current_user.id, content=message.content, session_id=message.session_id
    )


@router.get("/sessions/active", response_model=Optional[ChatSession])
async def get_active_session(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Obtiene la sesión activa del usuario si existe.
    """
    ai_service = AIService(db)
    return await ai_service.get_active_session(current_user.id)
