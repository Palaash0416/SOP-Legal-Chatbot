from fastapi import FastAPI
from pydantic import BaseModel
from sop_logic import sop_chatbot

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return {"response": sop_chatbot(request.user_id, request.user_input, request.session_state)}

@app.get("/")
async def root():
    return {"message": "SOP Legal AI Assistant is running"}
