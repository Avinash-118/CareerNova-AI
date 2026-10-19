import os
from advanced_job_filters import filter_frame
from typing import Literal
from auth_routes import get_current_user
from job_identity import annotate_tracking
from database import engine

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Query, Depends, HTTPException

router = APIRouter(prefix="/api", tags=["Historical Jobs"])

BASE_DIR = Path(os.getenv('JOB_DATA_DIR',str(Path(__file__).resolve().parent)))
DATA_PATH = BASE_DIR / "jobs_metadata.parquet"

jobs_df = pd.read_parquet(DATA_PATH).fillna("") if DATA_PATH.is_file() else None


@router.get("/historical-jobs")
def historical_jobs(
    query: str = "",
    employment_type: str = "",
    work_mode: str = "",
    location: str = "",
    visa_sponsorship: str = "",
    company: str = Query('', max_length=200),
    skills: str = Query('', max_length=500),
    exclude: str = Query('', max_length=500),
    seniority: Literal['', 'entry', 'senior', 'lead'] = '',
    posted_days: int = Query(0, ge=0, le=365),
    sort: Literal['relevance', 'newest', 'title', 'company'] = 'relevance',
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    user=Depends(get_current_user),
):
    if jobs_df is None:
        raise HTTPException(503, 'Historical dataset is not installed on this backend. Select Live Jobs.')
    filtered = jobs_df

    if query.strip():
        term = query.strip()
        mask = (
            filtered["title"].astype(str).str.contains(term, case=False, regex=False)
            | filtered["company"].astype(str).str.contains(term, case=False, regex=False)
            | filtered["search_text"].astype(str).str.contains(term, case=False, regex=False)
        )
        filtered = filtered[mask]

    for column, value in [
        ("employment_type", employment_type),
        ("work_mode", work_mode),
        ("location", location),
        ("visa_sponsorship", visa_sponsorship),
    ]:
        if value.strip():
            filtered = filtered[
                filtered[column].astype(str).str.contains(
                    value.strip(), case=False, regex=False
                )
            ]

    filtered = filter_frame(filtered, company, skills, exclude, seniority, posted_days, sort)
    total = len(filtered)
    start = (page - 1) * limit
    records = filtered.iloc[start:start + limit]

    jobs = []
    for record in records.to_dict(orient="records"):
        jobs.append({
            "id": str(record.get("id", "")),
            "title": record.get("title", ""),
            "company": record.get("company", ""),
            "location": record.get("location", ""),
            "employment_type": record.get("employment_type", ""),
            "work_mode": record.get("work_mode", ""),
            "visa_sponsorship": record.get("visa_sponsorship", ""),
            "url": record.get("apply_url", ""),
            "source": record.get("source_slug", ""),
            "listing_status": "historical_unverified",
        })

    with engine.connect() as conn:
        jobs=annotate_tracking(jobs,user["id"],conn)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "jobs": jobs,
    }
