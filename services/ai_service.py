from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from fastapi import HTTPException, status

from core.config import settings
from core.logging_config import logger
from db import models
from models.schemas import MessageCreate, MessageResponse, ChatSession
from services.vector_service import VectorService


class AIService:
    def __init__(self, db: Session):
        self.db = db
        # Usar OpenRouter en lugar de OpenAI directamente
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Document ChatBot",
            },
        )
        # Modelo debe estar en formato "provider/model" para OpenRouter
        # Ejemplo: "openai/gpt-3.5-turbo", "anthropic/claude-3-haiku", etc.
        self.model = settings.OPENAI_MODEL
        self.vector_service = VectorService()
        # Mínimo score de similitud para considerar un resultado relevante (0-1)
        self.similarity_threshold = 0.5  # Bajar threshold para detectar más resultados

    async def create_chat_session(self, user_id: int) -> ChatSession:
        """
        Crea una nueva sesión de chat para el usuario.
        """
        db_session = models.ChatSession(user_id=user_id, started_at=datetime.utcnow())

        try:
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            logger.info(f"Created chat session {db_session.id} for user {user_id}")
            return ChatSession.model_validate(db_session)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating chat session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la sesión de chat",
            )

    async def end_chat_session(self, session_id: int) -> None:
        """
        Finaliza una sesión de chat existente.
        """
        session = (
            self.db.query(models.ChatSession)
            .filter(models.ChatSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada"
            )

        session.ended_at = datetime.utcnow()
        try:
            self.db.commit()
            logger.info(f"Ended chat session {session_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error ending chat session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al finalizar la sesión",
            )

    async def get_chat_history(self, session_id: int) -> List[MessageResponse]:
        """
        Obtiene el historial de mensajes de una sesión de chat.
        """
        messages = (
            self.db.query(models.Message)
            .filter(models.Message.session_id == session_id)
            .order_by(models.Message.created_at.asc())
            .all()
        )

        return [MessageResponse.model_validate(msg) for msg in messages]

    async def process_message(
        self, user_id: int, content: str, session_id: Optional[int] = None
    ) -> MessageResponse:
        """
        Procesa una pregunta del usuario usando RAG (Retrieval-Augmented Generation).

        1. Busca información relevante en Qdrant
        2. Si encuentra contexto relevante, genera respuesta basada SOLO en ese contexto
        3. Si NO encuentra contexto relevante, indica que no tiene información
        """
        # 1. BUSCAR EN QDRANT (RAG)
        logger.info(f"Searching Qdrant for: {content[:50]}...")

        try:
            search_results = self.vector_service.search(content, limit=5)
        except Exception as e:
            logger.error(f"Error searching Qdrant: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al buscar en la base de conocimiento",
            )

        # Filtrar solo resultados relevantes (score >= threshold)
        relevant_chunks = [
            r for r in search_results if r["score"] >= self.similarity_threshold
        ]

        # Guardar la pregunta del usuario en la base de datos
        user_message = models.Message(
            content=content,
            is_bot=False,
            created_at=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
        )

        try:
            self.db.add(user_message)
            self.db.commit()
            self.db.refresh(user_message)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving user message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al guardar el mensaje",
            )

        # 2. SI NO HAY CONTEXTO RELEVANTE, RESPONDER QUE NO SABE
        if not relevant_chunks:
            logger.info(f"No relevant context found for query: {content[:50]}...")

            no_context_response = (
                "Lo siento, no tengo información sobre eso en mi base de conocimiento. "
                "Por favor, asegúrate de que el documento relevante haya sido subido e indexado."
            )

            bot_message = models.Message(
                content=no_context_response,
                is_bot=True,
                created_at=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id,
            )

            try:
                self.db.add(bot_message)
                self.db.commit()
                self.db.refresh(bot_message)
                return MessageResponse.model_validate(bot_message)
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error saving bot response: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al guardar la respuesta",
                )

        # 3. CONSTRUIR CONTEXTO Y PROMPT
        context_text = "\n\n".join(
            [
                f"[Fragmento {i + 1} - Score: {chunk['score']:.2f}]:\n{chunk['text']}"
                for i, chunk in enumerate(relevant_chunks)
            ]
        )

        sources = list(
            set(
                [
                    chunk["metadata"].get("source", "Desconocido")
                    for chunk in relevant_chunks
                ]
            )
        )

        # Prompt restrictivo: SOLO puede usar el contexto proporcionado
        system_prompt = f"""Eres un asistente especializado que responde preguntas basándose EXCLUSIVAMENTE en la información proporcionada en el contexto.

REGLAS IMPORTANTES:
1. Responde ÚNICAMENTE usando la información del contexto proporcionado abajo
2. Si la respuesta no está en el contexto, di claramente: "No tengo esa información en el documento"
3. NO inventes información que no esté en el contexto
4. NO uses conocimiento general externo
5. Cita los fragmentos relevantes cuando sea apropiado
6. Sé conciso pero completo en tus respuestas

CONTEXTO DEL DOCUMENTO:
{context_text}

Fuentes consultadas: {", ".join(sources)}"""

        logger.info(f"Generating RAG response using {len(relevant_chunks)} chunks")

        # 4. LLAMAR A OPENAI CON EL CONTEXTO
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Basándote únicamente en el contexto proporcionado, responde: {content}",
                    },
                ],
                temperature=0.3,  # Baja temperatura para respuestas más deterministas
                max_tokens=1000,
            )

            bot_response = response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling OpenRouter: {str(e)}")
            bot_response = "Lo siento, hubo un error al generar la respuesta. Por favor, intenta de nuevo."

        # 5. GUARDAR Y DEVOLVER RESPUESTA
        bot_message = models.Message(
            content=bot_response,
            is_bot=True,
            created_at=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
        )

        try:
            self.db.add(bot_message)
            self.db.commit()
            self.db.refresh(bot_message)

            logger.info(f"Generated RAG response for user {user_id}")

            return MessageResponse.model_validate(bot_message)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving bot message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al guardar la respuesta",
            )

    async def get_active_session(self, user_id: int) -> Optional[ChatSession]:
        """
        Obtiene la sesión activa del usuario si existe.
        """
        session = (
            self.db.query(models.ChatSession)
            .filter(
                models.ChatSession.user_id == user_id,
                models.ChatSession.ended_at.is_(None),
            )
            .first()
        )

        if session:
            return ChatSession.model_validate(session)
        return None
