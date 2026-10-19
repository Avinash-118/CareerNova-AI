"""OAuth authorization code + PKCE. Existing accounts require explicit linking."""
import base64
import os
import secrets
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
import requests
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from auth_routes import get_current_user,digest,issue_session,password_hash
from database import engine
router=APIRouter(prefix='/api/auth/oauth',tags=['Provider sign-in'])
PROVIDERS={
 'google':{'authorize':'https://accounts.google.com/o/oauth2/v2/auth','token':'https://oauth2.googleapis.com/token','scope':'openid email profile'},
 'github':{'authorize':'https://github.com/login/oauth/authorize','token':'https://github.com/login/oauth/access_token','scope':'read:user user:email'},
}

def config(provider):
    if provider not in PROVIDERS:raise HTTPException(404,'Unknown provider')
    client=os.getenv(provider.upper()+'_CLIENT_ID');secret=os.getenv(provider.upper()+'_CLIENT_SECRET')
    if not client or not secret:raise HTTPException(503,'This sign-in provider has not been configured')
    base=os.getenv('PUBLIC_BASE_URL',os.getenv('FRONTEND_URL','http://localhost:5173')).rstrip('/')
    return client,secret,base+f'/api/auth/oauth/{provider}/callback'


@router.get('/providers')
def providers():
    return {key:bool(os.getenv(key.upper()+'_CLIENT_ID') and os.getenv(key.upper()+'_CLIENT_SECRET')) for key in PROVIDERS}


@router.get('/{provider}/start')
def start(provider:str,request:Request,link:bool=False):
    client,_,redirect=config(provider)
    linked=get_current_user(request)['id'] if link else None
    state=secrets.token_urlsafe(48);verifier=secrets.token_urlsafe(64)
    challenge=base64.urlsafe_b64encode(__import__('hashlib').sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO public.oauth_flows VALUES(:s,:p,:v,:u,:e)'),{'s':digest(state),'p':provider,'v':verifier,'u':linked,'e':datetime.now(timezone.utc)+timedelta(minutes=10)})
    params={'client_id':client,'redirect_uri':redirect,'response_type':'code','scope':PROVIDERS[provider]['scope'],'state':state,'code_challenge':challenge,'code_challenge_method':'S256'}
    response=RedirectResponse(PROVIDERS[provider]['authorize']+'?'+urlencode(params))
    response.set_cookie('careernova_oauth',state,httponly=True,secure=os.getenv('COOKIE_SECURE','false').lower()=='true',samesite='lax',max_age=600,path='/')
    return response


def provider_identity(provider,access_token):
    headers={'Authorization':'Bearer '+access_token,'Accept':'application/json'}
    if provider=='google':
        response=requests.get('https://openidconnect.googleapis.com/v1/userinfo',headers=headers,timeout=15);response.raise_for_status();data=response.json()
        if not data.get('email_verified') or not data.get('sub'):raise ValueError('Verified email required')
        return str(data['sub']),data['email'].lower(),data.get('name') or data['email']
    response=requests.get('https://api.github.com/user',headers=headers,timeout=15);response.raise_for_status();data=response.json()
    emails=requests.get('https://api.github.com/user/emails',headers=headers,timeout=15);emails.raise_for_status()
    verified=next((e['email'] for e in emails.json() if e.get('primary') and e.get('verified')),None)
    if not verified or not data.get('id'):raise ValueError('Verified primary email required')
    return str(data['id']),verified.lower(),data.get('name') or data['login']


@router.get('/{provider}/callback')
def callback(provider:str,request:Request,state:str='',code:str='',error:str=''):
    client,secret,redirect=config(provider)
    frontend=os.getenv('FRONTEND_URL','http://localhost:5173').rstrip('/')
    def failed(message):
        response=RedirectResponse(frontend+'/login?oauth_error='+message)
        response.delete_cookie('careernova_oauth',path='/');return response
    if error or not code or not state or not secrets.compare_digest(state,request.cookies.get('careernova_oauth','')):return failed('invalid_state')
    with engine.begin() as conn:
        flow=conn.execute(text('DELETE FROM public.oauth_flows WHERE state_hash=:s AND provider=:p AND expires_at>NOW() RETURNING *'),{'s':digest(state),'p':provider}).mappings().first()
    if not flow:return failed('expired_sign_in')
    if flow['link_user_id']:
        try:
            if get_current_user(request)['id']!=flow['link_user_id']:return failed('link_requires_sign_in')
        except HTTPException:return failed('link_requires_sign_in')
    try:
        token=requests.post(PROVIDERS[provider]['token'],data={'client_id':client,'client_secret':secret,'code':code,'redirect_uri':redirect,'grant_type':'authorization_code','code_verifier':flow['verifier']},headers={'Accept':'application/json'},timeout=15)
        token.raise_for_status();access=token.json().get('access_token')
        if not access:return failed('provider_failed')
        subject,email,name=provider_identity(provider,access)
        with engine.begin() as conn:
            uid=conn.execute(text('SELECT user_id FROM public.oauth_identities WHERE provider=:p AND subject=:s'),{'p':provider,'s':subject}).scalar_one_or_none()
            if flow['link_user_id']:
                if uid and uid!=flow['link_user_id']:return failed('identity_already_linked')
                uid=flow['link_user_id']
                conn.execute(text('INSERT INTO public.oauth_identities(provider,subject,user_id) VALUES(:p,:s,:u) ON CONFLICT(provider,subject) DO NOTHING'),{'p':provider,'s':subject,'u':uid})
            elif not uid:
                if conn.execute(text('SELECT id FROM public.users WHERE email=:e'),{'e':email}).first():return failed('sign_in_then_link_in_settings')
                uid=conn.execute(text('INSERT INTO public.users(full_name,email,password_hash,email_verified) VALUES(:n,:e,:h,TRUE) RETURNING id'),{'n':name[:200],'e':email,'h':password_hash.hash(secrets.token_urlsafe(64))}).scalar_one()
                conn.execute(text('INSERT INTO public.oauth_identities VALUES(:p,:s,:u)'),{'p':provider,'s':subject,'u':uid})
        response=RedirectResponse(frontend+'/dashboard')
        issue_session(uid,response,auth_method='oauth')
        response.delete_cookie('careernova_oauth',path='/');return response
    except (requests.RequestException,ValueError,KeyError,IntegrityError):return failed('provider_failed')

@router.get('/identities')
def identities(user=Depends(get_current_user)):
    with engine.connect() as conn:
        rows=conn.execute(text('SELECT provider FROM public.oauth_identities WHERE user_id=:u ORDER BY provider'),{'u':user['id']}).scalars().all()
    return {'providers':list(rows)}
