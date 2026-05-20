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
    
    def process(self, message: str, phone_number: str, debug: bool = False) -> Dict:
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
                return self._handle_ticket_inquiry(message, phone_number, debug=debug)
            
            elif detected_intent == "crear_ticket":
                return self._handle_ticket_creation(message, phone_number, debug=debug)
            
            elif detected_intent == "urgente":
                return self._handle_urgent(message, phone_number, debug=debug)
            
            else:
                # Usar Groq para intenciones no identificadas
                return self._handle_general_inquiry(message, phone_number, debug=debug)
        
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
    
    def _handle_ticket_inquiry(self, message: str, phone_number: str, debug: bool = False) -> Dict:
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
        
        context = self._build_ticket_context(tickets, status_summary)
        action_response = self.groq.plan_action(
            f"El usuario pregunta: {message}",
            {"context": context}
        )
        if action_response.get("action") == "sql_query" and action_response.get("sql"):
            sql_query = action_response["sql"]
            try:
                rows = self.glpi.execute_select_query(sql_query)
                generated_response = self.groq.generate_response(
                    f"El usuario pregunta: {message}",
                    {"sql_query": sql_query, "sql_results": rows}
                )
                result = {
                    "intent": "consultar_tickets",
                    "entities": {
                        "phone_number": phone_number,
                        "ticket_count": len(tickets),
                        "status_summary": status_summary
                    },
                    "suggested_response": generated_response,
                    "needs_confirmation": False,
                    "tickets": tickets[:5],
                    "sql_query": sql_query,
                    "sql_results": rows
                }
                if debug:
                    result["debug_context"] = {
                        "plan": action_response,
                        "groq_context": context,
                        "sql_query": sql_query,
                        "sql_results": rows
                    }
                return result
            except Exception as e:
                return {
                    "intent": "error",
                    "entities": {},
                    "suggested_response": f"No pude ejecutar la consulta SQL: {str(e)}",
                    "needs_confirmation": False,
                    "error": str(e)
                }

        response = self.groq.generate_response(
            f"El usuario pregunta: {message}",
            context
        )
        result = {
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
        if debug:
            result["debug_context"] = {
                "plan": action_response,
                "groq_prompt": f"El usuario pregunta: {message}",
                "groq_context": context
            }
        return result
    
    def _build_ticket_context(self, tickets: List[Dict], status_summary: Dict) -> str:
        """Construye un contexto completo de tickets para enviar a Groq."""
        lines = [
            f"Usuario tiene {len(tickets)} tickets activos.",
            "Resumen de estados:",
            f"  - nuevo: {status_summary.get('new', 0)}",
            f"  - asignado: {status_summary.get('assigned', 0)}",
            f"  - planificado: {status_summary.get('planned', 0)}",
            f"  - en espera: {status_summary.get('waiting', 0)}",
            f"  - resuelto: {status_summary.get('solved', 0)}",
            f"  - cerrado: {status_summary.get('closed', 0)}",
            "Tickets más recientes:"
        ]
        for ticket in tickets[:5]:
            lines.append(
                f"  - ID {ticket.get('id')}: {ticket.get('name')} (estado {ticket.get('status')}, creado {ticket.get('date_creation')})"
            )
        return "\n".join(lines)
    
    def _handle_ticket_creation(self, message: str, phone_number: str, debug: bool = False) -> Dict:
        """Maneja creación de tickets"""
        # Usar Groq para extraer título y descripción
        groq_response = self.groq.analyze_message(message)
        
        response = """Entendido. Para crear tu ticket, necesito:
1. Título o resumen del problema
2. Descripción detallada

¿Puedes proporcionar estos detalles?"""
        result = {
            "intent": "crear_ticket",
            "entities": groq_response.get("entities", {}),
            "suggested_response": response,
            "needs_confirmation": True
        }
        if debug:
            result["debug_context"] = {
                "groq_analysis": groq_response
            }
        return result
    
    def _handle_urgent(self, message: str, phone_number: str, debug: bool = False) -> Dict:
        """Maneja casos urgentes"""
        response = """Entiendo que es urgente. 
        
Por favor proporciona:
1. Descripción breve del problema
2. Impacto en tu operación

Esto ayudará a priorizar tu solicitud."""
        result = {
            "intent": "urgente",
            "entities": {"priority": "high"},
            "suggested_response": response,
            "needs_confirmation": False
        }
        if debug:
            result["debug_context"] = {
                "message": message,
                "intent_detected": "urgente"
            }
        return result
    
    def _handle_general_inquiry(self, message: str, phone_number: str, debug: bool = False) -> Dict:
        """Maneja consultas generales con Groq"""
        context = None
        if self._is_ticket_related(message):
            tickets = self.glpi.get_user_tickets(phone_number)
            status_summary = self.glpi.get_ticket_status_summary(phone_number)
            if tickets:
                context = self._build_ticket_context(tickets, status_summary)

        action_response = self.groq.plan_action(message, {"context": context} if context else None)
        action = action_response.get("action", "answer")

        if action == "sql_query" and action_response.get("sql"):
            sql_query = action_response["sql"]
            try:
                rows = self.glpi.execute_select_query(sql_query)
                generated_response = self.groq.generate_response(
                    message,
                    {"sql_query": sql_query, "sql_results": rows}
                )
                result = {
                    "intent": "consultar_tickets",
                    "entities": action_response.get("entities", {}),
                    "suggested_response": generated_response,
                    "needs_confirmation": False,
                    "confidence": action_response.get("confidence", 0.5),
                    "sql_query": sql_query,
                    "sql_results": rows
                }
                if debug:
                    result["debug_context"] = {
                        "plan": action_response,
                        "sql_query": sql_query,
                        "sql_results": rows
                    }
                return result
            except Exception as e:
                return {
                    "intent": "error",
                    "entities": {},
                    "suggested_response": f"No pude ejecutar la consulta SQL: {str(e)}",
                    "needs_confirmation": False,
                    "error": str(e)
                }

        groq_response = self.groq.analyze_message(message)
        if action_response.get("action") == "answer" and action_response.get("answer"):
            generated_response = action_response["answer"]
        else:
            generated_response = self.groq.generate_response(message, context)

        result = {
            "intent": groq_response.get("intent", "general"),
            "entities": groq_response.get("entities", {}),
            "suggested_response": generated_response,
            "needs_confirmation": False,
            "confidence": groq_response.get("confidence", 0.5)
        }
        if debug:
            result["debug_context"] = {
                "plan": action_response,
                "analysis": groq_response,
                "prompt": message,
                "groq_context": context
            }
        return result

    def _is_ticket_related(self, message: str) -> bool:
        lower = message.lower()
        return any(keyword in lower for keyword in [
            "ticket", "tickets", "estado", "pendiente", "cierre", "cerrar", "prioridad", "GLPI", "soporte"
        ])
