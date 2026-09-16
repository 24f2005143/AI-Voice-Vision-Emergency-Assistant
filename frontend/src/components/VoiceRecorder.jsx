import { useEffect, useRef, useState } from "react";

// The backend voice module validates filename and MIME type, so the recording
// is handed over as a File rather than a bare Blob.
const MIME_CANDIDATES = [
  { mimeType: "audio/webm", extension: "webm" },
  { mimeType: "audio/ogg", extension: "ogg" },
  { mimeType: "audio/mp4", extension: "m4a" },
];

function pickMimeType() {
  if (typeof MediaRecorder === "undefined") {
    return null;
  }

  return (
    MIME_CANDIDATES.find((candidate) =>
      MediaRecorder.isTypeSupported?.(candidate.mimeType)
    ) || null
  );
}

function isSupported() {
  return (
    typeof navigator !== "undefined" &&
    typeof MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia
  );
}

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;

  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}


export default function VoiceRecorder({ onAudioReady, disabled }) {
  // READY -> LISTENING -> RECORDED
  const [status, setStatus] = useState("ready");
  const [elapsed, setElapsed] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const previewUrlRef = useRef("");

  const supported = isSupported();
  const listening = status === "listening";

  function releaseMicrophone() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  function revokePreview() {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }
  }

  // Elapsed time is shown so the user knows the microphone is genuinely live.
  useEffect(() => {
    if (!listening) {
      return undefined;
    }

    const timer = setInterval(() => setElapsed((value) => value + 1), 1000);

    return () => clearInterval(timer);
  }, [listening]);

  useEffect(() => {
    return () => {
      if (recorderRef.current?.state === "recording") {
        recorderRef.current.stop();
      }

      releaseMicrophone();
      revokePreview();
    };
  }, []);


  async function startRecording() {
    setError("");
    revokePreview();
    setPreviewUrl("");
    setElapsed(0);
    onAudioReady(null);

    const selected = pickMimeType();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(
        stream,
        selected ? { mimeType: selected.mimeType } : undefined
      );

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        releaseMicrophone();

        const type = selected?.mimeType || recorder.mimeType || "audio/webm";
        const extension = selected?.extension || "webm";
        const blob = new Blob(chunksRef.current, { type });

        if (!blob.size) {
          setStatus("ready");
          setError("Nothing was recorded. Try again, or type what you see.");

          return;
        }

        const url = URL.createObjectURL(blob);

        previewUrlRef.current = url;
        setPreviewUrl(url);
        setStatus("recorded");
        onAudioReady(new File([blob], `recording.${extension}`, { type }));
      };

      recorderRef.current = recorder;
      recorder.start();
      setStatus("listening");

    } catch {
      releaseMicrophone();
      setStatus("ready");
      setError("Microphone unavailable. You can type what you see instead.");
    }
  }


  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    } else {
      setStatus("ready");
    }
  }


  function discard() {
    revokePreview();
    setPreviewUrl("");
    setElapsed(0);
    setStatus("ready");
    setError("");
    onAudioReady(null);
  }


  return (
    <section className="panel panel--voice" aria-labelledby="voice-heading">

      <h2 id="voice-heading" className="panel__title">Speak</h2>

      {!supported && (
        <p className="panel__fallback">
          Recording is not available in this browser. Type what you see below —
          that works just as well.
        </p>
      )}

      {supported && (
        <>
          {!listening && (
            <button
              type="button"
              className="mic-button"
              onClick={startRecording}
              disabled={disabled}
            >
              <span className="mic-button__glyph" aria-hidden="true">●</span>

              <span className="mic-button__label">
                {status === "recorded" ? "Record again" : "Start speaking"}
              </span>
            </button>
          )}

          {listening && (
            <button
              type="button"
              className="mic-button mic-button--listening"
              onClick={stopRecording}
            >
              <span className="mic-button__glyph" aria-hidden="true">■</span>

              <span className="mic-button__label">Stop</span>
            </button>
          )}

          <p className="mic-status" role="status">
            {listening && (
              <>
                <span className="mic-status__dot" aria-hidden="true" />
                <span className="mic-status__text">Listening</span>
                <span className="mic-status__time">{formatElapsed(elapsed)}</span>
              </>
            )}

            {status === "ready" && (
              <span className="mic-status__text mic-status__text--idle">
                Ready
              </span>
            )}

            {status === "recorded" && (
              <span className="mic-status__text mic-status__text--done">
                Recorded · {formatElapsed(elapsed)}
              </span>
            )}
          </p>
        </>
      )}

      {previewUrl && status === "recorded" && (
        <>
          <audio className="audio-preview" src={previewUrl} controls />

          <button type="button" className="text-button" onClick={discard}>
            Remove recording
          </button>
        </>
      )}

      {error && <p className="panel__error">{error}</p>}

    </section>
  );
}
