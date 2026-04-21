from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="GLPI AI Agent Motor")

class ProcessRequest(BaseModel):
    message: str
    phone_number: str

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "fastapi-ai"}

@app.post("/ai/process")
def process_message(request: ProcessRequest):
    # Dummy processing para Sprint inicial
    return {
        "intent": "saludo",
        "entities": {},
        "suggested_response": "Hola, ¿en qué te puedo ayudar con tu ticket de soporte?",
        "needs_confirmation": False
    }
