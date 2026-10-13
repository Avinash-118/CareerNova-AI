
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

router = APIRouter(prefix="/api/profile", tags=["Candidate Profile"])

# Database engine is provided by backend.py during startup.
database_engine: Engine | None = None


def configure_profile_database(engine: Engine):
    global database_engine
    database_engine = engine

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS public.candidate_profiles (
                profile_id VARCHAR(100) PRIMARY KEY,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                location VARCHAR(255),
                linkedin_url TEXT,
                github_url TEXT,
                portfolio_url TEXT,
                education TEXT,
                university VARCHAR(255),
                degree VARCHAR(255),
                experience_years VARCHAR(50),
                skills TEXT,
                work_authorization VARCHAR(150),
                sponsorship_required VARCHAR(50),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))


class CandidateProfile(BaseModel):
    profile_id: str = Field(default="local-candidate", max_length=100)
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    education: str = ""
    university: str = ""
    degree: str = ""
    experience_years: str = ""
    skills: str = ""
    work_authorization: str = ""
    sponsorship_required: str = ""


@router.post("/save")
def save_candidate_profile(profile: CandidateProfile):
    if database_engine is None:
        raise HTTPException(503, "Profile database is unavailable")

    query = text("""
        INSERT INTO public.candidate_profiles (
            profile_id, first_name, last_name, email,
            phone, location, linkedin_url, github_url,
            portfolio_url, education, university, degree,
            experience_years, skills, work_authorization,
            sponsorship_required, updated_at
        )
        VALUES (
            :profile_id, :first_name, :last_name, :email,
            :phone, :location, :linkedin_url, :github_url,
            :portfolio_url, :education, :university, :degree,
            :experience_years, :skills, :work_authorization,
            :sponsorship_required, NOW()
        )
        ON CONFLICT (profile_id)
        DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            location = EXCLUDED.location,
            linkedin_url = EXCLUDED.linkedin_url,
            github_url = EXCLUDED.github_url,
            portfolio_url = EXCLUDED.portfolio_url,
            education = EXCLUDED.education,
            university = EXCLUDED.university,
            degree = EXCLUDED.degree,
            experience_years = EXCLUDED.experience_years,
            skills = EXCLUDED.skills,
            work_authorization = EXCLUDED.work_authorization,
            sponsorship_required = EXCLUDED.sponsorship_required,
            updated_at = NOW()
    """)

    try:
        with database_engine.begin() as connection:
            connection.execute(query, profile.model_dump())

        return {
            "message": "Candidate profile saved successfully",
            "profile_id": profile.profile_id
        }
    except Exception as exc:
        print("Profile save error:", exc)
        raise HTTPException(500, "Unable to save candidate profile") from exc


@router.get("/{profile_id}")
def get_candidate_profile(profile_id: str):
    if database_engine is None:
        raise HTTPException(503, "Profile database is unavailable")

    try:
        with database_engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT
                        profile_id, first_name, last_name, email,
                        phone, location, linkedin_url, github_url,
                        portfolio_url, education, university, degree,
                        experience_years, skills, work_authorization,
                        sponsorship_required
                    FROM public.candidate_profiles
                    WHERE profile_id = :profile_id
                """),
                {"profile_id": profile_id}
            ).mappings().first()

        if result is None:
            raise HTTPException(404, "Candidate profile not found")

        return dict(result)

    except HTTPException:
        raise
    except Exception as exc:
        print("Profile retrieval error:", exc)
        raise HTTPException(500, "Unable to retrieve candidate profile") from exc
