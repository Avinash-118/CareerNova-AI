import { API_URL as API_BASE, apiFetch } from "./api";
import { useEffect, useRef, useState } from 'react';
import HostedApplicationAssistant from './HostedApplicationAssistant';

const API = API_BASE;
const SpeechRecognitionClass = () => window.SpeechRecognition || window.webkitSpeechRecognition;


// Conservative exact-label matching. Never guess sponsorship, authorization, or eligibility.
function profileSuggestion(field, profile) {
  if (!profile || !field || field.type === 'file' || field.type === 'password' ||
      ['checkbox', 'radio'].includes(field.type)) return null;
  const label = String(field.label || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const names = {
    'first name': 'first_name', 'given name': 'first_name',
    'last name': 'last_name', 'family name': 'last_name', 'surname': 'last_name',
    'email': 'email', 'email address': 'email',
    'phone': 'phone', 'phone number': 'phone', 'mobile number': 'phone',
    'current location': 'location', 'current city': 'location',
    'linkedin': 'linkedin_url', 'linkedin url': 'linkedin_url', 'linkedin profile': 'linkedin_url',
    'github': 'github_url', 'github url': 'github_url',
    'portfolio': 'portfolio_url', 'portfolio url': 'portfolio_url',
    'university': 'university', 'university college': 'university',
    'degree': 'degree', 'years of experience': 'experience_years',
    'skills': 'skills', 'education details': 'education'
  };
  const key = names[label];
  if (!key || !String(profile[key] || '').trim()) return null;
  const value = String(profile[key]).trim();
  if (field.tag === 'select') {
    const option = (field.options || []).find(x => x.trim().toLowerCase() === value.toLowerCase());
    return option ? { value: option, key } : null;
  }
  return { value, key };
}

export default function ApplicationVoiceAssistant(props) {
  const [mode, setMode] = useState('loading');
  useEffect(() => {
    let active = true;
    apiFetch(`${API}/api/agent/capabilities`).then(async r => {
      if (!r.ok) throw new Error('Unable to check application tools.');
      const data = await r.json();
      if (active) setMode(data.desktop_browser ? 'desktop' : 'hosted');
    }).catch(() => { if (active) setMode('hosted'); });
    return () => { active = false; };
  }, []);
  if (mode === 'desktop') return <DesktopApplicationAssistant {...props}/>;
  return <HostedApplicationAssistant {...props} loadingMode={mode === 'loading'}/>;
}

function DesktopApplicationAssistant({ job, onClose, initialResumeFile = null, initialResumeId = '' }) {
  const automaticResumeAttempts = useRef(new Set());
  const [session, setSession] = useState(null);
  const [autofillSummary, setAutofillSummary] = useState('');
  const [fillErrors, setFillErrors] = useState([]);
  const [profile, setProfile] = useState(null);
  const [profileStatus, setProfileStatus] = useState('Loading saved profile…');
  const [suggestion, setSuggestion] = useState(null);
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [review, setReview] = useState(null);
  const [rememberAnswer, setRememberAnswer] = useState(false);
  const rememberRef = useRef(false);
  const answerSourceRef = useRef('typed');
  const [memories, setMemories] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [progress, setProgress] = useState(null);
  const [phase, setPhase] = useState('Opening application…');
  const [waitingForLogin, setWaitingForLogin] = useState(false);
  const [heard, setHeard] = useState(false);
  const busyRef = useRef(busy);
  busyRef.current = busy;
  const sessionRef = useRef(null);
  const profileRef = useRef(null);
  const recognitionRef = useRef(null);
  const activeRef = useRef(true);
  const questionRef = useRef(null);
  const answerRef = useRef('');
  const listeningRef = useRef(false);
  const speakRef = useRef(null);
  const listenTimerRef = useRef(null);
  const listeningModeRef = useRef('answer');
  const lastQuestionKeyRef = useRef('');
  const resumeRef = useRef(null);

  function stopAudio() {
    clearTimeout(listenTimerRef.current);
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    listeningRef.current = false;
    window.speechSynthesis?.cancel();
  }

  // Wait for the previous recognition session to finish before starting another.
  function beginListening(mode = 'answer') {
    if (!activeRef.current) return;
    const Recognition = SpeechRecognitionClass();
    if (!Recognition) {
      setPhase('Microphone recognition is unavailable. Type your answer instead.');
      return;
    }
    clearTimeout(listenTimerRef.current);
    const previous = recognitionRef.current;
    if (previous && listeningRef.current) {
      try { previous.abort(); } catch (_) { /* already stopped */ }
    }
    listeningModeRef.current = mode;
    listenTimerRef.current = setTimeout(() => {
      if (!activeRef.current) return;
      const rec = new Recognition();
      recognitionRef.current = rec;
      listeningRef.current = true;
      rec.lang = 'en-US';
      rec.interimResults = false;
      rec.continuous = false;
      rec.maxAlternatives = 3;
      let gotResult = false;
      rec.onresult = (event) => {
        gotResult = true;
        const transcript = event.results[0][0].transcript.trim();
        if (mode === 'confirm') {
          const command = transcript.toLowerCase().replace(/[.,!?]/g, '');
          if (!/\b(no|not|incorrect|wrong|retry|change)\b/.test(command) && /\b(confirm|correct|yes|continue|next|that's right|that is right)\b/.test(command)) {
            setPhase('Entering confirmed answer…');
            sendAnswer(answerRef.current);
          } else if (/\b(retry|repeat|change|no|not|incorrect|wrong)\b/.test(command)) {
            setHeard(false);
            speakRef.current?.('Okay. Please say your answer again.', () => beginListening('answer'));
          } else {
            setPhase('I did not understand the confirmation. Say confirm or retry, or use the buttons.');
          }
          return;
        }
        if (/\b(i(?:'| a)?m logged in|i have logged in|continue (my )?application|resume (my )?application|fill (the )?form|i signed in|i finished registration)\b/i.test(transcript)) {
          resumeRef.current?.();
          return;
        }
        const current = questionRef.current?.question;
        // Keep dictated text intact; never silently guess spellings or rewrite names.
        answerSourceRef.current = 'voice';
        answerRef.current = transcript;
        setAnswer(transcript);
        setHeard(true);
        setError('');
        setPhase('Check the recognized spelling. Say confirm or retry.');
        const sensitive = current?.type === 'email' || /name|email|phone|address/i.test(current?.label || '');
        const prompt = sensitive
          ? 'I have written your answer on screen. Please check the spelling carefully. Say confirm if correct, or retry to say it again.'
          : `I heard ${transcript}. Say confirm if correct, or retry to answer again.`;
        speakRef.current?.(prompt, () => beginListening('confirm'));
      };
      rec.onerror = (event) => {
        if (event.error === 'aborted') return;
        if (event.error === 'no-speech') {
          setPhase('No speech detected. Please try again or type your answer.');
        } else {
          setError(`Microphone: ${event.error}. You can retry or type your answer.`);
          setPhase('Voice paused.');
        }
      };
      rec.onend = () => {
        listeningRef.current = false;
        if (recognitionRef.current === rec) recognitionRef.current = null;
        if (!gotResult && activeRef.current) setPhase('Microphone stopped. Use Retry voice or type your answer.');
      };
      try {
        setPhase(mode === 'confirm' ? 'Listening for confirm or retry…' : 'Listening for your answer…');
        rec.start();
      } catch (e) {
        listeningRef.current = false;
        setError(`Microphone could not start: ${e.message}`);
      }
    }, 350);
  }

  function speak(text, after) {
    if (!activeRef.current) return;
    window.speechSynthesis?.cancel();
    if (!('speechSynthesis' in window)) {
      setPhase('Speech playback unavailable. Use the controls below.');
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 0.95;
    utterance.onend = () => { if (activeRef.current) after?.(); };
    utterance.onerror = () => setPhase('Speech playback unavailable. Use the controls below.');
    setPhase('AI speaking…');
    window.speechSynthesis.speak(utterance);
  }
  speakRef.current = speak;

  function presentQuestion(data) {
    if (!data) { setError('No question returned. Continue the application to inspect the form again.'); return; }
    rememberRef.current = false;
    setRememberAnswer(false);
    answerSourceRef.current = 'typed';
    setProgress(data.progress || null);
    questionRef.current = data;
    setQuestion(data);
    setAnswer('');
    answerRef.current = '';
    const evidence = data.question?.evidence || [];
    setSuggestion(evidence.length ? {value:evidence[0].value, key:evidence[0].source} : profileSuggestion(data.question, profileRef.current));
    setHeard(false);
    if (data.completed) {
      setPhase('All questions processed. Ready for review.');
      speak('All detected questions have been processed. Please review your answers before submitting the application yourself.');
    } else if (data.question?.type === 'file') {
      if (initialResumeId && /resume|\bcv\b/i.test(data.question.label || '')) {
        setPhase('Preparing your selected saved resume…');
        return;
      }
      setPhase('Resume upload requires selecting a file.');
      speak(`Question ${data.question_number}. ${data.question.label}. Please select your resume file using the upload control.`);
    } else {
      speak(`Question ${data.question_number} of ${data.total_questions}. ${data.question?.label || 'Application question'}. ${data.question?.options?.length ? 'Options are: ' + data.question.options.filter(Boolean).join(', ') + '.' : ''} Please answer when I finish speaking.`, () => beginListening('answer'));
    }
  }

  useEffect(() => {
    if (busy || !session || !initialResumeId || question?.question?.type !== 'file' || !/resume|\bcv\b/i.test(question.question.label || '')) return;
    const key = `${session}:${question.question_number}:${initialResumeId}`;
    if (automaticResumeAttempts.current.has(key)) return;
    automaticResumeAttempts.current.add(key);
    setPhase('Uploading your selected saved resume…');
    request('resume-version',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({resume_id:Number(initialResumeId)})});
  }, [busy, session, question, initialResumeId]);

  useEffect(() => {
    activeRef.current = true;
    let cancelled = false;
    async function start() {
      try {
        try {
          const profileResponse = await apiFetch(`${API}/api/profile/me`);
          if (profileResponse.ok) {
            const saved = await profileResponse.json();
            profileRef.current = saved;
            if (!cancelled) { setProfile(saved); setProfileStatus('Saved profile available'); }
          } else if (!cancelled) {
            setProfileStatus('No saved profile found; voice and manual entry remain available');
          }
        } catch (_) {
          if (!cancelled) setProfileStatus('Profile unavailable; voice and manual entry remain available');
        }

        const response = await apiFetch(`${API}/api/agent/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_url: job.apply_url })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
        if (cancelled) {
          await apiFetch(`${API}/api/agent/${data.session_id}/close`, { method: 'POST' }).catch(() => {});
          return;
        }
        sessionRef.current = data.session_id;
        setSession(data.session_id);
        if (!['ready', 'registration'].includes(data.stage)) {
          setWaitingForLogin(true);
          setPhase(data.message);
          speakRef.current?.(data.message, () => beginListening('resume'));
          return;
        }
        setPhase('Automatically filling known profile fields…');
        const qResponse = await apiFetch(`${API}/api/agent/${data.session_id}/autofill`, { method: 'POST' });
        const qData = await qResponse.json();
        if (!qResponse.ok) throw new Error(qData.detail || 'Could not autofill application');
        if (!cancelled) {
          if (qData.stage && !['ready', 'registration'].includes(qData.stage)) {
            setWaitingForLogin(true);
            setPhase(qData.message);
            speakRef.current?.(qData.message, () => beginListening('resume'));
          } else {
            setConflicts(qData.conflicts || []);
            setFillErrors(qData.field_errors || []);
            setAutofillSummary(`Filled ${qData.autofilled_count} fields automatically. ${qData.remaining_count} fields need attention.`);
            presentQuestion(qData.next_question);
          }
        }
      } catch (e) {
        if (!cancelled) { setError(e.message); setPhase('Unable to start the assistant.'); }
      } finally { if (!cancelled) setBusy(false); }
    }
    start();
    return () => {
      cancelled = true;
      activeRef.current = false;
      stopAudio();
      const id = sessionRef.current;
      if (id) apiFetch(`${API}/api/agent/${id}/close`, { method: 'POST' }).catch(() => {});
    };
  }, [job.apply_url]);

  useEffect(() => {
    if (!waitingForLogin || !session) return;
    let cancelled = false;
    let checking = false;
    const timer = setInterval(async () => {
      if (cancelled || checking || busyRef.current) return;
      checking = true;
      try {
        const response = await apiFetch(`${API}/api/agent/${session}/scan`, {method:'POST'});
        const data = await response.json();
        if (!response.ok) {
          if (!cancelled) setError(data.detail || 'Could not check the employer form. Try Rescan current form.');
          return;
        }
        if (!cancelled && ['ready', 'registration'].includes(data.stage)) {
          clearInterval(timer);
          resumeRef.current?.();
        }
      } catch (_) {
        if (!cancelled) setError('Could not reach the assistant. Keep the browser open and try Rescan current form.');
      } finally { checking = false; }
    }, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [waitingForLogin, session]);

  async function resumeApplication() {
    const id = sessionRef.current;
    if (!id) return;
    stopAudio();
    busyRef.current = true;
    setBusy(true);
    setError('');
    setReview(null);
    setPhase('Checking the employer application page…');
    try {
      const response = await apiFetch(`${API}/api/agent/${id}/resume`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not resume');
      if (!['ready', 'registration'].includes(data.stage)) {
        setWaitingForLogin(true);
        setPhase(data.message);
        speak(data.message, () => beginListening('resume'));
        return;
      }
      setWaitingForLogin(false);
      setPhase('Application form found. Filling saved profile fields…');
      speak('I found the application form. I will fill the details from your saved profile.');
      const fillResponse = await apiFetch(`${API}/api/agent/${id}/autofill`, { method: 'POST' });
      const fillData = await fillResponse.json();
      if (!fillResponse.ok) throw new Error(fillData.detail || 'Autofill failed');
      if (fillData.stage && !['ready', 'registration'].includes(fillData.stage)) {
        setWaitingForLogin(true);
        setPhase(fillData.message);
        speak(fillData.message, () => beginListening('resume'));
        return;
      }
      setConflicts(fillData.conflicts || []);
      setFillErrors(fillData.field_errors || []);
      setAutofillSummary(`Filled ${fillData.autofilled_count} fields automatically. ${fillData.remaining_count} fields need attention.`);
      presentQuestion(fillData.next_question);
    } catch (e) {
      setError(e.message);
      setPhase('Could not resume. Keep the employer browser open and try again.');
    } finally {
      setBusy(false);
    }
  }
  resumeRef.current = resumeApplication;

  async function request(path, options = {}) {
    if (!sessionRef.current || busyRef.current) return;
    stopAudio();
    busyRef.current = true;
    setBusy(true);
    setError('');
    try {
      const response = await apiFetch(`${API}/api/agent/${sessionRef.current}/${path}`, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      if (path === 'review') {
        setReview(data);
        setPhase('Review answers in the browser before submitting manually.');
        speak('Here is your review. The application has not been submitted.');
      } else {
        setReview(null);
        presentQuestion(data.next_question || data);
        if (path === 'answer') loadMemories();
      }
    } catch (e) { setError(e.message); setPhase('Please correct the error and try again.'); }
    finally { setBusy(false); }
  }

  function sendAnswer(value = answerRef.current) {
    if (!value?.trim()) { setError('Please speak or type an answer first.'); return; }
    request('answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value.trim(), remember: rememberRef.current, source: answerSourceRef.current })
    });
  }

  const [resumeVersions, setResumeVersions] = useState([]);
  const [selectedResumeVersion, setSelectedResumeVersion] = useState(String(initialResumeId || ''));
  useEffect(() => {
    apiFetch(`${API}/api/resumes`).then(r => r.ok ? r.json() : {resumes:[]}).then(d => setResumeVersions(d.resumes)).catch(() => {});
  }, []);
  async function loadMemories() {
    try {
      const response = await apiFetch(`${API}/api/agent/memory/answers`);
      if (!response.ok) throw new Error('Could not load remembered answers');
      setMemories((await response.json()).answers);
    } catch (e) { setError(e.message); }
  }
  async function checkEvidence() {
    if (!sessionRef.current || busyRef.current) return;
    stopAudio(); setBusy(true); busyRef.current = true; setError('');
    try {
      const response = await apiFetch(`${API}/api/agent/${sessionRef.current}/autofill`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({resume_id:selectedResumeVersion ? Number(selectedResumeVersion) : null})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Evidence check failed');
      setReview(null); setConflicts(data.conflicts || []); setFillErrors(data.field_errors || []);
      if (data.next_question) presentQuestion(data.next_question);
      else setPhase(data.message || 'Continue to the application form first.');
    } catch(e) { setError(e.message); }
    finally { setBusy(false); busyRef.current = false; }
  }
  const field = question?.question;
  return (
    <div role="dialog" aria-modal="true" aria-label="CareerNova AI voice application assistant" style={{ position: 'fixed', inset: 0, background: '#000d', zIndex: 2000, display: 'grid', placeItems: 'center', padding: 16 }}>
      <div style={{ background: '#191726', color: 'white', border: '1px solid #6b5c83', borderRadius: 16, padding: 26, width: 'min(100%, 620px)', maxHeight: '90vh', overflowY: 'auto' }}>
        <button type="button" className="secondary-button" onClick={onClose} style={{ float: 'right' }}>Close</button>
        <h2>CareerNova AI Application Assistant</h2>
        <p>{job.title} — {job.company}</p>
        <p>{profileStatus}. Nova fills supported saved details first, then asks for the remaining fields. If the employer requires sign-in, complete it in the opened browser and choose Continue.</p>
        <p>Saved profile details are filled first. For missing answers, allow microphone access, speak, then say confirm or retry. Browser speech recognition may use your browser provider’s speech service.</p>
        <button type="button" className="secondary-button" onClick={() => { stopAudio(); setPhase('Voice paused. Type an answer or choose Retry voice.'); }}>Pause voice</button>
        <p aria-live="polite">{phase}</p>
        {autofillSummary && <p style={{color: "#7ee8b2"}}>{autofillSummary}</p>}
        {fillErrors.length > 0 && <p role="status">Some fields could not be verified: {fillErrors.map(x => x.question).join(', ')}. Nova will ask for the remaining answers.</p>}
        {waitingForLogin && <div style={{ padding: 14, border: '1px solid #625c91', borderRadius: 10, marginBottom: 16 }}>
          <h3>Waiting for the Application tab / employer login</h3>
          <p>Click the Application tab in the employer browser, or complete sign-in if requested. Keep that browser open. Nova checks every few seconds and fills supported saved details when the form is found. You can also continue below.</p>
          <button type="button" className="primary-button" disabled={busy} onClick={resumeApplication}>Application is open — Scan & fill saved details</button>
          <button type="button" className="secondary-button" disabled={busy} onClick={() => { speak('I am waiting. When you are on the application form, say continue my application.', () => beginListening('resume')); }}>Listen for voice command</button>
        </div>}
        <details style={{marginBottom:16}}><summary>Application memory & consistency</summary>
          <p>Remembering is optional. Saved answers are suggestions for the exact same question, never automatically reused. Review eligibility and employer-specific answers each time.</p>
          <label>Resume to compare (optional)<select value={selectedResumeVersion} onChange={e=>setSelectedResumeVersion(e.target.value)}><option value="">Profile and memory only</option>{resumeVersions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
          <p>Resume comparison currently checks a single distinct email address. It does not validate employment dates, qualifications or experience.</p>
          <button type="button" className="secondary-button" disabled={busy||!session} onClick={checkEvidence}>Check sources & continue</button>
          <button type="button" className="secondary-button" onClick={loadMemories}>Show remembered answers</button>
          {memories.map(m=><div key={m.id} style={{padding:10,borderBottom:'1px solid #625c91'}}><strong>{m.question}</strong><p>{m.answer}</p><small>Confirmed {m.source} answer · {new Date(m.updated_at).toLocaleString()}</small><button type="button" className="secondary-button" onClick={async()=>{try{const r=await apiFetch(`${API}/api/agent/memory/answers/${m.id}`,{method:'DELETE'});if(!r.ok)throw new Error('Could not forget answer');await loadMemories();setPhase('Answer forgotten. Check sources again to refresh this session.');}catch(e){setError(e.message);}}}>Forget</button></div>)}
        </details>
        {conflicts.length>0 && <p role="status">Source differences need review: {conflicts.map(c=>c.question).join(', ')}. Choose or enter the correct answer when asked. Saved profile details are not changed.</p>}
        {session && <section aria-label="Application progress" style={{padding:14,border:'1px solid #625c91',borderRadius:10,marginBottom:16}}><h3>Application progress</h3>{progress&&<><p>{progress.filled} of {progress.total} detected fields filled. Skipped and manual fields still need your review.</p><progress value={progress.filled} max={Math.max(1,progress.total)} aria-label="Fields filled"/><details><summary>View fields / correct an answer</summary>{progress.fields.map(f=><div key={f.index} style={{padding:'8px 0'}}><strong>{f.question}</strong> · {f.state}{f.source&&<small> · {f.source}</small>}{f.error&&<p>{f.error}</p>}<button type="button" disabled={busy} className="secondary-button" onClick={()=>request(`revisit/${f.index}`,{method:'POST'})}>Review / retry</button></div>)}</details></>}<p>If you changed pages or filled something manually in the employer browser, rescan to recover its current values. Keep that browser open.</p><button type="button" className="secondary-button" disabled={busy} onClick={resumeApplication}>Rescan current form & recover</button><small> Recovery uses the current open browser. It cannot restore a closed browser or a restarted backend.</small></section>}
        {busy && <p>Working…</p>}
        {error && <p role="alert" style={{ color: '#ffb3b3' }}>{error}</p>}
        {field && !review && <>
          <p>Question {question.question_number} of {question.total_questions}</p>
          <h3>{field.label}</h3>
          {field.conflict && <p role="alert">Your sources disagree. Confirm the correct answer before Nova fills this field.</p>}
          {field.evidence?.map((item,i)=><div key={i} style={{padding:8,borderBottom:'1px solid #625c91'}}><small>{item.source}{item.updated_at ? ` · ${new Date(item.updated_at).toLocaleString()}` : ''}</small><p>{item.value}</p><button type="button" className="secondary-button" disabled={busy} onClick={()=>{stopAudio();answerRef.current=item.value;answerSourceRef.current='typed';setAnswer(item.value);setPhase('Source selected. Review and confirm to fill.');}}>Use this answer</button></div>)}
          {!['file','password'].includes(field.type) && <label style={{display:'block',margin:'12px 0'}}><input type="checkbox" checked={rememberAnswer} onChange={e=>{rememberRef.current=e.target.checked;setRememberAnswer(e.target.checked);}}/> Remember this confirmed answer for this exact question</label>}
          {suggestion && field.type !== 'file' && (
            <div style={{ padding: 12, border: '1px solid #625c91', borderRadius: 10, marginBottom: 14 }}>
              <p style={{ margin: '0 0 8px' }}>Suggested from your saved profile: <strong>{suggestion.value}</strong></p>
              <button type="button" className="secondary-button" disabled={busy}
                onClick={() => { stopAudio(); setAnswer(suggestion.value); answerRef.current = suggestion.value; setHeard(false); setPhase('Profile suggestion loaded. Review and click Confirm & next.'); }}>
                Use this suggestion
              </button>
            </div>
          )}
          {field.type === 'file' ? (
            <div className="platform-form">{initialResumeFile&&<div style={{padding:12,border:'1px solid #625c91',borderRadius:10}}><p>Resume used for these matches: <strong>{initialResumeFile.name}</strong></p><button type="button" className="primary-button" disabled={busy} onClick={()=>{const form=new FormData();form.append('file',initialResumeFile);request('upload',{method:'POST',body:form});}}>Upload matching resume to this field</button><small>This file is kept in this page session; it is not automatically saved to your resume library.</small></div>}<label>Saved resume version<select value={selectedResumeVersion} disabled={busy} onChange={e=>setSelectedResumeVersion(e.target.value)}><option value="">Choose a version</option>{resumeVersions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><button type="button" className="secondary-button" disabled={busy||!selectedResumeVersion} onClick={()=>request('resume-version',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({resume_id:Number(selectedResumeVersion)})})}>Use selected resume</button><label>Or upload a file<input type="file" accept=".pdf,.docx" disabled={busy} onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const form = new FormData();
              form.append('file', file);
              request('upload', { method: 'POST', body: form });
            }} /></label></div>
          ) : field.tag === 'select' ? (
            <select value={answer} disabled={busy} onChange={e => { answerSourceRef.current = 'typed'; setAnswer(e.target.value); answerRef.current = e.target.value; }} style={{ width: '100%', padding: 12 }}>
              <option value="">Choose an option</option>
              {(field.options || []).map((option, i) => <option key={i} value={option}>{option}</option>)}
            </select>
          ) : ['checkbox', 'radio'].includes(field.type) ? (
            <select value={answer} disabled={busy} onChange={e => { answerSourceRef.current = 'typed'; setAnswer(e.target.value); answerRef.current = e.target.value; }} style={{ width: '100%', padding: 12 }}>
              <option value="">Choose</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
          ) : (
            <input type="text" value={answer} disabled={busy} onChange={e => { answerSourceRef.current = 'typed'; setAnswer(e.target.value); answerRef.current = e.target.value; }} placeholder="Speak or type your answer" style={{ width: '100%', padding: 12, boxSizing: 'border-box' }} />
          )}
          <p style={{ fontSize: 13, opacity: 0.8 }}>Check names, email addresses and phone numbers carefully before confirming. You can edit the text below.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 18 }}>
            {field.type !== 'file' && <>
              <button type="button" className="primary-button" disabled={busy || !answer.trim()} onClick={() => sendAnswer(answer)}>Confirm & next</button>
              <button type="button" className="secondary-button" disabled={busy} onClick={() => { stopAudio(); setHeard(false); speak(`Please answer: ${field.label}`, () => beginListening('answer')); }}>Retry voice</button>
            </>}
            {!field.required && <button type="button" className="secondary-button" disabled={busy} onClick={() => request('skip', { method: 'POST' })}>Skip optional</button>}
          </div>
          {heard && <p>Recognized answer (please verify): {answer}</p>}
        </>}
        {question?.completed && !review && <>
          <p>All detected questions processed. The form has NOT been submitted.</p>
          <button type="button" className="primary-button" disabled={busy} onClick={() => request('review')}>Review answers</button>
        </>}
        {review && <>
          <h3>Review answers</h3>
          {review.answers.map((item, i) => <p key={i}><strong>{item.question}:</strong> {item.answer}<br/><small>Source: {item.source}</small></p>)}
          <p><strong>Not submitted.</strong> Check the employer browser and submit manually if everything is correct.</p>
        </>}
      </div>
    </div>
  );
}
