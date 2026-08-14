# 📚 AI Study Planner

An AI-powered day-by-day study planner built with **Streamlit** (frontend), **FastAPI** (backend), and **Groq LLM** (Llama 3.3 70B). Upload your syllabus PDF and/or enter topics — get a precise, personalised study plan that maps exactly to your content.

---

## ✨ Features

- 📄 **PDF upload** — extracts text from your syllabus/textbook automatically
- ✍️ **Manual topics** — add any extra topics you want covered
- 🤖 **AI-generated plans** — Llama 3.3-70B via Groq creates day-by-day breakdowns with:
  - Topic & subtopics
  - Exact chapter/page references
  - Actionable daily tasks
  - Key concepts to master
  - Study tips & time estimates
- ✅ **Progress tracking** — mark days complete, see overall progress
- 🔍 **Filter & search** — by status, difficulty, or topic keywords
- ⬇️ **Download** — export your plan as JSON

---

## 🗂 Project Structure

```
STUDY-PLANUU/
├── backend/
│   ├── __init__.py
│   └── main.py          # FastAPI — PDF extraction + Groq LLM
├── frontend/
│   ├── __init__.py
│   └── app.py           # Streamlit UI
├── requirements.txt
├── start.sh             # Railway single-service startup script
├── railway.json         # Railway deployment config
└── README.md
```

---

## 🚀 Deploy on Railway

### 1. Get a Groq API Key (free)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in → **API Keys** → **Create API Key**
3. Copy the key

### 2. Push this repo to GitHub (if not already done)

```bash
git init
git remote add origin https://github.com/RAPALLY-JAYENDRA/STUDY-PLANUU.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 3. Deploy on Railway

1. Go to [railway.app](https://railway.app) and create a new project
2. **Deploy from GitHub repo** → select `RAPALLY-JAYENDRA/STUDY-PLANUU`
3. Railway auto-detects `railway.json` and `start.sh`
4. Add **Environment Variables** in Railway:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_xxxxxxxxxxxxxxxxxxxxxxxx` |

5. Railway will build & deploy. The exposed URL is your **Streamlit UI**.

> ✅ Only **one environment variable** needed: `GROQ_API_KEY`

---

## 💻 Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
export GROQ_API_KEY="gsk_your_key_here"   # Windows: $env:GROQ_API_KEY="..."

# Terminal 1 — Start FastAPI backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Start Streamlit frontend
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py
```

Open http://localhost:8501 in your browser.

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | — | Groq API key for LLM inference |
| `PORT` | Auto (Railway) | 8501 | Port Streamlit listens on |
| `BACKEND_URL` | Optional | `http://localhost:8000` | FastAPI URL (auto-set in start.sh) |

---

## 🏗 Architecture

```
User → Streamlit (PORT) → FastAPI (:8000) → Groq API → Llama 3.3-70B
                                ↑
                          PyMuPDF (PDF extraction)
```

Both services run in the **same Railway container** via `start.sh`.

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| PDF Extraction | PyMuPDF (fitz) |
| LLM | Llama 3.3-70B via Groq API |
| Deployment | Railway (single service) |

---

## 📄 License

MIT
