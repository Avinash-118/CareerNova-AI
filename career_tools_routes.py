from email_service import email_configured
"""Authenticated career tools. All personal rows are scoped to the session user."""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import text
from auth_routes import get_current_user, digest, password_hash
from career_coaching import coach_resume, interview_questions, explain_match
from resume_parser import extract_resume_text

router = APIRouter(prefix='/api', tags=['Career workspace'])

def db():
    from database import engine
    return engine


def owned(conn, table, row_id, user):
    # table is selected by server code, never taken from request data.
    row = conn.execute(text(f'SELECT * FROM public.{table} WHERE id=:id AND user_id=:u'), {'id':row_id,'u':user['id']}).mappings().first()
    if row is None:
        raise HTTPException(404, 'Record not found')
    return row


@router.get('/resumes')
def resumes(user=Depends(get_current_user)):
    with db().connect() as conn:
        rows = conn.execute(text('SELECT id,name,filename,created_at FROM public.resume_versions WHERE user_id=:u ORDER BY id DESC'),{'u':user['id']}).mappings().all()
    return {'resumes':[dict(r) for r in rows]}


@router.post('/resumes', status_code=201)
def upload_resume(file: UploadFile=File(...), name: str=Form(...,min_length=1,max_length=120), user=Depends(get_current_user)):
    content=file.file.read(5*1024*1024+1)
    file.file.close()
    if not content or len(content)>5*1024*1024:
        raise HTTPException(400,'Use a nonempty PDF or DOCX no larger than 5 MB')
    try:
        resume_text=extract_resume_text(file.filename or '',content)
    except Exception as exc:
        raise HTTPException(400,'Unable to read resume. Use a text-based PDF or DOCX.') from exc
    with db().begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']})
        if conn.execute(text('SELECT COUNT(*) FROM public.resume_versions WHERE user_id=:u'),{'u':user['id']}).scalar_one()>=10:
            raise HTTPException(400,'You can store up to 10 resume versions')
        row=conn.execute(text('INSERT INTO public.resume_versions(user_id,name,filename,content,extracted_text) VALUES(:u,:n,:f,:c,:t) RETURNING id,name,filename,created_at'),{'u':user['id'],'n':name.strip(),'f':os.path.basename(file.filename or 'resume'),'c':content,'t':resume_text[:100000]}).mappings().one()
    return dict(row)


