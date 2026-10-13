from candidate_profile_routes import (

    router as candidate_profile_router,

    configure_profile_database

)

import os

from contextlib import asynccontextmanager

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query, UploadFile, File

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, Field, model_validator

from sqlalchemy import create_engine, text

from sqlalchemy.engine import URL

from typing import Literal

from faiss_search import semantic_search

from resume_parser import extract_resume_text

from match_scoring import calculate_match

# ============================================================

# 1. ENVIRONMENT CONFIGURATION

# ============================================================

load_dotenv()

password = os.getenv("POSTGRES_PASSWORD")

if not password:

    raise RuntimeError(

        "Set POSTGRES_PASSWORD in your .env file."

    )

database_url = URL.create(

    "postgresql+psycopg2",

    username="postgres",

    password=password,

    host="localhost",

    port=5432,

    database="careernova_db",

)

engine = create_engine(

    database_url,

    pool_pre_ping=True

)

# ============================================================

# 2. APPLICATION STARTUP

# ============================================================

@asynccontextmanager

async def lifespan(app: FastAPI):

    with engine.connect() as connection:

        connection.execute(text("SELECT 1"))

    configure_profile_database(engine)
    configure_autofill_database(engine)

    print("CareerNova AI backend connected to PostgreSQL!")

    yield

    engine.dispose()

app = FastAPI(

    title="CareerNova AI API",

    version="1.0.0",

    lifespan=lifespan,

)

# ============================================================

# 3. CORS CONFIGURATION

# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:5173",

        "http://localhost:5174",

        "http://127.0.0.1:5173",

        "http://127.0.0.1:5174",

    ],

    allow_credentials=False,

    allow_methods=["GET", "POST", "PATCH", "DELETE"],

    allow_headers=["*"],

)

# ============================================================

# 4. CAREER DASHBOARD ROUTER

# ============================================================

from career_dashboard import router as dashboard_router

app.include_router(dashboard_router)

app.include_router(candidate_profile_router)

# ============================================================

# 5. HOME API

# ============================================================

@app.get("/")

def home():

    return {

        "message": "CareerNova AI API is running",

        "status": "success"

    }

# ============================================================

# 6. POSTGRESQL JOB SEARCH

# ============================================================

@app.get("/api/jobs")

def get_jobs(

    search: str = "",

    location: str = "",

    limit: int = Query(default=20, ge=1, le=100),

    offset: int = Query(default=0, ge=0),

):

    conditions = []

    params = {

        "limit": limit,

        "offset": offset

    }

    if search.strip():

        conditions.append(

            "(title ILIKE :search OR company ILIKE :search "

            "OR job_description ILIKE :search)"

        )

        params["search"] = f"%{search.strip()}%"

    if location.strip():

        conditions.append(

            "location ILIKE :location"

        )

        params["location"] = f"%{location.strip()}%"

    where_clause = (

        "WHERE " + " AND ".join(conditions)

        if conditions else ""

    )

    query = text(f"""

        SELECT

            id,

            company,

            title,

            location,

            work_mode,

            employment_type,

            salary_min,

            salary_max,

            salary_currency,

            visa_sponsorship,

            cpt_status,

            opt_status,

            stem_opt_status,

            citizenship_requirement,

            job_description,

            apply_url,

            source_slug

        FROM public.jobs

        {where_clause}

        ORDER BY id

        LIMIT :limit OFFSET :offset

    """)

    count_query = text(f"""

        SELECT COUNT(*)

        FROM public.jobs

        {where_clause}

    """)

    try:

        with engine.connect() as connection:

            rows = connection.execute(

                query, params

            ).mappings().all()

            total = connection.execute(

                count_query, params

            ).scalar_one()

        return {

            "total": total,

            "limit": limit,

            "offset": offset,

            "jobs": [

                dict(row) for row in rows

            ]

        }

    except Exception as exc:

        print("Database query error:", exc)

        raise HTTPException(

            status_code=500,

            detail="Unable to retrieve jobs"

        ) from exc

# ============================================================

# 7. FAISS AI SEMANTIC JOB SEARCH

# ============================================================

@app.get("/api/ai-search")

def ai_search(

    q: str,

    limit: int = Query(default=20, ge=1, le=100)

):

    if not q.strip():

        raise HTTPException(

            status_code=400,

            detail="Search query cannot be empty"

        )

    try:

        results = semantic_search(

            q.strip(),

            limit

        )

        return {

            "query": q,

            "total": len(results),

            "jobs": results,

            "search_type": "FAISS Semantic Search"

        }

    except Exception as exc:

        print("FAISS search error:", exc)

        raise HTTPException(

            status_code=500,

            detail="AI search failed"

        ) from exc

# ============================================================

# 8. AI RESUME MATCHING + MATCH PERCENTAGE

# ============================================================

@app.post("/api/resume-match")

