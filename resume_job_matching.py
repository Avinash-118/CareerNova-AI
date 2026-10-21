"""Prefer the local semantic index, with a lightweight live-listing fallback."""
import html
import re
from fastapi import HTTPException
from faiss_search import INDEX_PATH, METADATA_PATH, semantic_search
from live_jobs import fetch_live_jobs
from match_scoring import calculate_match, find_skills

STOP = set('the and for with from that this your you our are will have has job work team role experience years skills company position responsibilities requirements about into using'.split())


def words(value):
    plain = html.unescape(re.sub(r'<[^>]+>', ' ', value or '')).lower()
    return {w for w in re.findall(r'[a-z][a-z0-9+#.-]{2,}', plain) if w not in STOP}


def match_resume_jobs(resume, limit=20):
    if INDEX_PATH.is_file() and METADATA_PATH.is_file():
        jobs = semantic_search(resume[:20000], limit)
        for job in jobs:
            job.update(calculate_match(resume, str(job.get('description', job.get('job_description', ''))), job.get('faiss_score', 0)))
        return jobs
    # Resume contents stay here; the feed request contains no candidate information.
    listings = fetch_live_jobs()
    if not listings:
        raise HTTPException(503, 'Live job feeds are temporarily unavailable. Please try again shortly.')
    resume_words = words(resume)
    resume_skills = set(find_skills(resume))
    ranked = []
    for listing in listings:
        job = dict(listing)
        description = html.unescape(re.sub(r'<[^>]+>', ' ', str(job.get('description', ''))))
        job_words = words(str(job.get('title', '')) + ' ' + description)
        overlap = resume_words & job_words
        required = set(find_skills(description))
        matched = sorted(required & resume_skills)
        if not matched and len(overlap) < 2:
            continue
        keyword_score = len(overlap) / max(1, len(job_words))
        skill_score = len(matched) / len(required) if required else None
        score = (0.7 * skill_score + 0.3 * keyword_score) if skill_score is not None else keyword_score
        job.update(match_percentage=round(score * 100, 1), matched_skills=matched,
                   missing_skills=sorted(required - resume_skills),
                   skill_match_percentage=round(skill_score * 100, 1) if skill_score is not None else None,
                   matching_method='live_keywords', faiss_score=None)
        ranked.append(job)
    ranked.sort(key=lambda j: j['match_percentage'], reverse=True)
    return ranked[:limit]
