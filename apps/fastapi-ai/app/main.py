from fastapi import FastAPI
from pydantic import BaseModel
from .message_analyzer import MessageAnalyzer
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GLPI AI Agent Motor")

# Inicializar analizador
try:
    analyzer = MessageAnalyzer()
except ValueError as e:
    print(f"Advertencia: {e}")
    analyzer = None

class ProcessRequest(BaseModel):
    message: str
    phone_number: str

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "fastapi-ai",
        "groq_available": analyzer is not None
    }

@app.post("/ai/process")
def process_message(request: ProcessRequest):
    """
    Procesa un mensaje del usuario integrando:
    - Análisis de intención con Groq
    - Conexión a base de datos GLPI
    - Generación dinámica de respuestas
    """
    
    # Si no hay Groq configurado, retornar respuesta dummy
    if analyzer is None:
        return {
            "intent": "error",
            "entities": {},
            "suggested_response": "La API de Groq no está configurada. Por favor, establece GROQ_API_KEY.",
            "needs_confirmation": False,
            "error": "Groq API key not configured"
        }
    
    try:
        # Procesar mensaje con análisis completo
        result = analyzer.process(request.message, request.phone_number)
        return result
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return {
            "intent": "error",
            "entities": {},
            "suggested_response": f"Ocurrió un error: {str(e)}",
            "needs_confirmation": False,
            "error": str(e)
        }
