from job_identity import deduplicate_jobs,tracked_match
"""Account-owned in-app job alerts. Refresh explicitly checks current live feeds."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from auth_routes import get_current_user
from live_jobs import fetch_live_jobs
from live_jobs_routes import filter_jobs

router = APIRouter(prefix='/api', tags=['Job alerts'])
engine = None


def configure_platform(db):
    global engine
    engine = db
    with db.begin() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS public.job_alert_rules (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            query TEXT NOT NULL, location TEXT NOT NULL DEFAULT '', enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW())'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS public.job_notifications (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            alert_id BIGINT NOT NULL REFERENCES public.job_alert_rules(id) ON DELETE CASCADE,
            job_id TEXT NOT NULL, title TEXT NOT NULL, company TEXT, url TEXT,
            read BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(alert_id, job_id))'''))


class AlertRule(BaseModel):
    query: str = Field(min_length=2, max_length=160)
    location: str = Field(default='', max_length=160)


class AlertToggle(BaseModel):
    enabled: bool


@router.get('/alerts')
def alerts(user=Depends(get_current_user)):
    with engine.connect() as conn:
        rules = conn.execute(text('SELECT * FROM public.job_alert_rules WHERE user_id=:u ORDER BY id DESC'), {'u':user['id']}).mappings().all()
        notices = conn.execute(text('SELECT * FROM public.job_notifications WHERE user_id=:u ORDER BY id DESC LIMIT 100'), {'u':user['id']}).mappings().all()
    return {'rules': [dict(r) for r in rules], 'notifications': [dict(r) for r in notices]}


@router.post('/alerts', status_code=201)
def add_alert(data: AlertRule, user=Depends(get_current_user)):
    with engine.begin() as conn:
        # Serialize rule creation per account to enforce the free limit under concurrency.
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'), {'u':user['id']})
        count = conn.execute(text('SELECT COUNT(*) FROM public.job_alert_rules WHERE user_id=:u'), {'u':user['id']}).scalar_one()
        if count >= 20:
            raise HTTPException(400, 'You can create up to 20 alerts')
        row = conn.execute(text('INSERT INTO public.job_alert_rules (user_id, query, location) VALUES (:u,:q,:l) RETURNING id'), {'u':user['id'], 'q':data.query.strip(), 'l':data.location.strip()}).scalar_one()
    return {'id':row}


@router.patch('/alerts/{rule_id}')
def toggle_alert(rule_id: int, data: AlertToggle, user=Depends(get_current_user)):
    with engine.begin() as conn:
        found = conn.execute(text('UPDATE public.job_alert_rules SET enabled=:e WHERE id=:id AND user_id=:u RETURNING id'), {'e':data.enabled,'id':rule_id,'u':user['id']}).scalar_one_or_none()
        if found is None:
            raise HTTPException(404, 'Alert not found')
    return {'message':'Alert updated'}


@router.delete('/alerts/{rule_id}')
def delete_alert(rule_id: int, user=Depends(get_current_user)):
    with engine.begin() as conn:
        found = conn.execute(text('DELETE FROM public.job_alert_rules WHERE id=:id AND user_id=:u RETURNING id'), {'id':rule_id,'u':user['id']}).scalar_one_or_none()
        if found is None:
            raise HTTPException(404, 'Alert not found')
    return {'message':'Alert removed'}


@router.post('/alerts/check')
def check_alerts(user=Depends(get_current_user)):
    jobs = deduplicate_jobs(fetch_live_jobs())
    with engine.begin() as conn:
        rules = conn.execute(text('SELECT * FROM public.job_alert_rules WHERE user_id=:u AND enabled=TRUE'), {'u':user['id']}).mappings().all()
        added = 0
        for rule in rules:
            existing=[dict(row) for row in conn.execute(text('SELECT job_id,title AS job_title,company,url AS apply_url FROM public.job_notifications WHERE alert_id=:id'),{'id':rule['id']}).mappings().all()]
            for job in filter_jobs(jobs, query=rule['query'], location=rule['location'])[:100]:
                if tracked_match(job,existing):continue
                result = conn.execute(text('''INSERT INTO public.job_notifications (user_id, alert_id, job_id, title, company, url)
                    VALUES (:u,:a,:j,:t,:c,:url) ON CONFLICT (alert_id,job_id) DO NOTHING RETURNING id'''),
                    {'u':user['id'],'a':rule['id'],'j':str(job.get('id') or job.get('apply_url') or job.get('url') or job['title']+job.get('company','')),
                     't':job['title'],'c':job.get('company',''),'url':job.get('apply_url') or job.get('url','')}).scalar_one_or_none()
                if result is not None:
                    existing.append({"job_id":str(job.get("id","")),"job_title":job["title"],"company":job.get("company",""),"apply_url":job.get("apply_url") or job.get("url","")})
                added += result is not None
    return {'message':f'{added} new matches added', 'checked_jobs':len(jobs)}


@router.post('/notifications/read')
def read_notifications(user=Depends(get_current_user)):
    with engine.begin() as conn:
        conn.execute(text('UPDATE public.job_notifications SET read=TRUE WHERE user_id=:u'), {'u':user['id']})
    return {'message':'All notifications marked as read'}
