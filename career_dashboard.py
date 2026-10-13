
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from typing import Literal

router = APIRouter(prefix="/api/dashboard", tags=["Career Dashboard"])

Status = Literal["Saved", "Applied", "Interview", "Offer", "Rejected"]


class SaveJob(BaseModel):
    job_id: str
    job_title: str
    company: str | None = None
    location: str | None = None
    apply_url: str | None = None
    match_percentage: float | None = Field(default=None, ge=0, le=100)


class UpdateJob(BaseModel):
    status: Status
    notes: str | None = None


# Temporary local development identity.
# Replace with authenticated user identity before deployment.
DEV_USER = "local_demo_user"


def get_engine():
    from backend import engine
    return engine


@router.post("/save", status_code=201)
def save_job(job: SaveJob):
    if not job.job_id.strip() or not job.job_title.strip():
        raise HTTPException(400, "Job ID and title are required")

    query = text("""
        INSERT INTO public.career_job_tracker (
            user_id, job_id, job_title, company,
            location, apply_url, match_percentage
        )
        VALUES (
            :user_id, :job_id, :job_title, :company,
            :location, :apply_url, :match_percentage
        )
        ON CONFLICT (user_id, job_id) DO NOTHING
        RETURNING id
    """)

    values = {
        **job.model_dump(),
        "user_id": DEV_USER,
        "job_id": job.job_id.strip(),
        "job_title": job.job_title.strip()
    }

    try:
        with get_engine().begin() as connection:
            result = connection.execute(query, values).scalar_one_or_none()

        return {
            "message": "Job saved" if result else "Job already saved",
            "id": result
        }
    except Exception as exc:
        print("Save job error:", exc)
        raise HTTPException(500, "Unable to save job") from exc


@router.get("/jobs")
def tracked_jobs(
    limit: int = Query(default=100, ge=1, le=500)
):
    query = text("""
        SELECT *
        FROM public.career_job_tracker
        WHERE user_id = :user_id
        ORDER BY saved_at DESC
        LIMIT :limit
    """)

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(
                query, {"user_id": DEV_USER, "limit": limit}
            ).mappings().all()

        return {"jobs": [dict(row) for row in rows]}
    except Exception as exc:
        print("Dashboard jobs error:", exc)
        raise HTTPException(500, "Unable to load jobs") from exc


@router.patch("/jobs/{tracker_id}")
def update_job(tracker_id: int, data: UpdateJob):
    query = text("""
        UPDATE public.career_job_tracker
        SET status = :status,
            notes = :notes,
            updated_at = NOW()
        WHERE id = :id AND user_id = :user_id
        RETURNING id, status, notes
    """)

    try:
        with get_engine().begin() as connection:
            row = connection.execute(query, {
                "id": tracker_id,
                "user_id": DEV_USER,
                "status": data.status,
                "notes": data.notes
            }).mappings().first()

        if not row:
            raise HTTPException(404, "Tracked job not found")

        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        print("Update job error:", exc)
        raise HTTPException(500, "Unable to update job") from exc


@router.delete("/jobs/{tracker_id}")
def remove_job(tracker_id: int):
    query = text("""
        DELETE FROM public.career_job_tracker
        WHERE id = :id AND user_id = :user_id
        RETURNING id
    """)

    try:
        with get_engine().begin() as connection:
            deleted = connection.execute(query, {
                "id": tracker_id,
                "user_id": DEV_USER
            }).scalar_one_or_none()

        if deleted is None:
            raise HTTPException(404, "Tracked job not found")

        return {"message": "Job removed"}
    except HTTPException:
        raise
    except Exception as exc:
        print("Remove job error:", exc)
        raise HTTPException(500, "Unable to remove job") from exc


@router.get("/stats")
def dashboard_stats():
    query = text("""
        SELECT
            COUNT(*) AS total_jobs,
            COUNT(*) FILTER (WHERE status = 'Saved') AS saved,
            COUNT(*) FILTER (WHERE status = 'Applied') AS applied,
            COUNT(*) FILTER (WHERE status = 'Interview') AS interviews,
            COUNT(*) FILTER (WHERE status = 'Offer') AS offers,
            COUNT(*) FILTER (WHERE status = 'Rejected') AS rejected,
            ROUND(AVG(match_percentage), 1) AS average_match
        FROM public.career_job_tracker
        WHERE user_id = :user_id
    """)

    try:
        with get_engine().connect() as connection:
            result = connection.execute(
                query, {"user_id": DEV_USER}
            ).mappings().one()

        return dict(result)
    except Exception as exc:
        print("Dashboard stats error:", exc)
        raise HTTPException(500, "Unable to load statistics") from exc
