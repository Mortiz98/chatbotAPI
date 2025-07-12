from openai import OpenAI
from typing import List, Optional
from .config import settings

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-3.5-turbo"  # Puedes cambiarlo a gpt-4 si lo prefieres
        
    async def get_chat_response(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Obtiene una respuesta del modelo de chat de OpenAI.
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            temperature: Controla la aleatoriedad de las respuestas (0.0 - 1.0)
            max_tokens: Número máximo de tokens en la respuesta
            
        Returns:
            str: La respuesta del modelo
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            # En un entorno de producción, deberías loggear el error
            raise Exception(f"Error al obtener respuesta de OpenAI: {str(e)}")
    
    def format_messages(self, chat_history: List[dict]) -> List[dict]:
        """
        Formatea el historial de chat para OpenAI.
        
        Args:
            chat_history: Lista de mensajes del chat
            
        Returns:
            List[dict]: Mensajes formateados para OpenAI
        """
        formatted_messages = []
        
        # Mensaje del sistema para establecer el contexto
        system_message = {
            "role": "system",
            "content": "Eres un asistente amable y servicial. Respondes de manera clara y concisa."
        }
        formatted_messages.append(system_message)
        
        # Formatear mensajes del historial
        for message in chat_history:
            role = "assistant" if message.get("is_bot", False) else "user"
            formatted_messages.append({
                "role": role,
                "content": message["content"]
            })
        
        return formatted_messages

# Instancia global del servicio
ai_service = AIService() 