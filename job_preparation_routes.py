from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text
from auth_routes import get_current_user
from database import engine
from job_preparation import build_preview

router=APIRouter(prefix='/api',tags=['Application preparation'])


class PreviewRequest(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    job_description:str=Field(default='',max_length=30000)
    resume_id:int|None=None


@router.post('/application-preview')
def preview(data:PreviewRequest,user=Depends(get_current_user)):
    with engine.connect() as conn:
        profile=conn.execute(text('SELECT first_name,last_name,email,phone,location,skills FROM public.candidate_profiles WHERE user_id=:u'),{'u':user['id']}).mappings().first()
        resume=None
        if data.resume_id is not None:
            resume=conn.execute(text('SELECT name,extracted_text FROM public.resume_versions WHERE id=:id AND user_id=:u'),{'id':data.resume_id,'u':user['id']}).mappings().first()
            if not resume:raise HTTPException(404,'Resume not found')
    return build_preview(data.job_description,dict(profile or {}),resume)
