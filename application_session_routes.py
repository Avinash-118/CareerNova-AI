"""Include this router in backend.py: app.include_router(application_session_router)."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import text
from application_session import create_session, get_session, close_session

profile_engine = None

def configure_autofill_database(engine):
    global profile_engine
    profile_engine = engine

application_session_router = APIRouter(prefix='/api/agent', tags=['Voice Application Sessions'])

class StartRequest(BaseModel):
    job_url: str

class AnswerRequest(BaseModel):
    value: str

@application_session_router.post('/start')
def start(data: StartRequest):
    try:
        return create_session(data.job_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        print('Session start error:', exc)
        raise HTTPException(500, 'Could not open application browser') from exc

def session_or_404(session_id):
    try:
        return get_session(session_id)
    except KeyError as exc:
        raise HTTPException(404, 'Session not found') from exc


@application_session_router.post('/{session_id}/autofill')
def autofill(session_id: str):
    session = session_or_404(session_id)
    if profile_engine is None:
        raise HTTPException(503, 'Profile database unavailable')
    with profile_engine.connect() as connection:
        profile = connection.execute(text("""SELECT first_name, last_name, email, phone, location,
            linkedin_url, github_url, portfolio_url, education, university,
            degree, experience_years, skills
            FROM public.candidate_profiles WHERE profile_id = :id"""), {'id': 'local-candidate'}).mappings().first()
    if profile is None:
        return {'autofilled_count': 0, 'remaining_count': len(session.fields),
                'next_question': session.question(), 'submitted': False}
    try:
        return session.autofill(dict(profile))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.get('/{session_id}/question')
def question(session_id: str):
    return session_or_404(session_id).question()

@application_session_router.post('/{session_id}/answer')
def answer(session_id: str, data: AnswerRequest):
    try:
        return session_or_404(session_id).answer(data.value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.post('/{session_id}/skip')
def skip(session_id: str):
    try:
        return session_or_404(session_id).skip()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.post('/{session_id}/upload')
async def upload(session_id: str, file: UploadFile = File(...)):
    filename = file.filename or ''
    if not filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(400, 'Use PDF or DOCX')
    content = await file.read(5 * 1024 * 1024 + 1)
    await file.close()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, 'File must be nonempty and at most 5 MB')
    try:
        return session_or_404(session_id).upload(filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@application_session_router.get('/{session_id}/review')
def review(session_id: str):
    return session_or_404(session_id).review()

@application_session_router.post('/{session_id}/close')
def close(session_id: str):
    return close_session(session_id)
