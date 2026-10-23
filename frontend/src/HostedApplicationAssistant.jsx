import { useEffect, useRef, useState } from 'react';
import { request } from './api';

const fields = [['first_name','First name'],['last_name','Last name'],['email','Email'],['phone','Phone'],['location','Location'],['linkedin_url','LinkedIn URL'],['github_url','GitHub URL'],['portfolio_url','Portfolio URL'],['university','University'],['degree','Degree'],['experience_years','Years of experience'],['skills','Skills'],['education','Education'],['work_authorization','Work authorization'],['sponsorship_required','Sponsorship required']];

export default function HostedApplicationAssistant({job,onClose,loadingMode}) {
  const [profile,setProfile]=useState({});
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [question,setQuestion]=useState('');
  const [answer,setAnswer]=useState('');
  const recognition=useRef(null);
  const [listening,setListening]=useState(false);
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError('');
    request('/api/profile/me').then(data=>{if(active)setProfile(data);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[attempt]);
  useEffect(()=>()=>recognition.current?.abort(),[]);
  const url=job.apply_url||job.url||'';
  const safeUrl=/^https?:\/\//i.test(url)?url:'';
  async function copy(value) {
    try {await navigator.clipboard.writeText(String(value));setMessage('Copied. Paste into the employer form.');}
    catch {setMessage('Clipboard unavailable. Select and copy the field text manually.');}
  }
  function dictate() {
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!Recognition){setMessage('Use your keyboard microphone or type an answer.');return;}
    recognition.current?.abort();
    const rec=new Recognition();recognition.current=rec;rec.lang='en-US';
    rec.onresult=e=>{setAnswer(e.results[0][0].transcript);setMessage('Review the transcript before copying.');};
    rec.onerror=()=>setMessage('Voice input stopped. Type your answer or try again.');
    rec.onend=()=>setListening(false);
    try{rec.start();setListening(true);}catch{setListening(false);setMessage('Microphone could not start. Type your answer instead.');}
  }
  function exportProfile() {
    const blob=new Blob([JSON.stringify({profile},null,2)],{type:'application/json'});
    const href=URL.createObjectURL(blob);const link=document.createElement('a');link.href=href;link.download='careernova-autofill-profile.json';link.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
    setMessage('Profile exported to your device. Import it only into your CareerNova extension. It contains personal information.');
  }
  return <div className="tool-modal-backdrop" style={{zIndex:2000}} role="dialog" aria-modal="true" aria-label="Nova application workspace"><div className="tool-modal platform-card">
    <button className="secondary-button" onClick={onClose} style={{float:'right'}}>Close</button><h2>Apply with Nova</h2><p>{job.title} — {job.company}</p>
    <p>Nova prepares your saved details here. Open the employer application, then use the desktop extension to fill supported fields, or copy answers on your phone. Review everything before submitting.</p>
    {safeUrl&&<a className="primary-button" href={safeUrl} target="_blank" rel="noopener noreferrer">Open employer application ↗</a>}
    {(loading||loadingMode)&&<p role="status">Loading saved application details…</p>}
    {error&&<div role="alert"><p>Saved profile could not be loaded: {error}</p><button onClick={()=>setAttempt(n=>n+1)}>Retry profile</button><a href="/profile">Open Candidate Profile</a></div>}
    {!loading&&!error&&<><h3>Your saved application details</h3><p>These edits are temporary. Use Candidate Profile to save permanent changes.</p>{fields.map(([key,label])=><label key={key} style={{display:'block',margin:'14px 0'}}>{label}<div style={{display:'flex',gap:8}}><input aria-label={label} value={profile[key]||''} onChange={e=>setProfile(p=>({...p,[key]:e.target.value}))} style={{flex:1,minWidth:0,padding:12}}/><button disabled={!profile[key]} onClick={()=>copy(profile[key])}>Copy</button></div></label>)}
    <details><summary>Automatic filling on a desktop browser</summary><p>Download the extension, unzip it, then open Chrome or Edge Extensions → Developer mode → Load unpacked. Select the extracted folder. Export your details below and import that file in the extension. On an employer form, click “Fill this page”. It fills empty supported text fields only; it does not submit, handle logins, upload resumes, or answer eligibility questions.</p><a className="secondary-button" href="/careernova-autofill.zip" download>Download desktop extension</a><button className="secondary-button" onClick={exportProfile}>Export details for extension</button><p>Phones can use the copy and dictation tools here. A website cannot directly edit another site's form on mobile Safari.</p></details></>}
    <h3>Answer an extra question</h3><label>Employer question<input value={question} onChange={e=>setQuestion(e.target.value)} style={{display:'block',width:'100%'}}/></label><label>Your answer<textarea aria-label="Your answer" value={answer} onChange={e=>setAnswer(e.target.value)} rows={4} style={{width:'100%',display:'block'}}/></label>
    <div className="platform-actions"><button disabled={listening} onClick={dictate}>Dictate answer</button><button disabled={!listening} onClick={()=>recognition.current?.stop()}>Stop microphone</button><button disabled={!answer.trim()} onClick={()=>copy(answer)}>Copy reviewed answer</button></div><small>Voice recognition may use your browser provider's speech service. No audio is stored by CareerNova.</small><p role="status">{message}</p>
  </div></div>;
}
