# AI Voice + Vision Emergency Assistant

> A multimodal emergency-assistance prototype combining voice input,
> visual hazard analysis, and an AI emergency reasoning agent to produce
> an emergency assessment, explanation, recommended actions, and a
> voice-ready response.

## Overview

The **AI Voice + Vision Emergency Assistant** accepts a user's voice,
image, or text description and combines the available information to
assess a possible emergency.

### Core flow

``` text
                    USER
                      |
             +--------+--------+
             |                 |
          Voice              Image
             |                 |
             v                 v
       Speech-to-Text      Vision Analysis
             |                 |
             +--------+--------+
                      |
                      v
                Emergency Agent
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
    Emergency Type Severity   Confidence
                      |
                      v
                    Reason
                      |
                      v
                 Action Plan
                      |
                      v
              Dashboard + Voice
                  Response
```

**Target experience:** Speak → See → Understand → Reason → Assess →
Respond

------------------------------------------------------------------------

## Features

-   Voice input and speech-to-text
-   Image upload and visual hazard analysis
-   Multimodal emergency reasoning
-   Emergency type classification
-   Severity assessment
-   Confidence score
-   Explanation/reason
-   Recommended actions
-   Voice-ready response
-   React frontend
-   FastAPI backend
-   Integration of voice, vision, and agent modules
-   Environment-variable based API-key configuration

------------------------------------------------------------------------

## Architecture

### Voice AI

``` text
Microphone
    ↓
Speechmatics
    ↓
Transcript
```

### Vision AI

``` text
Image
   ↓
Vision API
   ↓
Hazard + Objects + Confidence
```

### Emergency Agent

``` text
Transcript + Vision
        ↓
Emergency Agent
        ↓
Emergency Type
        ↓
Severity
        ↓
Reason
        ↓
Action Plan
```

### Full-stack integration

``` text
React Frontend
      ↓
FastAPI Backend
      ↓
+-----+-----+------+
|           |      |
Voice     Vision  Agent
|           |      |
+-----+-----+------+
      ↓
Emergency Result
      ↓
React Dashboard
```

------------------------------------------------------------------------

# Repository Structure

``` text
AI-Voice-Vision-Emergency-Assistant/
│
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
│
├── agent/
│   └── emergency_agent.py
│
├── backend/
│   ├── main.py
│   ├── models/
│   │   └── schemas.py
│   ├── routes/
│   │   └── emergency.py
│   └── services/
│       └── orchestrator.py
│
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── styles.css
│       ├── components/
│       │   ├── VoiceRecorder.jsx
│       │   ├── ImageUploader.jsx
│       │   └── EmergencyResult.jsx
│       └── services/
│           └── api.js
│
├── vision/
│   ├── hazard_detection.py
│   ├── image_analysis.py
│   └── README.md
│
├── voice/
│   ├── speech_to_text.py
│   ├── text_to_speech.py
│   └── README.md
│
├── tests/
│   ├── test_vision.py
│   ├── test_voice.py
│   └── test_backend_integration.py
│
└── docs/
    └── architecture.md
```

------------------------------------------------------------------------

# Team Responsibilities

  -----------------------------------------------------------------------
  Member                  Role                    Responsibility
  ----------------------- ----------------------- -----------------------
  **Muskan Jadon**        Full Stack +            Frontend, backend, API
                          Integration             integration, dashboard,
                                                  testing, final
                                                  integration

  **Kanchan**             Vision AI               Image analysis and
                                                  hazard detection

  **Ishank**              AI Agent                Emergency reasoning,
                                                  classification,
                                                  severity, explanation,
                                                  action planning

  **Abhi Bhaiya**         Voice AI                Speech-to-text and
                                                  voice-response
                                                  functionality
  -----------------------------------------------------------------------

The project is one integrated application rather than four independent
projects.

------------------------------------------------------------------------

# API Data Contracts

## Voice output

``` json
{
  "transcript": "There is smoke in my kitchen."
}
```

## Vision output

``` json
{
  "hazard": "smoke",
  "objects": ["stove", "person"],
  "confidence": 0.89
}
```

## Emergency agent output

