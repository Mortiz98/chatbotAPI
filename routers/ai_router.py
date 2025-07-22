from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from services.ai_service import AIService
from models.schemas import MessageCreate, MessageResponse, ChatSession
from core.security import get_current_user
from db.models import User

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva sesión de chat para el usuario autenticado.
    """
    ai_service = AIService(db)
    return await ai_service.create_chat_session(current_user.id)

@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finaliza una sesión de chat existente.
    """
    ai_service = AIService(db)
    await ai_service.end_chat_session(session_id)
    return {"message": "Sesión finalizada correctamente"}

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el historial de mensajes de una sesión de chat.
    """
    ai_service = AIService(db)
    return await ai_service.get_chat_history(session_id)

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Envía un mensaje y obtiene una respuesta del chatbot.
    """
    ai_service = AIService(db)
    return await ai_service.process_message(
        user_id=current_user.id,
        content=message.content,
        session_id=message.session_id
    )

@router.get("/sessions/active", response_model=Optional[ChatSession])
async def get_active_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la sesión activa del usuario si existe.
    """
    ai_service = AIService(db)
    return await ai_service.get_active_session(current_user.id)
