# Agent Context — Exercise Identifier

> **Audience:** AI coding assistants. Read this first to understand the architecture before making changes.

## Project Goal

A **RAG-based MVP** that identifies gym strength-training exercises from:

1. **Natural language descriptions** — a user types something like *"I lie on a bench and push a bar up"* and the system returns *"Barbell Bench Press"*.
2. **Video uploads** (planned) — a short clip is analysed via pose estimation to identify the movement.

The core insight is that beginners rarely know the canonical exercise name. They describe what they *see* or *feel*. The system bridges this vocabulary gap using vector-similarity search over pre-generated novice-voice descriptions.

---

## Tech Stack

| Layer          | Technology                          | Notes                                      |
| -------------- | ----------------------------------- | ------------------------------------------ |
| **Backend**    | Python 3.12 · FastAPI · Uvicorn     | Async-first. Lives in `backend/`.          |
| **Frontend**   | Next.js 14 · TypeScript · Tailwind  | Mobile-first PWA. Lives in `frontend/`.    |
| **Database**   | PostgreSQL · SQLAlchemy 2 (async)   | Declarative ORM with `asyncpg` driver.     |
| **Vector DB**  | Pinecone or Milvus (TBD)           | Stores embeddings of `MovementDescriptor`. |
| **LLM (data)** | Ollama (local) · `gemma4:e4b`      | Used *only* for offline data generation.   |
| **Embeddings** | TBD                                 | Will embed `beginner_description` text.    |

---

## Repository Layout

```
exercise-identifier/
├── AGENT_CONTEXT.md                    ← You are here
├── Exercise Identifier app/
│   ├── README.md                       ← User-facing quickstart
│   ├── backend/
│   │   ├── main.py                     ← FastAPI app entrypoint
│   │   ├── generate_exercise_dataset.py← Local Ollama data-ingestion script
│   │   ├── requirements.txt
│   │   ├── .env / .env.example
│   │   └── app/
│   │       ├── core/
│   │       │   ├── config.py           ← pydantic-settings (DATABASE_URL, etc.)
│   │       │   └── database.py         ← Async engine, session factory, Base
│   │       ├── models/
│   │       │   ├── enums.py            ← Shared taxonomy enums (str, Enum)
│   │       │   └── exercise.py         ← SQLAlchemy ORM models (aggregate root)
│   │       └── schemas/
│   │           └── exercise.py         ← Pydantic v2 API schemas
│   └── frontend/                       ← Next.js app (not yet connected to API)
```

---

## Data Ingestion Pipeline

### Why a local Ollama script?

We need realistic, varied *beginner-voice* descriptions of each exercise for our RAG retrieval corpus. Cloud APIs are expensive for iterative dataset work and introduce rate limits. Instead, `generate_exercise_dataset.py` runs a local Ollama model to produce structured JSON for each exercise, validates it with Pydantic, and writes it to Postgres.

### How it works

1. **Seed list** — 50 canonical exercise names covering chest, shoulders, triceps, back, biceps, legs, posterior chain, calves/glutes, and core.
2. **LLM call** — For each exercise, the script prompts the model with strict enum constraints and asks for 4 `beginner_descriptions` (see below).
3. **Validation** — Raw JSON is cleaned (fence stripping, brace matching), then validated against `LLMExerciseRecord` (Pydantic).
4. **Persistence** — The validated record is mapped into the normalised ORM graph (`Exercise` + child tables) and committed individually. The script is idempotent — existing exercises (matched by `primary_name`) are skipped on re-run.

### The `beginner_descriptions` field (critical)

Each exercise gets exactly **4 novice-voice descriptions** that deliberately avoid the exercise name, technical muscle names, and jargon:

| # | Perspective               | Example                                           |
|---|---------------------------|----------------------------------------------------|
| 1 | First-person sensation    | *"I feel my chest stretching as I lower the bar"*  |
| 2 | Third-person visual       | *"A person is lying flat, pushing a bar upward"*   |
| 3 | Equipment/setup-centred   | *"Using a long bar on a rack with a flat bench…"*  |
| 4 | Naive/informal            | *"It looks like you're bench-pressing a barbell"*  |

These are stored as `MovementDescriptor` rows with `category = BEGINNER_DESCRIPTION` and `needs_reindex = True`. A background worker (not yet built) will embed them into the vector DB. At query time, the user's input is embedded with the same model and nearest-neighbour search over these vectors identifies the exercise.

---

## Database Schema Overview

### Core tables

| Table                    | Purpose                                                                 |
| ------------------------ | ----------------------------------------------------------------------- |
| `exercises`              | Aggregate root — canonical name, slug, difficulty, mechanic, etc.       |
| `exercise_aliases`       | Alternate names / typos for fast prefix-match before vector search.     |
| `movement_descriptors`   | Embeddable text chunks — **the RAG retrieval surface**.                 |
| `exercise_muscle_groups` | Association: exercise ↔ muscle group with `is_primary` flag.            |
| `exercise_equipment`     | Association: exercise ↔ equipment type.                                 |
| `exercise_alternatives`  | Directional links (progression, regression, substitute, variation).     |

### Key design decisions

- **Rows, not JSON** — Child data uses real tables (not JSONB) so each text chunk can be independently embedded, indexed, and synced with the vector DB.
- **Vector DB seam** — `MovementDescriptor.vector_id` and `embedding_model` are the *only* coupling points to the external vector store. The ORM never calls the vector DB directly.
- **Single `is_primary` flag** — One `exercise_muscle_groups` table with a boolean flag, not two separate tables.
- **Directional alternatives** — `(A, PROGRESSION_OF, B)` is not auto-mirrored. Callers query both directions when needed.

### Enums (shared between ORM and Pydantic)

Defined in `app/models/enums.py`: `DifficultyLevel`, `MuscleGroup`, `EquipmentType`, `MovementPattern`, `MechanicType`, `ForceType`, `DescriptorCategory`, `AlternativeRelationship`.

---

## Current State & Next Steps

### Done
- [x] FastAPI boilerplate + async Postgres connection
- [x] Full ORM schema (6 tables, richly documented)
- [x] Pydantic API schemas (Create / Read / Update / Summary)
- [x] Data ingestion script with 50-exercise seed list
- [x] Idempotent, individually-committed ingestion with retry logic

### Not yet built
- [ ] Embedding worker (read `needs_reindex` rows → embed → upsert to vector DB → write back `vector_id`)
- [ ] RAG retrieval endpoint (`POST /identify` — embed user text, kNN search, return top-N exercises)
- [ ] CRUD API routes for exercises
- [ ] Frontend ↔ backend integration
- [ ] Video/pose-estimation pipeline (MediaPipe)
- [ ] Alembic migrations (currently using `CREATE TABLE IF NOT EXISTS`)
