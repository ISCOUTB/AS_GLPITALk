"""
Módulo para análisis dinámico de mensajes
"""
import re
from typing import Dict, List
from .groq_ai import GroqAI
from .glpi_connector import GLPIConnector

class MessageAnalyzer:
    """Analiza mensajes y gestiona las respuestas dinámicas"""
    
    def __init__(self):
        self.groq = GroqAI()
        self.glpi = GLPIConnector()
        
        # Patrones de intención comunes
        self.intent_patterns = {
            "consultar_tickets": [
                r"tickets?", r"mis?\s+tickets?", r"estado\s+de\s+mis?\s+tickets?",
                r"¿?cómo\s+van\s+mis?\s+tickets?", r"¿?qué\s+tickets?\s+tengo?",
                r"mis?\s+solicitudes?", r"estado\s+de\s+soporte"
            ],
            "crear_ticket": [
                r"crear\s+ticket", r"nuevo\s+ticket", r"reportar\s+problema",
                r"abrir\s+ticket", r"crear\s+solicitud", r"quiero\s+reportar",
                r"tengo\s+un\s+problema"
            ],
            "actualizar_ticket": [
                r"actualizar\s+ticket", r"cambiar\s+ticket", r"modificar\s+ticket"
            ],
            "urgente": [
                r"urgente", r"rápido", r"inmediato", r"ahora\s+mismo",
                r"no\s+espera", r"crítico", r"bloqueado"
            ],
            "saludo": [
                r"hola", r"buenos\s+(días|días|noches?)", r"¿?cómo\s+estás?",
                r"ayuda", r"hallo"
            ]
        }
    
    def process(self, message: str, phone_number: str) -> Dict:
        """
        Procesa un mensaje de usuario y retorna una respuesta estructurada
        """
        # Análisis inicial
        detected_intent = self._detect_intent(message)
        
        # Conectar con GLPI
        if not self.glpi.connect():
            return {
                "intent": "error",
                "entities": {},
                "suggested_response": "No puedo conectar con la base de datos. Por favor intenta más tarde.",
                "needs_confirmation": False,
                "error": "Database connection failed"
            }
        
        try:
            # Routing según intención
            if detected_intent == "consultar_tickets":
                return self._handle_ticket_inquiry(message, phone_number)
            
            elif detected_intent == "crear_ticket":
                return self._handle_ticket_creation(message, phone_number)
            
            elif detected_intent == "urgente":
                return self._handle_urgent(message, phone_number)
            
            else:
                # Usar Groq para intenciones no identificadas
                return self._handle_general_inquiry(message, phone_number)
        
        finally:
            self.glpi.disconnect()
    
    def _detect_intent(self, message: str) -> str:
        """Detecta la intención del mensaje usando patrones regex"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return "general"
    
    def _handle_ticket_inquiry(self, message: str, phone_number: str) -> Dict:
        """Maneja consultas sobre tickets"""
        tickets = self.glpi.get_user_tickets(phone_number)
        status_summary = self.glpi.get_ticket_status_summary(phone_number)
        
        if not tickets:
            response = f"No encontré tickets asociados al número {phone_number}. ¿Deseas crear uno nuevo?"
            return {
                "intent": "consultar_tickets",
                "entities": {"phone_number": phone_number},
                "suggested_response": response,
                "needs_confirmation": False,
                "ticket_count": 0
            }
        
        # Usar Groq para generar resumen natural
        context = f"""
Usuario tiene {len(tickets)} tickets activos.
Resumen de estados: {status_summary}
Últimos tickets: {tickets[:3]}
"""
        
        response = self.groq.generate_response(
            f"El usuario pregunta: {message}",
            context
        )
        
        return {
            "intent": "consultar_tickets",
            "entities": {
                "phone_number": phone_number,
                "ticket_count": len(tickets),
                "status_summary": status_summary
            },
            "suggested_response": response,
            "needs_confirmation": False,
            "tickets": tickets[:5]  # Retornar primeros 5 tickets
        }
    
    def _handle_ticket_creation(self, message: str, phone_number: str) -> Dict:
        """Maneja creación de tickets"""
        # Usar Groq para extraer título y descripción
        groq_response = self.groq.analyze_message(message)
        
        response = """Entendido. Para crear tu ticket, necesito:
1. Título o resumen del problema
2. Descripción detallada

¿Puedes proporcionar estos detalles?"""
        
        return {
            "intent": "crear_ticket",
            "entities": groq_response.get("entities", {}),
            "suggested_response": response,
            "needs_confirmation": True
        }
    
    def _handle_urgent(self, message: str, phone_number: str) -> Dict:
        """Maneja casos urgentes"""
        response = """Entiendo que es urgente. 
        
Por favor proporciona:
1. Descripción breve del problema
2. Impacto en tu operación

Esto ayudará a priorizar tu solicitud."""
        
        return {
            "intent": "urgente",
            "entities": {"priority": "high"},
            "suggested_response": response,
            "needs_confirmation": False
        }
    
    def _handle_general_inquiry(self, message: str, phone_number: str) -> Dict:
        """Maneja consultas generales con Groq"""
        groq_response = self.groq.analyze_message(message)
        generated_response = self.groq.generate_response(message)
        
        return {
            "intent": groq_response.get("intent", "general"),
            "entities": groq_response.get("entities", {}),
            "suggested_response": generated_response,
            "needs_confirmation": False,
            "confidence": groq_response.get("confidence", 0.5)
        }
