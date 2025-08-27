from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# If you serve static PDFs:
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Allow Framer & your production domains
ALLOWED_ORIGINS = [
    "https://sopai.framer.website",             # your Framer preview/published domain
    "https://www.soplegalaiassistant.co.in",    # your prod domain (when you point it)
    "https://soplegalaiassistant.co.in",        # naked prod domain
    "https://sop-legal-chatbot.onrender.com",   # your Render API origin  ⬅ add this
    "http://localhost:5173",                    # optional local dev
    "http://localhost:3000",                    # optional local dev
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

# 🔧 Health endpoint (for warm-up/monitoring)
@app.get("/health")
async def health():
    return {"status": "ok"}

# 🔧 Return JSON for any unhandled exception (no HTML error pages)
@app.exception_handler(Exception)
async def all_exceptions(request: Request, exc: Exception):
    # Optionally log: print(repr(exc))
    return JSONResponse(status_code=500, content={"error": "internal_error"})

# ==== Chat endpoint ====
from pydantic import BaseModel
from sop_logic import sop_chatbot

class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str | None = None

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    reply = sop_chatbot(
        payload.user_id,
        payload.user_input,
        payload.session_state or "start"
    )
    return JSONResponse({"response": reply})
