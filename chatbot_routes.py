"""Public website Q&A. No access to profiles, messages or application records."""
import time
import threading
from collections import defaultdict,deque
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field,ConfigDict
from chatbot_knowledge import BY_ID
from chatbot_service import answer_question,prepare_semantics
router=APIRouter(prefix='/api/chat',tags=['Nova website assistant'])
_attempts=defaultdict(deque)
_lock=threading.Lock()

class ChatQuestion(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    message:str=Field(min_length=1,max_length=2000)
    context_topic:str|None=Field(default=None,max_length=80)

@router.get('/help')
def help_topics():
    prepare_semantics()
    return {'suggestions':[{'label':BY_ID[key]['title'],'question':'How do I use '+BY_ID[key]['title']+'?'} for key in ('search','matching','alerts','social','timeline','privacy')],
            'description':'Answers are retrieved from reviewed CareerNova help. Conversations stay in this page and are not saved to your account.'}

@router.post('/message')
def chat(data:ChatQuestion,request:Request):
    key=request.client.host if request.client else 'unknown'
    now=time.monotonic()
    with _lock:
        for old in list(_attempts):
            if not _attempts[old] or _attempts[old][-1]<now-60:del _attempts[old]
        if key not in _attempts and len(_attempts)>=5000:raise HTTPException(429,'Chat is busy. Please try again shortly.',headers={'Retry-After':'60'})
        queue=_attempts[key]
        while queue and queue[0]<now-60:queue.popleft()
        if len(queue)>=30:raise HTTPException(429,'Please wait a minute before sending more questions.',headers={'Retry-After':'60'})
        queue.append(now)
    return answer_question(data.message,data.context_topic)
