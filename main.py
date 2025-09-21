import os
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# ===== optional: Key-Value (Redis/Valkey) =====
_redis = None
def _get_kv():
    """Return a usable KV client if KV_URL(/REDIS_URL/REDISS_URL) is set, else None."""
    global _redis
    if _redis is not None:
        return _redis
    url = (
        os.getenv("KV_URL")
        or os.getenv("REDIS_URL")
        or os.getenv("REDISS_URL")  # some providers use this
    )
    if not url:
        return None
    try:
        import redis  # requirements: redis>=4
        _redis = redis.Redis.from_url(url, decode_responses=True, ssl=url.startswith("rediss://"))
        # probe
        _redis.ping()
        return _redis
    except Exception as e:
        print("KV disabled (could not connect):", e)
        return None

# simple in-memory fallback with expiry
_mem_store = {}
def mem_setex(key: str, ttl_seconds: int, value: str):
    _mem_store[key] = (value, datetime.utcnow() + timedelta(seconds=ttl_seconds))

def mem_get(key: str):
    row = _mem_store.get(key)
    if not row:
        return None
    val, exp = row
    if datetime.utcnow() > exp:
        _mem_store.pop(key, None)
        return None
    return val

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
    if kv:
        return kv.get(key)
    return mem_get(key)

def kv_del(key: str):
    kv = _get_kv()
    if kv:
        kv.delete(key)
    else:
        mem_del(key)

# ===== optional: SMTP email (if you want real emails) =====
def send_email_otp(to_email: str, otp: str, purpose: str):
    """
    Send OTP via SMTP if EMAIL_SMTP_* vars are set; otherwise log to console.
    Env:
      EMAIL_SMTP_HOST, EMAIL_SMTP_PORT (e.g., 587), EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD,
      EMAIL_FROM, EMAIL_SMTP_STARTTLS (optional, '1' default)
    """
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

# ===== app / CORS / static =====
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

ALLOWED_ORIGINS = [
    "https://sopai.framer.website",
    "https://soplegalassistant.co.in",
    "https://soplegalaiassistant.co.in",
    "http://localhost:5173",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== minimal user store (demo) =====
# In production, replace with your real DB.
USERS: dict[str, dict] = {}  # { email: {"password": "<hash or plain for demo>"} }

# ===== utilities =====
def norm_email(email_or_username: str | None) -> str:
    if not email_or_username:
        return ""
    return email_or_username.strip().lower()

def gen_otp(n: int = 6) -> str:
    return "".join(random.choices(string.digits, k=n))

OTP_TTL = 600  # 10 minutes

# ===== models =====
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

# ===== routes =====
@app.get("/")
async def root():
    return {"message": "SOP Legal AI Assistant is live."}

# --- Chat passthrough to your business logic ---
from sop_logic import sop_chatbot  # keep your existing logic

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    reply = sop_chatbot(payload.user_id, payload.user_input, payload.session_state or "start")
    return JSONResponse({"response": reply})

# --- Auth: login start (password check + OTP send) ---
@app.post("/auth/login/start")
def auth_login_start(body: LoginStart):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    # Require user to exist
    user = USERS.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="No user")
    # Plain-text password check for demo. Replace with hash verify in prod.
    if user.get("password") != body.password:
        raise HTTPException(status_code=401, detail="invalid password")
    # Send OTP
    code = gen_otp()
    kv_setex(f"otp:login:{email}", OTP_TTL, code)
    send_email_otp(email, code, "login")
    return {"step": "otp_required"}

@app.post("/auth/login/verify")
def auth_login_verify(body: LoginVerify):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
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

# --- Auth: forgot password (enable reset) ---
@app.post("/auth/forgot/start")
def auth_forgot_start(body: ForgotStart):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")

    # For a friendlier flow we allow creating the account via forgot-confirm.
    # If you want to require the user to already exist, uncomment below:
    # if email not in USERS:
    #     raise HTTPException(status_code=404, detail="No user")

    # Stash the new password until OTP confirm
    kv_setex(f"otp:forgot:{email}:newpass", OTP_TTL, body.new_password)
    code = gen_otp()
    kv_setex(f"otp:forgot:{email}", OTP_TTL, code)
    send_email_otp(email, code, "password reset")
    return {"step": "otp_required"}

@app.post("/auth/forgot/confirm")
def auth_forgot_confirm(body: ForgotConfirm):
    email = norm_email(body.email or body.username)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    code = kv_get(f"otp:forgot:{email}")
    if not code:
        raise HTTPException(status_code=400, detail="no_pending_forgot")
    if code != body.otp:
        raise HTTPException(status_code=400, detail="otp_invalid")

    newpass = kv_get(f"otp:forgot:{email}:newpass")
    if not newpass:
        raise HTTPException(status_code=400, detail="missing_new_password")

    # Create or update the user
    USERS[email] = {"password": newpass}

    # cleanup
    kv_del(f"otp:forgot:{email}")
    kv_del(f"otp:forgot:{email}:newpass")

    return {"ok": True}

# --- optional health route to test KV ---
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
