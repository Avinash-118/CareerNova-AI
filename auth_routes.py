import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
password_hash = PasswordHash.recommended()
logger = logging.getLogger(__name__)
database_engine = None
COOKIE_NAME = "careernova_session"
SESSION_DURATION_HOURS = 8
RESET_DURATION_MINUTES = 30


def configure_auth_database(engine):
    """Initialize authentication tables without deleting existing account data."""
    global database_engine
    database_engine = engine

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.users (
                id BIGSERIAL PRIMARY KEY,
                full_name VARCHAR(200) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL,
                auth_method VARCHAR(30) NOT NULL DEFAULT 'password'
            )
        """))
        # Existing databases may already have auth_sessions without this column.
        conn.execute(text("""
            ALTER TABLE public.auth_sessions
            ADD COLUMN IF NOT EXISTS auth_method VARCHAR(30) NOT NULL DEFAULT 'password'
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.password_resets (
                token_hash TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
            ON public.auth_sessions (user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_password_resets_user
            ON public.password_resets (user_id)
        """))


def require_database():
    if database_engine is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return database_engine


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(user_id: int, response: Response, auth_method: str = "password"):
    engine = require_database()
    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.auth_sessions (token_hash, user_id, expires_at, auth_method)
            VALUES (:hash, :user_id, :expires, :auth_method)
        """), {
            "hash": digest(token),
            "user_id": user_id,
            "expires": expires,
            "auth_method": auth_method,
        })
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=SESSION_DURATION_HOURS * 3600,
        path="/",
    )
    return {"message": "Signed in"}


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


@router.post("/register", status_code=201)
def register(data: RegisterRequest, response: Response):
    engine = require_database()
    email = str(data.email).strip().lower()
    try:
        with engine.begin() as conn:
            user_id = conn.execute(text("""
                INSERT INTO public.users (full_name, email, password_hash)
                VALUES (:name, :email, :password_hash)
                RETURNING id
            """), {
                "name": data.full_name.strip(),
                "email": email,
                "password_hash": password_hash.hash(data.password),
            }).scalar_one()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return issue_session(user_id, response)


@router.post("/login")
def login(data: LoginRequest, response: Response):
    engine = require_database()
    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT id, password_hash FROM public.users WHERE email = :email
        """), {"email": str(data.email).strip().lower()}).mappings().first()
    if not user or not password_hash.verify(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return issue_session(user["id"], response)


def get_current_user(request: Request):
    engine = require_database()
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in")
    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT u.id, u.full_name, u.email
            FROM public.users AS u
            JOIN public.auth_sessions AS s ON s.user_id = u.id
            WHERE s.token_hash = :hash AND s.expires_at > NOW()
        """), {"hash": digest(token)}).mappings().first()
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again")
    return dict(user)


@router.get("/me")
def current_user(user=Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(request: Request, response: Response):
    engine = require_database()
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM public.auth_sessions WHERE token_hash = :hash
            """), {"hash": digest(token)})
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax")
    return {"message": "Signed out"}


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


def send_reset_email(email: str, token: str):
    """Email delivery uses the project's existing email_service.py module."""
    try:
        from email_service import send_email
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        url = f"{base_url}/reset-password?token={token}"
        send_email(
            email,
            "Reset your CareerNova password",
            f"Reset your password within {RESET_DURATION_MINUTES} minutes: {url}",
        )
    except Exception:
        logger.error("Password reset email delivery failed; check SMTP configuration and connectivity")


@router.post("/forgot-password")
def forgot_password(data: ForgotRequest, tasks: BackgroundTasks):
    engine = require_database()
    email = str(data.email).strip().lower()
    from email_service import email_configured
    email_ready = email_configured()
    if email_ready:
        with engine.begin() as conn:
            user_id = conn.execute(text("""
                SELECT id FROM public.users WHERE email = :email FOR UPDATE
            """), {"email": email}).scalar_one_or_none()
            if user_id is not None:
                token = secrets.token_urlsafe(48)
                conn.execute(text("""
                    DELETE FROM public.password_resets WHERE user_id = :user_id
                """), {"user_id": user_id})
                conn.execute(text("""
                    INSERT INTO public.password_resets (token_hash, user_id, expires_at)
                    VALUES (:hash, :user_id, :expires)
                """), {
                    "hash": digest(token),
                    "user_id": user_id,
                    "expires": datetime.now(timezone.utc) + timedelta(minutes=RESET_DURATION_MINUTES),
                })
                tasks.add_task(send_reset_email, email, token)
    # Do not reveal whether this email belongs to a registered user.
    return {"message": "If an account exists, password reset instructions will be sent when email delivery is available."}


@router.post("/reset-password")
def reset_password(data: ResetRequest, response: Response):
    engine = require_database()
    new_hash = password_hash.hash(data.password)
    with engine.begin() as conn:
        user_id = conn.execute(text("""
            DELETE FROM public.password_resets
            WHERE token_hash = :hash AND expires_at > NOW()
            RETURNING user_id
        """), {"hash": digest(data.token)}).scalar_one_or_none()
        if user_id is None:
            raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
        conn.execute(text("""
            UPDATE public.users SET password_hash = :password_hash WHERE id = :user_id
        """), {"password_hash": new_hash, "user_id": user_id})
        conn.execute(text("""
            DELETE FROM public.auth_sessions WHERE user_id = :user_id
        """), {"user_id": user_id})
        conn.execute(text("""
            DELETE FROM public.password_resets WHERE user_id = :user_id
        """), {"user_id": user_id})
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax")
    return {"message": "Password updated. Please sign in again."}


class AccountUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)


@router.patch("/me")
def update_account(data: AccountUpdate, user=Depends(get_current_user)):
    engine = require_database()
    name = data.full_name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Full name must contain at least 2 characters")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE public.users SET full_name = :name WHERE id = :user_id
        """), {"name": name, "user_id": user["id"]})
    return {**user, "full_name": name}
