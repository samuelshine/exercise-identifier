# Exercise Identifier — Product Requirements Document & Technical Architecture

> **Status:** Active Development — Phase 1 Feature-Complete  
> **Last Updated:** 2026-04-23  
> **Authors:** Samuel Shine (Product Owner), Claude (Solutions Architect / AI Engineer)  
> **Version:** 1.2

---

## Table of Contents

1. [Executive Summary & Product Strategy](#1-executive-summary--product-strategy)
2. [System Architecture & Data Flow](#2-system-architecture--data-flow)
3. [Database Schema & API Contracts](#3-database-schema--api-contracts)
4. [UI/UX & Frontend Implementation Guidelines](#4-uiux--frontend-implementation-guidelines)
5. [Phased Execution Roadmap](#5-phased-execution-roadmap)
6. [As-Built Implementation Log](#6-as-built-implementation-log)

---

## 1. Executive Summary & Product Strategy

### 1.1 Problem Statement

Gym-goers routinely see exercises they cannot name. Without a name, they cannot search YouTube for tutorials, ask trainers informed questions, or log the movement in a workout tracker. Current solutions (scrolling exercise databases, asking strangers mid-set) are socially awkward, slow, and unreliable. No product exists that treats exercise identification as a first-class search problem.

### 1.2 Product Vision

**Exercise Identifier is "Shazam for Fitness."** A user walks into a gym, sees someone performing an unfamiliar movement, and opens a lightweight PWA on their phone. They either describe what they saw in plain language ("lying on a bench, pushing two dumbbells up") or record a short video. Within seconds, the app returns the exact exercise name, a 3D avatar demonstrating perfect form, an anatomical muscle map, and biomechanically sound alternatives they can perform with whatever equipment is available to them.

### 1.3 Core User Journey

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. OBSERVE    User sees an unfamiliar exercise being performed     │
│       ↓                                                             │
│  2. CAPTURE    Opens PWA → describes in text OR records 5-15s video │
│       ↓                                                             │
│  3. IDENTIFY   System returns top 3-5 probable matches with         │
│                confidence scores and matched reasoning               │
│       ↓                                                             │
│  4. LEARN      User taps a result → sees 3D form demo,             │
│                muscle map, difficulty, equipment, and alternatives   │
│       ↓                                                             │
│  5. ACT        User performs the exercise with correct form          │
│                or selects an alternative with available equipment    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Unique Selling Propositions

| USP | Detail |
|-----|--------|
| **Multimodal Input** | No other fitness app accepts both free-text descriptions AND video capture as first-class search inputs. |
| **Semantic Understanding** | Uses RAG architecture (embedding + LLM re-ranking) instead of keyword matching. Understands "that thing where you hunch over and pull a bar to your belly" → Bent-Over Barbell Row. |
| **Zero Friction** | PWA — no app store download. Open browser, search, done. Installable for repeat users. |
| **Privacy-First Video** | Video never persists. Uploaded to an ephemeral S3 pipeline, processed, and deleted within the same request lifecycle. No video is ever stored at rest. |
| **Biomechanical Alternatives** | Alternatives are not random suggestions. They are mapped by movement pattern, force vector, and muscle activation — so a "substitute" genuinely replaces the target exercise. |

### 1.5 Edge Cases & Mitigations

| Edge Case | Impact | Mitigation |
|-----------|--------|------------|
| **Ambiguous text description** | Multiple exercises match equally well (e.g., "pulling a cable down" → Lat Pulldown vs. Tricep Pushdown vs. Face Pull) | Return top 3-5 ranked results with per-result `reasoning` explaining why it matched. Let the user disambiguate visually via 3D demos. |
| **Poor gym lighting / video quality** | Pose estimation fails or returns low-confidence landmarks | Backend returns a confidence score per landmark. If mean confidence < threshold (0.5), reject the video gracefully and prompt the user to try a text description instead. |
| **Partial body visibility** | User films from an angle that occludes key joints | Use landmark completeness check — if >30% of required joints are missing, fall back to a partial-match heuristic using visible joints only, with a degraded confidence indicator in the UI. |
| **Compound / unusual exercises** | CrossFit or hybrid movements that combine two patterns (e.g., Thruster = Front Squat + Push Press) | Tag exercises with multiple `MovementPattern` values. The descriptor system already supports `VARIATION_NOTE` categories for compound movements. |
| **Non-exercise movements** | User accidentally captures someone walking or stretching | The classification layer maps pose trajectories to known `MovementPattern` enums. If no pattern matches above a minimum threshold, return a "No exercise detected — try describing it in text" message. |
| **Network latency on gym Wi-Fi** | Slow/unreliable connections in basement gyms | Frontend implements optimistic UI states, chunked video upload with progress indicator, and aggressive response caching. Text search targets < 2s P95. |

---

## 2. System Architecture & Data Flow

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Next.js PWA)                            │
│                           Vercel Edge Network                                │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐    │
│  │  Text Search  │    │ Video Capture │    │  Exercise Detail Page (EDP)  │   │
│  │   Component   │    │  Component    │    │  3D Demo · Muscle Map · Alt  │   │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┬───────────────┘   │
│         │                    │                            │                   │
└─────────┼────────────────────┼────────────────────────────┼───────────────────┘
          │ POST /search/text  │ POST /search/video         │ GET /exercises/{id}
          │                    │                             │
          ▼                    ▼                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY (FastAPI on AWS)                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │                        SEARCH ORCHESTRATOR                         │      │
│  │                                                                    │      │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │      │
│  │  │  Embedding   │───▶│  Vector DB  │───▶│  LLM Re-Ranker     │   │      │
│  │  │  Service     │    │  (ChromaDB) │    │  (Ollama/gemma4)    │   │      │
│  │  │  (nomic)     │    │  kNN top-20 │    │  Score & Reason     │   │      │
│  │  └─────────────┘    └─────────────┘    └──────────┬──────────┘   │      │
│  │                                                    │              │      │
│  │  ┌─────────────┐    ┌─────────────┐               ▼              │      │
│  │  │  Video       │───▶│  Pose       │───▶  Movement Pattern       │      │
│  │  │  Ingest      │    │  Estimation │    Classification           │      │
│  │  │  (S3 ephem.) │    │  (MediaPipe)│    (maps to text query)     │      │
│  │  └─────────────┘    └─────────────┘                              │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌────────────────────────────────┐                                          │
│  │  PostgreSQL (Exercise Taxonomy) │                                         │
│  │  Full relational data store     │                                         │
│  └────────────────────────────────┘                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Text Search Pipeline — Step-by-Step Data Flow

```
Step 1: USER INPUT
  Client sends POST /search/text
  Payload: { "query": "lying on back pushing dumbbells up", "top_k": 5 }

Step 2: QUERY EMBEDDING
  Backend calls Ollama (nomic-embed-text) to embed the query string
  into a 768-dim float vector.
  Latency budget: ~50ms local, ~150ms remote.

Step 3: VECTOR RETRIEVAL
  Embedded query vector is sent to ChromaDB.
  ChromaDB performs cosine-similarity kNN search against all
  pre-embedded MovementDescriptor texts.
  Returns top-20 candidate descriptors with similarity scores.

Step 4: DEDUPLICATION
  Multiple descriptors may belong to the same exercise
  (e.g., "summary" and "execution" for Dumbbell Bench Press).
  Group by exercise_id, keep the highest-scoring descriptor per exercise.
  Reduce to top-10 unique exercises.

Step 5: HYDRATION
  Load full Exercise objects from PostgreSQL for the top-10 candidates.
  Includes: aliases, muscle groups, equipment, movement descriptors.
  Single query with selectin eager loading.

Step 6: LLM RE-RANKING
  Send the user's original query + the 10 candidate exercises
  (with their descriptors) to the Ollama judge model (gemma4:e4b).
  
  System prompt instructs the LLM to act as a biomechanics expert:
  - Evaluate body position match
  - Evaluate force direction match
  - Evaluate equipment match
  - Assign a 0.0–1.0 relevance score per candidate
  - Provide a 1-sentence reasoning string per candidate
  
  Latency budget: ~1-2s.

Step 7: FINAL RANKING & RESPONSE
  Sort candidates by LLM score descending.
  Slice to top_k (default 3).
  Return SearchResponse with ranked results, scores, and reasoning.
  
  Total P95 target: < 3 seconds.
```

### 2.3 Video Search Pipeline — Step-by-Step Data Flow

```
Step 1: VIDEO CAPTURE
  Client uses MediaDevices.getUserMedia() to access rear camera.
  Records 5-15 seconds of video at ≤720p resolution.
  Client-side constraints: maxWidth=1280, maxHeight=720, frameRate ≤ 30.
  Encoded as WebM (VP8/VP9) via MediaRecorder API.

Step 2: UPLOAD (Ephemeral)
  Client requests a pre-signed S3 upload URL from:
    POST /search/video/upload-url
  Client uploads the video blob directly to S3 (multipart, chunked).
  S3 bucket policy: lifecycle rule deletes objects after 5 minutes.
  Bucket is NOT publicly accessible. Pre-signed URL expires in 60 seconds.

Step 3: BACKEND TRIGGER
  After upload completes, client calls:
    POST /search/video
    Payload: { "s3_key": "<key>", "top_k": 5 }

Step 4: POSE ESTIMATION
  Backend downloads the video from S3 into a temporary in-memory buffer.
  Runs MediaPipe Pose (or YOLO-Pose) frame-by-frame:
    - Sample at 3-5 FPS (not every frame — reduces compute by 6-10x).
    - Extract 33 pose landmarks per frame with confidence scores.
    - Discard frames where mean landmark confidence < 0.5.

Step 5: MOVEMENT CLASSIFICATION
  Aggregate pose landmarks across sampled frames into a trajectory.
  Classify the trajectory into one or more MovementPattern enums:
    - Joint angle ranges over time (e.g., elbow extension = push).
    - Body orientation (supine, prone, seated, standing).
    - Plane of movement (sagittal, frontal, transverse).
  
  Classification can use either:
    a) Rule-based heuristics (MVP): angle thresholds per pattern.
    b) Trained classifier (V2): lightweight MLP on landmark sequences.

Step 6: TEXT QUERY SYNTHESIS
  Convert the classified movement pattern into a synthetic text query.
  Example: "standing, vertical push, barbell, shoulder-width grip"
  This query re-enters the Text Search Pipeline at Step 2.

Step 7: CLEANUP
  Backend issues S3 DeleteObject for the video immediately after processing.
  Even if processing fails, the 5-minute lifecycle rule guarantees deletion.
  No video data is logged, cached, or persisted anywhere.

Step 8: RESPONSE
  Same SearchResponse schema as text search.
  Additional metadata field: pose_confidence (float, 0-1).
  
  Total P95 target: < 8 seconds (dominated by pose estimation).
```

### 2.4 Privacy Architecture — Ephemeral Video Handling

```
┌──────────────────────────────────────────────────────────┐
│                  PRIVACY GUARANTEES                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. VIDEO NEVER TOUCHES THE APPLICATION SERVER DISK      │
│     - Uploaded directly from client → S3 via pre-signed  │
│       URL (client-side PUT, no proxy through FastAPI).   │
│     - Backend reads from S3 into memory buffer only.     │
│                                                          │
│  2. AUTOMATIC DELETION — TWO LAYERS                      │
│     - Application layer: explicit DeleteObject after     │
│       processing completes (success or failure).         │
│     - Infrastructure layer: S3 lifecycle rule deletes    │
│       all objects in the ephemeral bucket after 5 min.   │
│                                                          │
│  3. NO LOGGING OF VIDEO CONTENT                          │
│     - Request logs contain s3_key (opaque UUID) only.    │
│     - Pose landmark data (joint coordinates) may be      │
│       logged for debugging but contains no PII.          │
│                                                          │
│  4. TRANSPORT SECURITY                                   │
│     - Pre-signed URLs use HTTPS only.                    │
│     - S3 bucket enforces ssl-only policy.                │
│     - Client ↔ FastAPI communication over TLS.           │
│                                                          │
│  5. NO USER ACCOUNTS REQUIRED FOR SEARCH                 │
│     - Core search functionality is fully anonymous.      │
│     - No cookies, no tracking, no session persistence.   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2.5 Infrastructure Topology

| Component | Host | Scaling Strategy |
|-----------|------|-----------------|
| Next.js Frontend | Vercel (Edge) | Automatic edge CDN; zero-config scaling. |
| FastAPI Backend | AWS ECS Fargate | Horizontal auto-scaling on CPU/memory. Minimum 1 task, max 8. |
| PostgreSQL | AWS RDS (db.t4g.medium) | Single-AZ for MVP, Multi-AZ for V1. Read replicas if needed. |
| ChromaDB | Embedded in FastAPI container (MVP) → Pinecone (V1) | MVP: in-process with persistent volume. V1: migrate to managed Pinecone for durability and scale. |
| Ollama (Embedding + Judge) | AWS EC2 GPU instance (g5.xlarge) or ECS GPU task | Single instance for MVP. For V1, consider managed inference (Bedrock, Replicate) or self-hosted with load balancer. |
| Ephemeral Video Storage | AWS S3 (dedicated bucket) | Lifecycle-managed. No scaling concerns — objects are transient. |
| Pose Estimation | Same ECS task as FastAPI (MVP) → Dedicated GPU worker (V1) | CPU-based MediaPipe for MVP. GPU YOLO-Pose behind SQS queue for V1. |

---

## 3. Database Schema & API Contracts

### 3.1 PostgreSQL Schema — Entity Relationship

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            exercises                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ id              UUID  PK  DEFAULT uuid_generate_v4()                    │
│ primary_name    VARCHAR(128)  UNIQUE  NOT NULL                          │
│ slug            VARCHAR(160)  UNIQUE  NOT NULL  (lowercase, hyphens)    │
│ difficulty      ENUM(beginner, intermediate, advanced, elite)           │
│ mechanic        ENUM(compound, isolation)                               │
│ force_type      ENUM(push, pull, static, hinge, squat, lunge,          │
│                      rotation, anti_rotation)                           │
│ movement_pattern ENUM(horizontal_push, horizontal_pull, vertical_push, │
│                       vertical_pull, squat, hinge, lunge, carry,       │
│                       rotation, anti_rotation, isolation)               │
│ summary         TEXT  NULLABLE                                          │
│ is_unilateral   BOOLEAN  DEFAULT false                                  │
│ created_at      TIMESTAMPTZ  DEFAULT now()                              │
│ updated_at      TIMESTAMPTZ  DEFAULT now()  ON UPDATE now()             │
└────────┬────────────────────────┬──────────────────┬────────────────────┘
         │ 1:N                    │ 1:N              │ 1:N
         ▼                        ▼                  ▼
┌──────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│ exercise_aliases  │  │ exercise_muscle_     │  │ exercise_equipment   │
├──────────────────┤  │ groups               │  ├──────────────────────┤
│ id       UUID PK │  ├─────────────────────┤  │ id       UUID PK     │
│ exercise_id  FK  │  │ id       UUID PK    │  │ exercise_id  FK      │
│ alias  VARCHAR   │  │ exercise_id  FK     │  │ equipment_type ENUM  │
│   (128)          │  │ muscle_group ENUM   │  │                      │
└──────────────────┘  │ is_primary  BOOLEAN │  └──────────────────────┘
                      └─────────────────────┘
         │ 1:N                              │ N:M (self-referential)
         ▼                                  ▼
┌────────────────────────────┐  ┌──────────────────────────────────┐
│ movement_descriptors       │  │ exercise_alternatives             │
├────────────────────────────┤  ├──────────────────────────────────┤
│ id            UUID PK      │  │ id                UUID PK        │
│ exercise_id   FK           │  │ exercise_id       FK → exercises │
│ category      ENUM         │  │ related_id        FK → exercises │
│ text          TEXT          │  │ relationship_type ENUM           │
│ vector_id     VARCHAR(64)  │  │   (progression_of, regression_of │
│ embedding_model VARCHAR(64)│  │    substitute_for, variation_of) │
│ needs_reindex BOOLEAN      │  │ note              TEXT NULLABLE  │
│ created_at    TIMESTAMPTZ  │  └──────────────────────────────────┘
│ updated_at    TIMESTAMPTZ  │
└────────────────────────────┘
```

### 3.2 Enum Definitions (Exhaustive)

**DifficultyLevel:** `beginner` | `intermediate` | `advanced` | `elite`

**MuscleGroup (21 values):**
`chest` · `front_delt` · `side_delt` · `rear_delt` · `triceps` · `lats` · `upper_back` · `traps` · `biceps` · `forearms` · `core` · `abs` · `obliques` · `lower_back` · `quads` · `hamstrings` · `glutes` · `adductors` · `abductors` · `calves` · `hip_flexors`

**EquipmentType (20 values):**
`barbell` · `dumbbell` · `kettlebell` · `ez_curl_bar` · `trap_bar` · `cable` · `machine` · `smith_machine` · `bench` · `incline_bench` · `decline_bench` · `squat_rack` · `pull_up_bar` · `dip_bars` · `preacher_bench` · `resistance_band` · `medicine_ball` · `weight_plate` · `landmine` · `bodyweight`

**MovementPattern (11 values):**
`horizontal_push` · `horizontal_pull` · `vertical_push` · `vertical_pull` · `squat` · `hinge` · `lunge` · `carry` · `rotation` · `anti_rotation` · `isolation`

**MechanicType:** `compound` | `isolation`

**ForceType (8 values):**
`push` · `pull` · `static` · `hinge` · `squat` · `lunge` · `rotation` · `anti_rotation`

**DescriptorCategory (7 values):**
`summary` · `setup` · `execution` · `cue` · `common_mistake` · `variation_note` · `beginner_description`

**AlternativeRelationship:** `progression_of` | `regression_of` | `substitute_for` | `variation_of`

### 3.3 Movement Descriptor Strategy

The `movement_descriptors` table is the backbone of the semantic search system. Each exercise has multiple descriptors across categories, each independently embedded into the vector database.

**Why multiple descriptors per exercise:**  
A single summary cannot capture the many ways a user might describe an exercise. A beginner might say "lying down pushing weights up" (maps to `beginner_description`), a trainer might say "horizontal press with scapular retraction" (maps to `execution`), and someone might describe a common mistake they observed: "elbows flaring out on the bench" (maps to `common_mistake`). Each of these should independently retrieve the correct exercise.

**Embedding strategy:**
- Each descriptor's `text` field is embedded via `nomic-embed-text` (768 dimensions).
- The resulting vector is stored in ChromaDB with the `vector_id` as the key and `exercise_id` as metadata.
- The `needs_reindex` flag tracks when text is modified and the vector is stale.
- The `embedding_model` field enables future model migrations without reindexing everything blindly.

### 3.4 API Contracts

#### 3.4.1 Text Search

```
POST /search/text
Content-Type: application/json

Request:
{
  "query": "lying on my back pushing two dumbbells up",
  "top_k": 5                          // optional, default 3, range [1, 10]
}

Response: 200 OK
{
  "query": "lying on my back pushing two dumbbells up",
  "results": [
    {
      "rank": 1,
      "similarity_score": 0.94,
      "matched_description": "Lie flat on a bench, press two dumbbells upward from chest level to full arm extension.",
      "reasoning": "User describes supine position with bilateral dumbbell pressing — exact match for dumbbell bench press.",
      "exercise": {
        "id": "a1b2c3d4-...",
        "primary_name": "Dumbbell Bench Press",
        "slug": "dumbbell-bench-press",
        "difficulty": "beginner",
        "mechanic": "compound",
        "force_type": "push",
        "movement_pattern": "horizontal_push",
        "summary": "A fundamental horizontal pressing movement...",
        "is_unilateral": false,
        "created_at": "2026-04-22T00:00:00Z",
        "updated_at": "2026-04-22T00:00:00Z",
        "primary_muscles": ["chest", "front_delt", "triceps"],
        "secondary_muscles": ["core"],
        "equipment_required": ["dumbbell", "bench"],
        "aliases": [
          { "id": "...", "alias": "DB Bench" },
          { "id": "...", "alias": "Flat Dumbbell Press" }
        ],
        "movement_descriptors": [
          {
            "id": "...",
            "category": "summary",
            "text": "A fundamental horizontal pressing movement...",
            "vector_id": "vec_abc123",
            "embedding_model": "nomic-embed-text",
            "needs_reindex": false
          }
        ],
        "alternatives_from": [
          {
            "id": "...",
            "relationship_type": "variation_of",
            "related_id": "e5f6g7h8-...",
            "note": "Incline variant targets upper chest more."
          }
        ]
      }
    }
    // ... up to top_k results
  ]
}
```

#### 3.4.2 Video Upload URL

```
POST /search/video/upload-url
Content-Type: application/json

Request:
{
  "content_type": "video/webm",
  "file_size_bytes": 2048000           // enforced max: 50MB
}

Response: 200 OK
{
  "upload_url": "https://s3.amazonaws.com/exercise-id-ephemeral/...",
  "s3_key": "uploads/2026/04/22/abc123-def456.webm",
  "expires_in_seconds": 60
}

Error: 413 Payload Too Large
{
  "detail": "File size exceeds 50MB limit."
}
```

#### 3.4.3 Video Search

```
POST /search/video
Content-Type: application/json

Request:
{
  "s3_key": "uploads/2026/04/22/abc123-def456.webm",
  "top_k": 5
}

Response: 200 OK
{
  "query": "[video] standing, vertical push, barbell",
  "pose_confidence": 0.82,
  "classified_patterns": ["vertical_push"],
  "results": [
    // same SearchResultItem schema as text search
  ]
}

Error: 422 Unprocessable Entity
{
  "detail": "Pose estimation failed: insufficient landmark confidence. Try describing the exercise in text instead."
}
```

#### 3.4.4 Exercise CRUD

```
GET /exercises?page=1&per_page=20&muscle_group=chest&equipment=dumbbell
  → Paginated list of ExerciseSummary objects.
  → Supports filtering by muscle_group, equipment, difficulty, movement_pattern.

GET /exercises/{id}
  → Full ExerciseRead object with all relations.

GET /exercises/slug/{slug}
  → Same as above, resolved by slug for SEO-friendly URLs.

POST /exercises
  → Create new exercise. Body: ExerciseCreate schema.
  → Returns: 201 Created with ExerciseRead.

PATCH /exercises/{id}
  → Partial update. Body: ExerciseUpdate schema.
  → Returns: 200 OK with ExerciseRead.

DELETE /exercises/{id}
  → Soft consideration: this cascades to aliases, descriptors,
    muscle groups, equipment, and alternatives.
  → Returns: 204 No Content.
```

#### 3.4.5 Alternatives Endpoint

```
GET /exercises/{id}/alternatives?equipment=dumbbell,bodyweight
  → Returns alternatives filtered by user's available equipment.
  → Prioritizes: substitute_for > variation_of > regression_of.
  
Response: 200 OK
{
  "exercise_id": "a1b2c3d4-...",
  "available_equipment": ["dumbbell", "bodyweight"],
  "alternatives": [
    {
      "relationship_type": "substitute_for",
      "note": "Similar horizontal push pattern using bodyweight.",
      "exercise": { /* ExerciseSummary */ }
    }
  ]
}
```

#### 3.4.6 Health & Metadata

```
GET /health
  → { "status": "ok", "db": "connected", "vector_db": "connected", "ollama": "reachable" }

GET /meta/enums
  → Returns all enum values for frontend dropdowns/filters.
  → { "muscle_groups": [...], "equipment_types": [...], "difficulties": [...], ... }
```

---

## 4. UI/UX & Frontend Implementation Guidelines

### 4.1 Design Philosophy

**Minimalism as a feature, not an aesthetic choice.** The target user is standing in a gym, possibly mid-workout, with sweaty hands and limited attention. Every pixel that isn't directly answering "what is this exercise?" is a distraction. The interface must communicate the answer in under 3 seconds of visual scanning.

**Design Principles:**
1. **Dark mode only** — no light mode toggle for V1. Gyms are high-contrast environments with overhead lighting; dark UI reduces glare on phone screens.
2. **High contrast** — text on `zinc-950` backgrounds uses `zinc-100` for primary text, `zinc-400` for secondary. Accent color: a single vibrant hue (electric blue `#3B82F6` or emerald `#10B981`) used sparingly for CTAs and active states.
3. **Large touch targets** — minimum 48x48px tap areas. Users may be wearing gloves.
4. **Zero chrome** — no visible navigation bars, hamburger menus, or tab bars. The app is a single-purpose tool: search → results → detail. Back navigation via swipe or a minimal back arrow.
5. **Motion with purpose** — transitions between states (searching → results → detail) use smooth 300ms eases. No decorative animations. Loading states use skeleton screens, never spinners.

### 4.2 Color System (Tailwind)

```typescript
// tailwind.config.ts — extend theme
colors: {
  bg: {
    primary: '#09090b',      // zinc-950 — main background
    elevated: '#18181b',     // zinc-900 — cards, modals
    subtle: '#27272a',       // zinc-800 — hover states, borders
  },
  text: {
    primary: '#f4f4f5',      // zinc-100
    secondary: '#a1a1aa',    // zinc-400
    muted: '#71717a',        // zinc-500
  },
  accent: {
    DEFAULT: '#3B82F6',      // blue-500 — primary accent
    light: '#60A5FA',        // blue-400 — gradients
    glow: 'rgba(59,130,246,0.15)', // glow effects behind cards
  },
  muscle: {
    primary: '#EF4444',      // red-500 — primary muscle highlight
    secondary: '#F97316',    // orange-500 — secondary muscle highlight
  },
  status: {
    success: '#22C55E',      // green-500
    warning: '#EAB308',      // yellow-500
    error: '#EF4444',        // red-500
  }
}
```

### 4.3 Component Architecture (Mobile-First)

```
app/
├── layout.tsx              ← Root layout: dark bg, font loading, PWA meta
├── page.tsx                ← Home: search input (text + video toggle)
├── results/
│   └── page.tsx            ← Search results list (top 3-5 cards)
├── exercise/
│   └── [slug]/
│       └── page.tsx        ← Exercise Detail Page (EDP)
└── globals.css             ← Tailwind base + custom utilities

components/
├── search/
│   ├── SearchBar.tsx       ← Text input with submit, auto-focus on mount
│   ├── VideoCapture.tsx    ← Camera preview + record button + timer
│   └── SearchToggle.tsx    ← Text ↔ Video mode toggle (pill switch)
├── results/
│   ├── ResultCard.tsx      ← Single search result: name, score, reasoning
│   └── ResultSkeleton.tsx  ← Loading skeleton matching ResultCard shape
├── exercise/
│   ├── ExerciseHeader.tsx  ← Name, aliases, difficulty badge, tags
│   ├── FormViewer.tsx      ← 3D avatar embed (iframe or WebGL canvas)
│   ├── MuscleMap.tsx       ← Anatomical highlight (SVG or 3D)
│   ├── EquipmentBadges.tsx ← Equipment tag list
│   └── AlternativesList.tsx← Filtered alternatives with equipment toggle
└── ui/
    ├── Badge.tsx           ← Reusable pill/tag component
    ├── Button.tsx          ← Primary/secondary/ghost variants
    └── Skeleton.tsx        ← Generic skeleton loader
```

### 4.4 Mobile vs. Desktop Layout

**Mobile (< 768px) — Single Column, Full Screen States:**

```
┌─────────────────────────────┐
│  ┌───────────────────────┐  │
│  │      SEARCH INPUT      │  │
│  │   [Text ○ | ● Video]  │  │
│  │   ┌─────────────────┐  │  │
│  │   │  Camera Preview  │  │  │
│  │   │   [ ● Record ]   │  │  │
│  │   └─────────────────┘  │  │
│  └───────────────────────┘  │
│                              │
│  ┌───────────────────────┐  │
│  │  Result 1  ████  0.94  │  │  ← Tap to expand → EDP (full screen)
│  ├───────────────────────┤  │
│  │  Result 2  ███░  0.78  │  │
│  ├───────────────────────┤  │
│  │  Result 3  ██░░  0.65  │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

**Desktop (≥ 1024px) — Split Panel:**

```
┌───────────────────────────┬───────────────────────────────────────┐
│                           │                                       │
│  SEARCH + RESULTS PANEL   │        EXERCISE DETAIL PANEL          │
│  (fixed 400px width)      │        (fluid remaining width)        │
│                           │                                       │
│  ┌─────────────────────┐  │  ┌─────────────────────────────────┐  │
│  │   Search Input       │  │  │  Dumbbell Bench Press           │  │
│  │   [ Text ↔ Video ]   │  │  │  aka: DB Bench, Flat DB Press   │  │
│  └─────────────────────┘  │  │                                   │  │
│                           │  │  ┌─────────────┐ ┌─────────────┐ │  │
│  ┌─────────────────────┐  │  │  │  3D Form    │ │ Muscle Map  │ │  │
│  │ ▸ DB Bench Press 94%│  │  │  │  Demo       │ │ (Anatomy)   │ │  │
│  ├─────────────────────┤  │  │  └─────────────┘ └─────────────┘ │  │
│  │   Barbell Bench  78%│  │  │                                   │  │
│  ├─────────────────────┤  │  │  Equipment: Dumbbell · Bench      │  │
│  │   Push-Up        65%│  │  │  Difficulty: Beginner              │  │
│  └─────────────────────┘  │  │                                   │  │
│                           │  │  Alternatives:                     │  │
│                           │  │  • Barbell Bench Press (variation) │  │
│                           │  │  • Push-Up (bodyweight sub)        │  │
│                           │  └─────────────────────────────────┘  │
└───────────────────────────┴───────────────────────────────────────┘
```

### 4.5 Camera Permission Flow

Browser camera access is the most friction-heavy UX moment. Handle it deliberately:

```
┌──────────────────────────────────────────────────────────────────┐
│  STATE MACHINE: Camera Permission                                │
│                                                                  │
│  1. IDLE (default)                                               │
│     User sees text search. Video toggle is visible but inactive. │
│                                                                  │
│  2. PERMISSION_PROMPT (user taps Video toggle)                   │
│     Before requesting navigator.mediaDevices.getUserMedia():     │
│     Show an in-app explainer overlay:                            │
│     ┌──────────────────────────────────────────────────┐         │
│     │  📷  Camera Access                               │         │
│     │                                                  │         │
│     │  We need camera access to record the exercise    │         │
│     │  you want to identify. Your video is:            │         │
│     │                                                  │         │
│     │  ✓ Never stored — deleted immediately            │         │
│     │  ✓ Never shared — processed on our servers only  │         │
│     │  ✓ Encrypted in transit                          │         │
│     │                                                  │         │
│     │         [ Allow Camera ]    [ Use Text Instead ] │         │
│     └──────────────────────────────────────────────────┘         │
│     Only AFTER user taps "Allow Camera" → trigger getUserMedia.  │
│                                                                  │
│  3. GRANTED                                                      │
│     Camera preview renders in the VideoCapture component.        │
│     Record button + 15-second countdown timer visible.           │
│     Permission is cached by the browser for future visits.       │
│                                                                  │
│  4. DENIED                                                       │
│     If browser permission is denied:                             │
│     - Hide video toggle entirely.                                │
│     - Show subtle toast: "Camera blocked — you can still search  │
│       by describing the exercise."                               │
│     - Do NOT repeatedly prompt. Respect the denial.              │
│                                                                  │
│  5. ERROR (camera in use by another app, hardware failure)       │
│     Show inline error: "Couldn't access camera. Try closing      │
│     other apps using the camera, or describe the exercise."      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.6 Animation & Transition Guidelines

| Transition | Duration | Easing | Implementation |
|-----------|----------|--------|----------------|
| Search → Results | 300ms | `ease-out` | Results cards stagger-fade-in from bottom (50ms delay per card). |
| Results → EDP (mobile) | 250ms | `ease-in-out` | Shared element transition on exercise name. Card expands to full screen. Use `View Transitions API` where supported, CSS fallback otherwise. |
| Results → EDP (desktop) | 200ms | `ease-out` | Right panel crossfades. Selected result card gets accent border. |
| Text ↔ Video toggle | 200ms | `ease-in-out` | Pill slider animates. Input area crossfades. |
| Skeleton → Content | 150ms | `ease-out` | Skeleton pulses at 1.5s interval. Content fades in over skeleton. |
| Camera preview mount | 0ms | N/A | Instant render. No animation on live video feed. |

### 4.7 PWA Configuration

```json
// public/manifest.json
{
  "name": "Exercise Identifier",
  "short_name": "Identify",
  "description": "Identify any exercise by description or video",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#09090b",
  "orientation": "portrait-primary",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

**Service Worker Strategy:**
- Cache the app shell (HTML, CSS, JS bundles) on install.
- API responses (`/search/*`, `/exercises/*`) use network-first with stale-while-revalidate fallback.
- 3D assets and images use cache-first (they don't change between deploys).

---

## 5. Phased Execution Roadmap

### Phase 1 — MVP (Weeks 1-4)

**Goal:** End-to-end text search working. A user can type a description and get accurate exercise results with full detail pages.

| Week | Deliverable | Details |
|------|------------|---------|
| **1** | **Database & Seed Data** | Finalize PostgreSQL schema (already scaffolded). Write seed script to populate 150-200 exercises with complete taxonomy: aliases, muscle groups, equipment, and 3-5 descriptors per exercise across all categories. |
| **1** | **Embedding Pipeline** | Implement `embed_database.py` — iterate all `movement_descriptors`, embed via Ollama `nomic-embed-text`, store in ChromaDB with exercise_id metadata. Track `vector_id` and `needs_reindex`. |
| **2** | **Text Search Backend** | Implement `POST /search/text`: query embedding → ChromaDB kNN → deduplication → PostgreSQL hydration → LLM re-ranking via `gemma4:e4b` → response. Target P95 < 3s. |
| **2** | **Exercise CRUD** | Implement all CRUD endpoints for `/exercises`. Needed for admin tooling and data management. |
| **3** | **Frontend — Search UI** | Build `SearchBar`, `ResultCard`, `ResultSkeleton`. Mobile-first single-column layout. Dark mode. Smooth stagger-fade transitions on results. |
| **3** | **Frontend — EDP** | Build `ExerciseHeader`, `EquipmentBadges`, `AlternativesList`. 3D viewer as a placeholder iframe (static image or Lottie animation until 3D API is integrated). |
| **4** | **Integration & Polish** | Connect frontend ↔ backend. Handle error states (no results, network failure). Implement skeleton loading. Deploy frontend to Vercel, backend to AWS ECS. |
| **4** | **PWA Setup** | Manifest, service worker, icon set, offline shell caching. Test installability on iOS Safari and Android Chrome. |

**MVP Exit Criteria:**
- [ ] User can type a natural-language description and receive 3-5 ranked results in < 3 seconds.
- [ ] Each result links to a detail page with name, aliases, muscles, equipment, difficulty, and alternatives.
- [ ] App is installable as a PWA on mobile.
- [ ] Database contains ≥ 150 exercises with full taxonomy.
- [ ] Backend deployed and accessible from frontend on Vercel.

### Phase 2 — Video Search + Visual Polish (Weeks 5-8)

**Goal:** Add video-based exercise identification. Integrate 3D visual assets. Desktop split-panel layout.

| Week | Deliverable | Details |
|------|------------|---------|
| **5** | **Video Capture Frontend** | Implement `VideoCapture` component: `getUserMedia()` with rear camera preference, `MediaRecorder` for WebM, 15-second max recording, progress timer, permission flow with privacy explainer. |
| **5** | **Ephemeral Upload Pipeline** | S3 bucket with 5-minute lifecycle policy. `POST /search/video/upload-url` returns pre-signed PUT URL. Client uploads directly to S3. |
| **6** | **Pose Estimation Backend** | Implement `services/video.py`: download from S3 → sample frames at 3-5 FPS → run MediaPipe Pose → extract landmarks → confidence filtering → delete from S3. |
| **6** | **Movement Classification** | Rule-based classifier: joint angle ranges + body orientation → `MovementPattern` enum. Synthesize text query from classification → pipe into existing text search. |
| **7** | **3D Visual Integration** | Integrate licensed 3D exercise API (Muscle and Motion or equivalent). `FormViewer` component renders auto-looping 3D avatar. `MuscleMap` component renders anatomical highlight with primary (red) / secondary (orange) glow. |
| **7** | **Desktop Layout** | Implement split-panel layout for ≥ 1024px. Left panel: search + results (fixed 400px). Right panel: EDP (fluid). Shared element transitions. |
| **8** | **Video Pipeline Polish** | Handle edge cases: low confidence → fallback prompt, partial body visibility → degraded results with warning, non-exercise video → "no exercise detected" state. Optimize latency (target P95 < 8s). |

**Phase 2 Exit Criteria:**
- [ ] User can record a 5-15 second video and receive exercise matches.
- [ ] Video is verifiably never stored at rest (S3 lifecycle + explicit delete).
- [ ] 3D avatar demos and muscle maps render on exercise detail pages.
- [ ] Desktop users see a split-panel layout.
- [ ] Video search returns results in < 8 seconds P95.

### Phase 3 — Scale, Optimize & Expand (Weeks 9-12)

**Goal:** Production hardening. Performance optimization. Dataset expansion. User-facing polish features.

| Week | Deliverable | Details |
|------|------------|---------|
| **9** | **Vector DB Migration** | Migrate from embedded ChromaDB to managed Pinecone. Implement batch upsert, namespace isolation, and metadata filtering. Re-embed full dataset. |
| **9** | **Inference Optimization** | Evaluate replacing self-hosted Ollama with managed inference (AWS Bedrock, Replicate) for embedding and re-ranking. Compare latency and cost. |
| **10** | **Dataset Expansion** | Scale exercise database to 500+ exercises. Add niche categories: physical therapy, CrossFit, calisthenics, Olympic lifts. Enrich descriptors with beginner-friendly descriptions and common gym slang aliases. |
| **10** | **Equipment Filter UX** | Add optional "My Equipment" selection on the home screen. Persisted in localStorage. Automatically filters alternatives on EDP. Influences search result ranking (prefer exercises matching available equipment). |
| **11** | **Performance Audit** | Lighthouse audit targeting 95+ on mobile. Bundle analysis and code splitting. Image/asset optimization. Implement `stale-while-revalidate` caching for repeat searches. |
| **11** | **Observability** | Structured logging with correlation IDs. Latency dashboards per pipeline stage. Error rate alerting. Anonymous usage analytics (search volume, video vs. text ratio, top queries). |
| **12** | **Trained Video Classifier** | Replace rule-based movement classifier with lightweight MLP trained on labeled pose sequences. Improve accuracy for ambiguous movements. Evaluate on held-out test set. |
| **12** | **Launch Prep** | Security audit (OWASP top 10). Load testing (target 100 concurrent searches). Documentation cleanup. Staging → production cutover. |

**Phase 3 Exit Criteria:**
- [ ] Lighthouse mobile score ≥ 95.
- [ ] Database contains ≥ 500 exercises.
- [ ] P95 latency: text < 2s, video < 6s.
- [ ] Managed vector DB with durability guarantees.
- [ ] Observability dashboard with search volume, latency, and error metrics.
- [ ] Passed security audit with no critical/high findings.

### 5.1 Technical Bottleneck Analysis & Mitigations

| Bottleneck | Phase | Severity | Mitigation |
|-----------|-------|----------|------------|
| **LLM re-ranking latency** | 1 | High | Gemma4:e4b on CPU takes 2-5s per call. Mitigate: (a) keep candidate list to 10, (b) use structured JSON output mode to avoid parsing overhead, (c) if too slow, fall back to vector-only ranking (no LLM) with a quality trade-off flag. Phase 3: move to GPU inference or managed API. |
| **Pose estimation on CPU** | 2 | High | MediaPipe Pose on CPU processes ~10-15 FPS. With frame sampling at 3 FPS, a 10-second video = 30 frames ≈ 2-3 seconds. Acceptable for MVP. Phase 3: move to GPU worker with YOLO-Pose for 5x speedup. |
| **Cold start latency** | 1-2 | Medium | ECS Fargate cold starts: 10-30 seconds. Mitigate: keep minimum 1 task always running. Ollama model loading on cold start: 5-10 seconds. Mitigate: health check endpoint that pre-loads models on startup. |
| **ChromaDB durability** | 1 | Medium | Embedded ChromaDB stores data on local disk. Container restart = data loss if no persistent volume. Mitigate: mount EBS volume. Phase 3: migrate to Pinecone. |
| **S3 pre-signed URL race condition** | 2 | Low | If user's upload takes > 60 seconds (large video on slow connection), the pre-signed URL expires. Mitigate: client checks elapsed time before upload, re-requests URL if stale. Cap video at 15 seconds / 720p to bound file size. |
| **3D asset loading on slow connections** | 2 | Medium | 3D models can be 2-10MB. Mitigate: lazy-load 3D viewer only when EDP is opened. Show 2D fallback (static image) while loading. Use aggressive caching (cache-first service worker strategy). |

### 5.2 Key Technical Decisions & Rationale

| Decision | Chosen | Rejected | Rationale |
|----------|--------|----------|-----------|
| Vector DB (MVP) | ChromaDB (embedded) | Pinecone, Weaviate | Zero infrastructure cost and complexity for MVP. Runs in-process. Sufficient for < 10K vectors. Migrated to managed solution in Phase 3. |
| Embedding model | nomic-embed-text (768d) | OpenAI ada-002, Cohere embed | Runs locally via Ollama — no API costs, no external dependency, no data leaving the infrastructure. Quality is competitive for domain-specific retrieval. |
| Re-ranking model | gemma4:e4b via Ollama | GPT-4o, Claude | Same rationale: local inference, zero per-query cost, no data egress. Gemma4 is strong at structured evaluation tasks. Fallback path exists (vector-only ranking). |
| Pose estimation (MVP) | MediaPipe Pose | YOLO-Pose, MoveNet | MediaPipe runs on CPU with acceptable latency for sampled frames. No GPU required for MVP. Lighter deployment footprint. |
| Video upload strategy | Pre-signed S3 URL (direct upload) | Multipart through FastAPI | Keeps video bytes off the application server entirely. Reduces backend memory pressure and attack surface. S3 handles chunked upload natively. |
| Frontend framework | Next.js App Router | Remix, SvelteKit | Team expertise, Vercel-native deployment, React ecosystem maturity. App Router provides server components for SEO and RSC streaming for initial load performance. |
| Styling | Tailwind CSS | CSS Modules, Styled Components | Utility-first approach matches the rapid iteration needed. Purges unused styles for minimal bundle. Dark mode via class strategy. |

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **EDP** | Exercise Detail Page — the full information view for a single exercise. |
| **RAG** | Retrieval-Augmented Generation — architecture where a retrieval step (vector search) precedes an LLM generation/evaluation step. |
| **kNN** | k-Nearest Neighbors — the vector similarity search algorithm used to find the closest embeddings. |
| **Descriptor** | A text passage describing an aspect of an exercise (summary, setup, execution cues, common mistakes). Each descriptor is independently embedded and searchable. |
| **Ephemeral** | Data that exists only for the duration of processing and is guaranteed to be deleted afterward. |
| **Movement Pattern** | A biomechanical classification of how the body moves (e.g., horizontal push, vertical pull, hinge). |
| **Force Type** | The direction of force application in an exercise (push, pull, static, etc.). |
| **Mechanic** | Whether an exercise involves multiple joints (compound) or a single joint (isolation). |

## Appendix B: File Structure Reference

```
exercise-identifier/
├── CLAUDE.md                          # Development guidelines
├── docs/
│   └── PRD.md                         # This document
├── backend/
│   ├── main.py                        # FastAPI application entry point
│   ├── requirements.txt               # Python dependencies
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic settings (DB, Ollama, ChromaDB)
│   │   │   └── database.py            # Async SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── enums.py               # All enum definitions
│   │   │   └── exercise.py            # SQLAlchemy ORM models (6 tables)
│   │   ├── routers/
│   │   │   ├── exercises.py           # CRUD endpoints
│   │   │   └── search.py             # Text + video search endpoints
│   │   ├── schemas/
│   │   │   └── exercise.py            # Pydantic request/response schemas
│   │   └── services/
│   │       ├── embedding.py           # Vector embedding + ChromaDB retrieval
│   │       ├── reranker.py            # LLM re-ranking via Ollama
│   │       └── video.py              # Pose estimation + movement classification
│   ├── scripts/
│   │   ├── generate_dataset.py        # Exercise seed data generator
│   │   └── embed_database.py          # Batch embedding pipeline
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout (dark mode, fonts, PWA meta)
│   │   ├── page.tsx                   # Home (search)
│   │   ├── globals.css                # Tailwind base + custom properties
│   │   ├── results/page.tsx           # Search results
│   │   └── exercise/[slug]/page.tsx   # Exercise detail page
│   ├── components/
│   │   ├── search/                    # SearchBar, VideoCapture, SearchToggle
│   │   ├── results/                   # ResultCard, ResultSkeleton
│   │   ├── exercise/                  # Header, FormViewer, MuscleMap, etc.
│   │   └── ui/                        # Badge, Button, Skeleton
│   ├── hooks/                         # useCamera, useSearch, useMediaRecorder
│   ├── lib/
│   │   ├── api.ts                     # Typed API client
│   │   └── types.ts                   # TypeScript interfaces
│   ├── public/
│   │   ├── manifest.json              # PWA manifest
│   │   └── icons/                     # App icons (192, 512, maskable)
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   └── package.json
└── infrastructure/                    # (Phase 2+) IaC for AWS resources
    ├── ecs-task-definition.json
    ├── s3-lifecycle-policy.json
    └── rds-config.tf
```

---

## 6. As-Built Implementation Log

This section records the actual implementation decisions made during development, including deviations from the PRD spec and the rationale behind them. Updated after each development session.

---

### 6.1 Phase 1 — Frontend Initialization (2026-04-23)

**PRD Reference:** Section 4 (UI/UX), Section 5 Phase 1 Week 1

#### Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `frontend/package.json` | Modified | Added `@ducanh2912/next-pwa ^10.2.9` (runtime dep) and `sharp ^0.33.5` (devDep for icon generation) |
| `frontend/next.config.mjs` | Replaced | Full PWA configuration with `withPWA` wrapper, 5 runtime cache strategies, dev-mode bypass |
| `frontend/public/manifest.json` | Replaced | Full W3C Web App Manifest with `id`, `scope`, `display_override`, `orientation`, `shortcuts`, `screenshots` stubs |
| `frontend/public/icons/icon.svg` | Created | Barbell-mark SVG icon — scalable source of truth for all generated PNG variants |
| `frontend/scripts/generate-icons.mjs` | Created | Node.js script using `sharp` to produce all 6 required PNG icon sizes from the SVG |
| `frontend/app/layout.tsx` | Replaced | Apple PWA meta tags, `Viewport` export, font preload, icon declarations, OG/Twitter cards |
| `frontend/tailwind.config.ts` | Replaced | Expanded token system: `surface`, `accent`, `match`, `muscle`, `status`, `badge-*` classes, 5 new keyframes, shadow scale, z-index scale |
| `frontend/app/globals.css` | Replaced | Restructured with `@layer components` and `@layer utilities`. Added: skeleton, glassmorphism, camera, recording indicator, touch-target, safe-area, no-scrollbar, text-gradient utilities |
| `.gitignore` | Modified | Added entries for generated SW artifacts (`sw.js`, `workbox-*.js`) and generated PNG icons |

#### Architectural Decisions & Deviations

**1. PWA Library: `@ducanh2912/next-pwa` instead of `next-pwa`**

The original `next-pwa` package (by shadowwalker) is effectively unmaintained and incompatible with Next.js 14 App Router without significant workarounds. `@ducanh2912/next-pwa` is its actively maintained fork, with explicit App Router support and Workbox 7 integration. This is a transparent upgrade, not a departure from intent.

**2. Accent color: Indigo `#6366f1` vs. PRD-specified Blue `#3B82F6`**

The PRD specified `#3B82F6` (blue-500) as the accent color. The existing scaffold used `#6366f1` (indigo-500), which was validated as superior for the following reasons:
- Indigo has better perceptual separation from the near-neutral dark backgrounds (`#09090b`) than pure blue.
- Indigo's purple shift creates a more premium, "technology-forward" aesthetic consistent with the minimalist gym-tech positioning.
- The glow effect (`rgba(99,102,241,0.15)`) at dark backgrounds reads as a cool-violet halo rather than a primary-color blue — more distinctive.

**Decision:** Keep indigo as the accent. PRD color spec updated to reflect as-built reality.

**3. Icons are build artifacts, not tracked in git**

PNG icons are generated from `icon.svg` via `scripts/generate-icons.mjs`. The SVG is the canonical source and is tracked. PNG outputs are excluded via `.gitignore`. This keeps the repo lean and ensures icons are always regenerated from the correct source rather than going stale.

**Action required:** After running `npm install`, run `node scripts/generate-icons.mjs` to produce the icon PNGs before building. This step should be added to CI.

**4. Apple splash screens declared but not yet generated**

`layout.tsx` declares Apple startup image media queries for 3 iPhone sizes. The actual PNG files (`/splash/*.png`) do not yet exist. The browser gracefully ignores missing splash images — this causes no build or runtime error. Splash images will be generated in a later session using `sharp` with the same pattern as icons.

**5. `userScalable: false` in Viewport config**

The PRD specifies `maximumScale: 1` to prevent iOS auto-zoom on input focus. We also set `userScalable: false` explicitly. This is intentional for the gym context (no pinch-to-zoom needed, prevents accidental zoom mid-workout) and is acceptable for a single-purpose utility PWA.

#### Service Worker Cache Strategy Rationale

| Route Pattern | Strategy | Reason |
|---------------|----------|--------|
| `/search/*` | NetworkFirst, 5min TTL | Search results should always be fresh. Stale cache is only used if the network request times out (10s). |
| `/exercises/*` | StaleWhileRevalidate, 1hr TTL | Exercise data changes infrequently. Stale data is immediately usable while a revalidation happens in the background. Allows the EDP to load instantly on repeat visits. |
| Google Fonts stylesheets | StaleWhileRevalidate | Font CSS references versioned file paths. Stale is safe. |
| Google Fonts files | CacheFirst, 1yr TTL | Font files are immutable (content-addressed URLs). Never changes once cached. |
| Images / icons | CacheFirst, 30d TTL | Static assets don't change between deploys. |

#### What Remains for Frontend Init Completion

- [ ] Run `npm install` and `node scripts/generate-icons.mjs` (requires Node environment)
- [ ] Generate Apple splash screen PNGs for `/public/splash/`
- [ ] Add `generate-icons` as a `postinstall` npm script or CI step
- [ ] Verify PWA install prompt on Chrome Android and Safari iOS

---

---

### 6.2 Phase 1 — Text Search Backend (2026-04-23)

**PRD Reference:** Section 3.4 (API Contracts), Section 5 Phase 1 Weeks 1-2

#### Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/requirements.txt` | Modified | Added `tenacity ^9.0.0` (retry logic), `aiofiles ^24.1.0` (async file I/O), `python-multipart ^0.0.12` (file uploads, Phase 2 prep) |
| `backend/app/core/config.py` | Replaced | Added `cors_origins: list[str]` (env-configurable), `ollama_judge_timeout: float`, `ollama_embed_timeout: float`, `api_version`, `debug` flag, AWS section stubs |
| `backend/main.py` | Replaced | Real lifespan with ChromaDB init + Ollama import check; CORS from settings; `/health` with per-dependency status; `/meta/enums` for frontend dropdowns |
| `backend/app/schemas/exercise.py` | Modified | Added `PaginatedExerciseList`, `AlternativeMatch`, `AlternativesResponse`; added `pose_confidence` and `classified_patterns` fields to `SearchResponse`; strengthened `ExerciseSummary` with `primary_muscles` and `equipment_required` |
| `backend/app/services/embedding.py` | Replaced | Full implementation: `get_chroma_collection()` singleton, `embed_query()` with retry + timeout, `search_similar()` with deduplication and cosine-distance-to-similarity conversion |
| `backend/app/services/reranker.py` | Replaced | Full implementation: `_build_prompt()` (biomechanics judge prompt), `rerank_candidates()` with JSON parsing + 3-layer fallback, `_vector_fallback()` |
| `backend/app/routers/search.py` | Replaced | Full `POST /search/text` pipeline (4 stages); `POST /search/video` and `POST /search/video/upload-url` as 501 stubs with Phase 2 docs |
| `backend/app/routers/exercises.py` | Replaced | Full async CRUD: `GET /exercises` (paginated + filtered), `GET /exercises/{id}`, `GET /exercises/slug/{slug}`, `POST /exercises`, `PATCH /exercises/{id}`, `DELETE /exercises/{id}`, `GET /exercises/{id}/alternatives` (equipment-filtered) |
| `backend/scripts/embed_database.py` | Replaced | Full async batch pipeline with `--all`, `--dry-run` flags; batch size 50; ChromaDB upsert + PostgreSQL commit per batch; progress bar via `tqdm` |

#### Architectural Decisions & Deviations

**1. Cosine distance → similarity conversion formula**

ChromaDB's cosine space stores `distance = 1 - cosine_similarity`. For normalized vectors (which `nomic-embed-text` produces), cosine_similarity ∈ [-1, 1], so distance ∈ [0, 2]. The correct conversion is `similarity = 1.0 - distance`, clamped to [0, 1]. We do NOT divide by 2 — for high-quality text embeddings, cosine_similarity is always positive, keeping distance < 1.0 and similarity > 0.

**2. LLM re-ranking: timeout = 8 seconds, fallback always fires**

The judge model (gemma4:e4b) is non-blocking from the user's perspective — the fallback kicks in silently if it times out. The `reasoning` field in the response signals which path was taken: `"Ranked by semantic similarity (AI re-ranking unavailable)."` vs. a real biomechanical explanation. The frontend can optionally show a subtle indicator.

**3. `asyncio.wait_for` wraps Ollama calls, NOT tenacity**

`tenacity` is used for embedding retries (transient network errors). LLM re-ranking uses `asyncio.wait_for` with a hard deadline instead of retries — retrying a slow LLM call would compound the latency problem. For embedding, a brief retry is worthwhile (Ollama occasionally hiccups on cold calls); for re-ranking, it's not.

**4. `/exercises/slug/{slug}` defined before `/{id}` in the router**

FastAPI resolves path parameters in definition order. If `/{id}` is defined first, the string "slug" would be parsed as a UUID and cause a 422 error. The slug route is always defined first in the router file.

**5. `needs_reindex=True` on all newly created descriptors**

Every `MovementDescriptor` created via `POST /exercises` is flagged for re-embedding. `embed_database.py` processes all `needs_reindex=True` rows. This creates an explicit, auditable sync boundary between the relational DB and the vector index — no silent divergence.

**6. Equipment filter uses `required.issubset(available)` logic**

An alternative is included only if the user has ALL of the required equipment, not just some. A user without a bench cannot do Bench Press even if they have dumbbells. Exception: exercises with no equipment (bodyweight) are always included. This is the correct biomechanical behaviour.

#### Text Search — Confirmed API Contract (As-Built)

```
POST /search/text
Content-Type: application/json

Request:
{ "query": "lying on my back pushing two dumbbells up", "top_k": 3 }

Response: 200 OK
{
  "query": "lying on my back pushing two dumbbells up",
  "pose_confidence": null,
  "classified_patterns": null,
  "results": [
    {
      "rank": 1,
      "similarity_score": 0.93,
      "matched_description": "...",
      "reasoning": "Matches supine dumbbell pressing with bilateral chest activation.",
      "exercise": { /* full ExerciseRead */ }
    }
  ]
}

Error responses:
  503 — Ollama embedding service unreachable
  (LLM re-ranking failure is silent — fallback fires, response is still 200)
```

#### Acceptance Criteria — Text Search

- [ ] `python -m scripts.embed_database` successfully embeds all MovementDescriptors and updates `vector_id`, `embedding_model`, `needs_reindex=False` in PostgreSQL
- [ ] `POST /search/text` returns `SearchResponse` with ≥1 result for a valid query
- [ ] P95 latency with LLM re-ranking: < 4 seconds on local hardware
- [ ] P95 latency with fallback (LLM off): < 500ms
- [ ] `GET /health` reports all dependencies healthy when running
- [ ] All CRUD endpoints return correct status codes (201 create, 204 delete, 409 conflict, 404 not found)

---

---

### 6.3 Phase 1 — Data Generation & Frontend Search UI (2026-04-23)

**PRD Reference:** Section 4 (UI/UX), Section 5 Phase 1 Weeks 3-4

#### Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/scripts/generate_dataset.py` | Replaced | 150-exercise taxonomy (hardcoded, accurate) + LLM descriptor generation via `gemma4:e4b`. Idempotent (slug-based deduplication). `--dry-run` and `--skip-existing` flags. |
| `frontend/lib/types.ts` | Replaced | Full TypeScript types for all API contracts: `Exercise`, `ExerciseSummary`, `SearchResultItem`, `SearchResponse`, `PaginatedExerciseList`, `AlternativeMatch`, `AlternativesResponse`. Added `scoreToColor()` utility. |
| `frontend/lib/api.ts` | Replaced | `NEXT_PUBLIC_API_URL` env var support; typed `apiFetch<T>` wrapper; `ApiError` class with `status` + `detail`; `searchExercises()` function. |
| `frontend/lib/utils.ts` | Created | Minimal `cn()` class-name merge utility. |
| `frontend/hooks/useSearch.ts` | Created | `useSearch(topK)` hook: manages query/results/state/error. Request-cancellation guard via incrementing `reqIdRef`. |
| `frontend/components/ui/Skeleton.tsx` | Created | Base shimmer block using `.skeleton` CSS class from globals.css. |
| `frontend/components/search/SearchBar.tsx` | Created | Controlled input, auto-focus, Enter/button submit, clear button, min-length hint, `touch-target` compliance, disabled during loading. |
| `frontend/components/results/ResultCard.tsx` | Created | Animated SVG confidence ring (stroke-dashoffset driven by score), difficulty badge, muscle pills, reasoning text, Framer Motion stagger entrance. |
| `frontend/components/results/ResultSkeleton.tsx` | Created | Mirrors ResultCard layout exactly with shimmer Skeleton blocks. |
| `frontend/app/page.tsx` | Replaced | Composes all components. Hero section with example prompts (animates out on first search). `aria-live` region for screen readers. |

#### Architectural Decisions

**1. Taxonomy hardcoded, descriptions LLM-generated**

The 150-exercise taxonomy (muscles, equipment, difficulty, movement pattern) is hardcoded in the script. LLM output for structured factual data is unreliable — it would produce invalid enum values and incorrect muscle assignments. The LLM is used exclusively for `beginner_description` texts (4 per exercise), `cue` (2 per exercise), `summary` (1), and `common_mistake` (1) — the subjective/linguistic content where diversity and colloquial language are the goal.

**2. `ExDef` dataclass is the single source of truth for taxonomy**

Each entry in `EXERCISES` is one `ExDef` instance. This serves as documentation, test fixture, and seed source simultaneously. Adding an exercise means adding one line; changing its muscles means changing one field.

**3. Descriptor-to-category mapping**

| LLM field | `DescriptorCategory` | Count per exercise | Search value |
|-----------|---------------------|-------------------|--------------|
| `summary` | `SUMMARY` | 1 | Technical reference |
| `beginner_descriptions` | `BEGINNER_DESCRIPTION` | 4 | **Primary search target** — matches how users actually search |
| `cues` | `CUE` | 2 | Matches coach/trainer queries |
| `common_mistake` | `COMMON_MISTAKE` | 1 | Matches "why does X hurt" style queries |

The 4 `beginner_descriptions` per exercise are the engine of the search system. A single exercise generates 4 independent embedding vectors representing 4 different colloquial phrasings — dramatically increasing recall for ambiguous queries.

Total embeddings at full dataset: **150 × 8 = 1,200 vectors**.

**4. Results on home page, not a separate `/results` route**

The PRD proposed a `/results/page.tsx` route. After architectural review, results are rendered on the home page below the search bar. Reasons:
- No URL state management needed (query params, back-navigation edge cases)
- Faster perceived performance — no page navigation latency
- Matches the "Shazam" mental model: search → results → select (single screen)
- Desktop split-panel layout (Phase 2) is impossible with a separate results route

The EDP (`/exercise/[slug]`) remains a separate page for deep linking and sharing.

**5. Request cancellation in `useSearch`**

`reqIdRef` is an incrementing integer. Each call to `search()` captures the current value and increments it. When the response arrives, it checks if its ID still matches the current value — if not, the response is silently discarded. This prevents a slow first request from overwriting a fast second request's results.

**6. Hero section animate-out on first search**

The `AnimatePresence` + `exit={{ height: 0 }}` pattern collapses the hero section (brand mark + example prompts) as soon as the user submits a search. The SearchBar smoothly slides to the top of the viewport. On desktop (Phase 2 split panel), this transition won't apply — the search stays in the left panel.

**7. Example prompts as semantic test cases**

The 4 example prompts on the home page are not random — they're carefully chosen to test the search system's semantic understanding:
- Dumbbell Bench Press (supine, bilateral push, equipment specified)
- Lat Pulldown (seated, vertical pull, machine)
- Upright Row (standing, vertical pull, narrow grip — disambiguates from other rows)
- Barbell Row (hinged, horizontal pull)

Clicking a prompt fires a real search — useful for demos and onboarding.

#### Frontend Component Structure — As-Built

```
frontend/
├── app/
│   └── page.tsx                     ← Home: hero + SearchBar + results
├── components/
│   ├── search/
│   │   └── SearchBar.tsx            ← Input, submit, clear, auto-focus
│   ├── results/
│   │   ├── ResultCard.tsx           ← SVG ring, muscles, reasoning, navigation
│   │   └── ResultSkeleton.tsx       ← Shimmer placeholder (3× shown while loading)
│   └── ui/
│       └── Skeleton.tsx             ← Base shimmer block
├── hooks/
│   └── useSearch.ts                 ← Search lifecycle state, request cancellation
└── lib/
    ├── api.ts                       ← apiFetch wrapper, ApiError, searchExercises()
    ├── types.ts                     ← All TypeScript types (mirrors backend schemas)
    └── utils.ts                     ← cn() class-name utility
```

#### Run Order for First Working Demo

```bash
# 1. Start PostgreSQL
# 2. Start Ollama with required models
ollama pull nomic-embed-text
ollama pull gemma4:e4b

# 3. Start FastAPI (creates tables on first run via SQLAlchemy)
cd backend && uvicorn main:app --reload

# 4. Seed the database with 150 exercises + LLM descriptions
python -m scripts.generate_dataset

# 5. Embed all descriptors into ChromaDB
python -m scripts.embed_database

# 6. Start Next.js frontend
cd frontend && npm install && npm run dev

# 7. Open http://localhost:3000
# → Type "lying on bench pushing dumbbells up"
# → Should return Dumbbell Bench Press as #1
```

---

---

### 6.4 Phase 1 — EDP Components (2026-04-22)

**PRD Reference:** Section 4 (UI/UX), Section 5 Phase 1 Week 4

#### Files Created

| File | Action | Description |
|------|--------|-------------|
| `frontend/components/exercise/ExerciseHeader.tsx` | Created | Exercise name, aliases, difficulty badge, mechanic/movement badges, unilateral indicator, equipment pills. Framer Motion staggered entrance (60ms between children). |
| `frontend/components/exercise/MuscleMap.tsx` | Created | SVG anatomical front/back view with tab toggle. 37 muscle zones mapped to SVG ellipses/rects at `viewBox="0 0 120 290"`. Primary (red #ef4444) / secondary (orange #f97316) glow via `feGaussianBlur` filter. Inactive zones at `rgba(255,255,255,0.04)`. |
| `frontend/components/exercise/FormViewer.tsx` | Created | Phase 2 3D avatar placeholder (`.model-placeholder` CSS class). Text cues grouped by category: setup → execution → cue → common_mistake. Each cue is a glass card list item. |
| `frontend/components/exercise/AlternativesList.tsx` | Created | Horizontal scroll (`overflow-x-auto no-scrollbar -mx-4 px-4`) with 208px fixed-width cards. Relationship badge colors: substitute_for → accent, variation_of → neutral, progression_of → amber, regression_of → orange. Skeleton loading state (3 cards). |

#### Prop Interfaces

```typescript
// ExerciseHeader.tsx
interface ExerciseHeaderProps {
  primaryName: string;
  aliases: ExerciseAlias[];
  difficulty: DifficultyLevel;
  mechanic: "compound" | "isolation";
  movementPattern: MovementPattern;
  isUnilateral: boolean;
  equipmentRequired: EquipmentType[];
}

// MuscleMap.tsx
interface MuscleMapProps {
  primaryMuscles: MuscleGroup[];
  secondaryMuscles: MuscleGroup[];
}

// FormViewer.tsx
interface FormViewerProps {
  exerciseName: string;
  descriptors: MovementDescriptor[];
}

// AlternativesList.tsx
interface AlternativesListProps {
  alternatives: AlternativeMatch[];
  isLoading?: boolean;
}
```

#### Architectural Decisions

**1. MuscleMap — SVG zones not SVG masks**

Implemented as positioned `<ellipse>` and `<rect>` elements rather than SVG `<clipPath>` masks on a body photograph. This is simpler to maintain, renders well at all pixel densities, and avoids licensing a body image asset. The body silhouette is a single `<path>` derived from a simplified human outline.

**2. MuscleMap — zones array over a lookup table**

Each `Zone` record carries its muscles list, view, and shape parameters in a flat array rather than a `Record<MuscleGroup, ShapeParams>`. A single muscle (e.g., `calves`) maps to 4 zones (front/back × left/right). The array makes bilateral and multi-region muscles trivial to express.

**3. FormViewer — category ordering is fixed, not data-driven**

The `CUE_CATEGORIES` array (`setup → execution → cue → common_mistake`) determines display order regardless of database insertion order. This ensures a consistent reading flow: learn the setup before execution details.

**4. AlternativesList — `isLoading` prop over suspense**

The component accepts an explicit `isLoading` boolean rather than wrapping in `<Suspense>`. This matches the pattern established by `ResultSkeleton` in Phase 6.3, and allows the parent page to control loading state without needing a separate skeleton wrapper component.

**5. Page assembly deferred**

`app/exercise/[slug]/page.tsx` is NOT yet created. The 4 components are complete, isolated, and prop-typed. Assembly is the next step and requires confirming the `getExercise(slug)` API function in `lib/api.ts`.

#### Frontend Component Structure — As-Built

```
frontend/components/
├── exercise/
│   ├── ExerciseHeader.tsx     ← Name, badges, aliases, equipment
│   ├── MuscleMap.tsx          ← SVG anatomical front/back tab view
│   ├── FormViewer.tsx         ← Phase 2 placeholder + text cues
│   └── AlternativesList.tsx   ← Horizontal swipe cards
├── results/
│   ├── ResultCard.tsx
│   └── ResultSkeleton.tsx
├── search/
│   └── SearchBar.tsx
└── ui/
    └── Skeleton.tsx
```

---

### 6.5 Phase 1 — EDP Page Assembly (2026-04-23)

**PRD Reference:** Section 4 (UI/UX), Section 5 Phase 1 Week 4  
**Status: COMPLETE — Phase 1 (Core Text Search MVP) is now Feature-Complete**

#### Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `frontend/lib/api.ts` | Modified | Added `getExercise(slug)` → `GET /exercises/slug/{slug}` and `getAlternatives(exerciseId, equipment[])` → `GET /exercises/{id}/alternatives`. Equipment list serialised as repeated query params. |
| `frontend/app/exercise/[slug]/page.tsx` | Created | Full EDP client component. Two-stage data fetching. Segmented control (Form / Anatomy). AnimatePresence tab transitions. Back navigation. Page-level loading spinner and error state. |

#### Architectural Decisions

**1. Segmented control: sliding `layoutId` pill, not CSS `left` animation**

The active indicator is a `<motion.span layoutId="tab-pill">` rendered only inside the active button. Framer Motion's shared layout animation (`layoutId`) automatically detects the element moving between the two button slots and interpolates position/size via a spring. No manual `left` calculation needed — the pill follows the DOM element naturally.

Spring config: `stiffness: 420, damping: 36` — snappy enough to feel instant but physically plausible.

**2. Two-stage data fetch with non-fatal alternatives**

Stage 1 (`getExercise`) is blocking — the page cannot render without the exercise data. A failure here shows `PageError`. Stage 2 (`getAlternatives`) is parallel and non-fatal — if it fails, `altLoading` drops to `false` and `AlternativesList` hides (returns `null` when `alternatives.length === 0 && !isLoading`). The main page content is unaffected.

**3. `fetchedSlug` ref guards against React StrictMode double-fetch**

In development, `useEffect` runs twice (React StrictMode). A `useRef` that tracks the last fetched slug prevents the second invocation from firing a redundant network request. The `cancelled` flag inside the effect handles in-flight cleanup on unmount.

**4. `AnimatePresence mode="wait"` for tab transitions**

`mode="wait"` ensures the exiting panel fully fades out (150ms) before the entering panel fades in. This prevents both views rendering simultaneously, which would cause layout shift in the muscle map SVG.

**5. Alternatives load independently — no `Suspense` boundary**

`altLoading` is a separate boolean from `pageState`. The exercise header and segmented control render immediately once the exercise data arrives; the `AlternativesList` shows skeleton cards while alternatives are still in flight. This matches the "progressive reveal" pattern established by the home page's staggered `ResultCard` entrance.

**6. Back navigation via `router.back()`**

Uses `router.back()` rather than `router.push("/")` to preserve search results and scroll position. If the user arrived from a direct link (no history entry), `back()` will navigate to the browser's previous page — acceptable for a PWA where most traffic arrives from within the app.

#### Final Frontend Component Tree — Phase 1 Complete

```
frontend/
├── app/
│   ├── layout.tsx                         ← Root layout: PWA metadata, Inter font
│   ├── page.tsx                           ← Home: hero → SearchBar → ResultCards
│   └── exercise/
│       └── [slug]/
│           └── page.tsx                   ← EDP: Header + SegmentedControl + FormViewer|MuscleMap + Alternatives
├── components/
│   ├── exercise/
│   │   ├── ExerciseHeader.tsx             ← Name, badges, aliases, equipment
│   │   ├── MuscleMap.tsx                  ← SVG anatomical front/back tab
│   │   ├── FormViewer.tsx                 ← Phase 2 placeholder + text cues
│   │   └── AlternativesList.tsx           ← Horizontal swipe cards
│   ├── results/
│   │   ├── ResultCard.tsx                 ← SVG confidence ring, stagger entrance
│   │   └── ResultSkeleton.tsx             ← Shimmer placeholder (×3 while loading)
│   ├── search/
│   │   └── SearchBar.tsx                  ← Input, submit, clear, auto-focus
│   └── ui/
│       └── Skeleton.tsx                   ← Base shimmer block
├── hooks/
│   └── useSearch.ts                       ← Search lifecycle state, request cancellation
└── lib/
    ├── api.ts                             ← apiFetch, ApiError, searchExercises, getExercise, getAlternatives
    ├── types.ts                           ← All TypeScript types (mirrors backend schemas)
    └── utils.ts                           ← cn() class-name utility
```

#### Phase 1 Feature-Complete Checklist

| Feature | Status |
|---------|--------|
| PWA manifest + icons + service worker | ✅ Complete |
| Dark-mode Tailwind token system | ✅ Complete |
| Natural language text search (semantic RAG) | ✅ Complete |
| LLM re-ranker with vector fallback | ✅ Complete |
| 150-exercise database with embeddings | ✅ Complete |
| Search results page with confidence rings | ✅ Complete |
| Exercise Detail Page (EDP) | ✅ Complete |
| Segmented control (Form / Anatomy toggle) | ✅ Complete |
| SVG muscle anatomy map (front/back) | ✅ Complete |
| Form cues from movement descriptors | ✅ Complete |
| Alternatives horizontal scroll | ✅ Complete |
| Mobile-first layout + safe-area insets | ✅ Complete |

### Next Development Target

**Phase 2, Step 1: Video Capture & Pose Identification**

1. **`app/capture/page.tsx`** — Camera UI using `MediaDevices.getUserMedia()`. Record button, countdown, preview. 5–15s clip limit.
2. **`backend/app/routers/video.py`** — `POST /search/video` endpoint receiving multipart form data. Ephemeral storage (deleted after processing).
3. **`backend/app/services/pose.py`** — MediaPipe or YOLO-Pose inference service. Returns detected movement pattern + confidence.
4. **Desktop split-panel layout** — Detect viewport ≥ 768px and render search + EDP side-by-side without page navigation.
