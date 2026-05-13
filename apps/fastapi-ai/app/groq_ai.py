"""
Módulo para integración con Groq AI
"""
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

class GroqAI:
    """Gestor de AI mediante Groq"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY no está configurada")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-8b-instant"  # Modelo actual de Groq
    
    def analyze_message(self, message: str) -> dict:
        """
        Analiza un mensaje y extrae intención y entidades
        """
        system_prompt = """Eres un asistente de soporte para GLPI (herramienta de gestión de tickets).
        
Analiza el mensaje del usuario y proporciona:
1. intent: tipo de solicitud (crear_ticket, consultar_tickets, actualizar_ticket, etc.)
2. entities: información extraída (palabras clave, números, etc.)
3. confidence: confianza del análisis (0-1)

Responde en JSON válido."""
        
        try:
            message_obj = {
                "role": "user",
                "content": f"Analiza este mensaje: {message}"
            }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    message_obj
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            return self._parse_response(response_text)
        except Exception as e:
            print(f"Error al analizar mensaje con Groq: {e}")
            return {
                "intent": "error",
                "entities": {},
                "confidence": 0,
                "error": str(e)
            }
    
    def generate_response(self, message: str, context: dict = None) -> str:
        """
        Genera una respuesta personalizada basada en el mensaje y contexto
        """
        system_prompt = """Eres un asistente amable y profesional de soporte técnico para GLPI.
        
Ayuda a los usuarios con:
- Creación de tickets de soporte
- Consultas sobre el estado de sus tickets
- Preguntas sobre GLPI
- Problemas técnicos

Sé conciso, útil y profesional. Siempre ofrece siguiente pasos si es necesario."""
        
        context_str = ""
        if context:
            context_str = f"\n\nContexto: {context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{message}{context_str}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error al generar respuesta con Groq: {e}")
            return f"Disculpa, ocurrió un error: {str(e)}"
    
    def _parse_response(self, response_text: str) -> dict:
        """
        Intenta parsear la respuesta de Groq como JSON
        """
        import json
        try:
            # Buscar JSON en la respuesta
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except:
            pass
        
        # Si no es JSON válido, retornar estructura por defecto
        return {
            "intent": "general_inquiry",
            "entities": {},
            "confidence": 0.5,
            "raw_response": response_text
        }
