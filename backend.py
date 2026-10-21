from auth_routes import (
    router as auth_router,
    configure_auth_database,
)
import os
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    UploadFile,
    File,
    Depends,
    Request,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    model_validator,
)

from sqlalchemy import text

# ============================================================
# 1. DATABASE CONNECTION
# ============================================================

from database import engine
from auth_routes import get_current_user


# ============================================================
# 2. EXISTING AI FEATURES
# ============================================================

from faiss_search import semantic_search
from resume_parser import extract_resume_text
from match_scoring import calculate_match


# ============================================================
# 3. HISTORICAL JOB DATASET
# ============================================================

from historical_jobs_routes import (
    router as historical_jobs_router,
)


# ============================================================
# 4. CANDIDATE PROFILE
# ============================================================

from candidate_profile_routes import (
    router as candidate_profile_router,
    configure_profile_database,
)


# ============================================================
# 5. NOVA APPLICATION ASSISTANT
# ============================================================

from application_session_routes import (
    application_session_router,
    configure_autofill_database,
)


# ============================================================
# 6. LIVE JOB SOURCES
# ============================================================

from live_jobs_routes import (
    router as live_jobs_router,
)


# ============================================================
# 7. NEW USER AUTHENTICATION
# ============================================================

from auth_routes import (
    router as auth_router,
    configure_auth_database,
)


# ============================================================
# 8. ENVIRONMENT CONFIGURATION
# ============================================================

load_dotenv()


# ============================================================
# 9. APPLICATION STARTUP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    from deployment_config import validate_production
    validate_production()
    # Verify PostgreSQL connectivity
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    # Initialize candidate profile database
    configure_auth_database(engine)
    configure_dashboard(engine)
    configure_platform(engine)
    configure_features(engine)

    # Initialize Nova autofill database connection
    configure_profile_database(engine)

    # Initialize user registration/login database
    configure_autofill_database(engine)

    print("========================================")
    print("CareerNova AI backend started")
    print("PostgreSQL connected successfully")
    print("Candidate Profile initialized")
    print("Nova Application Assistant initialized")
    print("User Authentication initialized")
    print("========================================")

    yield

    # Close database connections on shutdown
    engine.dispose()


# ============================================================
# 10. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="CareerNova AI API",
    description=(
        "AI-powered career platform with job discovery, "
        "candidate profiles, resume matching, "
        "Nova application automation, and user authentication."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================
# 11. CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "DELETE",
    ],
    allow_headers=["*"],
)


# ============================================================
# 12. REGISTER ALL API ROUTERS
# ============================================================

# 99,999 historical jobs
app.include_router(historical_jobs_router, dependencies=[Depends(get_current_user)])

# Candidate Profile
app.include_router(candidate_profile_router)

# Nova Application Assistant
app.include_router(application_session_router)

# Live job sources
app.include_router(live_jobs_router, dependencies=[Depends(get_current_user)])

# Registration, login, and current user
app.include_router(auth_router)


# ============================================================
# 13. BASIC HEALTH CHECK
# ============================================================

@app.get("/api/health", tags=["System"])
def health_check():
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
    return {
        "status": "running",
        "application": "CareerNova AI",
        "version": "2.0.0",
        "database": "PostgreSQL",
    }


# ============================================================
# 14. HOME ENDPOINT
# ============================================================

@app.get("/", tags=["System"])
def home():
    return {
        "message": "Welcome to CareerNova AI",
        "status": "running",
        "features": [
            "99,999 Historical Jobs",
            "Live Job Discovery",
            "FAISS Semantic Search",
            "Candidate Profile",
            "Resume Matching",
            "Nova AI Application Assistant",
            "User Registration",
            "User Login",
        ],
    }


from auth_routes import get_current_user
from career_dashboard import router as dashboard_router, configure_dashboard
from platform_routes import router as platform_router, configure_platform
app.include_router(dashboard_router)
app.include_router(platform_router)

# The browser sends a non-simple header on every API mutation. Cross-origin
# callers must pass the explicit CORS origin allowlist before sending it.
from starlette.responses import JSONResponse
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
_auth_attempts = defaultdict(deque)
_rate_lock = Lock()

@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method in {"POST", "PATCH", "DELETE", "PUT"} and request.url.path.startswith("/api/"):
        if request.headers.get("x-careernova-client") != "web":
            return JSONResponse({"detail": "Missing request protection header"}, status_code=403)
    if request.url.path in {"/api/auth/login", "/api/auth/register", "/api/auth/forgot-password", "/api/auth/reset-password"} and request.method == "POST":
        key = request.client.host if request.client else "unknown"
        now = monotonic()
        with _rate_lock:
            for old_key in list(_auth_attempts):
                if not _auth_attempts[old_key] or _auth_attempts[old_key][-1] <= now-900:
                    del _auth_attempts[old_key]
            attempts = _auth_attempts[key]
            while attempts and attempts[0] <= now-900:
                attempts.popleft()
            if len(attempts) >= 30:
                return JSONResponse({"detail": "Too many attempts. Try again in 15 minutes."}, status_code=429, headers={"Retry-After":"900"})
            attempts.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/resume-match")
async def resume_match(file: UploadFile = File(...), limit: int = Query(20, ge=1, le=50), user=Depends(get_current_user)):
    from starlette.concurrency import run_in_threadpool
    content = await file.read(5*1024*1024+1)
    await file.close()
    if not content or len(content)>5*1024*1024:
        raise HTTPException(400, "Resume must be nonempty and at most 5 MB")
    try:
        resume = await run_in_threadpool(extract_resume_text, file.filename or "", content)
    except Exception as exc:
        raise HTTPException(400, "Unable to read resume. Use a text-based PDF or DOCX.") from exc
    from resume_job_matching import match_resume_jobs
    jobs = await run_in_threadpool(match_resume_jobs, resume, limit)
    from job_identity import annotate_tracking,deduplicate_jobs
    with engine.connect() as conn:
        jobs=annotate_tracking(deduplicate_jobs(jobs),user['id'],conn)
    return {"jobs": jobs}


from feature_schema import configure_features
from career_tools_routes import router as tools_router
from oauth_routes import router as oauth_router
app.include_router(tools_router)
app.include_router(oauth_router)

from search_history_routes import router as search_history_router
app.include_router(search_history_router)

from chatbot_routes import router as chatbot_router
app.include_router(chatbot_router)

from mock_interview_routes import router as mock_interview_router
app.include_router(mock_interview_router)

from job_preparation_routes import router as job_preparation_router
app.include_router(job_preparation_router)
