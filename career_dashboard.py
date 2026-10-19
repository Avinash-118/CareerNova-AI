"""Account-owned job tracker with transactional activity history."""
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy import text
from auth_routes import get_current_user
from application_history import record_event
from job_identity import tracked_match
router=APIRouter(prefix='/api/dashboard',tags=['Career Dashboard'])
Status=Literal['Saved','Applied','Interview','Offer','Rejected']

class SaveJob(BaseModel):
    job_id:str=Field(min_length=1,max_length=2000)
    job_title:str=Field(min_length=1,max_length=500)
    company:str|None=None
    location:str|None=None
    apply_url:str|None=None
    match_percentage:float|None=Field(default=None,ge=0,le=100)

class UpdateJob(BaseModel):
    status:Status
    notes:str|None=Field(default=None,max_length=10000)

def get_engine():
    from database import engine
    return engine

@router.post('/save',status_code=201)
def save_job(job:SaveJob,user=Depends(get_current_user)):
    if not job.job_id.strip() or not job.job_title.strip():raise HTTPException(400,'Job ID and title are required')
    payload={**job.model_dump(),'job_id':job.job_id.strip(),'job_title':job.job_title.strip()}
    with get_engine().begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']})
        tracked=[dict(row) for row in conn.execute(text('SELECT * FROM public.career_job_tracker WHERE user_id=:u'),{'u':str(user['id'])}).mappings().all()]
        existing=tracked_match({'id':payload['job_id'],**payload},tracked)
        if existing:return {'message':'Job already tracked','id':existing['id'],'status':existing['status'],'already_tracked':True}
        tracker_id=conn.execute(text('''INSERT INTO public.career_job_tracker
            (user_id,job_id,job_title,company,location,apply_url,match_percentage)
            VALUES(:u,:job_id,:job_title,:company,:location,:apply_url,:match_percentage) RETURNING id'''),
            {'u':str(user['id']),**payload}).scalar_one()
        record_event(conn,user['id'],tracker_id,'saved','Opportunity saved',event_key='baseline')
    return {'message':'Job saved','id':tracker_id,'status':'Saved','already_tracked':False}

@router.get('/jobs')
def tracked_jobs(limit:int=Query(100,ge=1,le=500),user=Depends(get_current_user)):
    with get_engine().connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.career_job_tracker WHERE user_id=:u ORDER BY saved_at DESC,id DESC LIMIT :limit'),{'u':str(user['id']),'limit':limit}).mappings().all()
    return {'jobs':[dict(row) for row in rows]}

@router.patch('/jobs/{tracker_id}')
def update_job(tracker_id:int,data:UpdateJob,user=Depends(get_current_user)):
    with get_engine().begin() as conn:
        previous=conn.execute(text('SELECT * FROM public.career_job_tracker WHERE id=:id AND user_id=:u FOR UPDATE'),{'id':tracker_id,'u':str(user['id'])}).mappings().first()
        if not previous:raise HTTPException(404,'Tracked job not found')
        notes=previous['notes'] if data.notes is None else data.notes
        changed=previous['status']!=data.status or (previous['notes'] or '')!=(notes or '')
        if changed:
            conn.execute(text('UPDATE public.career_job_tracker SET status=:s,notes=:n,updated_at=NOW() WHERE id=:id'),{'s':data.status,'n':notes,'id':tracker_id})
            if previous['status']!=data.status:record_event(conn,user['id'],tracker_id,'status',f"Stage changed: {previous['status']} to {data.status}")
            if (previous['notes'] or '')!=(notes or ''):record_event(conn,user['id'],tracker_id,'notes','Application notes updated',notes or 'Notes cleared.')
    return {'id':tracker_id,'status':data.status,'notes':notes}

@router.delete('/jobs/{tracker_id}')
def remove_job(tracker_id:int,user=Depends(get_current_user)):
    with get_engine().begin() as conn:
        row=conn.execute(text('DELETE FROM public.career_job_tracker WHERE id=:id AND user_id=:u RETURNING id'),{'id':tracker_id,'u':str(user['id'])}).scalar_one_or_none()
        if row is None:raise HTTPException(404,'Tracked job not found')
    return {'message':'Job removed'}

@router.get('/stats')
def dashboard_stats(user=Depends(get_current_user)):
    with get_engine().connect() as conn:
        row=conn.execute(text('''SELECT COUNT(*) AS total_jobs,
            COUNT(*) FILTER(WHERE status='Saved') AS saved,COUNT(*) FILTER(WHERE status='Applied') AS applied,
            COUNT(*) FILTER(WHERE status='Interview') AS interviews,COUNT(*) FILTER(WHERE status='Offer') AS offers,
            COUNT(*) FILTER(WHERE status='Rejected') AS rejected,ROUND(AVG(match_percentage),1) AS average_match
            FROM public.career_job_tracker WHERE user_id=:u'''),{'u':str(user['id'])}).mappings().one()
    return dict(row)

def configure_dashboard(engine):
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS public.career_job_tracker (
            id BIGSERIAL PRIMARY KEY,user_id TEXT NOT NULL,job_id TEXT NOT NULL,job_title TEXT NOT NULL,
            company TEXT,location TEXT,apply_url TEXT,match_percentage NUMERIC,status TEXT NOT NULL DEFAULT 'Saved',
            notes TEXT,saved_at TIMESTAMPTZ DEFAULT NOW(),updated_at TIMESTAMPTZ DEFAULT NOW(),UNIQUE(user_id,job_id))'''))
