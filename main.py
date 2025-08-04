from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from sop_logic import sop_chatbot

app = FastAPI()

# ✅ Temporary Access Control Middleware
@app.middleware("http")
async def block_unauthorized_requests(request: Request, call_next):
    # Allow access to homepage and static assets without restriction
    if request.url.path.startswith("/static") or request.url.path == "/":
        return await call_next(request)

    # Require access token for all other paths (e.g., /chat)
    token = request.headers.get("X-Access-Token")
    if token != "letmein":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return await call_next(request)

# Chat endpoint
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
