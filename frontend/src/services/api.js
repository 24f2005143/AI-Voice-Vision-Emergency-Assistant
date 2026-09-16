const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";


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

  const response = await fetch(
    `${API_BASE_URL}/api/emergency/analyze`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || "Emergency analysis failed."
    );
  }

  return data;
}