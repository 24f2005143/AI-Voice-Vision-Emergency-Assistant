
# AI Voice + Vision Emergency Assistant
## Team Guide & Development Plan

### Hackathon Project

This repository contains the complete development guide for our AI Voice + Vision Emergency Assistant.

The project is a multimodal emergency-response assistant that:
- accepts voice and image input,
- converts speech into text,
- analyzes visual information for possible hazards,
- combines both inputs using an AI reasoning agent,
- determines emergency type and severity,
- generates a context-aware action plan,
- displays the result in a dashboard,
- and can return the response through voice.

---

# 1. Team Members & Responsibilities

| Member | Role | Main Responsibility |
|---|---|---|
| **Muskan Jadon** | Full Stack + Integration | Frontend, backend, API integration, deployment |
| **Kanchan** | Vision AI | Image/video analysis and hazard detection |
| **Ishank** | AI Agent | Reasoning, risk analysis, emergency classification, action planning |
| **Abhi Bhaiya** | Voice AI | Speechmatics speech-to-text and text-to-speech/voice response |

## One-line responsibility

- **Abhi:** Voice -> Text and AI response -> Voice
- **Kanchan:** Image -> Hazard/visual information
- **Ishank:** Voice + Vision -> Emergency decision + action plan
- **Muskan:** Connect everything -> Final application

---

# 2. Project Flow

```text
                         USER
                          |
                 +--------+--------+
                 |                 |
                Voice             Image
                 |                 |
              ABHI             KANCHAN
                 |                 |
          Speechmatics          Vision AI
                 |                 |
                 +--------+--------+
                          |
                       ISHANK
                     AI AGENT
                          |
                +---------+---------+
                |                   |
            Risk Analysis      Action Plan
                |                   |
                +---------+---------+
                          |
                       MUSKAN
                  Backend + Frontend
                          |
                +---------+---------+
                |                   |
             Dashboard         Voice Response
```

The target experience is:

**Speak -> See -> Understand -> Reason -> Assess -> Respond**

---

# 3. Repository Structure

```text
ai-emergency-assistant/
│
├── README.md
├── GUIDE.md
├── .gitignore
├── .env.example
├── requirements.txt
├── package.json
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   └── models/
│
├── voice/
│   ├── speech_to_text.py
│   ├── text_to_speech.py
│   └── README.md
│
├── vision/
│   ├── image_analysis.py
│   ├── hazard_detection.py
│   └── README.md
│
├── agent/
│   ├── emergency_agent.py
│   ├── risk_analysis.py
│   ├── action_planner.py
│   └── README.md
│
├── tests/
│   ├── test_voice.py
│   ├── test_vision.py
│   └── test_agent.py
│
└── docs/
    ├── architecture.md
    ├── api.md
    └── demo-scenarios.md
```

---

# 4. Work Allocation

## 4.1 Muskan Jadon — Full Stack + Integration

### Folders

```text
frontend/
backend/
tests/
docs/
```

### Responsibilities

1. Build the main dashboard.
2. Add voice recording UI.
3. Add image upload UI.
4. Display transcription.
5. Display vision results.
6. Display emergency type.
7. Display severity.
8. Display confidence.
9. Display reason.
10. Display recommended actions.
11. Connect voice, vision and agent APIs.
12. Handle errors.
13. Manage environment variables.
14. Deploy the application.
15. Coordinate final integration.

### Frontend target

```text
+------------------------------------------+
|       AI EMERGENCY ASSISTANT             |
+------------------------------------------+
|                                          |
|  Voice                                   |
|  [ Start Recording ]                     |
|                                          |
|  Image                                   |
|  [ Upload Image ]                        |
|                                          |
+------------------------------------------+
|  EMERGENCY ANALYSIS                      |
|                                          |
|  Type: FIRE                              |
|  Severity: HIGH                          |
|  Confidence: 91%                         |
|                                          |
|  Reason: Smoke detected near stove       |
|                                          |
|  RECOMMENDED ACTIONS                     |
|  - Move away from danger                 |
|  - Avoid approaching fire                |
|  - Contact emergency services if needed  |
+------------------------------------------+
```

---

## 4.2 Kanchan — Vision AI

### Folder

```text
vision/
```

### Responsibilities

1. Accept an image (or video frame if supported).
2. Run the selected vision model/API.
3. Detect relevant emergency information.
4. Identify possible hazards.
5. Return confidence information.
6. Return structured JSON for the AI agent.

### Initial target

Input:

```text
Kitchen image
```

