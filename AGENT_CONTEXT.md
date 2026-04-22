# Agent Context — Exercise Identifier

> **Audience:** AI coding assistants. Read this file first to understand the architecture, design decisions, and current project state before making any changes.

---

## Project Goal

A **RAG-based MVP** that identifies gym strength-training exercises from:

1. **Natural language descriptions** — a user types something like *"I'm sitting down and pulling a bar to my chest"* and the system returns *"Lat Pulldown"* with full exercise metadata.
2. **Video uploads** (planned) — a short clip is analysed via pose estimation to identify the movement.

The core insight is that beginners rarely know the canonical exercise name. They describe what they *see* or *feel*. The system bridges this vocabulary gap using **vector-similarity search** over pre-generated novice-voice descriptions stored in ChromaDB, then joins back to PostgreSQL for the full structured exercise record.

---

## Tech Stack

| Layer           | Technology                       | Notes                                        |
| --------------- | -------------------------------- | -------------------------------------------- |
| **Backend**     | Python 3.14 · FastAPI · Uvicorn  | Async-first. Lives in `backend/`.            |
| **Frontend**    | Next.js 14 · TypeScript · Tailwind | Dark-mode, mobile-first SPA. `frontend/`.  |
| **Animations**  | Framer Motion                    | All transitions, stagger, layout animations. |
| **Icons**       | Lucide React                     | Minimalist icon set.                         |
| **Relational DB** | PostgreSQL · SQLAlchemy 2 (async) | Stores structured exercise taxonomy.       |
| **Vector DB**   | ChromaDB (persistent, local)     | Stores embeddings of `beginner_description`. |
| **LLM (data gen)** | Ollama · `gemma4:e4b` (local) | Used *only* for offline dataset generation.  |
| **Embeddings**  | Ollama · `nomic-embed-text` (local) | 768-dim vectors for both indexing and query.|

---

## Architecture: Dual-Database Design

```
┌──────────────────────────────────────────────────────────────────────┐
│                        User Query (natural language)                 │
│                  "sitting down pulling the bar to chest"             │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Ollama nomic-embed-text │
                    │  (local embedding)       │
                    └────────────┬────────────┘
                                 │ 768-dim vector
                    ┌────────────▼────────────┐
                    │       ChromaDB           │
                    │  cosine kNN search       │
                    │  → top-K matches         │
                    │  → returns exercise_id   │
                    └────────────┬────────────┘
                                 │ exercise_id (UUID)
                    ┌────────────▼────────────┐
                    │      PostgreSQL          │
                    │  Full exercise record    │
                    │  (name, muscles, equip,  │
                    │   aliases, descriptors)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    JSON Response         │
                    │  Ranked results with     │
                    │  similarity scores       │
                    └─────────────────────────┘
```

**Why two databases?**
- **PostgreSQL** stores the normalised, relational exercise taxonomy (50 exercises, their muscle groups, equipment, aliases, difficulty levels, etc.). This data is highly structured and needs joins, filtering, and constraints.
- **ChromaDB** stores the vector embeddings of `beginner_description` text. This data is purely for nearest-neighbour similarity search — something PostgreSQL with pgvector *could* do, but ChromaDB gives us a zero-config, in-process vector store perfect for an MVP.

The **only coupling point** between the two is the `exercise_id` UUID, stored as metadata in ChromaDB documents.

---

## Repository Layout

```
exercise-identifier/
├── AGENT_CONTEXT.md                        ← You are here
├── Exercise Identifier app/
│   ├── README.md                           ← User-facing quickstart
│   ├── backend/
│   │   ├── main.py                         ← FastAPI app + POST /search/text endpoint
│   │   ├── generate_exercise_dataset.py    ← Ollama data-ingestion script (gemma4:e4b)
│   │   ├── embed_database.py              ← Postgres → ChromaDB embedding pipeline
│   │   ├── chroma_db/                      ← ChromaDB persistent storage (gitignored)
│   │   ├── requirements.txt
│   │   ├── .env / .env.example
│   │   └── app/
│   │       ├── core/
│   │       │   ├── config.py               ← pydantic-settings (DATABASE_URL, etc.)
│   │       │   └── database.py             ← Async engine, session factory, Base
│   │       ├── models/
│   │       │   ├── enums.py                ← Shared taxonomy enums (str, Enum)
│   │       │   └── exercise.py             ← SQLAlchemy ORM models (aggregate root)
│   │       └── schemas/
│   │           └── exercise.py             ← Pydantic v2 API schemas
│   └── frontend/
│       ├── app/
│       │   ├── layout.tsx                  ← Root layout (dark mode, Inter font)
│       │   ├── page.tsx                    ← Main SPA page (search → results → modal)
│       │   └── globals.css                 ← Premium dark theme, glassmorphism, glows
│       ├── components/
│       │   ├── SearchHero.tsx              ← Glowing search input + suggestion pills
│       │   ├── ExerciseCard.tsx            ← Glassmorphic result card with confidence ring
│       │   ├── ExerciseModal.tsx           ← Expanded detail modal (shared-element)
│       │   ├── ConfidenceRing.tsx          ← Animated SVG circular progress ring
│       │   └── Toast.tsx                   ← Animated error toast
│       ├── lib/
│       │   ├── api.ts                      ← searchExercises() API client
│       │   └── types.ts                    ← TypeScript interfaces (mirrors backend)
│       ├── tailwind.config.ts              ← Extended dark theme + custom animations
│       └── package.json
```