@router.get('/resumes/{resume_id}/download')
def download_resume(resume_id:int,user=Depends(get_current_user)):
    with db().connect() as conn:
        row=owned(conn,'resume_versions',resume_id,user)
    extension='pdf' if row['filename'].lower().endswith('.pdf') else 'docx'
    return Response(bytes(row['content']),media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="resume-{resume_id}.{extension}"'})


@router.delete('/resumes/{resume_id}')
def delete_resume(resume_id:int,user=Depends(get_current_user)):
    with db().begin() as conn:
        owned(conn,'resume_versions',resume_id,user)
        conn.execute(text('DELETE FROM public.resume_versions WHERE id=:id'),{'id':resume_id})
    return {'message':'Resume deleted'}


class CoachingRequest(BaseModel):
    resume_id:int
    job_description:str=Field(min_length=20,max_length=30000)


@router.post('/resume-coach')
def resume_coach(data:CoachingRequest,user=Depends(get_current_user)):
    with db().connect() as conn:
        row=owned(conn,'resume_versions',data.resume_id,user)
    return coach_resume(row['extracted_text'],data.job_description)


class TailoredSave(BaseModel):
    text: str = Field(min_length=30, max_length=100000)
    name: str = Field(min_length=1, max_length=120)


@router.post('/resume-tailor')
def tailor_resume(data: CoachingRequest, user=Depends(get_current_user)):
    from resume_tailoring import prepare_draft
    with db().connect() as conn:
        row = owned(conn, 'resume_versions', data.resume_id, user)
    return {**prepare_draft(row['extracted_text'], data.job_description), 'source_name':row['name']}


@router.post('/resume-tailor/save', status_code=201)
def save_tailored_resume(data: TailoredSave, user=Depends(get_current_user)):
    from resume_tailoring import make_docx
    content = make_docx(data.text)
    with db().begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'), {'u':user['id']})
        if conn.execute(text('SELECT COUNT(*) FROM public.resume_versions WHERE user_id=:u'), {'u':user['id']}).scalar_one() >= 10:
            raise HTTPException(400, 'You can store up to 10 resume versions')
        row = conn.execute(text("""INSERT INTO public.resume_versions(user_id,name,filename,content,extracted_text)
            VALUES(:u,:n,'tailored-resume.docx',:c,:t) RETURNING id,name,filename,created_at"""),
            {'u':user['id'],'n':data.name.strip(),'c':content,'t':data.text}).mappings().one()
    return dict(row)


@router.post('/match-explanation')
def match_explanation(data:CoachingRequest,user=Depends(get_current_user)):
    with db().connect() as conn:
        row=owned(conn,'resume_versions',data.resume_id,user)
    from faiss_search import load_search_engine
    import numpy as np
    _,_,model=load_search_engine()
    vectors=model.encode([row['extracted_text'][:20000],data.job_description],normalize_embeddings=True,convert_to_numpy=True)
    return explain_match(row['extracted_text'],data.job_description,float(np.dot(vectors[0],vectors[1])))


class PracticeRequest(BaseModel):
    job_title:str=Field(min_length=2,max_length=200)
    job_description:str=Field(min_length=20,max_length=30000)


@router.post('/interviews',status_code=201)
def create_practice(data:PracticeRequest,user=Depends(get_current_user)):
    with db().begin() as conn:
        profile=conn.execute(text('SELECT skills FROM public.candidate_profiles WHERE user_id=:u'),{'u':user['id']}).scalar_one_or_none() or ''
        questions=interview_questions(data.job_title,data.job_description,profile)
        row=conn.execute(text('INSERT INTO public.interview_practice(user_id,job_title,questions) VALUES(:u,:t,CAST(:q AS JSONB)) RETURNING *'),{'u':user['id'],'t':data.job_title,'q':json.dumps(questions)}).mappings().one()
    return dict(row)


@router.get('/interviews')
def practices(user=Depends(get_current_user)):
    with db().connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.interview_practice WHERE user_id=:u ORDER BY id DESC LIMIT 50'),{'u':user['id']}).mappings().all()
    return {'sessions':[dict(r) for r in rows]}


class PracticeAnswers(BaseModel):
    answers:dict[str,str]


@router.patch('/interviews/{practice_id}')
def save_practice(practice_id:int,data:PracticeAnswers,user=Depends(get_current_user)):
    if len(data.answers)>20 or any(len(v)>10000 for v in data.answers.values()):
        raise HTTPException(400,'Answer limits exceeded')
    with db().begin() as conn:
        row=owned(conn,'interview_practice',practice_id,user)
        valid={q['id'] for q in row['questions']}
        if set(data.answers)-valid:
            raise HTTPException(400,'Unknown question')
        conn.execute(text('UPDATE public.interview_practice SET answers=CAST(:a AS JSONB) WHERE id=:id'),{'a':json.dumps(data.answers),'id':practice_id})
    return {'message':'Practice answers saved'}


@router.delete('/interviews/{practice_id}')
def delete_practice(practice_id:int,user=Depends(get_current_user)):
    with db().begin() as conn:
        owned(conn,'interview_practice',practice_id,user)
        conn.execute(text('DELETE FROM public.interview_practice WHERE id=:id'),{'id':practice_id})
    return {'message':'Practice removed'}


class ApplicationDetails(BaseModel):
    resume_id:int|None=None
    description:str=Field(default='',max_length=30000)
    salary:str=Field(default='',max_length=200)


@router.patch('/applications/{tracker_id}/details')
def application_details(tracker_id:int,data:ApplicationDetails,user=Depends(get_current_user)):
    with db().begin() as conn:
        row=conn.execute(text('SELECT * FROM public.career_job_tracker WHERE id=:id AND user_id=:u FOR UPDATE'),{'id':tracker_id,'u':str(user['id'])}).mappings().first()
        if not row: raise HTTPException(404,'Application not found')
        if data.resume_id is not None: owned(conn,'resume_versions',data.resume_id,user)
        conn.execute(text('UPDATE public.career_job_tracker SET resume_id=:r,description=:d,salary=:s,updated_at=NOW() WHERE id=:id'),{'r':data.resume_id,'d':data.description,'s':data.salary,'id':tracker_id})
        if row['resume_id']!=data.resume_id or row['description']!=data.description or row['salary']!=data.salary:
            from application_history import record_event
            record_event(conn,user['id'],tracker_id,'details','Application details updated','Resume version, compensation or requirements changed.')
    return {'message':'Application details saved'}


class ReminderRequest(BaseModel):
    title:str=Field(min_length=2,max_length=200)
    kind:Literal['Deadline','Interview','Follow-up']='Follow-up'
    due_at:datetime
    tracker_id:int|None=None


@router.post('/reminders',status_code=201)
def create_reminder(data:ReminderRequest,user=Depends(get_current_user)):
    if data.due_at.tzinfo is None:
        raise HTTPException(400,'Due date must include a timezone')
    with db().begin() as conn:
        if data.tracker_id is not None and not conn.execute(text('SELECT id FROM public.career_job_tracker WHERE id=:id AND user_id=:u'),{'id':data.tracker_id,'u':str(user['id'])}).first():
            raise HTTPException(404,'Application not found')
        row=conn.execute(text('INSERT INTO public.career_reminders(user_id,tracker_id,title,kind,due_at) VALUES(:u,:t,:title,:kind,:due) RETURNING *'),{'u':user['id'],'t':data.tracker_id,'title':data.title,'kind':data.kind,'due':data.due_at}).mappings().one()
    return dict(row)


@router.get('/reminders')
def reminders(user=Depends(get_current_user)):
    with db().connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.career_reminders WHERE user_id=:u ORDER BY completed,due_at LIMIT 200'),{'u':user['id']}).mappings().all()
    return {'reminders':[dict(r) for r in rows]}


class ReminderUpdate(BaseModel):
    completed:bool


@router.patch('/reminders/{reminder_id}')
def complete_reminder(reminder_id:int,data:ReminderUpdate,user=Depends(get_current_user)):
    with db().begin() as conn:
        owned(conn,'career_reminders',reminder_id,user)
        conn.execute(text('UPDATE public.career_reminders SET completed=:c WHERE id=:id'),{'c':data.completed,'id':reminder_id})
    return {'message':'Reminder updated'}


@router.delete('/reminders/{reminder_id}')
def delete_reminder(reminder_id:int,user=Depends(get_current_user)):
    with db().begin() as conn:
        owned(conn,'career_reminders',reminder_id,user)
        conn.execute(text('DELETE FROM public.career_reminders WHERE id=:id'),{'id':reminder_id})
    return {'message':'Reminder deleted'}


class JobReport(BaseModel):
    job_id:str=Field(min_length=1,max_length=1000)
    title:str=Field(min_length=1,max_length=300)
    url:str=Field(default='',max_length=2000)
    reason:Literal['Expired','Misleading','Suspicious','Other']
    details:str=Field(min_length=5,max_length=3000)


@router.post('/reports',status_code=201)
def report_job(data:JobReport,user=Depends(get_current_user)):
    with db().begin() as conn:
        row=conn.execute(text('INSERT INTO public.job_reports(user_id,job_id,title,url,reason,details) VALUES(:u,:job_id,:title,:url,:reason,:details) RETURNING id'),{'u':user['id'],**data.model_dump()}).scalar_one()
    return {'id':row,'message':'Report submitted for review'}


@router.get('/reports')
def my_reports(user=Depends(get_current_user)):
    with db().connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.job_reports WHERE user_id=:u ORDER BY id DESC LIMIT 100'),{'u':user['id']}).mappings().all()
    return {'reports':[dict(r) for r in rows]}


@router.get('/employers')
def employers(user=Depends(get_current_user)):
    with db().connect() as conn:
        rows=conn.execute(text('SELECT * FROM public.employer_reviews ORDER BY company LIMIT 500')).mappings().all()
    return {'employers':[dict(r) for r in rows]}


class NotificationPreference(BaseModel):
    email_digest:bool


@router.get('/notification-preferences')
def preferences(user=Depends(get_current_user)):
    with db().connect() as conn:
        enabled=conn.execute(text('SELECT email_digest FROM public.notification_preferences WHERE user_id=:u'),{'u':user['id']}).scalar_one_or_none()
        verified=conn.execute(text('SELECT email_verified FROM public.users WHERE id=:u'),{'u':user['id']}).scalar_one()
    return {'email_digest':bool(enabled),'email_verified':verified,'smtp_configured':email_configured()}


@router.patch('/notification-preferences')
def set_preferences(data:NotificationPreference,user=Depends(get_current_user)):
    with db().begin() as conn:
        conn.execute(text('INSERT INTO public.notification_preferences(user_id,email_digest) VALUES(:u,:e) ON CONFLICT(user_id) DO UPDATE SET email_digest=:e'),{'u':user['id'],'e':data.email_digest})
    return {'message':'Notification preferences saved'}


@router.post('/verify-email/request')
def request_verification(user=Depends(get_current_user)):
    token=secrets.token_urlsafe(48)
    url=os.getenv('FRONTEND_URL','http://localhost:5173').rstrip('/')+'/verify-email?token='+token
    with db().begin() as conn:
        conn.execute(text('SELECT id FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']})
        recent=conn.execute(text("SELECT COUNT(*) FROM public.mail_outbox WHERE user_id=:u AND dedupe_key LIKE 'verify:%' AND created_at>NOW()-INTERVAL '15 minutes'"),{'u':user['id']}).scalar_one()
        if recent>=5:raise HTTPException(429,'Please wait before requesting another verification email')
        conn.execute(text("UPDATE public.mail_outbox SET status='Cancelled' WHERE user_id=:u AND dedupe_key LIKE 'verify:%' AND status IN ('Pending','Retry')"),{'u':user['id']})
        conn.execute(text('DELETE FROM public.email_verifications WHERE user_id=:u'),{'u':user['id']})
        conn.execute(text('INSERT INTO public.email_verifications VALUES(:h,:u,:e)'),{'h':digest(token),'u':user['id'],'e':datetime.now(timezone.utc)+timedelta(minutes=30)})
        conn.execute(text("INSERT INTO public.mail_outbox(user_id,subject,body,dedupe_key) VALUES(:u,'Verify your CareerNova email',:b,:key)"),{'u':user['id'],'b':'Verify your email within 30 minutes: '+url,'key':'verify:'+digest(token)})
    return {'message':'Verification email queued. Delivery requires the worker and SMTP configuration.'}


