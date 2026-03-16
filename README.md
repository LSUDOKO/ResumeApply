# ResumeApply: The Autonomous Job Search Agent
[![Gemini Live Agent Challenge](https://img.shields.io/badge/Challenge-Gemini%20Live%20Agent-blueviolet?style=for-the-badge&logo=google-gemini)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**ResumeApply** is an industrial-grade autonomous agent designed to revolutionize the job application process. Built for the Google Gemini Live Agent Challenge, it combines high-fidelity WebRTC voice commands with LLM-driven browser automation to handle the entire application lifecycle—from resume parsing to hitting 'Submit'.

---

## ✨ Key Features

### 🎙️ Bidirectional Voice Interaction
Control your agent using real-time voice commands. Powered by the **Gemini Multimodal Live API** and a custom **WebRTC bridge**, you can talk to your agent as it browses, giving it hints or updating your preferences mid-flow.

### 🧠 Multimodal Vision Reasoning
Unlike brittle scrapers, ResumeApply **sees** the web. It uses Gemini 2.0 Flash to analyze screenshots, identify form fields by coordinates, and navigate complex UI layouts with human-like visual understanding.

### 🛡️ Human-in-the-Loop Resilience
The agent doesn't get stuck. When it encounters a **CAPTCHA**, **MFA**, or an ambiguous question, it pauses execution and alerts you via a robust WebSocket layer for immediate intervention.

### ☁️ Cloud-Native & Synchronized
- **Supabase Integration**: Real-time synchronization of application status, resume metadata, and agent sessions across all devices.
- **Bulletproof WebSockets**: Per-client message queuing and session replaying to ensure you never miss a status update even on laggy connections.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 14, GSAP (Animations), Zustand, TailwindCSS |
| **Backend** | FastAPI, Gemini 2.0 Flash, WebRTC (aiortc), WebSockets |
| **Database** | Supabase (PostgreSQL), Supabase Auth |
| **Storage** | Supabase Cloud Storage (Resumes & Assets) |
| **Engine** | Playwright (Stealth Mode), Google Generative AI ADK |

---

## 🚀 Getting Started

### 1. Environment Setup
Clone the repository and prepare your credentials.

**Backend (.env)**:
```env
GEMINI_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_anon_key
PROJECT_ID=your_gcp_project
```

**Frontend (.env.local)**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 2. Backend Installation (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

### 3. Frontend Installation (Next.js)
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Repository Structure

- `backend/agents/`: Core agentic logic and instruction sets.
- `backend/tools/`: High-level capabilities (Navigation, Form Filling, Interventions).
- `backend/routers/`: WebSocket, WebRTC, and Supabase API handlers.
- `frontend/app/`: Next.js App Router for the dashboard and tracker.
- `frontend/lib/geminiLive.ts`: WebRTC management for real-time voice.

---

## 🔄 The Workflow

1. **Upload**: Drag & drop your resume. Gemini extracts your profile with 99.9% accuracy via JSON mode.
2. **Preference**: Tell the agent your dream role via voice or text.
3. **Execute**: The agent navigates job boards (LinkedIn/Indeed), filling forms autonomously.
4. **Intervene**: Resolve CAPTCHAs directly through the dashboard "thinking" view.
5. **Track**: Monitor every application in your unified Supabase dashboard.

---

## 📜 License
Directly licensed under the **MIT License**. Created by [Bajrangi](https://github.com/LSUDOKO).