---

## Completed Phases

### Phase 1: Data Ingestion Pipeline ✅

**Script:** `generate_exercise_dataset.py`

We built a local data ingestion pipeline using the `gemma4:e4b` model running on Ollama. The script:

1. Iterates over a **50-exercise seed list** covering chest, shoulders, triceps, back, biceps, legs, posterior chain, calves/glutes, and core.
2. Prompts the LLM with strict enum constraints to produce structured JSON for each exercise.
3. Validates the output against `LLMExerciseRecord` (Pydantic) with retry logic.
4. Maps the flat LLM output into the normalised ORM graph and commits individually to Postgres.
5. Is idempotent — re-runs skip exercises that already exist by `primary_name`.

**Enum expansion during ingestion:** The initial `ForceType` enum only had `push`, `pull`, `static`, `hinge`. The LLM correctly output broader force profiles (`squat`, `lunge`, `rotation`, `anti_rotation`) for exercises like Barbell Back Squat and Cable Woodchopper. We expanded `ForceType` to include these 4 new values. We also added `CORE` as a convenience catch-all to `MuscleGroup` since the LLM used it as a grouping term.

> **PostgreSQL enum casing note:** SQLAlchemy + asyncpg stores Python Enum member **names** (UPPERCASE) as PostgreSQL enum values, not `.value` (lowercase). All `ALTER TYPE ADD VALUE` commands must use UPPERCASE. The existing enums have been standardised to all-uppercase with the lowercase duplicates removed via a type-swap migration.

### Phase 2: Vector Embedding Pipeline ✅

**Script:** `embed_database.py`

Reads all 200 `beginner_description` MovementDescriptor rows from PostgreSQL, generates 768-dimensional embeddings via `nomic-embed-text` (Ollama, local), and upserts them into a persistent ChromaDB collection (`exercise_descriptions`).

- **Collection config:** cosine distance metric (`hnsw:space: cosine`).
- **Document IDs:** deterministic, derived from the Postgres `MovementDescriptor.id` UUID.
- **Metadata per document:** `exercise_id` (UUID string) and `exercise_name` for join-back.
- **Idempotent:** re-running overwrites existing embeddings with fresh vectors.

### Phase 3: RAG Search Endpoint ✅

**Endpoint:** `POST /search/text`

The FastAPI app (`main.py`) exposes a search endpoint that implements the full RAG pipeline:

1. **Embed** — The user's query string is embedded locally via `nomic-embed-text` (Ollama).
2. **Search** — The query vector is compared against all 200 beginner_description embeddings in ChromaDB using cosine similarity. The top-K nearest neighbours are returned.
3. **Deduplicate** — Multiple descriptions from the same exercise are collapsed. Only the best-matching description per exercise is kept.
4. **Join** — The `exercise_id` UUIDs from ChromaDB metadata are used to fetch full exercise records from PostgreSQL (including muscles, equipment, aliases, all descriptors).
5. **Return** — A ranked JSON response with similarity scores, the matched description text, and the complete `ExerciseRead` schema for each hit.

**Verified working queries:**
- *"sitting down pulling the bar to my chest"* → **#1 Lat Pulldown** (0.77 similarity)
- *"lying on my back pushing a heavy bar up from my chest"* → **#3 Barbell Bench Press** (0.76 similarity)

### Phase 4: Frontend Architecture ✅

**Stack:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · Framer Motion · Lucide React

The frontend is a premium, ultra-dark single-page application that connects directly to the FastAPI backend's `POST /search/text` endpoint. It is fully operational.

#### Design System: Strict Dark Mode