class TokenRequest(BaseModel):
    token:str=Field(min_length=20,max_length=200)


@router.post('/verify-email')
def verify_email(data:TokenRequest,user=Depends(get_current_user)):
    with db().begin() as conn:
        uid=conn.execute(text('DELETE FROM public.email_verifications WHERE token_hash=:h AND user_id=:u AND expires_at>NOW() RETURNING user_id'),{'h':digest(data.token),'u':user['id']}).scalar_one_or_none()
        if uid is None: raise HTTPException(400,'Verification link is invalid or expired')
        conn.execute(text('UPDATE public.users SET email_verified=TRUE WHERE id=:u'),{'u':uid})
    return {'message':'Email verified'}


@router.get('/privacy/sessions')
def sessions(request:Request,user=Depends(get_current_user)):
    current=digest(request.cookies.get('careernova_session',''))
    with db().connect() as conn:
        rows=conn.execute(text('SELECT token_hash,created_at,expires_at,auth_method FROM public.auth_sessions WHERE user_id=:u AND expires_at>NOW() ORDER BY created_at DESC'),{'u':user['id']}).mappings().all()
    return {'sessions':[{'id':r['token_hash'],'current':r['token_hash']==current,'created_at':r['created_at'],'expires_at':r['expires_at'],'method':r['auth_method']} for r in rows]}


