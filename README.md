# ASIOE — Adaptive Skill Intelligence & Optimization Engine

> **Production-grade AI system for personalized corporate onboarding.**  
> Parses candidate capabilities, constructs a skill knowledge graph, and generates deterministic, explainable learning paths using graph algorithms.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         ASIOE System                            │
│                                                                 │
│  ┌──────────┐    ┌──────────────────────────────────────────┐   │
│  │ React UI │───▶│              FastAPI Backend             │   │
│  │  Vite    │    │                                          │   │
│  └──────────┘    │  ┌──────────┐  ┌──────────────────────┐ │   │
│                  │  │ Parsing  │  │  Skill Normalization  │ │   │
│                  │  │ Engine   │  │  Engine (SBERT)       │ │   │
│                  │  └────┬─────┘  └──────────┬───────────┘ │   │
│                  │       │                   │             │   │
│                  │  ┌────▼─────────────────▼──────────┐   │   │
│                  │  │     Skill Graph Engine (Neo4j)   │   │   │
│                  │  │     DAG: prerequisites + domains  │   │   │
│                  │  └────────────────┬─────────────────┘   │   │
│                  │                  │                      │   │
│                  │  ┌───────────────▼──────────────────┐   │   │
│                  │  │     Gap Analysis Engine           │   │   │
│                  │  │     cosine similarity + domains   │   │   │
│                  │  └───────────────┬──────────────────┘   │   │
│                  │                  │                      │   │
│                  │  ┌───────────────▼──────────────────┐   │   │
│                  │  │   Adaptive Path Engine            │   │   │
│                  │  │   Topological DFS + multi-factor  │   │   │
│                  │  │   ranking on NetworkX DiGraph     │   │   │
│                  │  └───────────────┬──────────────────┘   │   │
│                  │                  │                      │   │
│                  │  ┌───────────────▼──────────────────┐   │   │
│                  │  │   RAG Engine (FAISS)              │   │   │
│                  │  │   Course retrieval + reranking    │   │   │
│                  │  └───────────────┬──────────────────┘   │   │
│                  │                  │                      │   │
│                  │  ┌───────────────▼──────────────────┐   │   │
│                  │  │   Explainability Engine           │   │   │
│                  │  │   Full reasoning traces           │   │   │
│                  │  └──────────────────────────────────┘   │   │
│                  └──────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │PostgreSQL│  │  Neo4j   │  │  Redis   │                      │
│  │ Sessions │  │  Graph   │  │  Cache   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Llama-3.3-70B via Groq API | Structured skill extraction (deterministic, temp=0.1) |
| **Embeddings** | sentence-transformers/all-mpnet-base-v2 | Skill similarity, normalization |
| **Graph DB** | Neo4j 5.x | Skill DAG — prerequisites, domains, roles |
| **Vector DB** | FAISS (IndexFlatIP) | Course retrieval (ANN search) |
| **Relational DB** | PostgreSQL 16 | Session persistence, audit logs |
| **Cache** | Redis 7 | Result caching, session TTL |
| **API** | FastAPI + Uvicorn | Async REST API |
| **Frontend** | React 18 + Vite + Framer Motion | 7-screen enterprise UI |
| **Graphs** | D3.js v7 | Interactive skill graph visualization |
| **Containers** | Docker + Docker Compose | Full-stack orchestration |
| **Algorithms** | NetworkX (topological sort, DFS) | Path algorithm |

---

## Setup & Installation

### Prerequisites