Output:

```json
{
  "hazard": "smoke",
  "objects": ["stove", "person"],
  "confidence": 0.89
}
```

### Suggested files

```text
vision/
├── image_analysis.py
├── hazard_detection.py
└── README.md
```

### Development rule

Do not begin by training a large model from scratch.

First create a working prototype with an appropriate existing model/API. Improve it only after the end-to-end MVP works.

---

## 4.3 Ishank — AI Agent / Reasoning

### Folder

```text
agent/
```

### Responsibilities

1. Receive voice transcript.
2. Receive vision output.
3. Combine both sources.
4. Determine emergency type.
5. Determine severity.
6. Estimate confidence.
7. Explain the reason.
8. Generate recommended actions.
9. Return structured JSON.

### Example input

Voice:

```text
There is smoke in my kitchen.
```

Vision:

```json
{
  "hazard": "smoke",
  "objects": ["stove", "person"],
  "confidence": 0.89
}
```

### Example output

```json
{
  "emergency_type": "possible_fire",
  "severity": "high",
  "confidence": 0.91,
  "reason": "Smoke detected near a stove and a person is present.",
  "actions": [
    "Move away from danger.",
    "Avoid approaching the fire.",
    "Contact emergency services if necessary."
  ]
}
```

### Suggested files

```text
agent/
├── emergency_agent.py
├── risk_analysis.py
├── action_planner.py
└── README.md
```

### Important principle

The agent should not blindly trust one input. It should consider both the user's description and visual evidence.

---

## 4.4 Abhi Bhaiya — Voice AI

### Folder

```text
voice/
```

### Responsibilities

1. Capture microphone input.
2. Send audio to Speechmatics.
3. Convert speech to text.
4. Return the transcript.
5. Receive the AI's final response.
6. Convert the response to speech where supported.
7. Provide the voice interaction interface/API.

### Target flow

```text
Microphone
    |
    v
Speechmatics
    |
    v
Transcript
    |
    v
AI Agent
    |
    v
AI Response
    |
    v
Text-to-Speech
    |
    v
User hears response
```

### Suggested files

```text
voice/
├── speech_to_text.py
├── text_to_speech.py
└── README.md
```

---

# 5. API Contract

All team members must follow the same data format.

## 5.1 Voice output

Abhi -> Backend/Agent

```json
{
  "transcript": "There is smoke in my kitchen."
}
```

## 5.2 Vision output

Kanchan -> Backend/Agent

```json
{
  "hazard": "smoke",
  "objects": ["stove", "person"],
  "confidence": 0.89
}
```

## 5.3 Agent output

Ishank -> Backend/Frontend

```json
{
  "emergency_type": "possible_fire",
  "severity": "high",
  "confidence": 0.91,
  "reason": "Smoke detected near stove.",
  "actions": [
    "Move away from danger.",
    "Avoid approaching fire.",
    "Contact emergency services if necessary."
  ]
}
```

Do not change these field names without informing the whole team.

---

# 6. GitHub Workflow

Use one repository and separate branches.

```text
main
|
+-- feature/voice-abhi
+-- feature/vision-kanchan
+-- feature/agent-ishank
+-- feature/frontend-muskan
```

## Basic workflow

```bash
git clone <REPOSITORY_URL>
cd ai-emergency-assistant

git checkout -b feature/your-name
```

After completing a small piece of work:

```bash
git add .
git commit -m "Add voice transcription"
git push -u origin feature/your-name
```

Then create a Pull Request into `main`.

## Rules

- Do not directly modify another person's module.
- Pull from `main` regularly.
- Make small commits.
- Use clear commit messages.
- Do not commit API keys.
- Put secrets in `.env`.
- Keep `.env` in `.gitignore`.
- Merge only tested code.

---

# 7. Environment Variables

Create:

```text
.env
```

Example:

```text
SPEECHMATICS_API_KEY=your_key_here
AI_API_KEY=your_key_here
VISION_API_KEY=your_key_here
```

Also create:

```text
.env.example
```

with placeholders:

```text
SPEECHMATICS_API_KEY=
AI_API_KEY=
VISION_API_KEY=
```

Never push the real `.env` file to GitHub.

---

# 8. Development Plan

## Day 1 — Setup + Architecture

Everyone:

- Join GitHub repository.
- Clone repository.
- Create personal branch.
- Install dependencies.
- Read this GUIDE.md.
- Agree on API contract.
- Test local environment.

At the end of Day 1, everyone should be able to run the project.

