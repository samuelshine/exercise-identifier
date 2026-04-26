# Exercise Identifier

A "Shazam for Fitness" PWA. Describe an exercise you saw at the gym in your
own words and get back the canonical name, form cues, a muscle map, and
biomechanically sound alternatives.

> **Status:** Phase 1 (text search) is feature-complete. Phase 2 (video pose
> identification) is scaffolded behind 501 stubs. See [`docs/PRD.md`](docs/PRD.md)
> for the full Product Requirements Document.

---

## Stack

| Layer       | Tech                                                         |
| ----------- | ------------------------------------------------------------ |
| Frontend    | Next.js 14 App Router · React 18 · Tailwind · Framer Motion · PWA |
| Backend     | FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2                |
| Database    | PostgreSQL                                                   |
| Vector DB   | ChromaDB (cosine, `nomic-embed-text` 768-dim)                |
| LLM         | Ollama: `nomic-embed-text` (embed) · `gemma4:e4b` (judge)    |
| Migrations  | Alembic                                                      |
| Rate limit  | slowapi (per-IP, configurable)                               |

---

## Local development

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 14+ running locally
- [Ollama](https://ollama.com) running locally with the two models pulled:
  ```bash
  ollama pull nomic-embed-text
  ollama pull gemma4:e4b
  ```

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then edit DATABASE_URL etc.

# One-time DB bootstrap (creates the database + applies the initial migration)
python -m scripts.setup_db
alembic upgrade head

# Generate the canonical exercise dataset and embed descriptors into Chroma
python -m scripts.generate_dataset
python -m scripts.embed_database

# Run the API
uvicorn main:app --reload
```

The API listens on `http://localhost:8000`.
Visit `http://localhost:8000/docs` for the interactive OpenAPI UI (dev only).

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app is at `http://localhost:3000`. It reads `NEXT_PUBLIC_API_URL` to
reach the backend.

---

## Production checklist

The repo ships production-grade defaults; before you deploy, confirm:

- `ENVIRONMENT=production` and `DEBUG=false` in the backend env. This
  disables `/docs`, hides tracebacks, and skips the dev-only `create_all`.
- `CORS_ORIGINS` includes the deployed frontend URL.
- `DATABASE_URL` points at a managed Postgres with TLS.
- `alembic upgrade head` ran during deploy (do **not** rely on `create_all`).
- `NEXT_PUBLIC_SITE_URL` is the real frontend origin (used by `sitemap.xml`).
- Splash images referenced in `frontend/app/layout.tsx` exist in `public/splash/`
  (or remove the `appleWebApp.startupImage` block).

---

## Directory layout

```
backend/
  app/
    core/         # config, db engine, logging, middleware, errors, limiter
    models/       # SQLAlchemy ORM (single source of truth for schema)
    schemas/      # Pydantic request/response models
    routers/      # FastAPI endpoints
    services/     # embedding, reranker (LLM judge with vector fallback)
  alembic/        # migrations (autogenerate-driven)
  scripts/        # setup_db, generate_dataset, embed_database
  main.py         # FastAPI app entrypoint
frontend/
  app/            # App Router routes (page, error, not-found, loading, sitemap)
  components/     # search, results, exercise/* (Header, MuscleMap, FormViewer, …)
  lib/            # api client, types, utils
  hooks/          # useSearch
docs/PRD.md       # full product + architecture spec
```

---

## API surface (Phase 1)

| Method | Path                                       | Description                                  |
| ------ | ------------------------------------------ | -------------------------------------------- |
| GET    | `/health`                                  | Per-dependency status                        |
| GET    | `/meta/enums`                              | Enum values for frontend dropdowns           |
| POST   | `/search/text`                             | Semantic exercise search (rate-limited)      |
| GET    | `/exercises`                               | Paginated, filterable list                   |
| GET    | `/exercises/slug/{slug}`                   | Detail by slug (used by EDP)                 |
| GET    | `/exercises/{id}`                          | Detail by UUID                               |
| POST   | `/exercises`                               | Create (admin)                               |
| PATCH  | `/exercises/{id}`                          | Update (admin)                               |
| DELETE | `/exercises/{id}`                          | Delete (admin)                               |
| GET    | `/exercises/{id}/alternatives`             | Equipment-filtered alternatives              |

Phase 2 (video) endpoints respond `501 Not Implemented` today.

---

## License

Proprietary. All rights reserved.
