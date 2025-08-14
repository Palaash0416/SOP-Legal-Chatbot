from fastapi import FastAPI
from pydantic import BaseModel
from sop_logic import sop_chatbot
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI()

# ✅ Allow CORS so Framer can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can change this to ["https://sopai.framer.website"] for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Request model
class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str

# ✅ Health check route (GET)
@app.get("/")
def root():
    return {"message": "SOP Legal AI Assistant is live."}

# ✅ Chat endpoint (POST)
@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        reply = sop_chatbot(request.user_id, request.user_input, request.session_state)
        return {"response": reply}
    except Exception as e:
        return {"error": str(e)}

# ✅ Optional: Catch wrong HTTP method
@app.get("/chat")
def chat_wrong_method():
    return {"error": "This endpoint only supports POST requests. Please use POST method."}
