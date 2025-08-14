from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# If you serve static PDFs:
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Allow Framer & your production domain
ALLOWED_ORIGINS = [
    "https://sopai.framer.website",                 # your Framer preview/published domain
    "https://www.soplegalaiassistant.co.in",        # your prod domain (when you point it)
    "https://soplegalaiassistant.co.in",
    "http://localhost:5173",                        # optional local dev
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "SOP Legal AI Assistant is live."}

from pydantic import BaseModel
from sop_logic import sop_chatbot

class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str | None = None

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    reply = sop_chatbot(payload.user_id, payload.user_input, payload.session_state or "start")
    return JSONResponse({"response": reply})
