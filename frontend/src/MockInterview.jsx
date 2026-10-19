import {useEffect,useRef,useState} from 'react';
import {useLocation} from 'react-router-dom';
import {request} from './api';
import './MockInterview.css';

export default function MockInterview(){
 const location=useLocation();
 const[role,setRole]=useState(location.state?.job_title||'');
 const[description,setDescription]=useState(location.state?.job_description||'');
 const[resumes,setResumes]=useState([]);const[resumeId,setResumeId]=useState('');
 const[history,setHistory]=useState([]);const[session,setSession]=useState(null);
 const[index,setIndex]=useState(0);const[answer,setAnswer]=useState('');
 const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[status,setStatus]=useState('');
 const[listening,setListening]=useState(false);const[voice,setVoice]=useState(false);
 const recRef=useRef(null);const busyRef=useRef(false);const mountedRef=useRef(true);
 const question=session?.questions[index];
 async function loadHistory(){const d=await request('/api/mock-interviews');if(mountedRef.current)setHistory(d.interviews);}
 function stopVoice(){const rec=recRef.current;recRef.current=null;rec?.abort();window.speechSynthesis?.cancel();setListening(false);}
 useEffect(()=>{
  mountedRef.current=true;
  Promise.all([request('/api/resumes'),request('/api/mock-interviews')]).then(([r,h])=>{if(mountedRef.current){setResumes(r.resumes);setHistory(h.interviews);}}).catch(e=>{if(mountedRef.current)setError(e.message);});
  return()=>{mountedRef.current=false;recRef.current?.abort();window.speechSynthesis?.cancel();};
 },[]);
 function readQuestion(q=question){
  stopVoice();
  if(!q)return;
  if(!window.speechSynthesis){setStatus('Speech playback is unavailable. Read the question below.');return;}
  const utterance=new SpeechSynthesisUtterance(q.question+(q.resume_evidence?` Your resume says: ${q.resume_evidence}`:''));
  utterance.lang='en-US';utterance.rate=.95;
  utterance.onend=()=>{if(mountedRef.current)setStatus('Your turn. Type an answer or choose Dictate answer.');};
  utterance.onerror=()=>{if(mountedRef.current)setStatus('Voice paused. You can read the question and type.');};
  setStatus('Interviewer speaking…');window.speechSynthesis.speak(utterance);
 }
 function show(data,nextIndex){
  stopVoice();setSession(data);setIndex(nextIndex);setAnswer(data.answers[data.questions[nextIndex]?.id]||'');
  setStatus(data.status==='Completed'?'Your feedback is ready.':'Question ready. Your saved answers remain available.');
  if(voice&&data.status!=='Completed'&&data.questions[nextIndex])readQuestion(data.questions[nextIndex]);
 }
 async function action(fn){
  if(busyRef.current)return;
  busyRef.current=true;setBusy(true);setError('');
  try{await fn();}catch(e){if(mountedRef.current)setError(e.message);}
  finally{busyRef.current=false;if(mountedRef.current)setBusy(false);}
 }
 function create(){stopVoice();action(async()=>{const d=await request('/api/mock-interviews',{method:'POST',body:{role,resume_id:resumeId?Number(resumeId):null,job_description:description}});show(d,0);await loadHistory();});}
 function open(id){stopVoice();action(async()=>{const d=await request(`/api/mock-interviews/${id}`);const next=d.questions.findIndex(q=>!Object.hasOwn(d.answers,q.id));show(d,next<0?d.questions.length:next);});}
 function save(skip=false){
  stopVoice();action(async()=>{
   const d=await request(`/api/mock-interviews/${session.id}/answer`,{method:'POST',body:{question_id:question.id,answer:skip?'':answer.trim()}});
   const next=d.questions.findIndex((q,i)=>i>index&&!Object.hasOwn(d.answers,q.id));
   const earlier=d.questions.findIndex(q=>!Object.hasOwn(d.answers,q.id));
   show(d,next>=0?next:earlier>=0?earlier:d.questions.length);
  });
 }
 function pause(){
  stopVoice();action(async()=>{
   if(question){await request(`/api/mock-interviews/${session.id}/answer`,{method:'POST',body:{question_id:question.id,answer:answer.trim()}});}
   setSession(null);setAnswer('');setStatus('Interview paused. Open it from Previous interviews to continue. An empty answer is saved as skipped and can be revisited.');await loadHistory();
  });
 }
 function dictate(){
  stopVoice();setError('');
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Recognition){setStatus('Voice recognition is unavailable in this browser. Type your answer instead.');return;}
  const rec=new Recognition();recRef.current=rec;rec.lang='en-US';rec.interimResults=false;rec.continuous=false;
  rec.onresult=e=>{if(!mountedRef.current||recRef.current!==rec)return;const transcript=Array.from(e.results).filter(r=>r.isFinal).map(r=>r[0].transcript).join(' ');setAnswer(old=>(old.trim()+' '+transcript).trim().slice(0,10000));setStatus('Dictation added. Review and edit it before saving.');};
  rec.onerror=e=>{if(mountedRef.current&&e.error!=='aborted')setStatus(`Microphone: ${e.error}. You can type instead.`);};
  rec.onend=()=>{if(mountedRef.current&&recRef.current===rec){setListening(false);recRef.current=null;}};
  try{rec.start();setListening(true);setStatus('Listening… stop when finished, then review the transcript.');}catch{setStatus('Microphone could not start. Please try again or type.');}
 }
 const report=session?.report;
 return <section className="mock-interview" aria-label="Guided mock interview">
  <div className="mock-interview-heading"><span className="platform-eyebrow">ROLE + RESUME / GUIDED PRACTICE</span><h2>Your personal interview rehearsal</h2><p>Practise one question at a time, save your answers and get an improvement plan. Questions use role and resume templates. Feedback uses a local language model for topic overlap when available, plus answer-structure checks. No external AI API is required.</p></div>
  {error&&<p role="alert" className="platform-feedback">{error}</p>}
  <p role="status" aria-live="polite">{status}</p>
  <div className="mock-interview-layout"><aside>
   <form className="platform-card platform-form" onSubmit={e=>{e.preventDefault();create();}}><h3>Start an interview</h3>
    <label>Target role<input required minLength={2} maxLength={200} value={role} disabled={busy} onChange={e=>setRole(e.target.value)} placeholder="e.g. Data Analyst"/></label>
    <label>Your saved resume (optional)<select value={resumeId} disabled={busy} onChange={e=>setResumeId(e.target.value)}><option value="">Role-only interview</option>{resumes.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
    {!resumes.length&&<p>You can start with a role alone. Add a saved resume for questions about your own experience.</p>}
    <label>Job description (optional)<textarea rows={5} maxLength={30000} disabled={busy} value={description} onChange={e=>setDescription(e.target.value)} placeholder="Add requirements for more targeted skill questions."/></label>
    <label className="mock-check"><input type="checkbox" checked={voice} onChange={e=>{setVoice(e.target.checked);if(!e.target.checked)stopVoice();}}/> Read questions aloud</label>
    <button className="primary-button" disabled={busy||role.trim().length<2}>Start new interview</button>
    <small>Dictation is optional and may use your browser provider’s speech service. CareerNova stores the transcript you save, not microphone audio.</small>
   </form>
   <details className="platform-card"><summary>Previous interviews ({history.length})</summary>{history.map(h=><article className="mock-history" key={h.id}><strong>{h.role}</strong><small>{h.status} · {new Date(h.created_at).toLocaleDateString()}</small><div className="platform-actions"><button type="button" disabled={busy} onClick={()=>open(h.id)}>Open</button><button type="button" disabled={busy} onClick={()=>{if(window.confirm('Delete this interview and its answers?'))action(async()=>{await request(`/api/mock-interviews/${h.id}`,{method:'DELETE'});if(session?.id===h.id){stopVoice();setSession(null);}await loadHistory();});}}>Delete</button></div></article>)}</details>
  </aside><div className="platform-card mock-stage">
   {!session?<div className="platform-empty"><h3>Prepare, practise, reflect.</h3><p>Enter a role to begin; selecting a resume is optional. Your interview mixes technical knowledge, behavioral examples and HR questions, followed by feedback.</p></div>:<>
    <span className="platform-eyebrow">{session.status} · {session.resume_name}</span><h3>{session.role}</h3>
    <p>{Object.keys(session.answers).length} of {session.questions.length} questions processed · {Object.values(session.answers).filter(a=>a.trim()).length} answered</p>
    <progress max={session.questions.length} value={Object.keys(session.answers).length} aria-label="Interview progress"/>{!report&&<button type="button" className="secondary-button" disabled={busy} onClick={pause}>Save & pause interview</button>}
    {!report&&question&&<><span className="platform-eyebrow">QUESTION {index+1} / {session.questions.length} · {question.round ? `${question.round} · ` : ''}{question.category}</span><h2>{question.question}</h2>
     {question.resume_evidence&&<blockquote><small>From your selected resume</small><p>{question.resume_evidence}</p></blockquote>}
     <div className="platform-actions"><button type="button" disabled={busy} onClick={()=>readQuestion()}>Read question aloud</button><button type="button" onClick={()=>{stopVoice();setStatus('Voice stopped.');}}>Stop voice</button></div>
     <details><summary>Answer guidance</summary><p>{question.guide}</p>{question.resume_support===false&&<p>This skill was not recognized in your resume. Be clear about what you know and what you still need to learn.</p>}</details>
     <label className="mock-answer">Your answer<textarea rows={10} maxLength={10000} disabled={busy} value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Explain your thinking with a real example…"/></label>
     <small>{answer.length.toLocaleString()} / 10,000 characters. Voice text remains editable and is not saved until you choose Save answer.</small>
     <div className="platform-actions"><button type="button" className="primary-button" disabled={busy||listening||!answer.trim()} onClick={()=>save()}>Save answer & next</button><button type="button" className="secondary-button" disabled={busy} onClick={listening?()=>recRef.current?.stop():dictate}>{listening?'Finish dictation':'Dictate answer'}</button><button type="button" disabled={busy} onClick={()=>save(true)}>Skip question</button></div>
    </>}
    {!report&&!question&&<><h2>Ready to reflect?</h2><p>Review or revise any answer below, then finish to generate your feedback. Skipped answers are shown separately.</p><button type="button" className="primary-button" disabled={busy} onClick={()=>action(async()=>{const d=await request(`/api/mock-interviews/${session.id}/finish`,{method:'POST'});show(d,d.questions.length);await loadHistory();})}>Finish & get feedback</button></>}
    {!report&&<details className="mock-review"><summary>Review saved answers / revisit a question</summary>{session.questions.map((q,i)=><div className="mock-history" key={q.id}><strong>{q.category}</strong><p>{session.answers[q.id]||'Skipped / not answered'}</p><button type="button" disabled={busy} onClick={()=>show(session,i)}>Revisit question {i+1}</button></div>)}</details>}
    {report&&<div className="mock-report"><h2>Your practice overview</h2><p>{report.overview}</p><small>{report.analysis_method}</small><p className="mock-limitations">{report.limitations}</p>
     <h3>Technical, behavioral & HR overview</h3>{report.round_feedback?.map(r=><article className="mock-feedback" key={r.round}><strong>{r.round} · {r.answered} of {r.total} answered</strong>{r.strengths.length>0&&<><h4>Detected strengths</h4><ul>{r.strengths.map(x=><li key={x}>{x}</li>)}</ul></>}<h4>Practice priorities</h4><ul>{r.improvements.length?r.improvements.map(x=><li key={x}>{x}</li>):<li>{r.answered?'Review the detailed feedback and practise another example.':'Try answering this round in your next attempt.'}</li>}</ul></article>)}<h3>Where to focus next</h3>{report.priority_practice.length?report.priority_practice.map((p,i)=><article className="mock-feedback" key={p.question_id}><strong>{i+1}. {p.category}</strong><ul>{p.actions.map(a=><li key={a}>{a}</li>)}</ul></article>):<p>{report.answered_count?'Review each answer below and check technical accuracy separately.':'Answer some questions in a new attempt to receive answer feedback.'}</p>}
     {report.unanswered.length>0&&<p>{report.unanswered.length} questions were skipped. Include them in your next practice attempt.</p>}
     <h3>Question-by-question feedback</h3>{report.feedback.map(f=>{const q=session.questions.find(q=>q.id===f.question_id);return <details className="mock-feedback" key={f.question_id}><summary>{f.category} · {f.answered?'Answer reviewed':'Skipped'}</summary><p><strong>{q.question}</strong></p>{f.topic_overlap&&<p>Approximate topic overlap: {f.topic_overlap}. This does not establish correctness.</p>}<blockquote>{session.answers[f.question_id]||'No answer saved'}</blockquote>{f.answered&&<><h4>Detected strengths</h4><ul>{f.strengths.length?f.strengths.map(s=><li key={s}>{s}</li>):<li>No structure signals detected. Review your wording and level of detail.</li>}</ul></>}<h4>Improve your next answer</h4><ul>{f.improvements.map(s=><li key={s}>{s}</li>)}</ul></details>;})}
     <h3>Your next practice plan</h3><ol>{report.practice_plan.map(s=><li key={s}>{s}</li>)}</ol><button type="button" className="secondary-button" onClick={()=>{const blob=new Blob([JSON.stringify({role:session.role,questions:session.questions,answers:session.answers,report},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='careernova-interview-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>Download feedback</button>
    </div>}
   </>}
  </div></div>
 </section>;
}
