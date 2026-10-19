import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text
from auth_routes import get_current_user
from database import engine
from mock_interview_service import make_questions, make_report

router=APIRouter(prefix='/api/mock-interviews',tags=['Guided interview'])


class InterviewStart(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    role:str=Field(min_length=2,max_length=200)
    resume_id:int|None=None
    job_description:str=Field(default='',max_length=30000)


class InterviewAnswer(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    question_id:str=Field(min_length=1,max_length=80)
    answer:str=Field(default='',max_length=10000)


def owned(conn, interview_id, uid, lock=False):
    row=conn.execute(text('SELECT * FROM public.mock_interviews WHERE id=:id AND user_id=:u'+(' FOR UPDATE' if lock else '')),{'id':interview_id,'u':uid}).mappings().first()
    if not row:raise HTTPException(404,'Interview not found')
    return row


@router.post('',status_code=201)
def create(data:InterviewStart,user=Depends(get_current_user)):
    with engine.begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']})
        if conn.execute(text('SELECT COUNT(*) FROM public.mock_interviews WHERE user_id=:u'),{'u':user['id']}).scalar_one()>=100:
            raise HTTPException(400,'Remove an older interview before creating another (100 session limit).')
        resume=None
        if data.resume_id is not None:
            resume=conn.execute(text('SELECT name,extracted_text FROM public.resume_versions WHERE id=:id AND user_id=:u'),{'id':data.resume_id,'u':user['id']}).mappings().first()
            if not resume:raise HTTPException(404,'Resume not found')
        resume=resume or {'name':'Role-only practice','extracted_text':''}
        questions=make_questions(data.role,resume['extracted_text'],data.job_description)
        row=conn.execute(text('''INSERT INTO public.mock_interviews(user_id,role,resume_id,resume_name,questions)
            VALUES(:u,:r,:rid,:name,CAST(:q AS JSONB)) RETURNING *'''),{'u':user['id'],'r':data.role,'rid':data.resume_id,'name':resume['name'],'q':json.dumps(questions)}).mappings().one()
    return dict(row)


@router.get('')
def listing(user=Depends(get_current_user)):
    with engine.connect() as conn:
        rows=conn.execute(text('SELECT id,role,resume_name,status,created_at,updated_at FROM public.mock_interviews WHERE user_id=:u ORDER BY id DESC LIMIT 100'),{'u':user['id']}).mappings().all()
    return {'interviews':[dict(r) for r in rows]}


@router.get('/{interview_id}')
def detail(interview_id:int,user=Depends(get_current_user)):
    with engine.connect() as conn:return dict(owned(conn,interview_id,user['id']))


@router.post('/{interview_id}/answer')
def answer(interview_id:int,data:InterviewAnswer,user=Depends(get_current_user)):
    with engine.begin() as conn:
        row=owned(conn,interview_id,user['id'],True)
        if row['status']=='Completed':raise HTTPException(409,'This interview is complete. Start another attempt to practise again.')
        if data.question_id not in {q['id'] for q in row['questions']}:raise HTTPException(400,'Unknown question')
        answers={**row['answers'],data.question_id:data.answer}
        updated=conn.execute(text('UPDATE public.mock_interviews SET answers=CAST(:a AS JSONB),updated_at=NOW() WHERE id=:id RETURNING *'),{'a':json.dumps(answers),'id':interview_id}).mappings().one()
    return dict(updated)


@router.post('/{interview_id}/finish')
def finish(interview_id:int,user=Depends(get_current_user)):
    with engine.begin() as conn:
        row=owned(conn,interview_id,user['id'],True)
        if row['status']=='Completed':return dict(row)
        if len(row['answers'])<len(row['questions']):raise HTTPException(400,'Answer or explicitly skip every question before finishing.')
        report=make_report(row['questions'],row['answers'])
        row=conn.execute(text("UPDATE public.mock_interviews SET status='Completed',report=CAST(:r AS JSONB),updated_at=NOW() WHERE id=:id RETURNING *"),{'r':json.dumps(report),'id':interview_id}).mappings().one()
    return dict(row)


@router.delete('/{interview_id}')
def remove(interview_id:int,user=Depends(get_current_user)):
    with engine.begin() as conn:
        owned(conn,interview_id,user['id'])
        conn.execute(text('DELETE FROM public.mock_interviews WHERE id=:id'),{'id':interview_id})
    return {'message':'Interview removed'}
