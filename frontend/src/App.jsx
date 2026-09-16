import { useState } from "react";

import VoiceRecorder from "./components/VoiceRecorder";
import ImageUploader from "./components/ImageUploader";
import EmergencyResult from "./components/EmergencyResult";

import { analyzeEmergency } from "./services/api";


export default function App() {
  const [audio, setAudio] = useState(null);
  const [image, setImage] = useState(null);
  const [transcript, setTranscript] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleAnalyze() {
    if (!audio && !image && !transcript.trim()) {
      setError(
        "Please record audio, upload an image, or enter a description."
      );

      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await analyzeEmergency({
        audio,
        image,
        transcript,
      });

      setResult(response);

    } catch (err) {
      setError(
        err.message || "Something went wrong."
      );

    } finally {
      setLoading(false);
    }
  }


  return (
    <main className="container">

      <header>
        <h1>🚨 AI Emergency Assistant</h1>

        <p>
          Voice + Vision emergency detection
        </p>
      </header>


      <section className="input-grid">

        <VoiceRecorder
          onAudioReady={setAudio}
        />

        <ImageUploader
          onImageReady={setImage}
        />

      </section>


      <section className="card">

        <h2>📝 Emergency Description</h2>

        <textarea
          value={transcript}
          onChange={(event) =>
            setTranscript(event.target.value)
          }
          placeholder="Describe what is happening..."
          rows={5}
        />

      </section>


      <button
        className="analyze-button"
        onClick={handleAnalyze}
        disabled={loading}
      >
        {loading
          ? "Analyzing..."
          : "🚨 Analyze Emergency"}
      </button>


      {error && (
        <div className="error">
          {error}
        </div>
      )}


      <EmergencyResult
        result={result}
      />

    </main>
  );
}