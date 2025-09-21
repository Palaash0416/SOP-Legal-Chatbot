# ===== SIGNUP MODELS =====
class SignupStart(BaseModel):
    name: str
    gender: str | None = None
    birth_date: str | None = None  # dd/mm/yyyy
    email: EmailStr
    phone: str | None = None
    whatsapp: str | None = None
    password: str

class SignupVerify(BaseModel):
    email: EmailStr
    otp: str

# ===== SIGNUP ROUTES =====
@app.post("/auth/signup/start")
def auth_signup_start(body: SignupStart):
    email = norm_email(body.email)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    if email in USERS:
        raise HTTPException(status_code=409, detail="exists")

    # (optional) validate dd/mm/yyyy
    if body.birth_date:
        try:
            d, m, y = body.birth_date.split("/")
            _ = datetime(int(y), int(m), int(d))
        except Exception:
            raise HTTPException(status_code=422, detail="birth_date must be dd/mm/yyyy")

    # stash signup payload (without password hashing for demo)
    import json
    kv_setex(f"signup:data:{email}", OTP_TTL, json.dumps(body.dict()))
    code = gen_otp()
    kv_setex(f"otp:signup:{email}", OTP_TTL, code)
    send_email_otp(email, code, "sign up")
    return {"step": "otp_required"}

@app.post("/auth/signup/verify")
def auth_signup_verify(body: SignupVerify):
    email = norm_email(body.email)
    code = kv_get(f"otp:signup:{email}")
    if not code:
        raise HTTPException(status_code=400, detail="no_pending_signup")
    if code != body.otp:
        raise HTTPException(status_code=400, detail="otp_invalid")

    import json
    raw = kv_get(f"signup:data:{email}")
    if not raw:
        raise HTTPException(status_code=400, detail="missing_signup_data")
    data = json.loads(raw)

    # create user
    USERS[email] = {
        "password": data["password"],
        "name": data.get("name"),
        "gender": data.get("gender"),
        "birth_date": data.get("birth_date"),
        "phone": data.get("phone"),
        "whatsapp": data.get("whatsapp"),
        "created_at": datetime.utcnow().isoformat(),
    }

    # cleanup
    kv_del(f"otp:signup:{email}")
    kv_del(f"signup:data:{email}")

    return {"ok": True}

@app.post("/auth/signup/resend")
def auth_signup_resend(body: SignupVerify):
    email = norm_email(body.email)
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    code = gen_otp()
    kv_setex(f"otp:signup:{email}", OTP_TTL, code)
    send_email_otp(email, code, "sign up")
    return {"ok": True}
