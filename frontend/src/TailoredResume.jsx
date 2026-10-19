import {useEffect,useState} from 'react';
import {useLocation} from 'react-router-dom';
import {request,API_URL} from './api';

export default function TailoredResume(){
 const location=useLocation();
 const[resumes,setResumes]=useState([]);const[id,setId]=useState('');
 const[description,setDescription]=useState(location.state?.job_description||'');
 const[name,setName]=useState(location.state?.job_title ? `${location.state.job_title} resume`.slice(0,120) : 'Tailored resume');
 const[draft,setDraft]=useState(null);const[text,setText]=useState('');const[saved,setSaved]=useState(null);
 const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[reviewed,setReviewed]=useState(false);
 async function load(){const d=await request('/api/resumes');setResumes(d.resumes);}
 useEffect(()=>{const refresh=()=>load().catch(e=>setError(e.message));refresh();window.addEventListener('careernova-resumes-updated',refresh);return()=>window.removeEventListener('careernova-resumes-updated',refresh);},[]);
 function invalidate(){setDraft(null);setText('');setSaved(null);setReviewed(false);}
 async function generate(){setBusy(true);setError('');setSaved(null);setReviewed(false);try{const d=await request('/api/resume-tailor',{method:'POST',body:{resume_id:Number(id),job_description:description}});setDraft(d);setText(d.text);}catch(e){setError(e.message);}finally{setBusy(false);}}
 async function save(){setBusy(true);setError('');try{const d=await request('/api/resume-tailor/save',{method:'POST',body:{text,name}});setSaved(d);await load();window.dispatchEvent(new Event('careernova-resumes-updated'));}catch(e){setError(e.message);}finally{setBusy(false);}}
 return <section className="platform-card platform-form" style={{marginTop:24}} aria-label="Prepare a resume for a job"><span className="platform-eyebrow">PREPARE FOR THIS ROLE</span><h2>Job-specific resume draft</h2><p>Choose your resume and paste the job description. Local keyword matching prioritizes existing bullet points and highlights supported skills. Your experience, employers and dates are retained.</p>
 {error&&<p role="alert" className="platform-feedback">{error}</p>}
 <label>Source resume<select value={id} disabled={busy} onChange={e=>{setId(e.target.value);invalidate();}}><option value="">Choose a saved resume</option>{resumes.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
 <label>Job description<textarea rows={7} minLength={20} maxLength={30000} disabled={busy} value={description} onChange={e=>{setDescription(e.target.value);invalidate();}}/></label>
 <button type="button" className="primary-button" disabled={busy||!id||description.trim().length<20} onClick={generate}>{busy?'Working…':'Prepare resume draft'}</button>
 {draft&&<><p>{draft.method}</p><p><strong>Supported role skills:</strong> {draft.matched_skills.join(', ')||'None recognized'}</p><p><strong>Not supported by this resume:</strong> {draft.missing_skills.join(', ')||'None recognized in the supported vocabulary'}. Missing skills have not been added.</p><details><summary>What changed & source evidence</summary><ul>{draft.changes.map(c=><li key={c}>{c}</li>)}</ul>{draft.evidence.map((e,i)=><blockquote key={i}>{e.text}<br/><small>{e.source}</small></blockquote>)}</details>
 <label>Review and edit your draft<textarea rows={22} maxLength={100000} value={text} onChange={e=>{setText(e.target.value);setReviewed(false);setSaved(null);}}/></label><label>Version name<input maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label>
 <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/> I reviewed the draft and confirm it accurately represents my experience.</label>
 <button type="button" className="primary-button" disabled={busy||!reviewed||text.trim().length<30||!name.trim()} onClick={save}>Save reviewed DOCX version</button>
 {saved&&<p role="status">Saved as “{saved.name}”. <a href={`${API_URL}/api/resumes/${saved.id}/download`}>Download DOCX</a>. It is also available in your resume library and application assistant.</p>}</>}
 </section>;
}
