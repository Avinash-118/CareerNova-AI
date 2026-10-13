import { useEffect, useRef, useState } from 'react';

const API = 'http://127.0.0.1:8000';
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

export default function ApplicationVoiceAssistant({ job, onClose }) {
  const [session, setSession] = useState(null);
  const [autofillSummary, setAutofillSummary] = useState('');
  const [profile, setProfile] = useState(null);
  const [profileStatus, setProfileStatus] = useState('Loading saved profile…');
  const [suggestion, setSuggestion] = useState(null);
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [review, setReview] = useState(null);
  const [phase, setPhase] = useState('Opening application…');
  const [heard, setHeard] = useState(false);
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
          if (/\b(confirm|correct|yes|continue|next|that's right|that is right)\b/.test(command)) {
            setPhase('Entering confirmed answer…');
            sendAnswer(answerRef.current);
          } else if (/\b(retry|repeat|change|no|incorrect|wrong)\b/.test(command)) {
            setHeard(false);
            speakRef.current?.('Okay. Please say your answer again.', () => beginListening('answer'));
          } else {
            setPhase('I did not understand the confirmation. Say confirm or retry, or use the buttons.');
          }
          return;
        }
        const current = questionRef.current?.question;
        // Keep dictated text intact; never silently guess spellings or rewrite names.
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
    questionRef.current = data;
    setQuestion(data);
    setAnswer('');
    answerRef.current = '';
    setSuggestion(profileSuggestion(data.question, profileRef.current));
    setHeard(false);
    if (data.completed) {
      setPhase('All questions processed. Ready for review.');
      speak('All detected questions have been processed. Please review your answers before submitting the application yourself.');
    } else if (data.question?.type === 'file') {
      setPhase('Resume upload requires selecting a file.');
      speak(`Question ${data.question_number}. ${data.question.label}. Please select your resume file using the upload control.`);
    } else {
      speak(`Question ${data.question_number} of ${data.total_questions}. ${data.question?.label || 'Application question'}. Please answer when I finish speaking.`, () => beginListening('answer'));
    }
  }

  useEffect(() => {
    activeRef.current = true;
    let cancelled = false;
    async function start() {
      try {
        try {
          const profileResponse = await fetch(`${API}/api/profile/local-candidate`);
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

        const response = await fetch(`${API}/api/agent/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_url: job.apply_url })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
        if (cancelled) {
          await fetch(`${API}/api/agent/${data.session_id}/close`, { method: 'POST' }).catch(() => {});
          return;
        }
        sessionRef.current = data.session_id;
        setSession(data.session_id);
        setPhase('Automatically filling known profile fields…');
        const qResponse = await fetch(`${API}/api/agent/${data.session_id}/autofill`, { method: 'POST' });
        const qData = await qResponse.json();
        if (!qResponse.ok) throw new Error(qData.detail || 'Could not autofill application');
        if (!cancelled) {
          setAutofillSummary(`Filled ${qData.autofilled_count} fields automatically. ${qData.remaining_count} fields need attention.`);
          presentQuestion(qData.next_question);
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
      if (id) fetch(`${API}/api/agent/${id}/close`, { method: 'POST' }).catch(() => {});
    };
  }, [job.apply_url]);

  async function request(path, options = {}) {
    if (!sessionRef.current || busy) return;
    stopAudio();
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`${API}/api/agent/${sessionRef.current}/${path}`, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      if (path === 'review') {
        setReview(data);
        setPhase('Review answers in the browser before submitting manually.');
        speak('Here is your review. The application has not been submitted.');
      } else {
        presentQuestion(data.next_question || data);
      }
    } catch (e) { setError(e.message); setPhase('Please correct the error and try again.'); }
    finally { setBusy(false); }
  }

  function sendAnswer(value = answerRef.current) {
    if (!value?.trim()) { setError('Please speak or type an answer first.'); return; }
    request('answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value.trim() })
    });
  }

  const field = question?.question;
  return (
    <div role="dialog" aria-modal="true" aria-label="CareerNova AI voice application assistant" style={{ position: 'fixed', inset: 0, background: '#000d', zIndex: 2000, display: 'grid', placeItems: 'center', padding: 16 }}>
      <div style={{ background: '#191726', color: 'white', border: '1px solid #6b5c83', borderRadius: 16, padding: 26, width: 'min(100%, 620px)', maxHeight: '90vh', overflowY: 'auto' }}>
        <button type="button" className="secondary-button" onClick={onClose} style={{ float: 'right' }}>Close</button>
        <h2>CareerNova AI Application Assistant</h2>
        <p>{job.title} — {job.company}</p>
        <p aria-live="polite">{phase}</p>
        {autofillSummary && <p style={{color: "#7ee8b2"}}>{autofillSummary}</p>}
        {busy && <p>Working…</p>}
        {error && <p role="alert" style={{ color: '#ffb3b3' }}>{error}</p>}
        {field && !review && <>
          <p>Question {question.question_number} of {question.total_questions}</p>
          <h3>{field.label}</h3>
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
            <input type="file" accept=".pdf,.docx" disabled={busy} onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const form = new FormData();
              form.append('file', file);
              request('upload', { method: 'POST', body: form });
            }} />
          ) : field.tag === 'select' ? (
            <select value={answer} disabled={busy} onChange={e => { setAnswer(e.target.value); answerRef.current = e.target.value; }} style={{ width: '100%', padding: 12 }}>
              <option value="">Choose an option</option>
              {(field.options || []).map((option, i) => <option key={i} value={option}>{option}</option>)}
            </select>
          ) : ['checkbox', 'radio'].includes(field.type) ? (
            <select value={answer} disabled={busy} onChange={e => { setAnswer(e.target.value); answerRef.current = e.target.value; }} style={{ width: '100%', padding: 12 }}>
              <option value="">Choose</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
          ) : (
            <input type="text" value={answer} disabled={busy} onChange={e => { setAnswer(e.target.value); answerRef.current = e.target.value; }} placeholder="Speak or type your answer" style={{ width: '100%', padding: 12, boxSizing: 'border-box' }} />
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
          {review.answers.map((item, i) => <p key={i}><strong>{item.question}:</strong> {item.answer}</p>)}
          <p><strong>Not submitted.</strong> Check the employer browser and submit manually if everything is correct.</p>
        </>}
      </div>
    </div>
  );
}
