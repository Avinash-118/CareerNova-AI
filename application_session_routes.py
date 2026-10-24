from auth_routes import get_current_user
"""Include in backend.py: app.include_router(application_session_router)."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from typing import Literal
from application_memory import question_key
from sqlalchemy import text
from application_session import create_session, get_session, close_session

profile_engine = None
session_owners = {}

def configure_autofill_database(engine):
    global profile_engine
    profile_engine = engine

application_session_router = APIRouter(prefix='/api/agent', tags=['Voice Application Sessions'])

class StartRequest(BaseModel):
    job_url: str

class AnswerRequest(BaseModel):
    value: str = Field(min_length=1, max_length=10000)
    remember: bool = False
    source: Literal['typed', 'voice'] = 'typed'

class EvidenceRequest(BaseModel):
    resume_id: int | None = None

@application_session_router.get('/demo-form')
def demo_form():
    from deployment_config import production
    from fastapi.responses import HTMLResponse
    from pathlib import Path
    if production():
        raise HTTPException(404, 'Not found')
    return HTMLResponse(Path(__file__).with_name('test_application.html').read_text())

@application_session_router.get('/capabilities')
def capabilities(user=Depends(get_current_user)):
    from deployment_config import browser_assistant_enabled
    return {'desktop_browser': browser_assistant_enabled()}

@application_session_router.post('/start')
def start(data: StartRequest, user=Depends(get_current_user)):
    from deployment_config import browser_assistant_enabled
    if not browser_assistant_enabled():
        raise HTTPException(503, 'The assisted employer browser is available in the local desktop version only. Open the job posting to apply directly. Hosted profile, resume and interview tools remain available.')
    try:
        result = create_session(data.job_url)
        session_owners[result["session_id"]] = user["id"]
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        print('Session start error:', exc)
        raise HTTPException(500, 'Could not open application browser') from exc

def session_or_404(session_id, user):
    if session_owners.get(session_id) != user["id"]:
        raise HTTPException(404, "Session not found")
    try:
        return get_session(session_id)
    except KeyError as exc:
        raise HTTPException(404, 'Session not found') from exc

@application_session_router.get('/{session_id}/status')
def status(session_id: str, user=Depends(get_current_user)):
    session = session_or_404(session_id, user)
    return session.run(session._status)

@application_session_router.post('/{session_id}/scan')
def scan(session_id: str, user=Depends(get_current_user)):
    try:
        return session_or_404(session_id, user).scan_for_form()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, 'Could not inspect the employer browser. Keep it open and use Rescan current form.') from exc


@application_session_router.post('/{session_id}/resume')
def resume(session_id: str, user=Depends(get_current_user)):
    try:
        return session_or_404(session_id, user).resume()
    except Exception as exc:
        raise HTTPException(400, f'Could not inspect the current page: {exc}') from exc

@application_session_router.post('/{session_id}/autofill')
def autofill(session_id: str, data: EvidenceRequest = EvidenceRequest(), user=Depends(get_current_user)):
    session = session_or_404(session_id, user)
    if profile_engine is None:
        raise HTTPException(503, 'Profile database unavailable')
    with profile_engine.connect() as connection:
        profile = connection.execute(text("""SELECT first_name, last_name, email, phone, location,
            linkedin_url, github_url, portfolio_url, education, university,
            degree, experience_years, skills
            FROM public.candidate_profiles WHERE user_id = :id"""), {'id': user['id']}).mappings().first()
    with profile_engine.connect() as connection:
        memories = connection.execute(text('SELECT * FROM public.application_answer_memory WHERE user_id=:u'), {'u':user['id']}).mappings().all()
        resume = None
        if data.resume_id is not None:
            resume = connection.execute(text('SELECT name,extracted_text FROM public.resume_versions WHERE id=:id AND user_id=:u'), {'id':data.resume_id,'u':user['id']}).mappings().first()
            if resume is None:
                raise HTTPException(404, 'Resume not found')
    try:
        conflicts = session.run(session.prepare_evidence, dict(profile or {}), memories, resume)
        return {**session.autofill(dict(profile or {})), 'conflicts': conflicts}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.get('/{session_id}/question')
def question(session_id: str, user=Depends(get_current_user)):
    return session_or_404(session_id, user).question()

@application_session_router.post('/{session_id}/answer')
def answer(session_id: str, data: AnswerRequest, user=Depends(get_current_user)):
    session = session_or_404(session_id, user)
    def enter():
        if session.index >= len(session.fields):
            raise ValueError('No remaining questions')
        answered_index = session.index
        field = dict(session.fields[answered_index])
        if data.remember and field['type'] in ('password', 'file', 'hidden'):
            raise ValueError('This field cannot be remembered')
        result = session._answer(data.value)
        session.answer_sources[answered_index] = 'User-confirmed ' + data.source + ' answer'
        if data.remember:
            with profile_engine.begin() as conn:
                conn.execute(text("""INSERT INTO public.application_answer_memory(user_id,question_key,question,answer,source)
                    VALUES(:u,:k,:q,:a,:s) ON CONFLICT(user_id,question_key) DO UPDATE
                    SET answer=EXCLUDED.answer,source=EXCLUDED.source,updated_at=NOW()"""),
                    {'u':user['id'],'k':question_key(field),'q':field['label'],'a':data.value,'s':data.source})
        return result
    try:
        return session.run(enter)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.get('/memory/answers')
def list_memory(user=Depends(get_current_user)):
    with profile_engine.connect() as conn:
        rows = conn.execute(text('SELECT id,question,answer,source,updated_at FROM public.application_answer_memory WHERE user_id=:u ORDER BY updated_at DESC'), {'u':user['id']}).mappings().all()
    return {'answers':[dict(r) for r in rows]}

@application_session_router.delete('/memory/answers/{memory_id}')
def forget_memory(memory_id: int, user=Depends(get_current_user)):
    with profile_engine.begin() as conn:
        conn.execute(text('DELETE FROM public.application_answer_memory WHERE id=:id AND user_id=:u'), {'id':memory_id,'u':user['id']})
    return {'message':'Answer forgotten'}

@application_session_router.post('/{session_id}/revisit/{index}')
def revisit(session_id: str, index: int, user=Depends(get_current_user)):
    try:
        return session_or_404(session_id, user).revisit(index)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@application_session_router.post('/{session_id}/skip')
def skip(session_id: str, user=Depends(get_current_user)):
    try:
        return session_or_404(session_id, user).skip()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.post('/{session_id}/upload')
async def upload(session_id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    filename = file.filename or ''
    if not filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(400, 'Use PDF or DOCX')
    content = await file.read(5 * 1024 * 1024 + 1)
    await file.close()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, 'File must be nonempty and at most 5 MB')
    try:
        return session_or_404(session_id, user).upload(filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.get('/{session_id}/review')
def review(session_id: str, user=Depends(get_current_user)):
    return session_or_404(session_id, user).review()

@application_session_router.post('/{session_id}/close')
def close(session_id: str, user=Depends(get_current_user)):
    session_or_404(session_id, user)
    result = close_session(session_id)
    session_owners.pop(session_id, None)
    return result
