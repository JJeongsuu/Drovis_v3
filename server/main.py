# Drovis_v3/server/main.py
import os, ssl, smtplib, random, bcrypt, jwt
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from pathlib import Path

# ── .env 확실히 로드 (Drovis_v3/.env)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

app = FastAPI()

# ── 환경변수
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_MODE = os.getenv("SMTP_MODE", "ssl").lower()   # "ssl" 또는 "starttls"
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "15"))  # 초
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")

CODE_TTL_SEC = 300   # 5분
MAX_ATTEMPTS = 5

# ── 데모용 인메모리(운영은 Redis/DB 권장)
codes: Dict[str, Dict] = {}     # email -> {code, expires, attempts}
users: Dict[str, Dict] = {}     # email -> {username, pw_hash}

# ── 모델
class SendReq(BaseModel):
    email: EmailStr

class VerifyReq(BaseModel):
    email: EmailStr
    code: str

class RegisterReq(BaseModel):
    username: str
    email: EmailStr
    password: str
    verification_token: str

# ── 메일 전송 (타임아웃 + SSL/STARTTLS)
def _send_email_sync(to: str, subject: str, body: str):
    if not (SMTP_USER and SMTP_PASS):
        print("[MAIL][ERROR] SMTP 미설정(SMTP_USER/SMTP_PASS)")
        return

    # FROM/TO 디버그 로그
    print(f"[MAIL][DEBUG] HOST={SMTP_HOST} PORT={SMTP_PORT} MODE={SMTP_MODE}")
    print(f"[MAIL][DEBUG] FROM={SMTP_USER}  TO={to}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg.set_content(body)

    try:
        if SMTP_MODE == "starttls":
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(
                SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT,
                context=ssl.create_default_context()
            ) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        print(f"[MAIL] sent to {to} ({datetime.now().isoformat(timespec='seconds')})")
    except Exception as e:
        # 실패 원인은 콘솔에만 남김 (민감정보 제외)
        print(f"[MAIL][ERROR] {type(e).__name__}: {e}")

@app.post("/auth/send-code")
def send_code(req: SendReq, tasks: BackgroundTasks):
    # 입력 이메일 정리
    email = req.email.strip().lower()

    # API 레벨 디버그 로그 (최초 수신자)
    print(f"[API] /auth/send-code  TO={email}  FROM={SMTP_USER}")

    code = f"{random.randint(0, 999999):06d}"
    expires = datetime.now(tz=timezone.utc) + timedelta(seconds=CODE_TTL_SEC)
    codes[email] = {"code": code, "expires": expires, "attempts": 0}

    # 메일 전송을 백그라운드로 → API는 즉시 200 응답
    subject = "[Drovis] 이메일 인증코드"
    body = f"인증코드: {code}\n5분간 유효합니다."
    tasks.add_task(_send_email_sync, email, subject, body)

    return {"ok": True}

@app.post("/auth/verify-code")
def verify_code(req: VerifyReq):
    email = req.email.strip().lower()
    item = codes.get(email)
    if not item:
        raise HTTPException(400, "코드가 없거나 만료됨")
    if datetime.now(tz=timezone.utc) > item["expires"]:
        codes.pop(email, None)
        raise HTTPException(400, "코드가 만료됨")
    if item["attempts"] >= MAX_ATTEMPTS:
        raise HTTPException(429, "시도 초과")
    if req.code != item["code"]:
        item["attempts"] += 1
        raise HTTPException(400, "코드 불일치")
    # 성공 → 10분짜리 검증 토큰 발급
    token = jwt.encode(
        {
            "email": email,
            "typ": "email_verified",
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"ok": True, "verification_token": token}

@app.post("/auth/register")
def register(req: RegisterReq):
    # 토큰 검증
    try:
        payload = jwt.decode(req.verification_token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(400, "토큰 오류")
    if payload.get("typ") != "email_verified" or payload.get("email") != req.email.strip().lower():
        raise HTTPException(400, "토큰-이메일 불일치")

    email = req.email.strip().lower()
    if email in users:
        raise HTTPException(400, "이미 가입된 이메일")
    for u in users.values():
        if u["username"] == req.username:
            raise HTTPException(400, "이미 존재하는 아이디")

    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    users[email] = {"username": req.username, "pw_hash": pw_hash, "created_at": datetime.utcnow().isoformat()}
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}