@router.delete('/privacy/sessions/{session_id}')
def revoke_session(session_id:str,request:Request,response:Response,user=Depends(get_current_user)):
    with db().begin() as conn:
        conn.execute(text('DELETE FROM public.auth_sessions WHERE token_hash=:h AND user_id=:u'),{'h':session_id,'u':user['id']})
    if session_id==digest(request.cookies.get('careernova_session','')):
        response.delete_cookie('careernova_session',path='/')
    return {'message':'Session revoked'}


@router.get('/privacy/export')
def export_data(user=Depends(get_current_user)):
    result={'account':user}
    with db().connect() as conn:
        for table in ['candidate_profiles','career_job_tracker','career_reminders','interview_practice','job_alert_rules','job_notifications','job_reports','notification_preferences','saved_searches','application_events','application_answer_memory','mock_interviews']:
            uid=str(user['id']) if table=='career_job_tracker' else user['id']
            result[table]=[dict(r) for r in conn.execute(text(f'SELECT * FROM public.{table} WHERE user_id=:u'),{'u':uid}).mappings().all()]
        result['resume_versions']=[dict(r) for r in conn.execute(text('SELECT id,name,filename,extracted_text,created_at FROM public.resume_versions WHERE user_id=:u'),{'u':user['id']}).mappings().all()]
    return Response(json.dumps(jsonable_encoder(result),indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="careernova-data.json"'})


class DeleteAccount(BaseModel):
    confirmation:Literal['DELETE']
    password:str=Field(default='',max_length=128)


@router.post('/privacy/delete-account')
def delete_account(data:DeleteAccount,request:Request,response:Response,user=Depends(get_current_user)):
    with db().begin() as conn:
        account=conn.execute(text('SELECT password_hash FROM public.users WHERE id=:u FOR UPDATE'),{'u':user['id']}).scalar_one()
        session=conn.execute(text('SELECT created_at,auth_method FROM public.auth_sessions WHERE token_hash=:h'),{'h':digest(request.cookies.get('careernova_session',''))}).mappings().one()
        recent_oauth=session['auth_method']=='oauth' and session['created_at']>datetime.now(timezone.utc)-timedelta(minutes=10)
        if not recent_oauth and (not data.password or not password_hash.verify(data.password,account)):
            raise HTTPException(403,'Confirm your password, or sign in again with your linked provider within the last 10 minutes')
        # Close this user's active application browsers before removing the account.
        from application_session_routes import session_owners
        from application_session import close_session
        for sid,uid in list(session_owners.items()):
            if uid==user['id']:
                close_session(sid); session_owners.pop(sid,None)
        conn.execute(text('DELETE FROM public.career_job_tracker WHERE user_id=:u'),{'u':str(user['id'])})
        conn.execute(text('DELETE FROM public.users WHERE id=:u'),{'u':user['id']})
    response.delete_cookie('careernova_session',path='/')
    return {'message':'Account and personal workspace deleted. Submitted moderation reports are retained without your account identity.'}


def require_admin(user=Depends(get_current_user)):
    admins={e.strip().lower() for e in os.getenv('ADMIN_EMAILS','').split(',') if e.strip()}
    with db().connect() as conn:
        verified=conn.execute(text('SELECT email_verified FROM public.users WHERE id=:u'),{'u':user['id']}).scalar_one()
    if user['email'].lower() not in admins or not verified: raise HTTPException(403,'Administrator access required')
    return user


@router.get('/admin/overview')
def admin_overview(user=Depends(require_admin)):
    from live_jobs import get_source_status
    with db().connect() as conn:
        counts={table:conn.execute(text(f'SELECT COUNT(*) FROM public.{table}')).scalar_one() for table in ['users','job_reports','career_job_tracker','resume_versions']}
        reports=[dict(r) for r in conn.execute(text('SELECT id,title,url,reason,details,status,created_at FROM public.job_reports ORDER BY id DESC LIMIT 100')).mappings().all()]
        runs=[dict(r) for r in conn.execute(text('SELECT * FROM public.worker_runs ORDER BY id DESC LIMIT 20')).mappings().all()]
        mail=[dict(r) for r in conn.execute(text('SELECT id,subject,status,attempts,last_error,created_at,sent_at FROM public.mail_outbox ORDER BY id DESC LIMIT 50')).mappings().all()]
    return {'counts':counts,'reports':reports,'worker_runs':runs,'mail':mail,'sources':get_source_status() or (runs[0].get('sources',{}) if runs else {})}


class ReportReview(BaseModel):
    status:Literal['Open','Investigating','Resolved','Dismissed']


@router.patch('/admin/reports/{report_id}')
def review_report(report_id:int,data:ReportReview,user=Depends(require_admin)):
    with db().begin() as conn:
        found=conn.execute(text('UPDATE public.job_reports SET status=:s WHERE id=:id RETURNING id'),{'s':data.status,'id':report_id}).scalar_one_or_none()
        if found is None:raise HTTPException(404,'Report not found')
    return {'message':'Report updated'}


class EmployerReview(BaseModel):
    domain:str=Field(min_length=3,max_length=253,pattern=r'^[a-zA-Z0-9.-]+$')
    company:str=Field(min_length=2,max_length=200)
    status:Literal['Unverified','Verified','Flagged']
    evidence:str=Field(min_length=10,max_length=3000)


@router.post('/admin/employers')
def review_employer(data:EmployerReview,user=Depends(require_admin)):
    with db().begin() as conn:
        conn.execute(text('INSERT INTO public.employer_reviews(domain,company,status,evidence) VALUES(:domain,:company,:status,:evidence) ON CONFLICT(domain) DO UPDATE SET company=:company,status=:status,evidence=:evidence,updated_at=NOW()'),{**data.model_dump(),'domain':data.domain.lower()})
    return {'message':'Employer review saved'}
class ResumeVersionRequest(BaseModel):
    resume_id:int


@router.post('/agent/{session_id}/resume-version')
def use_resume_version(session_id:str,data:ResumeVersionRequest,user=Depends(get_current_user)):
    from application_session_routes import session_or_404
    session=session_or_404(session_id,user)
    with db().connect() as conn:
        resume=owned(conn,'resume_versions',data.resume_id,user)
    try:
        return session.upload(resume['filename'],bytes(resume['content']))
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc


@router.post('/resumes/{resume_id}/matches')
def saved_resume_matches(resume_id:int,user=Depends(get_current_user)):
    from faiss_search import semantic_search
    from match_scoring import calculate_match
    with db().connect() as conn:
        resume=owned(conn,'resume_versions',resume_id,user)
    jobs=semantic_search(resume['extracted_text'][:20000],20)
    for job in jobs:
        job.update(calculate_match(resume['extracted_text'],str(job.get('description',job.get('job_description',''))),job.get('faiss_score',0)))
    from job_identity import annotate_tracking,deduplicate_jobs
    with db().connect() as conn:
        jobs=annotate_tracking(deduplicate_jobs(jobs),user['id'],conn)
    return {'jobs':jobs}


@router.post('/admin/mail/{mail_id}/retry')
def retry_mail(mail_id:int,user=Depends(require_admin)):
    with db().begin() as conn:
        found=conn.execute(text("UPDATE public.mail_outbox SET status='Retry',attempts=0,next_attempt=NOW(),last_error=NULL WHERE id=:id AND status='Failed' RETURNING id"),{'id':mail_id}).scalar_one_or_none()
        if found is None:raise HTTPException(404,'Failed message not found')
    return {'message':'Email queued for retry'}


@router.post('/admin/feeds/check')
def check_feeds(user=Depends(require_admin)):
    from live_jobs import fetch_live_jobs,get_source_status
    jobs=fetch_live_jobs(force_refresh=True)
    with db().begin() as conn:
        conn.execute(text("INSERT INTO public.worker_runs(status,finished_at,detail,sources) VALUES('Completed',NOW(),:d,CAST(:s AS JSONB))"),{'d':f'Manual feed check: {len(jobs)} jobs','s':json.dumps(get_source_status())})
    return {'message':f'Feed check completed: {len(jobs)} jobs available','sources':get_source_status()}