``` json
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

> Keep these field names consistent when integrating modules.

------------------------------------------------------------------------

# Requirements

Install the following before running the project:

-   Python
-   Node.js and npm
-   Git
-   API credentials for the external voice and vision services

------------------------------------------------------------------------

# Installation

## 1. Clone the repository

``` bash
git clone <REPOSITORY_URL>
cd AI-Voice-Vision-Emergency-Assistant
```

For development, create a feature branch:

``` bash
git checkout -b feature/your-name
```

------------------------------------------------------------------------

# Backend Setup

## 2. Create a virtual environment

Windows PowerShell:

``` powershell
python -m venv .venv
```

Activate it:

``` powershell
.venv\Scripts\Activate.ps1
```

## 3. Install Python dependencies

``` powershell
python -m pip install -r requirements.txt
```

------------------------------------------------------------------------

# API Key Configuration

The application uses external services for speech transcription and
vision analysis.

**Every developer who runs the application locally must configure their
own API keys.**

### Required variables

  Variable                 Purpose
  ------------------------ -----------------------------------
  `SPEECHMATICS_API_KEY`   Speech-to-text using Speechmatics
  `VISION_API_KEY`         Image/vision analysis

## 4. Create `.env`

Create `.env` in the project root:

``` env
SPEECHMATICS_API_KEY=your_speechmatics_api_key
VISION_API_KEY=your_vision_api_key
```

Replace the placeholders with your own credentials.

### `.env.example`

The repository should contain `.env.example` with placeholders only:

``` env
SPEECHMATICS_API_KEY=
VISION_API_KEY=
```

### Security

Never commit `.env` or real API keys to GitHub.

Your `.gitignore` should include:

``` gitignore
.env
node_modules/
__pycache__/
.venv/
*.pyc
```

Do not hard-code secrets in source code.

If a secret is accidentally pushed to GitHub, revoke/rotate the affected
key immediately.

------------------------------------------------------------------------

# Running the Backend

From the project root:

``` powershell
uvicorn backend.main:app --reload
```

Backend:

``` text
http://127.0.0.1:8000
```

### Health check

Open:

``` text
http://127.0.0.1:8000/health
```

Expected:

``` json
{
  "status": "ok"
}
```

### Interactive API documentation

Open:

``` text
http://127.0.0.1:8000/docs
```

The Swagger UI can be used to test the API.

------------------------------------------------------------------------

# Emergency API

The current backend exposes:

``` text
POST /api/analyze
```

The endpoint accepts multipart form data including fields such as:

``` text
transcript
use_mock
audio
image
```

The Swagger/OpenAPI documentation at `/docs` is the source of truth for
the currently running API.

A successful response contains an emergency assessment with fields such
as:

``` json
{
  "emergency_type": "possible_fire",
  "severity": "high",
  "confidence": 0.51,
  "reason": "The description mentions fire and smoke...",
  "actions": [
    "Move yourself to a safe place first and stay away from the danger.",
    "Leave the area immediately and move away from the smoke or fire.",
    "Do not try to approach or put out the fire yourself."
  ],
  "transcript": "There is a fire in the kitchen and there is a lot of smoke.",
  "vision": {
    "hazard": "none",
    "objects": [],
    "confidence": 0
  }
}
```

Exact results depend on the supplied input and configured services.

------------------------------------------------------------------------

# Frontend Setup

Open a second terminal while the backend continues running:

``` powershell
cd frontend
```

Install dependencies:

``` powershell
npm install
```

Start the development server:

``` powershell
npm run dev
```

Open the local URL displayed by Vite, typically:

``` text
http://localhost:5173
```

------------------------------------------------------------------------

# Frontend Flow

### Voice

``` text
Start Recording
      ↓
Browser Microphone
      ↓
Audio
      ↓
Backend
      ↓
Speech-to-Text
```

### Image

``` text
Upload Image
      ↓
Image Preview
      ↓
Backend
      ↓
Vision Analysis
```

### Complete analysis

``` text
Voice + Image + Description
             ↓
        FastAPI Backend
             ↓
       Emergency Agent
             ↓
      Emergency Result
             ↓
       Result Dashboard
```

------------------------------------------------------------------------

# Demo Scenario

## Kitchen Smoke

Example user input:

``` text
There is smoke coming from my kitchen.
```

The system processes:

``` text
Voice
  → Speech-to-Text
  → Transcript

Image
  → Vision Analysis
  → Hazard + Objects + Confidence

Transcript + Vision
  → Emergency Agent
  → Emergency Assessment