| Token              | Value                                                  |
| ------------------ | ------------------------------------------------------ |
| Background         | `#0a0a0a` (near-black) with layered surface tones      |
| Surfaces           | Glassmorphism: `rgba(255,255,255,0.03)` + backdrop-blur |
| Borders            | `rgba(255,255,255,0.06)` — barely visible, premium     |
| Accent             | Indigo `#6366f1` with glow variants                    |
| Confidence colors  | Green `#34d399` (≥75%) · Amber `#fbbf24` (≥60%) · Red `#f87171` (<60%) |
| Font               | Inter (Google Fonts) — weights 300–800                 |
| Scrollbars         | Custom ultra-thin 4px with transparent track           |

#### Component Architecture

```
page.tsx (orchestrator)
├── SearchHero
│   ├── Gradient title ("Identify") with subtitle
│   ├── Glowing search input (glow-pulse on focus)
│   ├── "Analyzing biomechanics..." animated loading dots
│   └── Clickable suggestion pills (4 preset queries)
├── ExerciseCard[] (staggered entrance, one per result)
│   ├── ConfidenceRing (animated SVG circular progress)
│   ├── Exercise name + difficulty badge
│   ├── Matched description quote
│   ├── Muscle pills (primary=highlighted, secondary=muted)
│   └── Equipment / movement pattern footer
├── ExerciseModal (shared-element transition via layoutId)
│   ├── Full confidence ring + header
│   ├── 3D Model Placeholder (intentional, styled stub)
│   ├── Summary text
│   ├── "Why this matched" callout box
│   ├── Detail grid (primary/secondary muscles, equipment, pattern)
│   ├── Aliases (alternate names)
│   └── All 4 beginner descriptions
└── Toast (animated error notification with auto-dismiss)
```

#### Animation Strategy (Framer Motion)

- **Hero → Results transition**: Search input slides up smoothly when results arrive (`paddingTop` animation).
- **Card stagger**: Each result card fades in with a 100ms delay offset.
- **Shared-element modal**: `layoutId` on each card enables a seamless card-to-modal expansion.
- **Loading state**: Three pulsing dots with staggered opacity/scale animation.
- **Toast**: Spring-physics entrance (`damping: 25, stiffness: 300`) with auto-dismiss.

#### API Integration

- **`lib/api.ts`**: Clean `searchExercises(query, topK)` function hitting `POST http://localhost:8000/search/text`.
- **Error handling**: Typed `ApiError` class. Network failures and HTTP errors surface as animated Toast notifications, never raw console errors.
- **Types**: `lib/types.ts` mirrors the backend `ExerciseRead` / `SearchResponse` Pydantic schemas.

---

## Database Schema Overview

### PostgreSQL Tables

| Table                    | Purpose                                                                 |
| ------------------------ | ----------------------------------------------------------------------- |
| `exercises`              | Aggregate root — canonical name, slug, difficulty, mechanic, etc.       |
| `exercise_aliases`       | Alternate names / typos for fast prefix-match before vector search.     |
| `movement_descriptors`   | Embeddable text chunks — **the RAG retrieval surface**.                 |
| `exercise_muscle_groups` | Association: exercise ↔ muscle group with `is_primary` flag.            |
| `exercise_equipment`     | Association: exercise ↔ equipment type.                                 |
| `exercise_alternatives`  | Directional links (progression, regression, substitute, variation).     |

### ChromaDB Collection

| Field      | Value                                                           |
| ---------- | --------------------------------------------------------------- |
| Collection | `exercise_descriptions`                                         |
| Documents  | 200 (4 beginner_descriptions × 50 exercises)                    |
| Metric     | Cosine similarity                                               |
| Metadata   | `exercise_id` (UUID), `exercise_name` (string)                  |
| Storage    | `./chroma_db/` (persistent, local)                              |

### Key design decisions

- **Rows, not JSON** — Child data uses real tables (not JSONB) so each text chunk can be independently embedded, indexed, and synced with the vector DB.
- **Dual-DB architecture** — Structured data in PostgreSQL, vector data in ChromaDB. Coupled only by `exercise_id` UUID.
- **Single `is_primary` flag** — One `exercise_muscle_groups` table with a boolean flag, not two separate tables.
- **Directional alternatives** — `(A, PROGRESSION_OF, B)` is not auto-mirrored.
- **All-uppercase PG enums** — SQLAlchemy/asyncpg sends `.name` not `.value`. Confirmed empirically.

### Enums (shared between ORM and Pydantic)

Defined in `app/models/enums.py`:

