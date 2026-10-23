from job_identity import deduplicate_jobs

import os
import time
import threading
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_SECONDS = 900
_cache = {"time": 0, "jobs": [], "sources": {}}
_source_cache = {}
_refresh_lock = threading.Lock()


def iso_date(value):
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return str(value or '')


def unexpired(job):
    expiry = job.get('expires_at')
    if not expiry:
        return True
    try:
        return datetime.fromisoformat(expiry.replace('Z', '+00:00')).timestamp() > time.time()
    except (ValueError, TypeError):
        return False


def fetch_himalayas():
    jobs=[]
    cursor=None
    seen=set()
    # Bounded daily sample keeps the free service's memory and API use small.
    for _ in range(5):
        params={'limit':20}
        if cursor:params['cursor']=cursor
        data=get_json('https://himalayas.app/jobs/api',params)
        for item in data.get('jobs',[]):
            link=item.get('applicationLink')
            if not link:continue
            job=make_job('Himalayas',item.get('guid') or link,item.get('title'),item.get('companyName'),
                ', '.join(item.get('locationRestrictions') or []) or 'Worldwide',
                item.get('employmentType'),item.get('description') or item.get('excerpt'),link,iso_date(item.get('pubDate')))
            job.update(source_url='https://himalayas.app',work_mode='Remote',expires_at=iso_date(item.get('expiryDate')),
                timezone_restrictions=item.get('timezoneRestrictions') or [],
                min_salary=item.get('minSalary'),max_salary=item.get('maxSalary'),salary_currency=item.get('currency'),salary_period=item.get('salaryPeriod'))
            if unexpired(job):jobs.append(job)
        cursor=data.get('nextCursor')
        if not cursor or cursor in seen:break
        seen.add(cursor)
    return jobs


def fetch_arbeitnow():
    jobs=[]
    data=get_json('https://www.arbeitnow.com/api/job-board-api')
    for item in data.get('data',[]):
        if not item.get('url'):continue
        job=make_job('Arbeitnow',item.get('slug') or item['url'],item.get('title'),item.get('company_name'),
            item.get('location'),', '.join(item.get('job_types') or []) or 'Not specified',
            item.get('description'),item['url'],iso_date(item.get('created_at')))
        job.update(source_url='https://www.arbeitnow.com',work_mode='Remote' if item.get('remote') else 'Not specified')
        jobs.append(job)
    return jobs


def daily_feed(name, fetcher):
    cached=_source_cache.get(name)
    if cached and time.time()-cached['time']<86400:
        return [j for j in cached['jobs'] if unexpired(j)]
    jobs=fetcher()
    _source_cache[name]={'time':time.time(),'jobs':jobs}
    return jobs


def get_json(url, params=None):
    response = requests.get(
        url,
        params=params,
        timeout=20,
        headers={"Accept": "application/json"}
    )
    response.raise_for_status()
    return response.json()


def make_job(source, job_id, title, company, location,
             employment_type, description, url, published_at=""):
    return {
        "id": f"{source}:{job_id}",
        "title": title or "Untitled",
        "company": company or "Unknown",
        "location": location or "Not specified",
        "employment_type": employment_type or "Not specified",
        "description": description or "",
        "url": url or "",
        "source": source,
        "published_at": str(published_at or ""),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


def fetch_remotive():
    data = get_json("https://remotive.com/api/remote-jobs")
    return [
        make_job(
            "Remotive", j.get("id"), j.get("title"),
            j.get("company_name"),
            j.get("candidate_required_location", "Remote"),
            j.get("job_type"), j.get("description"),
            j.get("url"), j.get("publication_date")
        )
        for j in data.get("jobs", [])
    ]


def fetch_greenhouse(board):
    data = get_json(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
        {"content": "true"}
    )
    return [
        make_job(
            "Greenhouse", f"{board}:{j.get('id')}",
            j.get("title"), board,
            (j.get("location") or {}).get("name"),
            "Not specified", j.get("content"),
            j.get("absolute_url"), j.get("updated_at")
        )
        for j in data.get("jobs", [])
    ]


def fetch_lever(site):
    jobs = []
    for skip in range(0, 1000, 100):
        data = get_json(
            f"https://api.lever.co/v0/postings/{site}",
            {"mode": "json", "skip": skip, "limit": 100}
        )
        if not isinstance(data, list):
            break

        for j in data:
            category = j.get("categories") or {}
            jobs.append(make_job(
                "Lever", f"{site}:{j.get('id')}",
                j.get("text"), site,
                category.get("location"),
                category.get("commitment"),
                j.get("descriptionPlain") or j.get("description"),
                j.get("hostedUrl") or j.get("applyUrl"),
                j.get("createdAt")
            ))

        if len(data) < 100:
            break
    return jobs


def configured_boards(name):
    import re
    values = os.getenv(name, "").split(",")
    return [
        x.strip() for x in values
        if re.fullmatch(r"[A-Za-z0-9_-]+", x.strip())
    ]


def fetch_live_jobs(force_refresh=False):
    with _refresh_lock:
        return _fetch_live_jobs(force_refresh)


def _fetch_live_jobs(force_refresh=False):
    if not force_refresh and time.time() - _cache["time"] < CACHE_SECONDS:
        return [j for j in _cache['jobs'] if unexpired(j)]

    # Remotive is excluded: its public feed disallows signup-gated listings.
    tasks = [('Himalayas',lambda:daily_feed('Himalayas',fetch_himalayas)),
             ('Arbeitnow',lambda:daily_feed('Arbeitnow',fetch_arbeitnow))]

    for board in configured_boards("GREENHOUSE_BOARDS"):
        tasks.append((
            f"Greenhouse:{board}",
            lambda board=board: fetch_greenhouse(board)
        ))

    for site in configured_boards("LEVER_SITES"):
        tasks.append((
            f"Lever:{site}",
            lambda site=site: fetch_lever(site)
        ))

    all_jobs = []
    status = {}

    with ThreadPoolExecutor(max_workers=min(10, len(tasks))) as pool:
        futures = {
            pool.submit(function): name
            for name, function in tasks
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                all_jobs.extend(result)
                status[name] = len(result)
            except Exception as error:
                status[name] = f"Unavailable ({type(error).__name__})"
                print(f"{name} failed ({type(error).__name__})")

    jobs = deduplicate_jobs(all_jobs)

    # Do not silently retain closed listings indefinitely after a source outage.
    _cache["jobs"] = jobs

    _cache["time"] = time.time()
    _cache["sources"] = status
    return [j for j in _cache['jobs'] if unexpired(j)]


def get_source_status():
    return dict(_cache["sources"])


if __name__ == "__main__":
    jobs = fetch_live_jobs(force_refresh=True)
    print("Total jobs:", len(jobs))
    print("Sources:", get_source_status())