async def resume_match(

    file: UploadFile = File(...),

    limit: int = Query(default=20, ge=1, le=100),

):

    filename = file.filename or ""

    if not filename.lower().endswith((".pdf", ".docx")):

        raise HTTPException(

            status_code=400,

            detail="Please upload a PDF or DOCX resume."

        )

    try:

        file_bytes = await file.read()

        if not file_bytes:

            raise HTTPException(

                status_code=400,

                detail="Uploaded resume is empty."

            )

        if len(file_bytes) > 5 * 1024 * 1024:

            raise HTTPException(

                status_code=413,

                detail="Resume must be smaller than 5 MB."

            )

        resume_text = extract_resume_text(

            filename,

            file_bytes

        )

        if not resume_text.strip():

            raise HTTPException(

                status_code=400,

                detail="No readable text found in resume."

            )

        # Retrieve matching jobs from FAISS

        results = semantic_search(

            resume_text[:12000],

            limit

        )

        # Calculate AI resume match percentage

        for job in results:

            raw_similarity = float(

                job.get("faiss_score", 0.0)

            )

            similarity = max(

                0.0,

                min(1.0, raw_similarity)

            )

            job_description = str(

                job.get("job_description") or ""

            )

            match_details = calculate_match(

                resume_text,

                job_description,

                similarity

            )

            job.update(match_details)

        return {

            "message": "Resume analyzed successfully",

            "filename": filename,

            "characters_extracted": len(resume_text),

            "total": len(results),

            "jobs": results,

            "search_type": "Resume FAISS Matching"

        }

    except HTTPException:

        raise

    except Exception as exc:

        print("Resume matching error:", exc)

        raise HTTPException(

            status_code=500,

            detail="Unable to analyze resume."

        ) from exc

    finally:

        await file.close()

# ============================================================

# 9. SMART JOB ALERTS - EXISTING FEATURE

# ============================================================

class JobAlertRegistration(BaseModel):

    full_name: str = Field(

        min_length=2,

        max_length=150

    )

    email: EmailStr

    phone: str | None = None

    desired_job_role: str = Field(

        min_length=2,

        max_length=255

    )

    preferred_location: str = Field(

        min_length=2,

        max_length=255

    )

    employment_type: Literal[

        "Full-time",

        "Part-time",

        "Internship",

        "Contract"

    ]

    notification_channel: Literal[

        "email",

        "sms",

        "both"

    ]

    consent_given: bool

    @model_validator(mode="after")

    def validate_subscription(self):

        if not self.consent_given:

            raise ValueError(

                "You must consent to receiving job alerts."

            )

        if self.notification_channel in ("sms", "both"):

            if not self.phone or not self.phone.strip():

                raise ValueError(

                    "Phone number is required for SMS alerts."

                )

        return self

@app.post(

    "/api/job-alerts/register",

    status_code=201

)

def register_job_alert(data: JobAlertRegistration):

    query = text("""

        INSERT INTO public.job_alert_subscriptions (

            full_name,

            email,

            phone,

            desired_job_role,

            preferred_location,

            employment_type,

            notification_channel,

            consent_given,

            consent_timestamp

        )

        VALUES (

            :full_name,

            :email,

            :phone,

            :desired_job_role,

            :preferred_location,

            :employment_type,

            :notification_channel,

            TRUE,

            NOW()

        )

        RETURNING id

    """)

    params = {

        "full_name": data.full_name.strip(),

        "email": str(data.email).lower(),

        "phone": data.phone.strip() if data.phone else None,

        "desired_job_role": data.desired_job_role.strip(),

        "preferred_location": data.preferred_location.strip(),

        "employment_type": data.employment_type,

        "notification_channel": data.notification_channel,

    }

    try:

        with engine.begin() as connection:

            subscription_id = connection.execute(

                query,

                params

            ).scalar_one()

        return {

            "message": "Job alert subscription created successfully",

            "subscription_id": subscription_id,

            "status": "registered",

            "notification_channel": data.notification_channel

        }

    except Exception as exc:

        print("Job alert registration error:", exc)

        raise HTTPException(

            status_code=500,

            detail="Unable to register job alert"

        ) from exc

# ==========================================

# CareerNova AI Application Assistant

# ==========================================

from application_agent import open_job_application

from urllib.parse import urlparse

from concurrent.futures import ThreadPoolExecutor

agent_executor = ThreadPoolExecutor(max_workers=1)

class AIAgentRequest(BaseModel):

    job_url: str

@app.post(

    "/api/agent/open-application",

    tags=["AI Application Assistant"]

)

def launch_ai_application(data: AIAgentRequest):

    parsed = urlparse(data.job_url)

    if (

        parsed.scheme not in ("http", "https")

        or not parsed.hostname

    ):

        raise HTTPException(

            status_code=400,

            detail="Invalid job application URL"

        )

    try:

        agent_executor.submit(

            open_job_application,

            data.job_url

        )

        return {

            "message": "Application assistant launch requested",

            "job_url": data.job_url,

            "status": "launching",

            "note": "Review the application portal before submitting."

        }

    except Exception as exc:

        print("Application agent error:", exc)

        raise HTTPException(

            status_code=500,

            detail="Unable to launch application assistant"

        ) from exc

# New isolated application session routes

from application_session_routes import application_session_router, configure_autofill_database

app.include_router(application_session_router)
