# ResumeApply Agent — Hackathon Submission

This project is a full-stack autonomous job application agent built for the Google Gemini Live Agent Challenge.

## 🚀 Quick Start Instructions

### 1. Prerequisites
- **Gemini API Key**: Obtain one from [Google AI Studio](https://aistudio.google.com/).
- **Python 3.11+** and **Node.js 20+**.

---

### 2. Backend Setup (FastAPI)
Navigate to the backend directory and set up the environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

**Environment Variables**:
Create a `.env` file in the `backend/` folder:
```env
GEMINI_API_KEY=your_api_key_here
PROJECT_ID=your_gcp_project_id
GCS_BUCKET=your_bucket_name
```

**Run Server**:
```bash
uvicorn main:app --reload --port 8000
```

---

### 3. Frontend Setup (Next.js)
Navigate to the frontend directory:
```bash
cd frontend
npm install
```

**Environment Variables**:
Create a `.env.local` file in the `frontend/` folder:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

**Run Development Server**:
```bash
npm run dev
```

---

### 4. Verification Flow
1. Open `http://localhost:3000` in your browser.
2. **Step 1**: Upload your resume (PDF/DOCX) on the `/upload` page.
3. **Step 2**: Set preferences on the `/preferences` page.
4. **Step 3**: Launch the agent! Watch the live feed and reasoning logs on the `/dashboard`.
5. **Step 4**: Track status on the `/tracker` page.

## 🛠 Tech Stack
- **Frontend**: Next.js 14, GSAP (Animations), Zustand (State), WebSocket client.
- **Backend**: FastAPI, Google ADK (Agent Development Kit), Gemini 2.0 Flash (Multimodal reasoning).
- **Agent Tools**: Playwright (Browser control), Gemini Vision (Page understanding).
