import pandas as pd
from advanced_job_filters import filter_frame
from typing import Literal
from auth_routes import get_current_user
from job_identity import deduplicate_jobs,annotate_tracking
from database import engine

import math
from fastapi import APIRouter, Query, Depends
from live_jobs import fetch_live_jobs, get_source_status

router = APIRouter(prefix="/api", tags=["Live Jobs"])


def filter_jobs(jobs, query="", employment_type="", location="",
                work_arrangement=""):
    results = []

    categories = {
        "internship": ["intern", "internship", "co-op"],
        "research": ["research", "postdoc", "graduate assistant"],
        "full-time": ["full-time", "full time", "fulltime"],
        "part-time": ["part-time", "part time", "parttime"],
        "contract": ["contract", "freelance"],
        "temporary": ["temporary", "seasonal"]
    }

    for job in jobs:
        searchable = " ".join(str(job.get(key, "")) for key in
                              ["title", "company", "location", "description"]).lower()

        if query and not all(word in searchable for word in query.lower().split()):
            continue

        if location and location.lower() not in job["location"].lower():
            continue

        if employment_type and employment_type.lower() not in ["all", "all jobs"]:
            kind = employment_type.lower()
            text = (job["title"] + " " + job["employment_type"]).lower()
            options = categories.get(kind, [kind])
            if not any(option in text for option in options):
                continue

        if work_arrangement:
            arrangement = work_arrangement.lower()
            text = (job["location"] + " " + job["title"] + " " + job.get("work_mode", "")).lower()
            if arrangement in ["remote", "hybrid", "on-site"]:
                if arrangement not in text:
                    continue

        results.append(job)

    return results


@router.get("/live-jobs")
def get_live_jobs(refresh: bool = False,user=Depends(get_current_user)):
    jobs = deduplicate_jobs(fetch_live_jobs(force_refresh=refresh))
    return {
        "total": len(jobs),
        "source": "Multiple sources",
        "sources": get_source_status(),
        "jobs": owned_job_results(jobs,user)
    }


@router.get("/jobs/discover")
def discover_jobs(
    query: str = "",
    employment_type: str = "",
    location: str = "",
    work_arrangement: str = "",
    company: str = Query('', max_length=200),
    skills: str = Query('', max_length=500),
    exclude: str = Query('', max_length=500),
    seniority: Literal['', 'entry', 'senior', 'lead'] = '',
    posted_days: int = Query(0, ge=0, le=365),
    sort: Literal['relevance', 'newest', 'title', 'company'] = 'relevance',
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    refresh: bool = False,
    user=Depends(get_current_user)
):
    jobs = deduplicate_jobs(fetch_live_jobs(force_refresh=refresh))

    filtered = filter_jobs(
        jobs, query, employment_type, location, work_arrangement
    )

    if filtered:
        filtered = filter_frame(pd.DataFrame(filtered), company, skills, exclude, seniority, posted_days, sort).to_dict(orient='records')
    start = (page - 1) * limit

    return {
        "total": len(filtered),
        "available_total": len(jobs),
        "page": page,
        "limit": limit,
        "pages": math.ceil(len(filtered) / limit),
        "sources": get_source_status(),
        "jobs": owned_job_results(filtered[start:start + limit],user)
    }


def owned_job_results(jobs,user):
    with engine.connect() as conn:
        return annotate_tracking(jobs,user["id"],conn)