| Enum                      | Values                                                                     |
| ------------------------- | -------------------------------------------------------------------------- |
| `DifficultyLevel`         | BEGINNER, INTERMEDIATE, ADVANCED, ELITE                                    |
| `MuscleGroup`             | CHEST, FRONT_DELT, SIDE_DELT, REAR_DELT, TRICEPS, LATS, UPPER_BACK, TRAPS, BICEPS, FOREARMS, CORE, ABS, OBLIQUES, LOWER_BACK, QUADS, HAMSTRINGS, GLUTES, ADDUCTORS, ABDUCTORS, CALVES, HIP_FLEXORS |
| `EquipmentType`           | BARBELL, DUMBBELL, KETTLEBELL, EZ_CURL_BAR, TRAP_BAR, CABLE, MACHINE, SMITH_MACHINE, BENCH, INCLINE_BENCH, DECLINE_BENCH, SQUAT_RACK, PULL_UP_BAR, DIP_BARS, PREACHER_BENCH, RESISTANCE_BAND, MEDICINE_BALL, WEIGHT_PLATE, LANDMINE, BODYWEIGHT |
| `MovementPattern`         | HORIZONTAL_PUSH, HORIZONTAL_PULL, VERTICAL_PUSH, VERTICAL_PULL, SQUAT, HINGE, LUNGE, CARRY, ROTATION, ANTI_ROTATION, ISOLATION |
| `MechanicType`            | COMPOUND, ISOLATION                                                        |
| `ForceType`               | PUSH, PULL, STATIC, HINGE, SQUAT, LUNGE, ROTATION, ANTI_ROTATION          |
| `DescriptorCategory`      | SUMMARY, SETUP, EXECUTION, CUE, COMMON_MISTAKE, VARIATION_NOTE, BEGINNER_DESCRIPTION |
| `AlternativeRelationship` | PROGRESSION_OF, REGRESSION_OF, SUBSTITUTE_FOR, VARIATION_OF               |

---

## The `beginner_descriptions` Field (Critical)

This is the **single most important data field** in the entire system. Each exercise gets exactly **4 novice-voice descriptions** that deliberately avoid the exercise name, technical muscle names, and jargon:

| # | Perspective               | Example                                           |
|---|---------------------------|----------------------------------------------------|
| 1 | First-person sensation    | *"I feel my chest stretching as I lower the bar"*  |
| 2 | Third-person visual       | *"A person is lying flat, pushing a bar upward"*   |
| 3 | Equipment/setup-centred   | *"Using a long bar on a rack with a flat bench…"*  |
| 4 | Naive/informal            | *"It looks like you're bench-pressing a barbell"*  |

These are stored as `MovementDescriptor` rows (category = `BEGINNER_DESCRIPTION`) in PostgreSQL, embedded via `nomic-embed-text` into ChromaDB, and matched against user queries at inference time.

---

## Current State & Next Steps

### Done
- [x] FastAPI boilerplate + async Postgres connection
- [x] Full ORM schema (6 tables, richly documented)
- [x] Pydantic API schemas (Create / Read / Update / Summary)
- [x] Data ingestion with 50 exercises via local Ollama (gemma4:e4b)
- [x] Enum expansion (ForceType + MuscleGroup) and DB standardisation
- [x] ChromaDB embedding pipeline (200 vectors via nomic-embed-text)
- [x] `POST /search/text` RAG endpoint (embed → search → join → return)
- [x] End-to-end verified with real queries
- [x] Premium dark-mode Next.js frontend (Framer Motion, glassmorphism)
- [x] Frontend ↔ backend integration (fully wired to ChromaDB/Postgres RAG)
- [x] Search → animated cards → expanded detail modal flow

### Not yet built
- [ ] CRUD API routes for exercises (GET/POST/PATCH/DELETE)
- [ ] Video/pose-estimation pipeline (MediaPipe)
- [ ] Alembic migrations (currently using `CREATE TABLE IF NOT EXISTS`)
- [ ] Production deployment config (Docker, env separation)
- [ ] Alias-based fast-path search (prefix match before vector search)
- [ ] `MovementDescriptor.vector_id` / `embedding_model` sync-back from ChromaDB
- [ ] 3D avatar integration (placeholder stub exists in ExerciseModal)

---

## How to Run

### Prerequisites
```bash
ollama serve                     # Terminal 1
ollama pull gemma4:e4b           # One-time (data gen model)
ollama pull nomic-embed-text     # One-time (embedding model)
# PostgreSQL running locally
```

### Backend
```bash
cd "Exercise Identifier app/backend"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Step 1: Generate exercise data (≈14 min — runs LLM for each exercise)
python generate_exercise_dataset.py

# Step 2: Embed into ChromaDB (≈30 sec)
python embed_database.py

# Step 3: Start the API
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd "Exercise Identifier app/frontend"
npm install
npm run dev
# Open http://localhost:3000
```

### Test the search (CLI)
```bash
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "sitting down pulling the bar to my chest", "top_k": 3}'
```
