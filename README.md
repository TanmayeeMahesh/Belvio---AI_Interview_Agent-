# Belvio — AI Interview Agent

An end-to-end automated technical interview platform. Upload a resume and job description, and Belvio handles everything — candidate analysis, question generation, email invite, live AI-conducted voice interview, scoring, and PDF report — completely autonomously.

---

## What It Does

1. **Analyse** — HR uploads a resume + JD PDF. The system extracts candidate info, detects experience level, scores JD match, and identifies skill gaps.
2. **Schedule** — Generates a tailored question plan, emails the candidate an invite, and schedules the AI bot to join the meeting.
3. **Interview** — At the scheduled time, a voice bot joins the Teams / Google Meet / Zoom call, conducts the full interview, asks follow-ups, handles meta-commands ("repeat that", "rephrase"), and manages timeouts.
4. **Evaluate** — After the call, the system scores each answer on 4 dimensions, produces a composite score, generates a recommendation, and writes a PDF report.
5. **Review** — HR views all sessions, scores, transcripts, and downloads reports from the dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Voice Bot | Recall.ai |
| Text-to-Speech | gTTS (Google TTS) |
| Realtime LLM | Groq `llama-3.1-8b-instant` |
| Evaluation LLM | Groq `llama-3.3-70b-versatile` |
| Analysis LLM | Gemini → Claude → Groq (fallback chain) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase JWT (via FastAPI backend) |
| PDF | reportlab |
| Email | Gmail SMTP |
| Tunnel | ngrok |
| Frontend | React 18 + Vite |

---

## Project Structure

```
├── app_full.py          # Main interview engine + webhook handler
├── api_routes.py        # REST API endpoints
├── auth.py              # JWT verification + encrypted API key storage
├── db.py                # Supabase database operations
├── extraction.py        # PDF parsing + LLM resume/JD analysis
├── llm_stack.py         # Multi-provider LLM with fallback chain
├── evaluator.py         # Post-interview scoring (4 dimensions)
├── report_pdf.py        # PDF report generation
├── scheduler.py         # Email invite + bot scheduling
├── .env.example         # Environment variable template
└── frontend/
    ├── src/
    │   ├── App.jsx          # Auth + navigation
    │   ├── api.js           # Axios instance
    │   ├── pages/
    │   │   ├── Dashboard.jsx    # Upload → Analyse → Schedule
    │   │   ├── Sessions.jsx     # Session list + filters
    │   │   └── Reports.jsx      # Scores + transcript + PDF download
    │   └── index.css        # Global styles
    └── package.json
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [ngrok](https://ngrok.com) account (free tier)
- [Recall.ai](https://recall.ai) account
- [Supabase](https://supabase.com) project
- [Groq](https://console.groq.com) API key
- Gmail account with App Password enabled

### 1. Clone the repo
```bash
git clone https://github.com/TanmayeeMahesh/Belvio---AI_Interview_Agent-.git
cd Belvio---AI_Interview_Agent-
```

### 2. Set up Python environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Fill in all values in `.env` — see the comments in `.env.example` for guidance.

### 4. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

---

## Running the App

Open **3 terminals** in order:

**Terminal 1 — ngrok**
```bash
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.app` URL and set `NGROK_URL=...` in `.env`.

**Terminal 2 — Backend**
```bash
.venv\Scripts\activate
python app_full.py
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** and sign in.

> **Tip:** Get a free static ngrok domain from the ngrok dashboard so the URL never changes.

---

## How the Interview Works

```
HR Dashboard
  └─ Upload Resume + JD → /api/analyse → LLM analysis
  └─ Schedule → /api/schedule → questions generated + email sent
                                       ↓
                              Bot joins meeting at scheduled time
                                       ↓
                         Consent prompt → "Yes" → Interview starts
                                       ↓
                    Per answer: gate (strong/partial/vague) → follow-up or advance
                                       ↓
                         All questions done / 45 min cap / silence timeout
                                       ↓
                    Evaluate → Score per topic → PDF report → Supabase
```

### Concurrent Interviews
Multiple interviews can run simultaneously. Each bot gets a unique `routing_key` UUID embedded in its webhook URL, so transcription events are always routed to the correct session — even when Recall.ai doesn't include a bot ID in webhook payloads.

### Scoring
Each topic is scored on 4 dimensions:

| Dimension | Weight |
|---|---|
| Technical Accuracy | 40% |
| Depth | 30% |
| Clarity & Communication | 20% |
| Problem Solving | 10% |

### Recommendation Bands
| Composite Score | Recommendation |
|---|---|
| ≥ 8.0 | Strongly Recommended |
| ≥ 6.5 | Recommended |
| ≥ 5.0 | Needs Further Review |
| < 5.0 | Not Recommended |

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `RECALLAI_API_KEY` | Recall.ai API key |
| `NGROK_URL` | Your ngrok tunnel URL |
| `GROQ_API_KEY` | Groq API key (required) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key (server-side only) |
| `GMAIL_ADDRESS` | Gmail address for sending invites |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not login password) |
| `APP_ENCRYPTION_KEY` | Fernet key for encrypting per-user API keys |

---

## Supported Meeting Platforms

- Microsoft Teams
- Google Meet
- Zoom
- Webex

---

## Known Constraints

- Requires ngrok (or equivalent tunnel) for Recall.ai webhooks
- Google Meet bots wait in the lobby — the host must admit them manually
- PDF text extraction only (no OCR for scanned documents)
- Recording URL may take up to 10 minutes to become available after the call
- All services run locally — no cloud deployment included

---

## License

MIT
