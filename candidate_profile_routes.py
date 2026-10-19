"""Authenticated candidate profiles for CareerNova AI.
Replace candidate_profile_routes.py with this file.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine
from auth_routes import get_current_user

router = APIRouter(prefix="/api/profile", tags=["Candidate Profile"])
database_engine: Engine | None = None

FIELDS = (
    "first_name", "last_name", "email", "phone", "location", "linkedin_url",
    "github_url", "portfolio_url", "education", "university", "degree",
    "experience_years", "skills", "work_authorization", "sponsorship_required",
)


def configure_profile_database(engine: Engine):
    global database_engine
    database_engine = engine
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.candidate_profiles (
                profile_id VARCHAR(100) PRIMARY KEY,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50), location VARCHAR(255), linkedin_url TEXT,
                github_url TEXT, portfolio_url TEXT, education TEXT,
                university VARCHAR(255), degree VARCHAR(255),
                experience_years VARCHAR(50), skills TEXT,
                work_authorization VARCHAR(150), sponsorship_required VARCHAR(50),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        # Additive migration: old local-candidate data remains intact but is not assigned.
        conn.execute(text("""
            ALTER TABLE public.candidate_profiles
            ADD COLUMN IF NOT EXISTS user_id BIGINT
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS candidate_profiles_user_id_unique
            ON public.candidate_profiles(user_id)
            WHERE user_id IS NOT NULL
        """))
        # Users are created by configure_auth_database during startup.
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'candidate_profiles_user_id_fkey'
                      AND conrelid = 'public.candidate_profiles'::regclass
                ) THEN
                    ALTER TABLE public.candidate_profiles
                    ADD CONSTRAINT candidate_profiles_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES public.users(id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """))


class CandidateProfile(BaseModel):
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(default="", max_length=50)
    location: str = Field(default="", max_length=255)
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    education: str = ""
    university: str = Field(default="", max_length=255)
    degree: str = Field(default="", max_length=255)
    experience_years: str = Field(default="", max_length=50)
    skills: str = ""
    work_authorization: str = Field(default="", max_length=150)
    sponsorship_required: str = Field(default="", max_length=50)


def require_database():
    if database_engine is None:
        raise HTTPException(503, "Profile database unavailable")
    return database_engine


@router.get('/me')
def get_my_profile(user=Depends(get_current_user)):
    engine = require_database()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT first_name, last_name, email, phone, location, linkedin_url,
                   github_url, portfolio_url, education, university, degree,
                   experience_years, skills, work_authorization, sponsorship_required
            FROM public.candidate_profiles
            WHERE user_id = :user_id
        """), {"user_id": user["id"]}).mappings().first()
    if result is None:
        raise HTTPException(404, "You have not created a candidate profile yet")
    return dict(result)


@router.post('/save')
def save_candidate_profile(profile: CandidateProfile, user=Depends(get_current_user)):
    engine = require_database()
    values = profile.model_dump()
    values['user_id'] = user['id']
    # Fixed, server-derived key: never trust profile_id supplied by the client.
    values['profile_id'] = f"user-{user['id']}"
    columns = ', '.join(FIELDS)
    placeholders = ', '.join(':' + col for col in FIELDS)
    updates = ', '.join(f'{col} = EXCLUDED.{col}' for col in FIELDS)
    statement = text(f"""
        INSERT INTO public.candidate_profiles (profile_id, user_id, {columns}, updated_at)
        VALUES (:profile_id, :user_id, {placeholders}, NOW())
        ON CONFLICT (profile_id) DO UPDATE SET
            {updates}, updated_at = NOW()
        WHERE public.candidate_profiles.user_id = EXCLUDED.user_id
    """)
    with engine.begin() as conn:
        conn.execute(statement, values)
    return {"message": "Candidate profile saved successfully"}


# Deliberately no GET /{profile_id}: it exposed other users' profiles.