---

## Day 2 — Individual Modules

### Abhi

Make:

```text
Microphone -> Speechmatics -> Transcript
```

### Kanchan

Make:

```text
Image -> Vision -> Hazard JSON
```

### Ishank

Use dummy data first:

```text
Transcript + Vision JSON
        |
        v
     AI Agent
        |
        v
Emergency JSON
```

### Muskan

Build dashboard using dummy data.

---

## Day 3 — Integration

Connect:

```text
Voice
  +
Vision
  |
  v
AI Agent
  |
  v
Backend
  |
  v
Frontend
```

Goal: one complete end-to-end demo.

---

## Day 4 — Improve the MVP

Add:

- Severity levels.
- Confidence score.
- Reasoning/explanation.
- Action plan.
- Voice response.
- Better UI.
- Loading/error states.

---

## Day 5 — Testing + Deployment

Test:

1. Possible fire.
2. Smoke.
3. Accident.
4. Person fallen.
5. Voice-only emergency.
6. Image-only emergency.
7. Normal/non-emergency input.
8. Incorrect or unclear input.

Then deploy the application.

---

## Day 6 — Submission

Prepare:

- GitHub repository.
- Live application.
- README.
- Architecture diagram.
- Demo scenarios.
- Presentation slides.
- Demo video.
- Final project description.

---

# 9. MVP Definition

Do not add too many features before the core system works.

The minimum working product is:

```text
VOICE + IMAGE
      |
      v
SPEECH + VISION
      |
      v
AI AGENT
      |
      v
EMERGENCY TYPE
      |
      v
SEVERITY
      |
      v
REASON
      |
      v
ACTION PLAN
      |
      v
DASHBOARD + VOICE RESPONSE
```

If this works reliably, the project has a complete demonstrable flow.

---

# 10. Demo Scenario

Use one strong scenario for the main demo.

### Scenario: Kitchen Smoke

User uploads an image showing a kitchen situation and says:

```text
There is smoke coming from my kitchen.
```

System:

```text
Voice
  -> Speechmatics
  -> "There is smoke coming from my kitchen."

Image
  -> Vision
  -> Smoke + Stove + Person

Both
  -> AI Agent
  -> Possible Fire
  -> HIGH Severity
  -> Explanation
  -> Action Plan

Result
  -> Dashboard
  -> Voice Response
```

The judge should be able to understand the entire project from this single flow.

---

# 11. Safety

This application is a prototype for emergency assistance.

It must not claim to replace emergency services, professional responders, or human judgment.

For high-risk situations, responses should encourage the user to prioritize immediate personal safety and contact appropriate local emergency services when necessary.

The system should clearly communicate uncertainty when confidence is low.

---

# 12. Communication Between Team Members

Use one shared communication channel.

Every member should report:

```text
DONE:
What I completed.

WORKING:
What I am currently building.

BLOCKED:
What is preventing progress.

NEEDED:
What I need from another member.
```

Example:

```text
DONE:
Speech-to-text working.

WORKING:
Connecting transcript API.

BLOCKED:
Need backend endpoint.

NEEDED:
Muskan to provide /api/voice endpoint.
```

---

# 13. Final Responsibility Checklist

## Muskan

- [ ] Frontend
- [ ] Backend
- [ ] API integration
- [ ] Dashboard
- [ ] Testing
- [ ] Deployment
- [ ] Final integration

## Kanchan

- [ ] Image input
- [ ] Vision model/API
- [ ] Hazard detection
- [ ] Confidence
- [ ] Vision JSON
- [ ] Vision README

## Ishank

- [ ] Agent
- [ ] Emergency classification
- [ ] Risk analysis
- [ ] Severity
- [ ] Explanation
- [ ] Action planner
- [ ] Agent JSON
- [ ] Agent README

## Abhi Bhaiya

- [ ] Microphone input
- [ ] Speechmatics
- [ ] Speech-to-text
- [ ] Transcript
- [ ] Text-to-speech/voice response
- [ ] Voice README

---

# 14. Golden Rule

**We are building ONE application, not four separate projects.**

```text
                 ONE APP
                   |
       +-----------+-----------+
       |           |           |
     VOICE       VISION      AGENT
       |           |           |
       +-----------+-----------+
                   |
              FULL STACK
                   |
              FINAL DEMO
```

The first goal is not perfection.

The first goal is:

**Make one complete emergency scenario work from beginning to end.**

Once the end-to-end MVP works, improve accuracy, UI, reliability, and presentation.
