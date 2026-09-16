// Every user-facing word derives from this file.
//
// Two rules drive it:
//   1. Internal identifiers (possible_fire, person_down) must never reach the
//      screen. A frightened person should not have to decode a database label.
//   2. Uncertainty is stated in plain language, never as a bare percentage.
//      "0.37" is not something anyone can act on in two seconds.

export const SEVERITY_ORDER = ["low", "medium", "high", "critical"];

const TYPE_LABELS = {
  possible_fire: "Possible fire",
  medical_emergency: "Medical emergency",
  fall: "Person may have fallen",
  accident: "Accident",
  intrusion: "Someone may have broken in",
  none: "No emergency detected",
  unknown: "Situation unclear",
};

const SEVERITY_WORDS = {
  low: "LOW",
  medium: "MEDIUM",
  high: "HIGH",
  critical: "CRITICAL",
};

// Spoken aloud, so these are sentence-cased rather than shouted.
const SEVERITY_SPOKEN = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
  critical: "Critical",
};

export const GUIDANCE_DISCLAIMER =
  "Guidance only. This assistant cannot contact emergency services for you.";


export function normalizeSeverity(value) {
  const severity = typeof value === "string" ? value.toLowerCase() : "";

  return SEVERITY_ORDER.includes(severity) ? severity : "";
}


export function severityWord(severity) {
  return SEVERITY_WORDS[normalizeSeverity(severity)] || "";
}


export function severitySpoken(severity) {
  return SEVERITY_SPOKEN[normalizeSeverity(severity)] || "";
}


/**
 * The agent returns `unknown` both for "no usable input" and for a distress
 * signal it cannot classify ("Someone is trapped inside" -> unknown/critical).
 * Those need very different headlines, and the only signal distinguishing them
 * is the agent's own reason text, so it is matched here deliberately.
 */
export function isTrappedCase(result) {
  return (
    result?.emergency_type === "unknown" &&
    typeof result?.reason === "string" &&
    /trapped|stuck/i.test(result.reason)
  );
}


export function headlineFor(result) {
  if (!result) {
    return "";
  }

  if (isTrappedCase(result)) {
    return "Someone may be trapped";
  }

  const type = result.emergency_type;

  if (typeof type === "string" && TYPE_LABELS[type]) {
    return TYPE_LABELS[type];
  }

  if (typeof type === "string" && type.trim()) {
    const words = type.replace(/[_-]+/g, " ").trim();

    return words.charAt(0).toUpperCase() + words.slice(1);
  }

  return "Situation unclear";
}


/**
 * Plain-language confidence. A percentage is not actionable under stress, and
 * a high number next to a serious warning invites false precision.
 */
export function confidencePhrase(confidence, sources) {
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    return "";
  }

  if (confidence < 0.5) {
    return "Unconfirmed";
  }

  if (confidence < 0.8) {
    return "Likely";
  }

  if (sources?.voice && sources?.image) {
    return "Supported by voice and image";
  }

  return "Strongly supported";
}


export function confidencePercent(confidence) {
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    return "";
  }

  const bounded = Math.max(0, Math.min(1, confidence));

  return `${Math.round(bounded * 100)}%`;
}


export function cleanActions(actions) {
  return Array.isArray(actions)
    ? actions.filter((action) => typeof action === "string" && action.trim())
    : [];
}


/**
 * The agent appends its own disclaimer sentence as the final action. It is
 * shown once, quietly, at the bottom rather than as a numbered step.
 */
export function isDisclaimerAction(action) {
  return action.toLowerCase().includes("does not replace");
}


/**
 * The agent also emits two sentences that state uncertainty rather than tell
 * the user to do anything. They are already shown by the "Unconfirmed" banner,
 * and rendering them under "Do this now" would present a statement as an
 * instruction. Both only ever appear when that banner is shown, so removing
 * them here loses nothing.
 */
export function isUncertaintyNote(action) {
  return /not enough to identify|assessment is uncertain/i.test(action);
}


export function splitActions(actions) {
  const cleaned = cleanActions(actions).filter(
    (action) => !isDisclaimerAction(action) && !isUncertaintyNote(action)
  );

  return { primary: cleaned[0] || "", rest: cleaned.slice(1), all: cleaned };
}


export function isEmergency(result) {
  return !!result && result.emergency_type !== "none";
}
