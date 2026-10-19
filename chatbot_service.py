"""Local semantic retrieval over reviewed website help; no remote chat service."""
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from chatbot_knowledge import ARTICLES,BY_ID

STOP=set('a an the i me my you your we our it its this that those these there here what which who how when where why can could would should do does did am is are was were be been being to of for on in at with and or about please tell show help want need using use get website site careernova nova question questions'.split())
ALIASES={'cv':'resume','cvs':'resume','jobs':'job','resumes':'resume','searches':'search','alerts':'alert','notifications':'notification','applications':'application','accounts':'account','versions':'version','filters':'filter','scores':'score','emails':'email','signing':'sign','logging':'log'}

def tokens(value):
    return {ALIASES.get(word,word) for word in re.findall(r'[a-z0-9]+',value.lower()) if word not in STOP}

DOCS=[tokens(entry['title']+' '+entry['questions']) for entry in ARTICLES]
FREQUENCY=Counter(word for doc in DOCS for word in doc)

def lexical_scores(question):
    query=tokens(question)
    weights={word:math.log(1+len(ARTICLES)/(1+FREQUENCY[word])) for word in query}
    total=sum(weights.values()) or 1
    return [sum(weights[word] for word in query&doc)/total for doc in DOCS]

_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='nova-help')
_future=None
_init_lock=threading.Lock()
_encode_lock=threading.Lock()
_retry_after=0

def _load_index():
    from faiss_search import get_embedding_model
    model=get_embedding_model(local_only=True)
    with _encode_lock:
        vectors=model.encode([entry['title']+'. '+entry['questions'] for entry in ARTICLES],convert_to_numpy=True,normalize_embeddings=True)
    return model,vectors


def prepare_semantics():
    global _future,_retry_after
    if os.getenv('CHATBOT_SEMANTIC_ENABLED','true').lower()!='true':return None
    with _init_lock:
        if _future is None or (_future.done() and _future.exception() is not None and time.monotonic()>_retry_after):
            _future=_executor.submit(_load_index)
            _retry_after=time.monotonic()+300
        return _future


def semantic_scores(question,wait_seconds=1.5):
    future=prepare_semantics()
    if future is None:return None
    try:
        model,vectors=future.result(timeout=wait_seconds)
        with _encode_lock:
            vector=model.encode([question],convert_to_numpy=True,normalize_embeddings=True)[0]
        return [float(score) for score in vectors@vector]
    except Exception:
        # Missing local weights or an unavailable model never prevent website help.
        return None


def sources_for(entries):
    return [{'topic':entry['id'],'title':entry['title'],'path':entry['path']} for entry in entries]


def build_response(entries,mode):
    parts=[]
    for entry in entries:
        answer=entry['answer']
        if entry['id']=='social':
            configured=[p.title() if p=='google' else 'GitHub' for p in ('google','github') if os.getenv(p.upper()+'_CLIENT_ID') and os.getenv(p.upper()+'_CLIENT_SECRET')]
            answer=('Available on this installation: '+', '.join(configured)+'. ' if configured else 'Neither provider is enabled on this installation yet. ')+answer
        parts.append((entry['title']+'\n' if len(entries)>1 else '')+answer)
    related=[]
    for entry in entries:
        for key in entry['related']:
            if key not in related and key not in {e['id'] for e in entries}:related.append(key)
    return {'answer':'\n\n'.join(parts),'topic':entries[0]['id'],'sources':sources_for(entries),
            'suggestions':[{'label':BY_ID[key]['title'],'question':'How do I use '+BY_ID[key]['title']+'?'} for key in related[:3]],'mode':mode}


def answer_question(question,context_topic=None):
    clean=question.strip()
    if re.fullmatch(r'(hi|hello|hey|good morning|good evening)[! .]*',clean,re.I):
        result=build_response([BY_ID['help']],'knowledge');result['answer']='Hi! I’m Nova, your CareerNova website assistant. '+result['answer'];return result
    if re.fullmatch(r'(thanks|thank you|ok|okay|got it)[! .]*',clean,re.I):
        result=build_response([BY_ID.get(context_topic,BY_ID['help'])],'knowledge');result['answer']='You’re welcome. You can ask another CareerNova question or use the page links below.';return result
    # Short references use the last reviewed topic, never untrusted chat instructions.
    references=bool(re.search(r'\b(it|that|this|those|there|more|next)\b',clean,re.I))
    named=tokens(clean)&{'resume','profile','google','github','password','email','alert','timeline','interview','privacy','session','duplicate','search','board','reminder','compare','admin','account'}
    if context_topic in BY_ID and references and not named and len(clean.split())<=16:
        return build_response([BY_ID[context_topic]],'knowledge')
    lexical=lexical_scores(clean)
    semantic=semantic_scores(clean)
    scores=[.78*semantic[index]+.22*lexical[index] if semantic is not None else lexical[index] for index in range(len(ARTICLES))]
    ranking=sorted(range(len(ARTICLES)),key=lambda i:scores[i],reverse=True)
    best=ranking[0]
    recognized=bool(tokens(clean)&set(FREQUENCY))
    confident=(semantic is not None and semantic[best]>=.36 and scores[best]>=.29) or (lexical[best]>=.27 and recognized)
    if not confident:
        return {'answer':'I can help with CareerNova website questions, but I couldn’t find a reliable answer to that. Try asking about job search, resumes, applications, alerts, account access or privacy. I can explain these features, but I can’t view your private account records or perform actions for you.',
                'topic':None,'sources':[],'suggestions':[{'label':BY_ID[key]['title'],'question':BY_ID[key]['title']} for key in ('search','matching','help')],'mode':'semantic' if semantic is not None else 'knowledge'}
    entries=[ARTICLES[best]]
    if re.search(r'\b(difference|versus|vs)\b',clean,re.I):
        second=ranking[1]
        if scores[second]>=scores[best]*.72 and lexical[second]>=.2:entries.append(ARTICLES[second])
    return build_response(entries,'semantic' if semantic is not None else 'knowledge')
