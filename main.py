from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from sop_logic import sop_chatbot

app = FastAPI()

# Store session data in memory
session_greeted: Dict[str, bool] = {}

class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str

@app.get("/")
async def root():
    return {"message": "SOP Legal AI Assistant is live."}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    global session_greeted

    # First message in session → Send greeting
    if request.user_id not in session_greeted:
        session_greeted[request.user_id] = True
        return {"response": "👋 Hey! I’m SOP — your personal AI legal assistant. How may I help you today?"}

    # All other messages → Normal chatbot response
    reply = sop_chatbot(request.user_id, request.user_input, request.session_state)
    return {"response": reply}
