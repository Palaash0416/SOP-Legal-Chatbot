from fastapi import FastAPI
from pydantic import BaseModel
from sop_logic import sop_chatbot  # Your chatbot logic
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI()

# Enable CORS for Framer (replace "*" with your Framer domain for more security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sopai.framer.website"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for incoming chat request
class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str

# Root GET endpoint to confirm server is live
@app.get("/")
async def home():
    return {"message": "SOP Legal AI Assistant is live."}

# GET handler for /chat to avoid 'Method Not Allowed' in browser
@app.get("/chat")
async def chat_info():
    return {
        "message": "Chat endpoint is working. Please send a POST request with user_id, user_input, and session_state."
    }

# POST handler for chatbot requests
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    reply = sop_chatbot(request.user_id, request.user_input, request.session_state)
    return {"response": reply}