- Docker ≥ 24.0 and Docker Compose ≥ 2.20
- **Groq API key** (free at [console.groq.com](https://console.groq.com))
- 8GB RAM minimum (16GB recommended for embedding model)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/asioe.git
cd asioe
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
GROQ_API_KEY=gsk_your_key_here
SECRET_KEY=your_64_char_hex_secret
POSTGRES_PASSWORD=strong_password
NEO4J_PASSWORD=strong_password
REDIS_PASSWORD=strong_password
```

Generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Launch the full stack

```bash
docker-compose up --build -d
```

This starts:
- `postgres` on port 5432
- `neo4j` on ports 7474 (browser) and 7687 (bolt)
- `redis` on port 6379
- `backend` (FastAPI) on port 8000
- `frontend` (Nginx + React) on port **80**

### 4. Seed skill ontology and courses

The seed data is automatically built into the Docker image. If running locally:

```bash
cd backend
python ../scripts/seed_data.py
```

This generates:
- `backend/data/processed/skill_ontology.json` — 42 canonical skills with prerequisites
- `backend/data/processed/course_catalog.json` — 17 curated courses from major providers

### 5. Access the application

| Service | URL |
|---------|-----|
| **Application** | http://localhost:80 |
| **API Docs (Swagger)** | http://localhost:8000/api/docs |
| **API Docs (ReDoc)** | http://localhost:8000/api/redoc |
| **Neo4j Browser** | http://localhost:7474 |
| **Health Check** | http://localhost:8000/api/health |
| **Metrics** | http://localhost:8000/metrics |

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure env
cp ../.env.example .env            # Edit with your values

# Run database migrations
# (ensure PostgreSQL and Neo4j are running locally)

# Start dev server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

---

## Secret Handling Policy

1. Never commit real credentials (API keys, DB passwords, tokens, private keys) to git.
2. Use `.env` locally and CI repository secrets for all sensitive values.
3. Keep `.env.example` placeholder-only; it must never contain a real secret.
4. Treat any leaked secret as compromised: rotate it immediately.
5. CI runs a blocking repository secret scan (`security-secrets` job using Gitleaks).

### Local Secret Scan (recommended before push)

```bash
docker run --rm -v "${PWD}:/repo" zricethezav/gitleaks:latest detect --source=/repo --config=/repo/gitleaks.toml --verbose
```

---

## Skill-Gap Analysis Logic

### Core Algorithm: Adaptive Topological Learning Path

```
Input:  Resume skills (normalized) + JD skills (normalized)
Output: Ordered learning path optimized for the candidate

Step 1: PARSE
  PDF/DOCX → PyMuPDF text extraction
  Text → Groq Llama-3.3-70B structured JSON extraction
  Result: {skill_name, proficiency_level, domain, confidence}

Step 2: NORMALIZE
  Pass 1: Exact match against 42-skill ontology
  Pass 2: Semantic embedding similarity (threshold: 0.82)
           using sentence-transformers/all-mpnet-base-v2
  Pass 3: Synthetic ID generation for unknown skills
  Output: Canonical skill IDs with deduplication

Step 3: GAP ANALYSIS
  For each JD skill:
    gap_delta = max(0, required_score - candidate_score)
    Severity: critical(>0.6), major(0.35–0.6), minor(<0.35)
  Domain coverage = weighted coverage per skill domain
  Readiness score = weighted domain coverage - gap penalties

Step 4: GRAPH TRAVERSAL
  For each gap skill → backward DFS to collect prerequisites
  Max depth: 15 levels
  Prune: remove skills candidate already possesses

Step 5: TOPOLOGICAL SORT
  Build NetworkX DiGraph from gap + prerequisite set
  Apply nx.topological_sort() to guarantee prerequisite ordering
  Handle cycles with safe edge removal

Step 6: MULTI-FACTOR RANKING
  composite_score =
    0.35 × importance_score     (from O*NET)
    + 0.30 × gap_severity_boost (critical=1.0, major=0.7)
    + 0.20 × depth_score        (foundational first)
    + 0.10 × domain_priority
    + 0.05 × efficiency_score   (hours/importance)

Step 7: PHASE ASSIGNMENT
  Phase 1 (Foundation): beginner / no prerequisites
  Phase 2 (Core):       intermediate / direct gap mapping
  Phase 3 (Advanced):   advanced / expert

Step 8: RAG ENRICHMENT
  Embed skill description → FAISS ANN search (top-10)
  Rerank by domain + difficulty alignment
  Attach best course to each module
```

---

## Datasets Used

| Dataset | Source | Usage |
|---------|--------|-------|
| Resume Dataset | [Kaggle — snehaanbhawal](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset/data) | Skill frequency analysis, ontology building |
| Job Description Dataset | [Kaggle — kshitizregmi](https://www.kaggle.com/datasets/kshitizregmi/jobs-and-job-description) | Required skill extraction patterns |
| O*NET Technology Skills | [O*NET Database](https://www.onetcenter.org/db_releases.html) | Canonical skill taxonomy, O*NET codes |
| Curated Course Catalog | Coursera / Udemy / Educative | Course recommendations (17 curated entries) |

---

## Evaluation Metrics

| Metric | Implementation | Location |
|--------|---------------|---------|
| **Skill Match Accuracy** | Cosine similarity score on normalized embeddings | `GapAnalysisEngine._find_partial_match()` |
| **Path Efficiency** | `redundancy_eliminated / total_considered` | `PathEngine._compute_efficiency_score()` |
| **Redundancy Reduction** | Count of candidate-known skills pruned from path | `PathEngine._prune_known_skills()` |
| **Readiness Score** | Weighted domain coverage − gap penalties | `GapAnalysisEngine._compute_readiness_score()` |
| **Parsing Confidence** | Text extraction method quality + LLM confidence | `ParsingEngine._validate_resume_extraction()` |
| **Engine Latency** | Per-engine timing tracked in AuditLog | `GET /api/v1/metrics/{session_id}` |

---

## API Reference

### POST `/api/v1/analyze`
Run full adaptive analysis pipeline.

**Request**: `multipart/form-data`
```
resume          File     Resume (PDF/DOCX/TXT, max 10MB)
jd_text         string   Job description (min 50 chars)
target_role     string   Optional role name
max_modules     int      Max learning modules (5–50, default 20)
time_constraint_weeks int  Optional time budget
```

**Response**: Full `AnalysisCompleteResponse` with skill profile, gap analysis, learning path, and reasoning traces.

### GET `/api/v1/explain/{session_id}`
Returns per-module explainability data including `why_selected`, `dependency_chain`, and `confidence_score` for every recommendation.

### POST `/api/v1/simulate`
Recompute learning path with updated time constraint or domain priorities — without re-running the full pipeline.

### GET `/api/v1/graph/{session_id}`
Returns D3-compatible graph data (nodes + edges with gap severity annotations).

### GET `/api/v1/metrics/{session_id}`
Returns per-engine processing times, token usage, and audit trail.

---

## Project Structure

```
asioe/
├── backend/
│   ├── engines/
│   │   ├── parsing/          # PyMuPDF + Groq Llama-3.3-70B extraction
│   │   ├── normalization/    # sentence-BERT semantic matching
│   │   ├── skill_graph/      # Neo4j DAG + NetworkX algorithms
│   │   ├── gap/              # Cosine similarity gap analysis
│   │   ├── path/             # Topological DFS adaptive path
│   │   ├── rag/              # FAISS course retrieval
│   │   └── explainability/   # Reasoning trace generation
│   ├── api/routes/           # FastAPI route handlers
│   ├── db/                   # PostgreSQL, Neo4j, Redis managers
│   ├── schemas/              # Pydantic API contracts
│   ├── services/             # Pipeline orchestration
│   ├── core/                 # Config, logging
│   └── data/processed/       # Seed data (ontology, courses)
├── frontend/
│   └── src/
│       ├── pages/            # HomePage, AnalyzePage, DashboardPage
│       ├── components/
│       │   ├── dashboard/    # SkillProfile, GapAnalysis, LearningPath, Simulation
│       │   ├── graph/        # D3 interactive skill graph
│       │   └── explainability/ # Reasoning console
│       ├── store/            # Zustand global state
│       ├── utils/            # API client, helpers
│       └── types/            # Full TypeScript types
├── infra/
│   ├── docker/               # Dockerfiles (backend + frontend)
│   └── nginx/                # Nginx reverse proxy config
├── scripts/
│   └── seed_data.py          # Ontology + course catalog generation
├── docker-compose.yml
└── .env.example
```

---

## Security Notes

- All secrets injected via environment variables — never hardcoded
- File uploads validated by type and size (max 10MB)
- SQL injection prevented by SQLAlchemy ORM with parameterized queries
- Neo4j queries use parameterized Cypher
- Non-root user in production Docker containers
- Request ID middleware for distributed tracing
- CORS configured per environment

---

## License

MIT License — see LICENSE file for details.
