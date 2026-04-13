from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from fastapi import HTTPException, status
from tenacity import retry, stop_after_attempt, wait_exponential

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
        # Bajamos el threshold para ser más permisivo y encontrar más contexto relevante
        self.similarity_threshold = 0.3

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

        # 1.5 CREAR SESIÓN SI NO EXISTE
        if not session_id:
            try:
                new_session = models.ChatSession(
                    user_id=user_id, started_at=datetime.utcnow()
                )
                self.db.add(new_session)
                self.db.commit()
                self.db.refresh(new_session)
                session_id = new_session.id
                logger.info(f"Created new session {session_id} for user {user_id}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error creating session: {str(e)}")

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

        # 2. OBTENER HISTORIAL DE CONVERSACIÓN (si hay sesión)
        conversation_history = []
        if session_id:
            try:
                # Excluir el mensaje actual que acabamos de guardar
                previous_messages = (
                    self.db.query(models.Message)
                    .filter(
                        models.Message.session_id == session_id,
                        models.Message.id != user_message.id,
                    )
                    .order_by(models.Message.created_at.asc())
                    .limit(10)  # Últimos 10 mensajes para contexto
                    .all()
                )
                for msg in previous_messages:
                    role = "assistant" if msg.is_bot else "user"
                    conversation_history.append({"role": role, "content": msg.content})
                logger.info(
                    f"Retrieved {len(conversation_history)} messages from session {session_id}"
                )
            except Exception as e:
                logger.warning(f"Could not retrieve conversation history: {e}")

        # 3. SI NO HAY CONTEXTO RELEVANTE, INTENTAR RECUPERAR CON BÚSQUEDA AMPLIA
        if not relevant_chunks:
            logger.info(f"No relevant context found for query: {content[:50]}...")

            # Intentar búsqueda más amplia con palabras clave individuales
            search_terms = content.lower().split()
            all_chunks = []

            for term in search_terms[:3]:  # Buscar con primeros 3 términos
                if len(term) > 3:  # Solo términos significativos
                    try:
                        results = self.vector_service.search(term, limit=3)
                        all_chunks.extend(results)
                    except:
                        pass

            # Si encontramos algo relacionado, usarlo
            if all_chunks:
                # Ordenar por score y quitar duplicados
                seen_ids = set()
                relevant_chunks = []
                for chunk in sorted(all_chunks, key=lambda x: x["score"], reverse=True):
                    if chunk["id"] not in seen_ids and chunk["score"] >= 0.2:
                        seen_ids.add(chunk["id"])
                        relevant_chunks.append(chunk)

                if relevant_chunks:
                    logger.info(
                        f"Found related content with broad search: {len(relevant_chunks)} chunks"
                    )

            # Si aún no hay nada, hacer respuesta perspicaz
            if not relevant_chunks:
                # Obtener temas disponibles en los documentos
                try:
                    all_docs = self.vector_service.get_all_documents(limit=50)
                    available_topics = list(
                        set(
                            [
                                doc.get("metadata", {}).get("source", "")
                                for doc in all_docs
                                if doc.get("metadata", {}).get("source")
                            ]
                        )
                    )[:5]
                except:
                    available_topics = []

                # Respuesta perspicaz basada en el historial
                if conversation_history:
                    # Si es seguimiento de conversación anterior
                    no_context_prompt = f"""Eres un asistente amigable. El usuario ha hecho una pregunta sobre la que NO tienes información específica en los documentos.
                    
HISTORIAL RECIENTE:
{chr(10).join([f"{'Usuario' if msg['role'] == 'user' else 'Asistente'}: {msg['content']}" for msg in conversation_history[-4:]])}

PREGUNTA ACTUAL: {content}

INSTRUCCIONES:
1. NO digas directamente "no tengo información"
2. Intenta entender qué busca el usuario basándote en el contexto de la conversación
3. Sugiere temas relacionados que podrías tener información (si los hay)
4. Mantén un tono conversacional y útil
5. NO termines cada respuesta con "¿Te gustaría saber más?" - varía tus despedidas
6. Puedes terminar con una pregunta, una afirmación amigable, o simplemente cerrar la respuesta de forma natural

Respuesta:"""

                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Eres un asistente perspicaz y conversacional.",
                                },
                                {"role": "user", "content": no_context_prompt},
                            ],
                            temperature=0.8,
                            max_tokens=200,
                            timeout=30,
                        )
                        no_context_response = response.choices[0].message.content
                    except:
                        # Fallback si falla el LLM
                        if available_topics:
                            topics_str = ", ".join(
                                [t.replace(".pdf", "") for t in available_topics if t]
                            )
                            no_context_response = (
                                f"Buena pregunta. En mis documentos tengo información sobre {topics_str}. "
                                f"¿Sobre alguno de estos temas te gustaría que conversemos?"
                            )
                        else:
                            no_context_response = (
                                "Interesante pregunta. Cuéntame un poco más sobre lo que buscas, "
                                "así puedo orientarte mejor con la información que tengo disponible."
                            )
                else:
                    # Primera interacción sin contexto
                    if available_topics:
                        topics_str = ", ".join(
                            [t.replace(".pdf", "") for t in available_topics if t]
                        )
                        no_context_response = (
                            f"¡Hola! Veo que tienes documentos sobre {topics_str}. "
                            f"Estoy listo para conversar sobre cualquiera de estos temas."
                        )
                    else:
                        no_context_response = (
                            "¡Hola! Estoy listo para ayudarte. Cuando subas documentos, podré conversar contigo "
                            "sobre su contenido de forma natural."
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

        # 4. CONSTRUIR CONTEXTO Y PROMPT CONVERSACIONAL
        context_text = "\n\n".join(
            [
                f"[Fragmento {i + 1}]:\n{chunk['text']}"
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

        # Prompt conversacional pero manteniendo RAG
        system_prompt = f"""Eres un asistente amigable, empático y conversacional. Mantén conversaciones naturales como lo haría una persona.

PERSONALIDAD:
- Sé cálido, cercano y genuino
- Usa lenguaje natural, evita sonar robótico
- Muestra interés real en la conversación
- Puedes usar emojis cuando encajen naturalmente
- NO cites fragmentos literalmente con "[Fragmento X]" - integra la información fluidamente

RESTRICCIÓN FUNDAMENTAL:
- Solo usa información del CONTEXTO DE DOCUMENTOS abajo
- NUNCA inventes información externa
- Si algo no está en el contexto, sé honesto pero mantén la conversación

CONTEXTO DE DOCUMENTOS:
{context_text}

ESTRATEGIA PARA RESPUESTAS:
1. Responde directamente a la pregunta con la información disponible
2. Si el usuario dice "sí", "ok", "cuéntame más", etc., EXPANDE la información dando más detalles del contexto
3. Si hay ambigüedad, pide aclaración de forma natural
4. Mantén continuidad con temas previos de la conversación
5. NO preguntes "¿Te gustaría saber más?" al final de cada mensaje - varía tus despedidas
6. A veces termina la respuesta directamente, otras veces con una pregunta relevante, otras simplemente con una afirmación amigable

Ejemplos de buenas respuestas (VARIADAS):
- "Según los documentos, X se refiere a... Es un tema bastante interesante."
- "La información indica que... ¿Hay algo específico sobre esto que te interese?"
- "X está relacionado con... Como curiosidad, también se menciona Y en el mismo contexto."
- "Perfecto, también menciona que... Esto conecta bastante bien con lo que decías antes."

Evita decir "según el fragmento 1" o "en el documento se dice". Integra la información naturalmente."""

        logger.info(
            f"Generating conversational RAG response using {len(relevant_chunks)} chunks"
        )

        # Construir mensajes incluyendo historial
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": content})

        # 5. LLAMAR A OPENAI CON HISTORIAL Y CONTEXTO
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        def generate_response():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Más alto para respuestas más naturales/conversacionales
                max_tokens=1500,
                timeout=60,
            )

        try:
            response = generate_response()
            bot_response = response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling OpenRouter: {str(e)}")
            bot_response = "Ups, parece que tuve un pequeño problema al procesar tu mensaje. ¿Podrías intentarlo de nuevo?"

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
