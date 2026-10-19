import {useEffect,useRef,useState} from 'react';
import {Link,useLocation} from 'react-router-dom';
import {Bot,Send,X,ArrowUpRight,RotateCcw,LoaderCircle} from 'lucide-react';
import {request} from './api';
import './NovaChatbot.css';

const greeting={role:'assistant',answer:'Hi, I’m Nova. Ask me how CareerNova works, where to find a feature, or how to solve a website issue.',sources:[]};
const starters=[{label:'Find jobs',question:'How do I search and filter jobs?'},{label:'Resume matching',question:'How does resume matching work?'},{label:'Google / GitHub login',question:'Why are Google and GitHub sign-in unavailable?'},{label:'Job alerts',question:'How do job alerts and email delivery work?'}];
const safePath=path=>typeof path==='string'&&path.startsWith('/')&&!path.startsWith('//')&&!/[\\\r\n]/.test(path);

export default function NovaChatbot(){
 const[open,setOpen]=useState(false);const[draft,setDraft]=useState('');const[messages,setMessages]=useState([greeting]);const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[context,setContext]=useState(null);const[suggestions,setSuggestions]=useState(starters);const[lastQuestion,setLastQuestion]=useState(null);
 const input=useRef(null);const launcher=useRef(null);const log=useRef(null);const controller=useRef(null);const sending=useRef(false);const timeout=useRef(null);const location=useLocation();
 useEffect(()=>{if(open)input.current?.focus();},[open]);
 useEffect(()=>{if(log.current)log.current.scrollTop=log.current.scrollHeight;},[messages,busy,error]);
 useEffect(()=>()=>{const active=controller.current;controller.current=null;active?.abort();clearTimeout(timeout.current);},[]);
 useEffect(()=>{if(!open)return;const abort=new AbortController();request('/api/chat/help',{signal:abort.signal}).catch(()=>{});return()=>abort.abort();},[open]);
 function close(){setOpen(false);launcher.current?.focus();}
 function reset(){const active=controller.current;controller.current=null;active?.abort();clearTimeout(timeout.current);sending.current=false;setBusy(false);setMessages([greeting]);setContext(null);setSuggestions(starters);setError('');setLastQuestion(null);setDraft('');input.current?.focus();}
 async function ask(text,retry=false){
   const question=text.trim();if(!question||sending.current)return;
   const payload=retry?lastQuestion:{message:question,context_topic:context};if(!payload)return;
   sending.current=true;setBusy(true);setError('');setLastQuestion(payload);
   if(!retry)setMessages(old=>[...old.slice(-39),{role:'user',answer:question}]);
   setDraft('');const abort=new AbortController();controller.current=abort;timeout.current=setTimeout(()=>abort.abort(),20000);
   try{
     const data=await request('/api/chat/message',{method:'POST',body:payload,signal:abort.signal});
     if(abort.signal.aborted)return;
     if(typeof data.answer!=='string'||!Array.isArray(data.sources))throw new Error('The assistant returned an unreadable response. Please try again.');
     setMessages(old=>[...old.slice(-39),{role:'assistant',...data}]);setContext(data.topic||null);setSuggestions(data.suggestions?.length?data.suggestions:starters);setLastQuestion(null);
   }catch(err){
     if(controller.current!==abort)return;
     setError(abort.signal.aborted?'Nova took too long to reply. Please try again.':err.message||'Could not connect to Nova. Please try again.');
   }finally{
     if(controller.current===abort){clearTimeout(timeout.current);sending.current=false;setBusy(false);input.current?.focus();}
   }
 }
 return <div className="nova-chat-widget">
   {open&&<section id="nova-help-panel" className="nova-chat-panel" role="dialog" aria-label="Nova website assistant" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close();}}}>
     <header className="nova-chat-header"><span className="nova-chat-avatar"><Bot size={22}/></span><div><strong>Nova</strong><small>CareerNova website assistant</small></div><button type="button" onClick={reset} aria-label="Start a new chat" title="Clear this conversation"><RotateCcw size={17}/></button><button type="button" onClick={close} aria-label="Close Nova chat"><X size={20}/></button></header>
     <div className="nova-chat-location">Help for {location.pathname==='/'?'CareerNova':location.pathname.slice(1).split('?')[0].replaceAll('-',' ')}</div>
     <div className="nova-chat-log" ref={log} role="log" aria-label="Chat messages" aria-live="polite" aria-relevant="additions text">
       {messages.map((message,index)=><article key={index} className={`nova-chat-message ${message.role==='user'?'nova-chat-user':'nova-chat-assistant'}`}><span className="nova-chat-speaker">{message.role==='user'?'You':'Nova'}</span><p>{message.answer}</p>{message.sources?.length>0&&<div className="nova-chat-sources">{message.sources.filter(source=>safePath(source.path)).map(source=><Link key={source.topic||source.path} to={source.path}>{source.title}<ArrowUpRight size={14}/></Link>)}</div>}</article>)}
       {busy&&<p className="nova-chat-thinking" role="status"><LoaderCircle size={15} aria-hidden="true"/>Finding the right help…</p>}
     </div>
     {error&&<div className="nova-chat-error" role="alert"><p>{error}</p>{lastQuestion&&<button type="button" disabled={busy} onClick={()=>ask(lastQuestion.message,true)}>Try again</button>}</div>}
     <div className="nova-chat-suggestions" aria-label="Suggested questions">{suggestions.slice(0,4).map(item=><button key={item.question} type="button" disabled={busy} onClick={()=>ask(item.question)}>{item.label}</button>)}</div>
     <form className="nova-chat-compose" onSubmit={e=>{e.preventDefault();ask(draft);}}><label className="nova-chat-input-label" htmlFor="nova-help-message">Ask a CareerNova question</label><textarea id="nova-help-message" ref={input} rows={2} maxLength={2000} value={draft} onChange={e=>setDraft(e.target.value)} placeholder="How do I save a search?" onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();ask(draft);}}}/><button className="nova-chat-send" type="submit" disabled={busy||!draft.trim()} aria-busy={busy} aria-label="Send message">{busy?<LoaderCircle size={19}/>:<Send size={19}/>}</button></form>
     <footer className="nova-chat-footer">Answers from CareerNova help · Chat stays on this page</footer>
   </section>}
   <button ref={launcher} className="nova-chat-launcher" type="button" onClick={()=>open?close():setOpen(true)} aria-label={open?'Close Nova chat':'Open Nova chat'} aria-expanded={open} aria-controls="nova-help-panel">{open?<X size={23}/>:<><Bot size={24}/><span>Ask Nova</span></>}</button>
 </div>;
}
