import { useEffect, useRef, useState } from "react";
import { Mic, MicOff } from "lucide-react";

export default function VoiceInput({ onTranscript, disabled = false }) {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [message, setMessage] = useState("");
  const supported = typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.abort();
      }
    };
  }, []);

  function toggleListening() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage("Voice recognition is unavailable in this browser. Try Chrome or Edge, or type your search.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => { setListening(true); setMessage("Listening… say a job title or skills."); };
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (transcript) {
        setMessage(`Heard: ${transcript}`);
        onTranscript(transcript);
      }
    };
    recognition.onerror = (event) => {
      setMessage(`Microphone error: ${event.error}. You can still type your search.`);
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    try { recognition.start(); }
    catch { setListening(false); setMessage("Unable to start microphone. Check browser permissions."); }
  }

  return (
    <div style={{ marginTop: 12, marginBottom: 12 }}>
      <button type="button" className="secondary-button" onClick={toggleListening} disabled={disabled || !supported}
        aria-label={listening ? "Stop voice search" : "Start voice search"}>
        {listening ? <MicOff size={18} /> : <Mic size={18} />}
        {listening ? " Stop Listening" : " Search by Voice"}
      </button>
      <p role="status" aria-live="polite" className="panel-note" style={{ marginTop: 8 }}>
        {message || (supported ? "Say: Find Data Analyst internships in Houston" : "Voice input is unavailable in this browser; manual search still works.")}
      </p>
    </div>
  );
}
