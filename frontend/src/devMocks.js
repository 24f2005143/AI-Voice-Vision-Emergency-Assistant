// DEVELOPMENT ONLY.
//
// Hard-coded sample responses for inspecting every important visual state
// while backend/main.py is not implemented. This is NOT a mock backend and no
// network call is involved — App.jsx renders the controls only behind
// `import.meta.env.DEV`, so none of this reaches a production build.
//
// Shapes are identical to the real API contract:
// emergency_type, severity, confidence, reason, actions.

export const DEV_MOCK_RESULTS = [
  {
    label: "No emergency",
    result: {
      emergency_type: "none",
      severity: "low",
      confidence: 0.7,
      reason: "No emergency indicators were detected.",
      actions: [],
    },
  },
  {
    label: "Medium · fall",
    result: {
      emergency_type: "fall",
      severity: "medium",
      confidence: 0.92,
      reason:
        "Your description mentions someone falling, and the photo shows a person on the floor.",
      actions: [
        "Do not move the person until you know whether they are injured.",
        "Check whether the person is conscious and responsive.",
        "Keep the person warm and still while help is arranged.",
        "Contact your local emergency services if the situation gets worse.",
        "This assistant only offers guidance and does not replace professional emergency services.",
      ],
    },
  },
  {
    label: "High · possible fire",
    result: {
      emergency_type: "possible_fire",
      severity: "high",
      confidence: 0.95,
      reason:
        "Your description mentions smoke, and the photo shows smoke near a stove.",
      actions: [
        "Leave the area immediately and move away from the smoke or fire.",
        "Do not try to approach or put out the fire yourself.",
        "Turn off the gas or stove supply on your way out only if it is safe.",
        "Contact your local emergency services now.",
        "This assistant only offers guidance and does not replace professional emergency services.",
      ],
    },
  },
  {
    label: "Critical · medical",
    result: {
      emergency_type: "medical_emergency",
      severity: "critical",
      confidence: 0.51,
      reason:
        "Your description mentions someone unconscious and not breathing, but the photo shows no hazard.",
      actions: [
        "Check that the area around the person is safe before you approach them.",
        "Stay with the affected person and keep them calm and still.",
        "Check whether the person is breathing and responsive.",
        "Contact your local emergency services now.",
        "This assistant only offers guidance and does not replace professional emergency services.",
      ],
    },
  },
  {
    label: "Unknown · trapped",
    result: {
      emergency_type: "unknown",
      severity: "critical",
      confidence: 0.4,
      reason:
        "The description reports someone trapped or stuck, but neither source shows what kind of emergency it is.",
      actions: [
        "The available information is not enough to identify the situation.",
        "Describe what you can see or hear in more detail.",
        "Contact your local emergency services now.",
        "This assessment is uncertain, so confirm what is happening before relying on it.",
        "This assistant only offers guidance and does not replace professional emergency services.",
      ],
    },
  },
  {
    label: "Low confidence · conflict",
    result: {
      emergency_type: "possible_fire",
      severity: "high",
      confidence: 0.15,
      reason:
        "Your description mentions fire while the photo appears to show a fallen person; the more dangerous possibility was kept for safety, so this assessment is uncertain.",
      actions: [
        "Move yourself to a safe place first and stay away from the danger.",
        "Leave the area immediately and move away from the smoke or fire.",
        "Contact your local emergency services now.",
        "This assessment is uncertain, so confirm what is happening before relying on it.",
        "This assistant only offers guidance and does not replace professional emergency services.",
      ],
    },
  },
];
