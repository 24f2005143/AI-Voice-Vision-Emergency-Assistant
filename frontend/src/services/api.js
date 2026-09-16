const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Speech transcription can legitimately poll for around 90 seconds, and image
// analysis adds up to 30 more, so the ceiling is generous on purpose. It only
// exists so a stalled request eventually surfaces the retry UX instead of
// leaving a frightened user watching a spinner forever.
export const REQUEST_TIMEOUT_MS = 120000;

const TIMEOUT_MESSAGE =
  "This is taking longer than expected. Check your connection and try again.";

const NETWORK_MESSAGE =
  "We could not reach the assistant. Check your connection and try again.";

const FALLBACK_MESSAGE = "Emergency analysis failed.";


export async function analyzeEmergency({
  audio,
  image,
  transcript = "",
}) {
  const formData = new FormData();

  if (audio) {
    formData.append("audio", audio);
  }

  if (image) {
    formData.append("image", image);
  }

  if (transcript.trim()) {
    formData.append("transcript", transcript.trim());
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS
  );

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/emergency/analyze`,
      {
        method: "POST",
        body: formData,
        signal: controller.signal,
      }
    );

  } catch (err) {
    // Neither branch surfaces the underlying exception text to the user.
    throw new Error(
      err?.name === "AbortError" ? TIMEOUT_MESSAGE : NETWORK_MESSAGE
    );

  } finally {
    // Always cleared, on success and on failure, so no timer outlives the call.
    clearTimeout(timeoutId);
  }

  let data;

  try {
    data = await response.json();

  } catch {
    // A non-JSON body (proxy page, gateway error) must not leak a parser error.
    throw new Error(response.ok ? FALLBACK_MESSAGE : NETWORK_MESSAGE);
  }

  if (!response.ok) {
    throw new Error(
      data.detail || FALLBACK_MESSAGE
    );
  }

  return data;
}
