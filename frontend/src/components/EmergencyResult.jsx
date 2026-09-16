import { useEffect, useRef, useState } from "react";

import { useSpeech } from "../useSpeech";
import {
  GUIDANCE_DISCLAIMER,
  confidencePercent,
  confidencePhrase,
  headlineFor,
  isTrappedCase,
  normalizeSeverity,
  severitySpoken,
  severityWord,
  splitActions,
} from "../emergencyLabels";


function WhyThisResult({ result, sources, phrase }) {
  const percent = confidencePercent(result.confidence);

  const used = [
    sources?.voice && "your recording",
    sources?.text && "your written description",
    sources?.image && "the photo",
  ].filter(Boolean);

  return (
    <details className="why">
      <summary className="why__summary">Why this result?</summary>

      <div className="why__body">
        {result.reason && <p>{result.reason}</p>}

        {used.length > 0 && (
          <p>
            Based on {used.join(" and ")}.
          </p>
        )}

        {phrase && (
          <p>
            Certainty: <strong>{phrase}</strong>
            {percent && <span className="why__percent"> ({percent})</span>}
          </p>
        )}

        <p className="why__note">
          This assessment is produced by automated reasoning over what you
          described and what the photo appears to show. It can be wrong.
        </p>
      </div>
    </details>
  );
}


function CriticalSteps({ actions, onSpeak }) {
  const [step, setStep] = useState(0);

  const current = actions[step];
  const isLast = step >= actions.length - 1;

  function goNext() {
    const next = Math.min(step + 1, actions.length - 1);

    setStep(next);
    onSpeak?.(actions[next]);
  }

  return (
    <div className="critical-steps">

      <p className="do-now-label">
        Do this now
        {actions.length > 1 && (
          <span className="do-now-count">
            Step {step + 1} of {actions.length}
          </span>
        )}
      </p>

      <p className="do-now-action do-now-action--critical" aria-live="assertive">
        {current}
      </p>

      <div className="critical-steps__controls">
        {step > 0 && (
          <button
            type="button"
            className="button button--quiet"
            onClick={() => setStep(step - 1)}
          >
            Back
          </button>
        )}

        {!isLast && (
          <button type="button" className="button button--next" onClick={goNext}>
            Next action
          </button>
        )}
      </div>

    </div>
  );
}


export default function EmergencyResult({ result, sources, onReset }) {
  const { speak, cancel, speaking, supported } = useSpeech();
  const headingRef = useRef(null);

  const severity = normalizeSeverity(result?.severity);
  const critical = severity === "critical";
  const { primary, rest, all } = splitActions(result?.actions);
  const headline = headlineFor(result);
  const phrase = confidencePhrase(result?.confidence, sources);
  const unconfirmed = phrase === "Unconfirmed";
  const isNone = result?.emergency_type === "none";

  // Speak severity plus the first action only, once per result. A six-item
  // monologue would delay the one thing that matters.
  useEffect(() => {
    if (!result || isNone || !primary) {
      return;
    }

    const spokenSeverity = severitySpoken(severity);

    speak(
      [spokenSeverity, headline, primary].filter(Boolean).join(". ")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  // Move focus to the result so screen readers and keyboard users land on the
  // thing that just changed, instead of staying on the Analyze button.
  useEffect(() => {
    if (result) {
      headingRef.current?.focus();
    }
  }, [result]);

  if (!result) {
    return null;
  }

  if (isNone) {
    return (
      <section className="calm-result" aria-live="polite">

        <p className="calm-result__label">No emergency detected</p>

        {result.reason && (
          <p className="calm-result__reason">{result.reason}</p>
        )}

        <p className="calm-result__hint">
          If something changes, describe it again or add a photo.
        </p>

        <button type="button" className="text-button" onClick={onReset}>
          Start over
        </button>

        <p className="disclaimer">{GUIDANCE_DISCLAIMER}</p>

      </section>
    );
  }

  return (
    <section
      className={`result result--${severity || "unknown"}`}
      role="alert"
      aria-label={`${severityWord(severity) || "Assessment"}: ${headline}`}
    >

      <header className="result__band">
        <span className="result__severity">{severityWord(severity) || "ASSESSED"}</span>

        <h2 className="result__headline" ref={headingRef} tabIndex={-1}>
          {headline}
        </h2>
      </header>

      {unconfirmed && (
        <p className="unconfirmed">
          <strong>Unconfirmed.</strong>{" "}
          {isTrappedCase(result)
            ? "We can't determine the exact emergency yet."
            : "Check for yourself before relying on this."}
        </p>
      )}

      <div className="result__main">
        {critical && all.length > 0 ? (
          <CriticalSteps actions={all} onSpeak={speak} />
        ) : (
          <>
            <p className="do-now-label">Do this now</p>

            <p className="do-now-action">{primary || "Move somewhere safe."}</p>
          </>
        )}
      </div>

      {!critical && (result.reason || rest.length > 0) && (
        <div className="result__context">
          {result.reason && <p className="result__reason">{result.reason}</p>}

          {rest.length > 0 && (
            <div className="then">
              <p className="then__label">Then</p>

              <ol className="then__list">
                {rest.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      <footer className="result__footer">
        {supported && (
          <p className="speaking" aria-hidden="true">
            {speaking ? (
              <>
                <span className="speaking__wave" />
                <span>Speaking</span>
              </>
            ) : (
              <span className="speaking__idle">Voice ready</span>
            )}
          </p>
        )}

        <div className="result__controls">
          {supported && speaking && (
            <button type="button" className="text-button" onClick={cancel}>
              Stop voice
            </button>
          )}

          {supported && !speaking && primary && (
            <button
              type="button"
              className="text-button"
              onClick={() =>
                speak([severitySpoken(severity), headline, primary]
                  .filter(Boolean)
                  .join(". "))
              }
            >
              Repeat aloud
            </button>
          )}

          <button type="button" className="text-button" onClick={onReset}>
            New report
          </button>
        </div>

        <WhyThisResult result={result} sources={sources} phrase={phrase} />

        <p className="disclaimer">{GUIDANCE_DISCLAIMER}</p>
      </footer>

    </section>
  );
}
