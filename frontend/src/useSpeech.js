import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Browser SpeechSynthesis, kept deliberately small.
 *
 * The assistant speaks severity and the first action only. Reading six
 * instructions aloud is useless under stress: auditory working memory is
 * shorter than visual, and a long monologue delays the one thing that matters.
 *
 * Nothing is sent to a third party; this is the browser's own voice.
 */
export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const supported =
    typeof window !== "undefined" && "speechSynthesis" in window;

  const supportedRef = useRef(supported);

  supportedRef.current = supported;

  const cancel = useCallback(() => {
    if (supportedRef.current) {
      window.speechSynthesis.cancel();
    }

    setSpeaking(false);
  }, []);

  const speak = useCallback(
    (text) => {
      if (!supportedRef.current || !text) {
        return;
      }

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);

      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);

      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    },
    []
  );

  // Never let the assistant keep talking after the user has moved on.
  useEffect(() => cancel, [cancel]);

  return { speak, cancel, speaking, supported };
}
