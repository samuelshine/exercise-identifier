# Exercise Identifier

Web-based MVP that identifies gym strength-training exercises from text
descriptions or video uploads.

## Repo layout

```
.
├── backend/     # FastAPI service (Python)
└── frontend/    # Next.js 14 + Tailwind (TypeScript, mobile-first PWA)
```

## Quickstart

**Terminal 1 — backend**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The backend root endpoint is at
http://localhost:8000/ (returns `{"message": "Hello World"}`).

## Stack

- **Backend:** Python + FastAPI + Uvicorn. Async-first.
- **Frontend:** Next.js (App Router) + Tailwind CSS. Mobile-first PWA.
- **Planned:** PostgreSQL, Pinecone/Milvus, RAG for text, MediaPipe for video.

AI routing will live in a dedicated module to keep it decoupled from core
business logic.
