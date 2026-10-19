from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import text
from auth_routes import get_current_user
from application_history import record_event
from database import engine
import json
router=APIRouter(prefix='/api',tags=['Searches and timeline'])

class SearchFilters(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    source:Literal['historical','live']='historical'
    term:str=Field(default='',max_length=200)
    type:Literal['','full-time','part-time','internship','contract','temporary','research']=''
    mode:Literal['','remote','hybrid','on-site']=''
    city:str=Field(default='',max_length=200)
    field:str=Field(default='',max_length=120)

    company:str=Field(default='',max_length=200)
    skills:str=Field(default='',max_length=500)
    exclude:str=Field(default='',max_length=500)
    seniority:Literal['','entry','senior','lead']=''
    posted_days:int=Field(default=0,ge=0,le=365)
    sort:Literal['relevance','newest','title','company']='relevance'

class SavedSearchData(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    name:str=Field(min_length=1,max_length=100)
    filters:SearchFilters

@router.get('/saved-searches')
def saved_searches(user=Depends(get_current_user)):
    with engine.connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.saved_searches WHERE user_id=:u ORDER BY updated_at DESC,id DESC'),{'u':user['id']}).mappings().all()
    return {'searches':[dict(r) for r in rows]}

@router.get('/saved-searches/{search_id}')
def saved_search(search_id:int,user=Depends(get_current_user)):
    with engine.connect() as conn:
        row=conn.execute(text('SELECT * FROM public.saved_searches WHERE id=:id AND user_id=:u'),{'id':search_id,'u':user['id']}).mappings().first()
    if not row:raise HTTPException(404,'Saved search not found')
    return dict(row)

@router.post('/saved-searches',status_code=201)
def save_search(data:SavedSearchData,user=Depends(get_current_user)):
    with engine.begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']})
        count=conn.execute(text('SELECT COUNT(*) FROM public.saved_searches WHERE user_id=:u'),{'u':user['id']}).scalar_one()
        if count>=30:raise HTTPException(400,'You can save up to 30 searches')
        row=conn.execute(text('INSERT INTO public.saved_searches(user_id,name,filters) VALUES(:u,:n,CAST(:f AS JSONB)) RETURNING *'),{'u':user['id'],'n':data.name,'f':json.dumps(data.filters.model_dump(exclude_unset=True))}).mappings().one()
    return dict(row)

@router.patch('/saved-searches/{search_id}')
def update_search(search_id:int,data:SavedSearchData,user=Depends(get_current_user)):
    with engine.begin() as conn:
        row=conn.execute(text('UPDATE public.saved_searches SET name=:n,filters=CAST(:f AS JSONB),updated_at=NOW() WHERE id=:id AND user_id=:u RETURNING *'),{'id':search_id,'u':user['id'],'n':data.name,'f':json.dumps(data.filters.model_dump(exclude_unset=True))}).mappings().first()
    if not row:raise HTTPException(404,'Saved search not found')
    return dict(row)

@router.delete('/saved-searches/{search_id}')
def delete_search(search_id:int,user=Depends(get_current_user)):
    with engine.begin() as conn:
        row=conn.execute(text('DELETE FROM public.saved_searches WHERE id=:id AND user_id=:u RETURNING id'),{'id':search_id,'u':user['id']}).scalar_one_or_none()
    if row is None:raise HTTPException(404,'Saved search not found')
    return {'message':'Saved search removed'}

@router.get('/timeline')
def timeline(tracker_id:int|None=None,before:int|None=Query(None,ge=1),limit:int=Query(50,ge=1,le=100),user=Depends(get_current_user)):
    with engine.connect() as conn:
        if tracker_id is not None and not conn.execute(text('SELECT id FROM public.career_job_tracker WHERE id=:id AND user_id=:u'),{'id':tracker_id,'u':str(user['id'])}).first():
            raise HTTPException(404,'Application not found')
        # Cursor is an event ID; compare its chronological tuple for stable backdated paging.
        cursor=None
        if before is not None:
            cursor=conn.execute(text('SELECT occurred_at,id FROM public.application_events WHERE id=:id AND user_id=:u'),{'id':before,'u':user['id']}).mappings().first()
            if not cursor:raise HTTPException(404,'Timeline cursor not found')
        rows=conn.execute(text('''SELECT e.*,t.job_title,t.company,t.status AS current_status
            FROM public.application_events e JOIN public.career_job_tracker t ON t.id=e.tracker_id
            WHERE e.user_id=:u AND (:tracker IS NULL OR e.tracker_id=:tracker)
            AND (:cursor_id IS NULL OR (e.occurred_at,e.id)<(:cursor_time,:cursor_id))
            ORDER BY e.occurred_at DESC,e.id DESC LIMIT :limit'''),{'u':user['id'],'tracker':tracker_id,'cursor_id':cursor['id'] if cursor else None,'cursor_time':cursor['occurred_at'] if cursor else None,'limit':limit+1}).mappings().all()
    return {'events':[dict(r) for r in rows[:limit]],'next_cursor':rows[limit-1]['id'] if len(rows)>limit else None}

class TimelineEvent(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    tracker_id:int
    kind:Literal['Recruiter reply','Interview','Follow-up','Note','Offer','Submission']='Note'
    title:str=Field(min_length=2,max_length=200)
    body:str=Field(default='',max_length=10000)
    occurred_at:datetime

@router.post('/timeline',status_code=201)
def add_event(data:TimelineEvent,user=Depends(get_current_user)):
    if data.occurred_at.tzinfo is None:raise HTTPException(400,'Event date must include a timezone')
    with engine.begin() as conn:
        if not conn.execute(text('SELECT id FROM public.career_job_tracker WHERE id=:id AND user_id=:u FOR UPDATE'),{'id':data.tracker_id,'u':str(user['id'])}).first():raise HTTPException(404,'Application not found')
        event_id=record_event(conn,user['id'],data.tracker_id,data.kind,data.title,data.body,data.occurred_at)
    return {'id':event_id,'message':'Timeline event added'}

@router.delete('/timeline/{event_id}')
def delete_event(event_id:int,user=Depends(get_current_user)):
    with engine.begin() as conn:
        row=conn.execute(text('SELECT event_key,kind FROM public.application_events WHERE id=:id AND user_id=:u FOR UPDATE'),{'id':event_id,'u':user['id']}).mappings().first()
        if not row:raise HTTPException(404,'Timeline event not found')
        if row['event_key'] or row['kind'] in {'status','notes','details','saved','baseline'}:raise HTTPException(400,'Automatic history entries cannot be removed individually')
        conn.execute(text('DELETE FROM public.application_events WHERE id=:id AND user_id=:u'),{'id':event_id,'u':user['id']})
    return {'message':'Timeline event removed'}
