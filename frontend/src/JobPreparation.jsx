import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {request} from './api';
import './JobPreparation.css';

const labels={responsibilities:'Responsibilities',required:'Essential / required wording',preferred:'Preferred / optional wording',conditions:'Working conditions & other terms',review:'Other wording to review'};

export default function JobPreparation({job}){
 const[description,setDescription]=useState(job.description||'');const[resumeId,setResumeId]=useState('');
 const[resumes,setResumes]=useState([]);const[result,setResult]=useState(null);const[busy,setBusy]=useState(false);const[error,setError]=useState('');
 useEffect(()=>{let active=true;request('/api/resumes').then(d=>{if(active)setResumes(d.resumes);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
 useEffect(()=>{let active=true;setBusy(true);setResult(null);setError('');request('/api/application-preview',{method:'POST',body:{job_description:job.description||'',resume_id:null}}).then(d=>{if(active)setResult(d);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});return()=>{active=false;};},[job.id,job.description]);
 async function analyze(){setBusy(true);setError('');setResult(null);try{setResult(await request('/api/application-preview',{method:'POST',body:{job_description:description,resume_id:resumeId?Number(resumeId):null}}));}catch(e){setError(e.message);}finally{setBusy(false);}}
 function invalidate(){setResult(null);}
 return <section className="job-preparation" aria-label="Job decoder and application preparation">
  <h3>Understand the role before applying</h3><p>Decode the description and check your preparation using your saved profile and an optional resume.</p>
  {error&&<p role="alert">{error}</p>}
  <label>Resume to check<select value={resumeId} disabled={busy} onChange={e=>{setResumeId(e.target.value);invalidate();}}><option value="">No resume selected</option>{resumes.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
  <details><summary>{job.description?'Review / replace description':'Paste the job description'}</summary><label>Job description<textarea rows={7} maxLength={30000} disabled={busy} value={description} onChange={e=>{setDescription(e.target.value);invalidate();}} placeholder="Paste the employer’s description. Text is analyzed locally; the employer page is not fetched."/></label></details>
  <button type="button" className="secondary-button" disabled={busy} onClick={analyze}>{busy?'Checking…':'Decode description & check preparation'}</button>
  {result&&<><div className="preparation-checks"><h3>Your preparation checklist</h3>{result.checks.map(c=><article key={c.label}><strong>{c.label} · {c.state==='available'?'Available':'Prepare'}</strong><p>{c.detail}</p><Link to={c.link}>{c.state==='available'?'Review':'Add'} {c.label.toLowerCase()} →</Link></article>)}</div>
   <p className="preparation-limit">{result.limitations}</p>
   {!result.decoder.has_description?<p>No description was supplied. Paste it above to decode requirements; the profile and resume checks are still available.</p>:<>
    <h3>Job description decoder</h3><p>{result.decoder.method}</p>
    {Object.entries(labels).map(([key,title])=><details className="decoder-section" key={key} open={key==='required'||key==='preferred'}><summary>{title} ({result.decoder.sections[key].length})</summary>{result.decoder.sections[key].length?result.decoder.sections[key].map((entry,i)=><blockquote key={i}>{entry.quote}<small>{entry.basis}</small></blockquote>):<p>No explicit wording recognized. Check the original description.</p>}</details>)}
    <p><strong>Not specified in supplied text:</strong> {result.decoder.not_specified.join(', ')||'Each checked topic was mentioned; review the quoted wording for actual terms.'}</p>
    <div className="preparation-skills"><h3>Evidence for recognized required skills</h3><p><strong>Found in profile / selected resume:</strong> {result.skill_evidence.supported.join(', ')||'None recognized'}</p><p><strong>Not found in those sources:</strong> {result.skill_evidence.not_found.join(', ')||'None recognized'}</p><small>{result.skill_evidence.note}</small></div>
    <h3>Documents mentioned</h3>{result.documents.length?result.documents.map(d=><details className="decoder-section" key={d.name}><summary>{d.name} · {d.status}</summary>{d.quotes.map((q,i)=><blockquote key={i}>{q}</blockquote>)}</details>):<p>No additional document mentions recognized. The employer form may still request uploads.</p>}
   </>}
   <details className="decoder-section"><summary>Steps that may need your attention</summary><ul>{result.manual_steps.map(s=><li key={s}>{s}</li>)}</ul></details>
  </>}
 </section>;
}
