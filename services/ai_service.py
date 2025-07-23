from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from fastapi import HTTPException, status

from core.config import settings
from db import models
from models.schemas import MessageCreate, MessageResponse, ChatSession

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def create_chat_session(self, user_id: int) -> ChatSession:
        """
        Crea una nueva sesión de chat para el usuario.
        """
        db_session = models.ChatSession(
            user_id=user_id,
            started_at=datetime.utcnow()
        )
        

        try:
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            return ChatSession.model_validate(db_session)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la sesión de chat"
            )

    async def end_chat_session(self, session_id: int) -> None:
        """
        Finaliza una sesión de chat existente.
        """
        session = self.db.query(models.ChatSession).filter(
            models.ChatSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
            
        session.ended_at = datetime.utcnow()
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al finalizar la sesión"
            )

    async def get_chat_history(self, session_id: int) -> List[MessageResponse]:
        """
        Obtiene el historial de mensajes de una sesión de chat.
        """
        messages = self.db.query(models.Message).filter(
            models.Message.session_id == session_id
        ).order_by(models.Message.created_at.asc()).all()
        
        return [MessageResponse.model_validate(msg) for msg in messages]

    async def process_message(self, user_id: int, content: str, session_id: Optional[int] = None) -> MessageResponse:
        """
        Procesa un mensaje del usuario y genera una respuesta usando OpenAI.
        """
        # Crear el mensaje del usuario
        user_message = models.Message(
            content=content,
            is_bot=False,
            created_at=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id
        )
        
        try:
            self.db.add(user_message)
            self.db.commit()
            self.db.refresh(user_message)
            
            # Obtener el historial de la conversación si hay session_id
            conversation_history = []
            if session_id:
                previous_messages = await self.get_chat_history(session_id)
                conversation_history = [
                    {"role": "assistant" if msg.is_bot else "user", "content": msg.content}
                    for msg in previous_messages
                ]
            
            # Añadir el mensaje actual
            conversation_history.append({"role": "user", "content": content})
            
            # Obtener respuesta de OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente amable y servicial."},
                    *conversation_history
                ]
            )
            
            # Crear el mensaje de respuesta del bot
            bot_response = response.choices[0].message.content
            bot_message = models.Message(
                content=bot_response,
                is_bot=True,
                created_at=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id
            )
            
            self.db.add(bot_message)
            self.db.commit()
            self.db.refresh(bot_message)
            
            return MessageResponse.model_validate(bot_message)
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar el mensaje: {str(e)}"
            )

    async def get_active_session(self, user_id: int) -> Optional[ChatSession]:
        """
        Obtiene la sesión activa del usuario si existe.
        """
        session = self.db.query(models.ChatSession).filter(
            models.ChatSession.user_id == user_id,
            models.ChatSession.ended_at.is_(None)
        ).first()
        
        if session:
            return ChatSession.model_validate(session)
        return None