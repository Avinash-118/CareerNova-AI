
import { useRef, useState } from "react";

export default function VoiceInput({ onTranscript }) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);

  const handleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError("Please use a browser that supports speech recognition.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setListening(true);
      setError("");
    };

    recognition.onresult = (event) => {
      const spokenText = event.results[0][0].transcript;
      onTranscript(spokenText);
    };

    recognition.onerror = (event) => {
      setError(`Voice recognition error: ${event.error}`);
    };

    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };

    recognition.start();
  };

  return (
    <div>
      <button
        type="button"
        onClick={handleVoice}
        aria-pressed={listening}
        style={{
          padding: "12px 20px",
          borderRadius: "10px",
          background: listening ? "#dc2626" : "#7048ff",
          color: "white",
          border: "none",
          cursor: "pointer",
          fontWeight: "bold",
        }}
      >
        {listening ? "■ Stop Listening" : "🎤 Voice Command"}
      </button>

      {listening && <p>Listening...</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