```

The dashboard presents the resulting:

-   Emergency type
-   Severity
-   Confidence
-   Reason
-   Recommended actions
-   Voice-ready response

------------------------------------------------------------------------

# Testing

Recommended scenarios:

1.  Possible fire
2.  Smoke
3.  Accident
4.  Person fallen
5.  Voice-only emergency
6.  Image-only emergency
7.  Normal/non-emergency input
8.  Unclear or incorrect input

First verify:

``` text
GET /health
```

Then test:

``` text
POST /api/analyze
```

using the FastAPI Swagger UI.

------------------------------------------------------------------------

# GitHub Workflow

The project uses a shared `main` branch and feature branches.

``` text
main
 |
 +-- feature/voice-abhi
 +-- feature/vision-kanchan
 +-- feature/agent-ishank
 +-- feature/muskan
```

## Create a branch

``` bash
git checkout -b feature/your-name
```

## Check changes

``` bash
git status
```

## Stage

``` bash
git add .
```

## Commit

``` bash
git commit -m "Describe the change"
```

## Push

``` bash
git push -u origin feature/your-name
```

## Pull Request

Create a Pull Request from:

``` text
feature/your-name → main
```

Only merge tested changes.

------------------------------------------------------------------------

# Development Rules

-   Do not commit API keys.
-   Keep `.env` in `.gitignore`.
-   Do not unnecessarily modify another teammate's module.
-   Keep API field names consistent.
-   Make focused commits.
-   Use clear commit messages.
-   Test locally before creating a Pull Request.
-   Keep the `main` branch stable.
-   Coordinate integration changes with the team.

------------------------------------------------------------------------

# Safety Notice

This application is an **emergency-assistance prototype**.

It must not be treated as a replacement for:

-   Emergency services
-   Professional responders
-   Medical professionals
-   Fire and rescue services
-   Human judgment

For a real emergency, users should prioritize immediate personal safety
and contact appropriate local emergency services.

The system can make mistakes. Confidence scores and explanations are
supporting information, not guarantees.

------------------------------------------------------------------------

# Current Scope

The MVP focuses on:

``` text
VOICE + IMAGE
      ↓
SPEECH + VISION
      ↓
AI AGENT
      ↓
EMERGENCY TYPE
      ↓
SEVERITY
      ↓
REASON
      ↓
ACTION PLAN
      ↓
DASHBOARD + VOICE RESPONSE
```

The primary goal is a reliable end-to-end emergency scenario before
adding additional features.

------------------------------------------------------------------------

# Future Improvements

Potential improvements include:

-   More emergency categories
-   Improved hazard recognition
-   Better multimodal reasoning
-   Real-time streaming voice interaction
-   Improved mobile responsiveness
-   Event/history tracking
-   Authentication
-   Production deployment
-   Monitoring and logging
-   Additional automated tests
-   Accessibility improvements
-   More robust failure recovery

------------------------------------------------------------------------

# Contributing

1.  Create a feature branch.
2.  Make a focused change.
3.  Test locally.
4.  Do not commit secrets.
5.  Commit with a clear message.
6.  Push the feature branch.
7.  Open a Pull Request into `main`.
8.  Address review feedback before merging.

------------------------------------------------------------------------

# Hackathon

This project was developed as an **online-track project for the AI Infra
Summit Hackathon**.

The project follows the hackathon's online build format and focuses on a
multimodal AI application integrating voice, vision, and an emergency
reasoning workflow.

------------------------------------------------------------------------

# License

Add the project's chosen license before public release.

If the team has not selected a license yet, do not claim a specific
license.

------------------------------------------------------------------------

# Quick Start

### Terminal 1 --- Backend

``` powershell
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
```

### Terminal 2 --- Frontend

``` powershell
cd frontend
npm install
npm run dev
```

Configure your own local API keys first:

``` env
SPEECHMATICS_API_KEY=your_key
VISION_API_KEY=your_key
```

Then open the frontend URL provided by Vite.

------------------------------------------------------------------------

## Project Goal

> **Build one complete emergency scenario from user input to actionable
> response.**

``` text
USER
 ↓
VOICE + IMAGE
 ↓
SPEECH + VISION
 ↓
AI AGENT
 ↓
EMERGENCY TYPE
 ↓
SEVERITY
 ↓
REASON
 ↓
ACTION PLAN
 ↓
DASHBOARD + VOICE RESPONSE
```
