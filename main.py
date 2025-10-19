# main.py
import os
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# =========================================================
# Static files (serves /static/*) and constants
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TERMS_PDF = os.path.join(STATIC_DIR, "terms-privacy.pdf")

app = FastAPI()

# Mount /static (do this once)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Optional direct route for Terms & Privacy (stable URL)
@app.get("/terms", include_in_schema=False)
def terms_pdf():
    if os.path.exists(TERMS_PDF):
        return FileResponse(TERMS_PDF, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="terms_pdf_not_found")

# =========================================================
# CORS
# =========================================================
ALLOWED_ORIGINS = [
    "https://sopai.framer.website",     # Framer preview domain
    "http://localhost:5173",            # local dev (Vite)
    "http://localhost:3000",            # local dev (Next/CRA)
    # Add your production domains here when ready:
    # "https://yourdomain.com",
    # "https://www.yourdomain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# Optional: Redis/Valkey as a KV store for OTPs; in-memory fallback
# =========================================================
_redis = None

def _get_kv():
    """Return Redis client if KV_URL/REDIS_URL/REDISS_URL is set and reachable; else None."""
    global _redis
    if _redis is not None:
        return _redis
    url = os.getenv("KV_URL") or os.getenv("REDIS_URL") or os.getenv("REDISS_URL")
    if not url:
        return None
    try:
        import redis  # requires redis>=4 in requirements.txt
        _redis = redis.Redis.from_url(url, decode_responses=True, ssl=url.startswith("rediss://"))
        _redis.ping()
        return _redis
    except Exception as e:
        print("KV disabled (could not connect):", e)
        return None

# in-memory fallback for demo/dev
_mem_store: dict = {}

def mem_setex(key: str, ttl_seconds: int, value: str):
    _mem_store[key] = (value, datetime.utcnow() + timedelta(seconds=ttl_seconds))

def mem_get(key: str):
    row = _mem_store.get(key)
    if not row:
        return None
    value, exp = row
    if datetime.utcnow() > exp:
        _mem_store.pop(key, None)
        return None
    return value

def mem_del(key: str):
    _mem_store.pop(key, None)

def kv_setex(key: str, ttl_seconds: int, value: str):
    kv = _get_kv()
    if kv:
        kv.setex(key, ttl_seconds, value)
    else:
        mem_setex(key, ttl_seconds, value)

def kv_get(key: str):
    kv = _get_kv()
    return kv.get(key) if kv else mem_get(key)

def kv_del(key: str):
    kv = _get_kv()
    kv.delete(key) if kv else mem_del(key)

# =========================================================
# Email (OTP sender) — uses SMTP if env vars are set; otherwise logs OTP
# =========================================================
def send_email_otp(to_email: str, otp: str, purpose: str):
    host = os.getenv("EMAIL_SMTP_HOST")
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    user = os.getenv("EMAIL_SMTP_USER")
    pwd  = os.getenv("EMAIL_SMTP_PASSWORD")
    from_addr = os.getenv("EMAIL_FROM")
    starttls = os.getenv("EMAIL_SMTP_STARTTLS", "1") == "1"

    if not (host and user and pwd and from_addr):
        print(f"[DEV] OTP for {to_email} ({purpose}): {otp}")
        return

    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["Subject"] = f"SOP: Your OTP for {purpose}"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(f"Your OTP is {otp}. It will expire in 10 minutes.")
    with smtplib.SMTP(host, port) as s:
        if starttls:
            s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
    print(f"[SMTP] OTP sent to {to_email} for {purpose}")

# =========================================================
# In-memory users (replace with DB in production)
# =========================================================
USERS: dict = {}  # { email: {"password": "...", "name": "...", ...} }

def norm_email(s: str | None) -> str:
    return (s or "").strip().lower()

def gen_otp(n: int = 6) -> str:
    return "".join(random.choices(string.digits, k=n))

OTP_TTL = 600  # 10 minutes

# =========================================================
# Schemas (Pydantic v2)
# =========================================================
class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str | None = None

class LoginStart(BaseModel):
    username: EmailStr | None = None
    email: EmailStr | None = None
    password: str

class LoginVerify(BaseModel):
    username: EmailStr | None = None
    email: EmailStr | None = None
    otp: str

class ForgotStart(BaseModel):
    username: EmailStr | None = None
    email: EmailStr | None = None
    new_password: str

class ForgotConfirm(BaseModel):
    username: EmailStr | None = None
    email: EmailStr | None = None
    otp: str

class SignupStart(BaseModel):
    # Accept both "birth_date" and "birthdate" from the frontend
    model_config = ConfigDict(populate_by_name=True)
    name: str
    gender: str | None = None
    birth_date: str | None = Field(default=None, alias="birthdate")  # dd/mm/yyyy
    email: EmailStr
    phone: str | None = None
    whatsapp: str | None = None
    password: str

# =========================================================
# Basic routes
# =========================================================
@app.get("/")
def root():
    return {"message": "SOP Legal AI Assistant is live."}

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.get("/redis/ping")
def redis_ping():
    kv = _get_kv()
    if not kv:
        return {"ok": False, "detail": "KV not configured"}
    try:
        kv.ping()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "detail": str(e)}

