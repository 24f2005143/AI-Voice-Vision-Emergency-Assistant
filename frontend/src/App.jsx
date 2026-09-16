import { useState } from "react";

import VoiceRecorder from "./components/VoiceRecorder";
import ImageUploader from "./components/ImageUploader";
import EmergencyResult from "./components/EmergencyResult";
import AnalyzingState from "./components/AnalyzingState";
import DevPanel from "./components/DevPanel";

import { analyzeEmergency } from "./services/api";
import { isEmergency } from "./emergencyLabels";


export default function App() {
  const [audio, setAudio] = useState(null);
  const [image, setImage] = useState(null);
  const [transcript, setTranscript] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  // What the user actually supplied, so the interface never claims to have
  // examined something that was never provided.
  const [sources, setSources] = useState({
    voice: false,
    image: false,
    text: false,
  });

  // The whole layout switches on this. An emergency does not get a card on a
  // dashboard; it takes over the screen and the inputs step aside.
  const emergencyMode = isEmergency(result);

  const pending = {
    voice: !!audio,
    image: !!image,
    text: !!transcript.trim(),
  };

  const hasInput = pending.voice || pending.image || pending.text;


  function resetAll() {
    setResult(null);
    setError("");
    setHint("");
  }


  async function handleAnalyze() {
    if (!hasInput) {
      // A prompt, not an error. The user has not done anything wrong.
      setHint(
        "Tell me what is happening — speak, add a photo, or type a description."
      );

      return;
    }

    setLoading(true);
    setError("");
    setHint("");
    setResult(null);
    setSources(pending);

    try {
      const response = await analyzeEmergency({ audio, image, transcript });

      setResult(response);

    } catch (err) {
      setError(
        err?.message ||
          "We could not analyze this right now. Check your connection and try again."
      );

    } finally {
      setLoading(false);
    }
  }


  return (
    <div className={emergencyMode ? "app app--emergency" : "app app--calm"}>

      <main className="shell">

        {!emergencyMode && (
          <header className="masthead">
            <p className="masthead__product">Emergency Assistant</p>

            <h1 className="masthead__question">What is happening?</h1>

            <p className="masthead__sub">
              Describe the situation. Add a photo if you can. You will get
              immediate steps to take.
            </p>
          </header>
        )}


        {!emergencyMode && !loading && (
          <>
            <div className="inputs">
              <VoiceRecorder onAudioReady={setAudio} disabled={loading} />

              <ImageUploader onImageReady={setImage} disabled={loading} />
            </div>

            <section className="panel panel--text">
              <label className="panel__title" htmlFor="description">
                Or describe what you see
              </label>

              <textarea
                id="description"
                value={transcript}
                onChange={(event) => setTranscript(event.target.value)}
                placeholder="There is smoke coming from my kitchen…"
                rows={3}
              />
            </section>

            {hint && (
              <p className="hint" role="status">
                {hint}
              </p>
            )}

            {error && (
              <div className="error" role="alert">
                <p className="error__text">{error}</p>

                <button type="button" className="text-button" onClick={handleAnalyze}>
                  Try again
                </button>
              </div>
            )}

            <div className="analyze-bar">
              <button
                type="button"
                className="button button--analyze"
                onClick={handleAnalyze}
              >
                Analyze situation
              </button>
            </div>

            <EmergencyResult
              result={result}
              sources={sources}
              onReset={resetAll}
            />
          </>
        )}


        {loading && <AnalyzingState sources={sources} />}


        {emergencyMode && !loading && (
          <EmergencyResult
            result={result}
            sources={sources}
            onReset={resetAll}
          />
        )}


        {import.meta.env.DEV && (
          <DevPanel
            onSelect={(mock) => {
              setError("");
              setHint("");
              setSources({ voice: true, image: true, text: false });
              setResult(mock);
            }}
            onError={() => {
              setResult(null);
              setError(
                "We could not analyze this right now. Check your connection and try again."
              );
            }}
            onReset={resetAll}
          />
        )}

      </main>

    </div>
  );
}
