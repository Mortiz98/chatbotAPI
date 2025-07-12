from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from core.ai_service import ai_service
from models.schemas import MessageCreate, MessageResponse, ChatSession
from models.crud import (
    create_message,
    get_messages_by_user,
    create_chat_session,
    get_chat_session
)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/send", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Envía un mensaje al chatbot y obtiene una respuesta.
    """
    # Guardar el mensaje del usuario
    user_message = create_message(db, message)
    
    # Obtener historial de mensajes reciente
    chat_history = get_messages_by_user(
        db,
        user_id=message.user_id,
        limit=10  # Últimos 10 mensajes para contexto
    )
    
    try:
        # Formatear mensajes para OpenAI
        formatted_messages = ai_service.format_messages(chat_history)
        
        # Obtener respuesta del modelo
        bot_response = await ai_service.get_chat_response(formatted_messages)
        
        # Guardar respuesta del bot
        bot_message = MessageCreate(
            content=bot_response,
            user_id=message.user_id,
            is_bot=True
        )
        bot_message_db = create_message(db, bot_message)
        
        return bot_message_db
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el mensaje: {str(e)}"
        )

@router.get("/history/{user_id}", response_model=List[MessageResponse])
def get_chat_history(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de mensajes de un usuario.
    """
    return get_messages_by_user(db, user_id=user_id, limit=limit)

@router.post("/sessions", response_model=ChatSession)
def start_chat_session(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Inicia una nueva sesión de chat.
    """
    return create_chat_session(db, user_id)

@router.get("/sessions/{session_id}", response_model=ChatSession)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una sesión de chat específica.
    """
    session = get_chat_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Sesión de chat no encontrada"
        )
    return session 