# =========================================================
# Chat (delegates to your sop_logic.py)
# =========================================================
from sop_logic import sop_chatbot

@app.post("/chat")
def chat_endpoint(payload: ChatRequest, request: Request):
    try:
        reply = sop_chatbot(payload.user_id, payload.user_input, payload.session_state or "start")
        return JSONResponse({"response": reply})
    except Exception as e:
        # Log the actual error but keep a friendly client message
        import traceback, sys
        print("\n[CHAT ERROR] --------------------------", file=sys.stderr)
        traceback.print_exc()
        print("--------------------------------------\n", file=sys.stderr)
        return JSONResponse(
            {"response": "I’m having trouble accessing my legal database right now. Please try again in a moment."},
            status_code=200,
        )

# =========================================================
# Auth — Login (password ➜ email OTP)
# =========================================================
@app.post("/auth/login/start")
def auth_login_start(body: LoginStart):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    user = USERS.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="No user")
    if user.get("password") != body.password:  # TODO: use hashed passwords in production
        raise HTTPException(status_code=401, detail="invalid password")
    code = gen_otp()
    kv_setex(f"otp:login:{email}", OTP_TTL, code)
    send_email_otp(email, code, "login")
    return {"step": "otp_required"}

@app.post("/auth/login/verify")
def auth_login_verify(body: LoginVerify):
    email = norm_email(body.email or body.username)
    code = kv_get(f"otp:login:{email}")
    if not code:
        raise HTTPException(status_code=400, detail="no_pending_otp")
    if code != body.otp:
        raise HTTPException(status_code=400, detail="otp_invalid")
    kv_del(f"otp:login:{email}")
    return {"ok": True}

@app.post("/auth/login/resend")
def auth_login_resend(body: LoginVerify):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    code = gen_otp()
    kv_setex(f"otp:login:{email}", OTP_TTL, code)
    send_email_otp(email, code, "login")
    return {"ok": True}

# =========================================================
# Auth — Forgot password (email OTP + confirm)
# =========================================================
@app.post("/auth/forgot/start")
def auth_forgot_start(body: ForgotStart):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    if email not in USERS:
        raise HTTPException(status_code=404, detail="No user")
    kv_setex(f"otp:forgot:{email}:newpass", OTP_TTL, body.new_password)
    code = gen_otp()
    kv_setex(f"otp:forgot:{email}", OTP_TTL, code)
    send_email_otp(email, code, "password reset")
    return {"step": "otp_required"}

@app.post("/auth/forgot/confirm")
def auth_forgot_confirm(body: ForgotConfirm):
    email = norm_email(body.email or body.username)
    code = kv_get(f"otp:forgot:{email}")
    if not code:
        raise HTTPException(status_code=400, detail="no_pending_forgot")
    if code != body.otp:
        raise HTTPException(status_code=400, detail="otp_invalid")
    newpass = kv_get(f"otp:forgot:{email}:newpass")
    if not newpass:
        raise HTTPException(status_code=400, detail="missing_new_password")
    USERS[email] = {**USERS.get(email, {}), "password": newpass}
    kv_del(f"otp:forgot:{email}")
    kv_del(f"otp:forgot:{email}:newpass")
    return {"ok": True}

# =========================================================
# Auth — Sign up (no OTP — immediate create)
# =========================================================
@app.post("/auth/signup/start")
def auth_signup_start(body: SignupStart):
    email = norm_email(body.email)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    if email in USERS:
        raise HTTPException(status_code=409, detail="exists")

    # Validate dd/mm/yyyy if provided
    if body.birth_date:
        try:
            d, m, y = body.birth_date.split("/")
            _ = datetime(int(y), int(m), int(d))
        except Exception:
            raise HTTPException(status_code=422, detail="birth_date must be dd/mm/yyyy")

    USERS[email] = {
        "password": body.password,  # TODO: store a password hash in production
        "name": body.name,
        "gender": body.gender,
        "birth_date": body.birth_date,
        "phone": body.phone,
        "whatsapp": body.whatsapp,
        "created_at": datetime.utcnow().isoformat(),
    }
    return {"ok": True}

# (Intentionally disabled; present to avoid accidental calls from old UIs)
@app.post("/auth/signup/verify")
def auth_signup_verify_disabled():
    raise HTTPException(status_code=410, detail="signup_verify_disabled")

@app.post("/auth/signup/resend")
def auth_signup_resend_disabled():
    raise HTTPException(status_code=410, detail="signup_resend_disabled")

# =========================================================
# Local run (Render uses Start Command)
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
