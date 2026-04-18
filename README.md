<div align="center">

# 🏟️ CrowdSense AI

### Real-time crowd intelligence for large-scale sporting venues

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Claude](https://img.shields.io/badge/Claude-Sonnet_4-7C3AED?logo=anthropic)](https://anthropic.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docker.com/)

</div>

---

## What is CrowdSense AI?

CrowdSense AI simulates and reasons about real-time crowd density across **14 stadium zones**, pushes live data via WebSocket, and uses Claude to generate proactive attendee nudges *before queues form*. It also provides natural-language Q&A grounded in live crowd data and an admin dashboard with per-zone staff action recommendations.

> **Venues lose revenue to poor crowd flow. CrowdSense reasons about it, communicates in plain language, and acts before the problem peaks.**

---

## Architecture

```
┌─────────────────────────────────────┐     WebSocket /ws/crowd (5 s)
│         React + Vite Frontend       │◄────────────────────────────────┐
│  (Vercel)                           │                                  │
│  / → Attendee view                  │  POST /chat                      │
│  /admin → Admin Dashboard           │  POST /nudges/generate           │
└──────────────┬──────────────────────┘  GET  /crowd/state               │
               │ REST + WS             POST /events/trigger               │
               ▼                                                          │
┌─────────────────────────────────────┐                                  │
│         FastAPI Backend             │──────────────────────────────────►│
│  (Railway / Docker)                 │                                  │
│  simulator.py  → 14-zone density    │  Anthropic Claude API            │
│  llm_service.py → nudges + chat     │◄─────────────────────────────────┘
└─────────────────────────────────────┘
```

---

## Project Structure

```
CrowdSenseAI/
├── backend/
│   ├── simulator.py        # 14-zone density simulator + event profiles
│   ├── llm_service.py      # Claude nudge / chat / staff-action calls
│   ├── main.py             # FastAPI app + WebSocket broadcaster
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── railway.toml
│   └── .env.example
└── frontend/
    ├── index.html
    ├── vercel.json
    ├── vite.config.js
    ├── package.json
    ├── .env.example
    └── src/
        ├── main.jsx
        ├── App.jsx                      # Router: / and /admin
        ├── index.css                    # Full design system
        ├── hooks/
        │   └── useCrowdStream.js        # WebSocket hook + auto-reconnect
        └── components/
            ├── StadiumMap.jsx           # SVG heatmap — 14 zones
            ├── NudgePanel.jsx           # LLM nudges every 60 s
            ├── CrowdChat.jsx            # NL Q&A chat widget
            └── AdminDashboard.jsx       # Zone table + event triggers
```

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### 1 — Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run
set ANTHROPIC_API_KEY=sk-ant-... # Windows
# OR
export ANTHROPIC_API_KEY=sk-ant-... # macOS/Linux

uvicorn main:app --reload --port 8000
```

The API is now live at **http://localhost:8000**. Visit **http://localhost:8000/docs** for interactive Swagger docs.

### 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the Vite dev server proxies all API and WebSocket calls to `localhost:8000`, so no env vars are needed for local dev.

---

## Docker (Backend)

```bash
# Build
docker build -t crowdsense ./backend

# Run (replace with your key)
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... crowdsense
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/crowd/state` | Full crowd snapshot — all 14 zones |
| `POST` | `/events/trigger` | Switch event phase (`PRE_GAME`, `IN_PLAY`, `HALF_TIME`, `FULL_TIME`) |
| `POST` | `/nudges/generate` | LLM-generated attendee nudges |
| `POST` | `/chat` | Natural language Q&A grounded in live data |
| `GET` | `/admin/staff-actions` | LLM staff action for every zone |
| `POST` | `/admin/staff-action` | LLM staff action for a single zone |
| `GET` | `/health` | Health check |
| `WS` | `/ws/crowd` | WebSocket — pushes crowd state every 5 s |

### Example: Trigger HALF_TIME

```bash
curl -X POST http://localhost:8000/events/trigger \
  -H "Content-Type: application/json" \
  -d '{"event": "HALF_TIME"}'
```

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Which concession stand has the shortest queue?", "history": []}'
```

### CORS test (post-deployment)

```bash
curl -H "Origin: https://your-app.vercel.app" \
     https://your-backend.up.railway.app/crowd/state
```

---

## Deployment

### Backend → Railway

1. Push the `backend/` folder (or the whole repo) to GitHub.
2. On [Railway](https://railway.app/), create a new project → **Deploy from GitHub repo**.
3. Railway auto-detects the `Dockerfile`.
4. Add the environment variable: `ANTHROPIC_API_KEY` = your key.
5. Enable **Public Networking** and note your Railway HTTPS URL.

### Frontend → Vercel

1. Push the whole repo to GitHub.
2. On [Vercel](https://vercel.com/), import the repository.
3. Set **Root Directory** to `frontend`.
4. Add environment variable: `VITE_API_URL` = your Railway HTTPS URL (no trailing slash).
5. Deploy — Vercel auto-runs `npm run build`.
6. The `vercel.json` handles SPA routing rewrites automatically.

---

## Event Profiles

| Phase | Gates | Concessions | Restrooms | Exits |
|-------|-------|-------------|-----------|-------|
| **PRE_GAME** | 🔴 85% | 🟡 55% | 🟢 30% | ⚫ 5% |
| **IN_PLAY** | ⚫ 10% | 🟢 25% | 🟢 20% | ⚫ 5% |
| **HALF_TIME** | ⚫ 5% | 🔴 90% | 🔴 85% | ⚫ 10% |
| **FULL_TIME** | ⚫ 5% | 🟢 20% | 🟡 40% | 🔴 95% |

Each target is multiplied by 100 and a sinusoidal noise term (`sin(t·0.3 + phase)·8`) plus random ±3 is added, so density is always dynamic.

---

## Colour Legend

| Colour | Hex | Density |
|--------|-----|---------|
| 🟢 Green | `#1D9E75` | < 40% |
| 🟡 Amber | `#EF9F27` | 40–70% |
| 🔴 Red | `#E24B4A` | > 70% |

Opacity formula: `0.15 + (density / 100) × 0.65` — faint at low crowd, vivid at high crowd.

---

## Environment Variables

| Variable | Where | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | Backend | Claude API key |
| `VITE_API_URL` | Frontend (build) | Railway HTTPS URL, e.g. `https://xyz.up.railway.app` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Uvicorn · httpx |
| LLM | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Frontend | React 18 · Vite · React Router · Vanilla CSS |
| Hosting | Railway (backend) · Vercel (frontend) |
| Container | Docker (`python:3.11-slim`) |

