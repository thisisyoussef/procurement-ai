# Tamkin Backend — Comprehensive Documentation

> **Audience**: AI agents, developers, and automated tools navigating this codebase.
> **Last updated**: 2026-02-13

---

## TABLE OF CONTENTS

```
SECTION 1  — SYSTEM OVERVIEW & ARCHITECTURE DIAGRAM
SECTION 2  — DIRECTORY STRUCTURE (file map)
SECTION 3  — APPLICATION ENTRY POINT (app/main.py)
SECTION 4  — CONFIGURATION (app/core/config.py)
SECTION 5  — DATABASE LAYER (app/core/database.py, app/models/*)
SECTION 6  — AUTHENTICATION (app/core/auth.py, app/api/v1/auth.py)
SECTION 7  — SCHEMAS & STATE MODELS (app/schemas/*)
SECTION 8  — AGENT PIPELINE & ORCHESTRATOR (app/agents/orchestrator.py)
SECTION 9  — INDIVIDUAL AGENTS (app/agents/*.py)
SECTION 10 — AGENT TOOLS (app/agents/tools/*.py)
SECTION 11 — API ENDPOINTS (app/api/v1/*.py)
SECTION 12 — CORE SERVICES (app/core/*.py)
SECTION 13 — PERSISTENCE SERVICES (app/services/*.py)
SECTION 14 — BACKGROUND SCHEDULER (app/core/scheduler.py)
SECTION 15 — DATA FLOW DIAGRAMS
SECTION 16 — FUNCTION REFERENCE INDEX
SECTION 17 — ENVIRONMENT VARIABLES
SECTION 18 — ERROR HANDLING & RESILIENCE
SECTION 19 — IMPORT DEPENDENCY GRAPH
```

---

## SECTION 1 — SYSTEM OVERVIEW & ARCHITECTURE DIAGRAM

### What This System Does

Tamkin is an AI-powered procurement system for small businesses. A user describes what they need in natural language, and the system:

1. Parses requirements into structured specs
2. Discovers suppliers across multiple global sources
3. Verifies supplier legitimacy
4. Compares suppliers side-by-side
5. Generates ranked recommendations
6. (Optional) Autonomously sends RFQ emails, monitors responses, and escalates to phone

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                            │
│  Landing Page → Project Create → Pipeline Status → Outreach → Chat     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTP/SSE
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FastAPI APPLICATION (app/main.py)                  │
│                                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ Auth Router  │  │Projects Router│  │Chat Router │  │Outreach Router│ │
│  │ /api/v1/auth │  │/api/v1/projects│ │.../chat    │  │.../outreach  │  │
│  └─────────────┘  └──────┬───────┘  └─────┬──────┘  └──────┬───────┘  │
│                          │                │                 │           │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐                │
│  │ Phone Router  │  │Webhooks Router│  │Leads/Events/ │                │
│  │ .../phone     │  │.../webhooks   │  │Intake Routers│                │
│  └───────┬───────┘  └───────┬───────┘  └──────────────┘                │
│          │                  │                                           │
│  ┌───────▼──────────────────▼───────────────────────────────────────┐  │
│  │                    ORCHESTRATOR (LangGraph Pipeline)              │  │
│  │                                                                   │  │
│  │  ┌─────────┐   ┌──────────┐   ┌────────┐   ┌─────────┐         │  │
│  │  │  PARSE  │──▶│ DISCOVER │──▶│ VERIFY │──▶│ COMPARE │         │  │
│  │  │ (Sonnet)│   │ (Sonnet) │   │(Hybrid)│   │ (Sonnet)│         │  │
│  │  └─────────┘   └──────────┘   └────────┘   └────┬────┘         │  │
│  │                                                   │              │  │
│  │                              ┌───────────┐   ┌────▼─────┐       │  │
│  │                              │  OUTREACH  │◀──│RECOMMEND │       │  │
│  │                              │  (Sonnet)  │   │ (Sonnet) │       │  │
│  │                              └───────────┘   └──────────┘       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     CORE SERVICES                                │  │
│  │  LLM Gateway │ Email Service │ Phone Service │ Scheduler        │  │
│  │  Log Stream  │ Progress      │ Auth (JWT)    │ Config           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   PERSISTENCE LAYER                              │  │
│  │  ProjectStore (DB + in-memory fallback)                          │  │
│  │  SupplierMemory (search, persist, interaction logging)           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────────┐
            ▼                  ▼                      ▼
┌───────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  PostgreSQL   │  │  Anthropic Claude  │  │ External APIs    │
│  (Supabase)   │  │  (Haiku + Sonnet)  │  │ Google Places    │
│  + pgvector   │  │                    │  │ Firecrawl        │
│               │  │                    │  │ Resend (email)   │
│               │  │                    │  │ Retell (phone)   │
│               │  │                    │  │ Hunter.io        │
│               │  │                    │  │ Gmail API        │
└───────────────┘  └───────────────────┘  └──────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web framework | FastAPI (async) | REST API + SSE streaming |
| Agent orchestration | LangGraph (with sequential fallback) | Multi-stage pipeline |
| LLM | Anthropic Claude (Haiku + Sonnet) | AI reasoning + generation |
| Database | PostgreSQL + pgvector (via Supabase) | Persistent storage |
| ORM | SQLAlchemy (async, asyncpg) | Database access |
| Email | Resend SDK | RFQ sending + webhook tracking |
| Phone | Retell AI SDK | AI-powered phone calls |
| Web scraping | Firecrawl + BeautifulSoup (fallback) | Supplier discovery |
| Validation | Pydantic v2 | Request/response + state typing |
| Auth | Google OAuth + JWT (python-jose) | User authentication |

---

## SECTION 2 — DIRECTORY STRUCTURE

```
/home/user/procurement-ai/
│
├── app/
│   ├── main.py                          # FastAPI app creation, CORS, lifespan, error handler
│   │
│   ├── agents/                          # AI agent implementations
│   │   ├── orchestrator.py              # LangGraph pipeline (6 nodes)
│   │   ├── requirements_parser.py       # Stage 1: NL → structured specs
│   │   ├── supplier_discovery.py        # Stage 2: Multi-source supplier search
│   │   ├── supplier_verifier.py         # Stage 3: Legitimacy verification
│   │   ├── comparison_agent.py          # Stage 4: Side-by-side comparison
│   │   ├── recommendation_agent.py      # Stage 5: Ranked recommendations
│   │   ├── outreach_agent.py            # Stage 6: RFQ email drafting
│   │   ├── followup_agent.py            # Follow-up email generation
│   │   ├── response_parser.py           # Supplier response → structured quote
│   │   ├── negotiation_agent.py         # Counter-offer logic
│   │   ├── chat_agent.py                # Conversational advisor (post-pipeline)
│   │   ├── phone_agent.py              # AI phone call orchestration
│   │   ├── inbox_monitor.py            # Gmail response monitoring
│   │   │
│   │   ├── tools/                       # Shared agent utilities
│   │   │   ├── google_places.py         # Google Places API wrapper
│   │   │   ├── firecrawl_scraper.py     # Firecrawl web scraper
│   │   │   ├── web_search.py            # Fallback scraper (httpx + BS4)
│   │   │   ├── contact_enricher.py      # Hunter.io + Browserless
│   │   │   ├── intermediary_resolver.py # Marketplace/directory detection
│   │   │   └── browser_service.py       # Browserless headless browser
│   │   │
│   │   └── prompts/                     # System prompts (markdown)
│   │       ├── requirements_parser.md
│   │       ├── phone_agent.md
│   │       └── ...
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py                # Route aggregator (/api/v1 prefix)
│   │       ├── projects.py              # Project CRUD + pipeline control
│   │       ├── auth.py                  # Google OAuth + JWT endpoints
│   │       ├── chat.py                  # Chat streaming (SSE)
│   │       ├── outreach.py              # RFQ drafting, sending, follow-ups
│   │       ├── phone.py                 # Phone call management
│   │       ├── webhooks.py              # Resend + Retell webhooks
│   │       ├── intake.py                # Landing page intake forms
│   │       ├── leads.py                 # Email lead capture
│   │       └── events.py               # Analytics event logging
│   │
│   ├── core/
│   │   ├── config.py                    # Pydantic Settings (all env vars)
│   │   ├── database.py                  # SQLAlchemy async engine + session
│   │   ├── auth.py                      # JWT creation, parsing, FastAPI deps
│   │   ├── llm_gateway.py              # Anthropic SDK wrapper + cost tracking
│   │   ├── email_service.py            # Resend SDK + HTML templates + queue
│   │   ├── phone_service.py            # Retell AI SDK wrapper
│   │   ├── progress.py                 # Granular progress event emission
│   │   ├── log_stream.py              # Per-project SSE log streaming
│   │   └── scheduler.py               # Background async task loops
│   │
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── user.py                      # User (synced from Supabase Auth)
│   │   ├── project.py                   # SourcingProject + Quote
│   │   ├── supplier.py                  # Supplier + SupplierInteraction
│   │   └── runtime.py                  # RuntimeProject, LandingLead, AnalyticsEvent
│   │
│   ├── schemas/                         # Pydantic request/response models
│   │   ├── agent_state.py               # ALL agent pipeline state models
│   │   ├── project.py                   # API request/response schemas
│   │   ├── auth.py                      # Auth request/response schemas
│   │   └── supplier.py                  # Supplier API schema
│   │
│   ├── services/
│   │   ├── project_store.py             # Abstract persistence + DB/in-memory
│   │   └── supplier_memory.py           # Supplier retrieval + interaction logging
│   │
│   └── repositories/
│       ├── user_repository.py           # User DB queries
│       ├── supplier_repository.py       # Supplier DB queries
│       └── runtime_repository.py        # RuntimeProject DB queries
│
├── requirements.txt
├── .env.example
├── CLAUDE.md
├── Dockerfile
├── docker-compose.yml
└── alembic.ini
```

---

## SECTION 3 — APPLICATION ENTRY POINT

### File: `app/main.py`

The FastAPI application is created and configured here.

```
STARTUP SEQUENCE:
1. Configure logging (INFO level, timestamped)
2. Install ProjectLogHandler (per-project log capture)
3. Load Settings from .env
4. Parse CORS origins (frontend_url + localhost + env overrides)
5. Create FastAPI app with lifespan manager
6. Add CORS middleware
7. Register global exception handler
8. Include API router (/api/v1/*)
9. Register root (/) and health (/health) endpoints
```

#### Functions

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `_parse_cors_origins` | 30 | `(raw_origins: str) -> list[str]` | Parse comma-separated CORS origins |
| `lifespan` | 51 | `async (_: FastAPI)` | Recover stale runs on startup, start/stop scheduler |
| `global_exception_handler` | 91 | `async (request, exc) -> JSONResponse` | Return error details instead of bare 500 |
| `root` | 104 | `async () -> dict` | Health check with app info |
| `health` | 114 | `async () -> dict` | Simple health check |

#### Lifespan Behavior

```
ON STARTUP:
  1. get_project_store() → store.recover_stale_runs()
     - Finds projects stuck in running states (parsing, discovering, etc.)
     - Marks them as "failed" with recovery reason "server_restart"
  2. get_scheduler() → scheduler.start()
     - Launches 4 background asyncio loops

ON SHUTDOWN:
  1. scheduler.stop()
     - Cancels all background tasks gracefully
```

---

## SECTION 4 — CONFIGURATION

### File: `app/core/config.py`

Uses `pydantic-settings` to load configuration from environment variables and `.env` file.

#### Settings Class Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `app_env` | str | "development" | Environment (development/production) |
| `app_secret_key` | str | "change-me..." | JWT signing secret |
| `app_title` | str | "Tamkin" | Application title |
| `app_version` | str | "0.1.0" | API version |
| `frontend_url` | str | "http://localhost:3000" | Frontend URL for CORS |
| `project_store_backend` | str | "database" | "database" or "inmemory" |
| `project_store_fallback_inmemory` | bool | True | Fall back to memory if DB fails |
| `auth_jwt_ttl_hours` | int | 720 | JWT token TTL (30 days) |
| `database_url` | str | "postgresql+asyncpg://..." | Async Postgres connection |
| `anthropic_api_key` | str | "" | Claude API key |
| `resend_api_key` | str | "" | Email service key |
| `retell_api_key` | str | "" | Phone service key |
| `google_places_api_key` | str | "" | Places API key |
| `firecrawl_api_key` | str | "" | Web scraping key |
| `hunter_api_key` | str | "" | Contact enrichment (optional) |
| `browserless_api_key` | str | "" | Screenshots (optional) |
| `model_cheap` | str | "claude-haiku-4-5-20251001" | Fast, cheap LLM tasks |
| `model_balanced` | str | "claude-sonnet-4-5-20250929" | Reasoning-heavy LLM tasks |
| `model_premium` | str | "claude-sonnet-4-5-20250929" | Premium LLM tasks |

#### Access Pattern

```python
from app.core.config import get_settings
settings = get_settings()  # lru_cached singleton
```

---

## SECTION 5 — DATABASE LAYER

### File: `app/core/database.py`

#### Components

| Component | Purpose |
|-----------|---------|
| `_normalize_async_database_url(url)` | Converts `postgres://` → `postgresql+asyncpg://` |
| `engine` | Global async SQLAlchemy engine (pool_size=10, max_overflow=20) |
| `async_session_factory` | Session maker (expire_on_commit=False) |
| `Base` | SQLAlchemy DeclarativeBase for all models |
| `get_db()` | FastAPI dependency: yields session, auto-commit/rollback |

### ORM Models

#### `app/models/user.py` — User

```
TABLE: users
COLUMNS:
  id              UUID (PK, server default)
  google_sub      VARCHAR(255) (unique, indexed)
  email           VARCHAR(500) (unique, indexed)
  full_name       VARCHAR(500)
  avatar_url      TEXT
  company_name    VARCHAR(500)
  plan            VARCHAR(50)  — "free", "pro", etc.
  last_login_at   TIMESTAMP WITH TZ
  created_at      TIMESTAMP WITH TZ (server default)
```

#### `app/models/project.py` — SourcingProject + Quote

```
TABLE: sourcing_projects
COLUMNS:
  id                    UUID (PK)
  user_id               UUID (FK → users.id)
  title                 VARCHAR(500)
  product_description   TEXT
  status                VARCHAR(50) — ProjectStatus enum
  parsed_requirements   JSONB
  agent_state           JSONB
  discovered_suppliers  JSONB
  verification_results  JSONB
  comparison_result     JSONB
  recommendation        JSONB
  created_at, updated_at  TIMESTAMP WITH TZ

TABLE: quotes
COLUMNS:
  id                      UUID (PK)
  sourcing_project_id     UUID (FK)
  supplier_id             UUID (FK)
  unit_price, currency    NUMERIC, VARCHAR
  moq, lead_time_days     INTEGER
  payment_terms, shipping_terms  VARCHAR
  certifications_offered  ARRAY(VARCHAR)
  sample_cost             NUMERIC
  parsed_data             JSONB
  raw_response_text       TEXT
```

#### `app/models/supplier.py` — Supplier + SupplierInteraction

```
TABLE: suppliers
COLUMNS:
  id                  UUID (PK)
  name                VARCHAR(500)
  website, email, phone  TEXT
  address, city, state, country  VARCHAR
  description         TEXT
  categories          ARRAY(VARCHAR)
  certifications      ARRAY(VARCHAR)
  year_established    INTEGER
  employee_count      INTEGER
  moq_range, lead_time_days  VARCHAR, INTEGER
  verification_score  FLOAT
  verification_data   JSONB
  is_verified         BOOLEAN
  source              VARCHAR(100) — thomasnet, alibaba, google, etc.
  google_rating       FLOAT
  google_review_count INTEGER
  embedding           VECTOR(1536) — pgvector (text-embedding-3-small)

TABLE: supplier_interactions
COLUMNS:
  id                UUID (PK)
  supplier_id       UUID (FK)
  project_id        VARCHAR(200)
  interaction_type  VARCHAR(100) — contact, email_sent, phone_call, etc.
  source            VARCHAR(100)
  details           JSONB
  created_at        TIMESTAMP WITH TZ
```

#### `app/models/runtime.py` — RuntimeProject, LandingLead, AnalyticsEvent

```
TABLE: runtime_projects  (ephemeral pipeline state)
COLUMNS:
  id, user_id, title, product_description
  status, current_stage, error
  state               JSONB — full pipeline state blob
  created_at, updated_at

TABLE: landing_leads
COLUMNS:
  id, email (unique), sourcing_note, source
  first_seen_at, last_seen_at

TABLE: analytics_events
COLUMNS:
  id, event_name, session_id, path
  project_id, payload (JSONB)
  created_at
```

---

## SECTION 6 — AUTHENTICATION

### File: `app/core/auth.py` — JWT utilities

#### Types

```python
@dataclass
class AuthUser:
    user_id: str
    email: str | None
    full_name: str | None
    avatar_url: str | None
```

#### Functions

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `create_access_token` | 27 | `(user: AuthUser) -> tuple[str, int]` | Create JWT (HS256), returns (token, expires_in_seconds) |
| `parse_access_token` | 42 | `(token: str) -> AuthUser` | Decode JWT, raises 401 on failure |
| `get_current_auth_user` | 77 | `async (request, credentials, access_token) -> AuthUser` | FastAPI dependency, extracts token from Bearer header or query param |
| `get_optional_auth_user` | 91 | `async (...) -> AuthUser \| None` | Same but returns None if no token |

#### JWT Payload Structure

```json
{
  "sub": "<user_id>",
  "email": "<email>",
  "name": "<full_name>",
  "picture": "<avatar_url>",
  "iat": 1234567890,
  "exp": 1234567890
}
```

### File: `app/api/v1/auth.py` — Auth endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/auth/google` | POST | None | Google OAuth sign-in |
| `/api/v1/auth/me` | GET | JWT | Get current user info |

#### Google OAuth Flow

```
1. Frontend gets Google ID token via Google Sign-In SDK
2. POST /api/v1/auth/google { id_token: "..." }
3. Backend verifies token at https://oauth2.googleapis.com/tokeninfo
4. Backend checks: audience matches, issuer is Google, email is verified
5. Backend upserts user in database (creates if new)
6. Backend creates JWT token
7. Returns: { access_token, expires_in, user: {...} }
```

---

## SECTION 7 — SCHEMAS & STATE MODELS

### File: `app/schemas/agent_state.py`

This is the **central type system** for the entire agent pipeline. Every piece of data flowing between agents is defined here.

### Pipeline Stage Enum

```python
class PipelineStage(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    CLARIFYING = "clarifying"      # Paused for user input
    DISCOVERING = "discovering"
    VERIFYING = "verifying"
    COMPARING = "comparing"
    RECOMMENDING = "recommending"
    OUTREACHING = "outreaching"
    COMPLETE = "complete"
    FAILED = "failed"
```

### Schema Dependency Diagram

```
ParsedRequirements ─────┐
  ├── RegionalSearchConfig │
  └── ClarifyingQuestion   │
                           ▼
DiscoveryResults ──────────┤
  ├── DiscoveredSupplier   │
  │   ├── ContactEnrichmentResult
  │   └── IntermediaryDetection
  │                        │
  ▼                        ▼
VerificationResults ───────┤
  └── SupplierVerification │
      └── VerificationCheck│
                           ▼
ComparisonResult ──────────┤
  └── SupplierComparison   │
                           ▼
RecommendationResult ──────┤
  └── SupplierRecommendation
                           │
                           ▼
OutreachState ─────────────┘
  ├── DraftEmail
  ├── FollowUpEmail
  ├── ParsedQuote
  ├── SupplierOutreachStatus
  │   └── EmailDeliveryEvent
  ├── PhoneCallStatus
  ├── ParsedCallResult
  ├── SupplierOutreachPlan
  │   └── OutreachPlanStep
  ├── OutreachEvent
  └── AutoOutreachConfig
```

### Key Models (Field-by-Field)

#### ParsedRequirements (Stage 1 output)

| Field | Type | Description |
|-------|------|-------------|
| `product_type` | str | Primary product category |
| `material` | str? | Material specification |
| `dimensions` | str? | Size/dimensions |
| `quantity` | int? | Order quantity |
| `customization` | str? | Customization details |
| `delivery_location` | str? | Delivery city/state/country |
| `deadline` | date? | Delivery deadline |
| `certifications_needed` | list[str] | Required certifications |
| `budget_range` | str? | Budget range (e.g., "$2-5 per unit") |
| `missing_fields` | list[str] | Fields that couldn't be parsed |
| `search_queries` | list[str] | Generated search queries for discovery |
| `regional_searches` | list[RegionalSearchConfig] | Multi-language search strategies |
| `clarifying_questions` | list[ClarifyingQuestion] | Questions to ask user |
| `sourcing_strategy` | str? | LLM's strategic sourcing approach |
| `sourcing_preference` | str? | Preferred sourcing country/region |

#### DiscoveredSupplier (Stage 2 output item)

| Field | Type | Description |
|-------|------|-------------|
| `supplier_id` | str? | DB ID (populated after persistence) |
| `name` | str | Supplier name |
| `website` | str? | Company website URL |
| `product_page_url` | str? | Direct product page link |
| `email` | str? | Contact email |
| `phone` | str? | Contact phone |
| `address`, `city`, `country` | str? | Location fields |
| `description` | str? | Business description |
| `categories` | list[str] | Product categories |
| `certifications` | list[str] | Held certifications |
| `source` | str | Discovery source (google, alibaba, etc.) |
| `relevance_score` | float | 0-100 relevance to requirements |
| `google_rating` | float? | Google Maps rating |
| `google_review_count` | int? | Number of Google reviews |
| `estimated_shipping_cost` | str? | Estimated shipping to buyer |
| `is_intermediary` | bool | Whether this is a middleman |
| `intermediary_detection` | IntermediaryDetection? | Detection details |
| `enrichment` | ContactEnrichmentResult? | Enrichment results |
| `filtered_reason` | str? | Why supplier was filtered out |

#### SupplierVerification (Stage 3 output item)

| Field | Type | Description |
|-------|------|-------------|
| `supplier_name` | str | Supplier name |
| `supplier_index` | int | Index in discovery results |
| `checks` | list[VerificationCheck] | Individual check results |
| `composite_score` | float | Weighted average (0-100) |
| `risk_level` | str | "low" (>70), "medium" (40-70), "high" (<40) |
| `recommendation` | str | "proceed", "caution", "reject" |
| `summary` | str | Human-readable summary |
| `preferred_contact_method` | str | "email", "phone", "website_form" |

#### SupplierComparison (Stage 4 output item)

| Field | Type | Description |
|-------|------|-------------|
| `supplier_name`, `supplier_index` | str, int | Identity |
| `verification_score` | float | From verification stage |
| `estimated_unit_price` | str? | Estimated unit price |
| `estimated_shipping_cost` | str? | Estimated shipping cost |
| `estimated_landed_cost` | str? | Unit price + shipping |
| `moq`, `lead_time` | str? | Minimum order, delivery time |
| `strengths`, `weaknesses` | list[str] | Pro/con lists |
| `overall_score` | float | 0-100 weighted composite |
| `price_score`, `quality_score`, `shipping_score`, `review_score`, `lead_time_score` | float | 0.0-5.0 star ratings |

#### SupplierRecommendation (Stage 5 output item)

| Field | Type | Description |
|-------|------|-------------|
| `rank` | int | 1-based rank |
| `supplier_name`, `supplier_index` | str, int | Identity |
| `overall_score` | float | 0-100 |
| `confidence` | str | "high", "medium", "low" |
| `reasoning` | str | 2-3 sentence explanation |
| `best_for` | str | "best overall", "budget pick", etc. |

#### OutreachState (Stage 6 state)

| Field | Type | Description |
|-------|------|-------------|
| `selected_suppliers` | list[int] | Indices of selected suppliers |
| `supplier_statuses` | list[SupplierOutreachStatus] | Per-supplier tracking |
| `draft_emails` | list[DraftEmail] | RFQ email drafts |
| `follow_up_emails` | list[FollowUpEmail] | Follow-up drafts |
| `parsed_quotes` | list[ParsedQuote] | Parsed supplier responses |
| `auto_config` | AutoOutreachConfig? | Automation settings |
| `phone_calls` | list[PhoneCallStatus] | Phone call tracking |
| `parsed_call_results` | list[ParsedCallResult] | Parsed phone transcripts |
| `supplier_plans` | list[SupplierOutreachPlan] | Execution plans |
| `events` | list[OutreachEvent] | Immutable event log |

### File: `app/schemas/project.py` — API Schemas

| Schema | Purpose |
|--------|---------|
| `ProjectCreateRequest` | Create project: title, product_description, auto_outreach |
| `PipelineStatusResponse` | Full pipeline status with all stage outputs |
| `ChatMessageRequest` | Chat message: message |
| `OutreachStartRequest` | Start outreach: supplier_indices[] |
| `EmailApprovalRequest` | Approve email: draft_index, edited_subject?, edited_body? |
| `QuoteParseRequest` | Parse response: supplier_index, response_text |
| `ClarifyingAnswerRequest` | Answer questions: answers{field: answer} |
| `PhoneCallStartRequest` | Start call: supplier_index, phone_number, questions[] |
| `PhoneCallConfigRequest` | Configure phone: enabled, voice_id, max_duration, questions |
| `IntakeStartRequest` | Landing intake: message, source, session_id |
| `LeadCreateRequest` | Lead capture: email, sourcing_note, source |
| `AnalyticsEventRequest` | Log event: event_name, session_id, path, payload |

---

## SECTION 8 — AGENT PIPELINE & ORCHESTRATOR

### File: `app/agents/orchestrator.py`

The orchestrator wires all agents into a directed pipeline using LangGraph.

### Pipeline Graph Structure

```
                    ┌─────────┐
                    │  START   │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  parse  │  parse_node()
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │ error?   │ success  │
              ▼          ▼          │
            [END]   ┌────────────┐  │
                    │  discover  │  │  discover_node()
                    └────┬───────┘  │
                         │          │
              ┌──────────┼──────────┤
              │ error?   │ success  │
              ▼          ▼          │
            [END]   ┌────────────┐  │
                    │   verify   │  │  verify_node()
                    └────┬───────┘  │
                         │          │
              ┌──────────┼──────────┤
              │ error?   │ success  │
              ▼          ▼          │
            [END]   ┌────────────┐  │
                    │  compare   │  │  compare_node() [NON-FATAL]
                    └────┬───────┘  │
                         │          │
                    ┌────▼────────┐ │
                    │  recommend  │ │  recommend_node()
                    └────┬────────┘ │
                         │          │
              ┌──────────┼──────────┘
              │ auto_outreach?
              │ yes       │ no
              ▼           ▼
        ┌──────────┐   [END]
        │ outreach  │  outreach_node() [NON-FATAL]
        └────┬─────┘
             │
           [END]
```

### GraphState TypedDict

```python
class GraphState(TypedDict, total=False):
    raw_description: str           # User's natural language input
    current_stage: str             # Current pipeline stage
    error: str | None              # Error message (stops pipeline)
    parsed_requirements: dict      # Stage 1 output
    discovery_results: dict        # Stage 2 output
    verification_results: dict     # Stage 3 output
    comparison_result: dict        # Stage 4 output
    recommendation_result: dict    # Stage 5 output
    outreach_result: dict          # Stage 6 output
    progress_events: list[dict]    # Granular progress updates
    user_answers: dict | None      # Answers to clarifying questions
    auto_outreach_enabled: bool    # Whether to auto-draft RFQs
```

### Node Functions

| Node | Function | Line | Input | Output | Error Handling |
|------|----------|------|-------|--------|----------------|
| parse | `parse_node(state)` | 60 | raw_description | parsed_requirements | **Fatal** — stops pipeline |
| discover | `discover_node(state)` | 81 | parsed_requirements | discovery_results | **Fatal** |
| verify | `verify_node(state)` | 103 | discovery_results (top 20 by relevance) | verification_results | **Fatal** |
| compare | `compare_node(state)` | 129 | requirements + discovery + verifications | comparison_result | **Non-fatal** — creates empty comparison |
| recommend | `recommend_node(state)` | 163 | requirements + comparison + verifications | recommendation_result | **Fatal** |
| outreach | `outreach_node(state)` | 187 | requirements + discovery + recommendations | outreach_result | **Non-fatal** — pipeline still completes |

### Routing Functions

| Function | Line | Purpose |
|----------|------|---------|
| `should_continue(state)` | 270 | Route based on current_stage — stop on error or complete |
| `should_continue_after_recommend(state)` | 287 | Route to outreach if auto_outreach_enabled, else end |

### Pipeline Execution Functions

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `build_pipeline_graph()` | 298 | `() -> CompiledGraph \| None` | Build LangGraph pipeline, returns None if not installed |
| `run_pipeline_sequential(raw_description, auto_outreach)` | 352 | `async -> GraphState` | Fallback: run nodes sequentially |
| `rerun_from_stage(project_state, from_stage, modified_state)` | 390 | `async -> GraphState` | Re-run from a specific stage (used by chat agent) |
| `run_pipeline(raw_description, auto_outreach)` | 451 | `async -> GraphState` | Main entry: tries LangGraph, falls back to sequential |

---

## SECTION 9 — INDIVIDUAL AGENTS

### Agent A: Requirements Parser

**File**: `app/agents/requirements_parser.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.01-0.05 per call

```
INPUT:  raw_description (str) — user's natural language input
OUTPUT: ParsedRequirements

PROCESS:
1. Load system prompt from prompts/requirements_parser.md
2. Call LLM with structured output request
3. Parse JSON response → ParsedRequirements
4. Generate search_queries for supplier discovery
5. Generate regional_searches for multi-language discovery
6. Generate clarifying_questions for missing critical fields
```

### Agent B: Supplier Discovery

**File**: `app/agents/supplier_discovery.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.10-0.50 per run

```
INPUT:  ParsedRequirements
OUTPUT: DiscoveryResults (50+ suppliers)

SEARCH SOURCES:
  1. Google Places API (local manufacturers)
  2. Firecrawl web search (global suppliers)
  3. B2B Marketplaces (Alibaba, ThomasNet, IndiaMART, Faire, etc.)
  4. Regional searches (Chinese, Turkish, Vietnamese queries)
  5. Supplier Memory (previously discovered suppliers from DB)

PROCESSING:
  1. Execute all search queries in parallel
  2. Deduplicate by domain/name
  3. Detect intermediaries (directories, trading companies)
  4. Resolve direct manufacturers from marketplace listings
  5. Enrich contacts (Hunter.io, Browserless — optional)
  6. Score relevance (0-100)
  7. Filter low-relevance results
  8. Return top 50+ ranked suppliers
```

### Agent C: Supplier Verifier

**File**: `app/agents/supplier_verifier.py`
**Model**: Haiku (cheap checks) + Sonnet (evaluation)
**Cost**: ~$0.05-0.15 per supplier

```
INPUT:  list[DiscoveredSupplier] (top 20 by relevance)
OUTPUT: VerificationResults

CHECKS PERFORMED:
  1. Website quality — Firecrawl scrape → LLM evaluation
  2. Google reviews — rating + count → score
  3. Registration — business legitimacy (LLM analysis)
  4. Social media — presence check (placeholder)
  5. Certifications — extracted from discovery data

SCORING:
  composite_score = weighted average of all checks (0-100)
  risk_level = "low" (>70) | "medium" (40-70) | "high" (<40)
  recommendation = "proceed" | "caution" | "reject"
```

### Agent G: Comparison Agent

**File**: `app/agents/comparison_agent.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.10-0.30 per run

```
INPUT:  ParsedRequirements + verified suppliers + VerificationResults
OUTPUT: ComparisonResult (up to 20 comparisons)

ESTIMATES GENERATED:
  - Unit price (based on region, company size, categories)
  - MOQ (based on product type minimums)
  - Lead time (based on location, certifications)
  - Shipping cost (based on destination, weight)
  - Landed cost = unit_price × qty + shipping

SCORING (0.0-5.0 star scale):
  price_score, quality_score, shipping_score, review_score, lead_time_score
  overall_score = weighted composite (0-100)

NARRATIVE:
  analysis_narrative comparing top 3-5 suppliers
  best_value, best_quality, best_speed labels
```

### Agent H: Recommendation Agent

**File**: `app/agents/recommendation_agent.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.05-0.15 per run

```
INPUT:  ParsedRequirements + ComparisonResult + VerificationResults
OUTPUT: RecommendationResult (up to 12 recommendations)

OUTPUT FIELDS:
  - rank (1-based)
  - overall_score (0-100)
  - confidence: "high" | "medium" | "low"
  - reasoning (2-3 sentences)
  - best_for label ("best overall", "budget pick", etc.)
  - executive_summary (paragraph)
  - caveats[] (risks, data gaps)
```

### Agent D: Outreach Agent

**File**: `app/agents/outreach_agent.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.02-0.05 per email draft

```
INPUT:  list[DiscoveredSupplier] + ParsedRequirements + RecommendationResult
OUTPUT: OutreachResult (draft emails)

FUNCTIONS:
  draft_outreach_emails(suppliers, requirements, recommendations) → OutreachResult
  auto_draft_and_queue(verified_suppliers, verifications, requirements, recommendations, config) → OutreachResult

PROCESS:
  1. For each selected supplier, generate personalized RFQ email
  2. Include: product specs, quantity, deadline, certifications
  3. Personalize: supplier name, capabilities, location
  4. Set status = "draft" (manual) or "auto_queued" (automatic)
```

### Agent E: Follow-up Agent

**File**: `app/agents/followup_agent.py`
**Model**: Sonnet (balanced)
**Cost**: ~$0.02-0.05 per follow-up

```
INPUT:  OutreachState + ParsedRequirements
OUTPUT: FollowUpResult

SCHEDULE:
  Follow-up 1: Day 3 after initial email
  Follow-up 2: Day 7
  Follow-up 3: Day 14

TONE VARIATION:
  #1: Gentle reminder
  #2: Emphasis on urgency/deadline
  #3: Final attempt, alternative options mentioned
```

### Agent F: Response Parser

**File**: `app/agents/response_parser.py`
**Model**: Haiku (cheap)
**Cost**: ~$0.001-0.003 per response

```
INPUT:  supplier_name, supplier_index, response_text, requirements
OUTPUT: ParsedQuote

EXTRACTED FIELDS:
  unit_price, currency, moq, lead_time
  payment_terms, shipping_terms, validity_period
  notes, confidence_score (0-100)
```

### Chat Agent

**File**: `app/agents/chat_agent.py`
**Model**: Sonnet (balanced, streaming)

```
INPUT:  user_message + conversation_history + project_state
OUTPUT: streaming text + optional ChatAction

ACTIONS IT CAN TRIGGER:
  - rescore/adjust_weights → re-run compare+recommend
  - rediscover/research → re-run discover+verify+compare+recommend
  - draft_outreach → draft RFQ emails for specific suppliers
  - none → just conversational response

AVAILABLE ONLY: after pipeline completes (status = "complete" or "failed")
```

### Phone Agent

**File**: `app/agents/phone_agent.py`
**Model**: Sonnet (script generation)

```
FUNCTIONS:
  initiate_supplier_call(name, index, phone, requirements, questions, voice_id, max_duration) → PhoneCallStatus
  get_call_detail(call_id) → dict
  parse_call_transcript(transcript, supplier_name, call_id) → ParsedCallResult

PROCESS:
  1. Generate conversation script from prompts/phone_agent.md template
  2. Create Retell AI agent with script
  3. Initiate outbound call
  4. Track via webhooks or polling
  5. Parse transcript → structured data (pricing, MOQ, lead time, findings)
```

### Inbox Monitor

**File**: `app/agents/inbox_monitor.py`

```
FUNCTIONS:
  get_monitor(provider) → InboxMonitor
  InboxMonitor.check_once(config, project_id) → list[dict]

PROCESS:
  1. Connect to Gmail API (OAuth with refresh tokens)
  2. Search for emails from supplier addresses/domains
  3. Return matching messages with body content
  4. Called by scheduler every 5 minutes for auto mode
```

---

## SECTION 10 — AGENT TOOLS

### `app/agents/tools/google_places.py`

| Function | Signature | Purpose |
|----------|-----------|---------|
| `search_google_places` | `async (query, location_bias?, max_results?, language_code?) -> list[dict]` | Search Google Places Text Search API |

**Returns per result**: name, address, phone, website, rating, review_count, types, description
**Cost**: ~$0.032 per request

### `app/agents/tools/firecrawl_scraper.py`

| Function | Signature | Purpose |
|----------|-----------|---------|
| `scrape_website` | `async (url, max_length?) -> dict` | Scrape URL to markdown |
| `search_web` | `async (query, max_results?) -> list[dict]` | Web search + auto-scrape |

### `app/agents/tools/web_search.py`

| Function | Signature | Purpose |
|----------|-----------|---------|
| `scrape_url_basic` | `async (url, max_length?) -> dict` | Fallback scraper (httpx + BeautifulSoup) |

**Extracts**: title, text, emails, phones, meta description, SSL status

### `app/agents/tools/intermediary_resolver.py`

| Function | Signature | Purpose |
|----------|-----------|---------|
| `detect_intermediary_by_url` | `(url) -> IntermediaryDetection` | Pattern-match marketplace/directory URLs |
| `classify_intermediary_by_content` | `async (name, content) -> IntermediaryDetection` | LLM-based content analysis |
| `resolve_direct_website` | `async (marketplace_url) -> str?` | Find direct manufacturer from listing |
| `extract_manufacturers_from_listing` | `async (content) -> list[str]` | LLM extraction of manufacturer names |

### `app/agents/tools/contact_enricher.py`

| Function | Purpose |
|----------|---------|
| `enrich_supplier_contacts` | Hunter.io API for email finding |
| `capture_contact_screenshot` | Browserless API for visual contact extraction |

### `app/agents/tools/browser_service.py`

| Function | Purpose |
|----------|---------|
| `take_screenshot` | Browserless headless browser screenshot |
| `extract_page_data` | Form filling, data extraction |

---

## SECTION 11 — API ENDPOINTS

### Route Aggregation

**File**: `app/api/v1/router.py` (line 15)
All routes are mounted under `/api/v1`:

```
/api/v1/auth/*          → auth_router
/api/v1/projects/*      → projects_router
/api/v1/intake/*        → intake_router
/api/v1/leads/*         → leads_router
/api/v1/events/*        → events_router
/api/v1/projects/*/chat → chat_router
/api/v1/projects/*/outreach → outreach_router
/api/v1/projects/*/phone → phone_router
/api/v1/webhooks/*      → webhooks_router
```

### Complete Endpoint Reference

#### Authentication (`app/api/v1/auth.py`)

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|-------------|----------|---------|
| POST | `/api/v1/auth/google` | None | `{id_token}` | `{access_token, expires_in, user}` | Google OAuth sign-in |
| GET | `/api/v1/auth/me` | JWT | — | `{id, email, full_name, avatar_url, plan}` | Get current user |

#### Projects (`app/api/v1/projects.py`)

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|-------------|----------|---------|
| POST | `/api/v1/projects` | JWT | `{title, product_description, auto_outreach}` | `{project_id, status}` | Create project + start pipeline |
| GET | `/api/v1/projects` | JWT | — | `[{id, title, status, current_stage}]` | List user's projects |
| GET | `/api/v1/projects/{id}/status` | JWT | — | `PipelineStatusResponse` | Get pipeline status + all outputs |
| GET | `/api/v1/projects/{id}/run-sync` | JWT | — | `PipelineStatusResponse` | Run pipeline synchronously (testing) |
| POST | `/api/v1/projects/search` | JWT | `{title, product_description}` | Full pipeline result | Quick synchronous search |
| GET | `/api/v1/projects/{id}/logs` | JWT | — | `list[log_entry]` | Get stored log entries |
| GET | `/api/v1/projects/{id}/logs/stream` | JWT | — | SSE stream | Live log streaming |
| POST | `/api/v1/projects/{id}/answer` | JWT | `{answers: {field: answer}}` | `{status, message}` | Submit clarifying answers, resume pipeline |
| POST | `/api/v1/projects/{id}/skip-questions` | JWT | — | `{status, message}` | Skip questions, resume pipeline |

#### Chat (`app/api/v1/chat.py`)

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|-------------|----------|---------|
| POST | `/api/v1/projects/{id}/chat` | JWT | `{message}` | SSE stream | Send chat message, get streaming response |
| GET | `/api/v1/projects/{id}/chat/history` | JWT | — | `list[ChatMessage]` | Get full chat history |

**SSE Event Types**:
- `{type: "token", content: "..."}` — Streamed response token
- `{type: "done", action: {...}}` — Stream complete, optional action
- `{type: "action_result", result: "..."}` — Action execution result
- `{type: "error", message: "..."}` — Error during streaming

#### Outreach (`app/api/v1/outreach.py`)

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|-------------|----------|---------|
| POST | `.../outreach/start` | JWT | `{supplier_indices: [0,1,2]}` | `{drafts, summary}` | Select suppliers + draft RFQ emails |
| POST | `.../outreach/approve/{idx}` | JWT | `{draft_index, edited_subject?, edited_body?}` | `{sent, error, supplier_name}` | Approve/edit and send email |
| POST | `.../outreach/parse-response` | JWT | `{supplier_index, response_text}` | `ParsedQuote` | Parse supplier response |
| POST | `.../outreach/follow-up` | JWT | — | `{follow_ups, summary}` | Generate follow-up emails |
| POST | `.../outreach/send-follow-up/{idx}` | JWT | — | `{sent, error, supplier_name}` | Send a follow-up email |
| GET | `.../outreach/status` | JWT | — | `OutreachState` | Full outreach state |
| GET | `.../outreach/plan` | JWT | — | `{funnel, friction_risks, plans}` | Execution plan + funnel metrics |
| GET | `.../outreach/timeline` | JWT | — | `{events, count}` | Immutable event log |
| POST | `.../outreach/auto-config` | JWT | `AutoOutreachConfig` | `{status, config}` | Set automation config |
| POST | `.../outreach/auto-start` | JWT | — | `{status, drafts_queued, summary}` | Auto-draft and queue emails |
| GET | `.../outreach/auto-status` | JWT | — | `{enabled, config, queued_count, sent_count}` | Auto-outreach status |
| GET | `.../outreach/delivery-status` | JWT | — | `{total_sent, deliveries}` | Email delivery tracking |
| POST | `.../outreach/check-inbox` | JWT | — | `{messages_found, messages}` | Manual inbox check |
| POST | `.../outreach/recompare` | JWT | — | `{status, message}` | Re-compare with real quotes |
| POST | `.../outreach/auto-send` | None | — | `{status, emails_sent}` | Bypass scheduler, send now |
| GET | `.../outreach/scheduler-status` | None | — | `scheduler.stats` | Scheduler health info |

#### Phone (`app/api/v1/phone.py`)

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|-------------|----------|---------|
| POST | `.../phone/configure` | JWT | `{enabled, voice_id, max_duration, questions}` | `{status, config}` | Configure phone calling |
| POST | `.../phone/call` | JWT | `{supplier_index, phone_number, questions}` | `{call_id, supplier_name, status}` | Initiate AI phone call |
| GET | `.../phone/calls` | JWT | — | `{calls, total, config}` | List all calls |
| GET | `.../phone/calls/{call_id}` | JWT | — | `PhoneCallStatus` | Get call status + transcript |
| POST | `.../phone/calls/{call_id}/parse` | JWT | — | `ParsedCallResult` | Parse call transcript |

#### Webhooks (`app/api/v1/webhooks.py`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/webhooks/resend` | Signature | Email delivery events (sent, delivered, bounced, opened) |
| POST | `/api/v1/webhooks/retell` | None | Phone call status events (started, ended, failed) |

#### Growth (`app/api/v1/intake.py`, `leads.py`, `events.py`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/intake/ask` | Optional | Landing page intake form |
| POST | `/api/v1/leads` | None | Capture email leads |
| POST | `/api/v1/events` | None | Log analytics events |

---

## SECTION 12 — CORE SERVICES

### LLM Gateway (`app/core/llm_gateway.py`)

Unified interface to Anthropic Claude with cost tracking.

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `get_anthropic_client()` | 29 | `() -> AsyncAnthropic` | Singleton async client (120s timeout) |
| `call_llm()` | 40 | `async (messages, model?, system?, max_tokens?, temperature?, tools?) -> Message` | Full LLM call with cost tracking |
| `call_llm_structured()` | 98 | `async (prompt, system?, model?, max_tokens?) -> str` | Single prompt → text response |
| `call_llm_stream()` | 185 | `async (messages, model?, system?, max_tokens?, temperature?) -> AsyncGenerator[str]` | Stream tokens |
| `repair_truncated_json()` | 126 | `(text: str) -> str \| None` | Fix JSON truncated by max_tokens |

**Cost tracking**: Tracks input/output tokens and USD cost per call. Logs cumulative session cost.

**Model cost rates** (per 1M tokens):

| Model | Input | Output |
|-------|-------|--------|
| claude-haiku-4-5 | $1.00 | $5.00 |
| claude-sonnet-4-5 | $3.00 | $15.00 |

### Email Service (`app/core/email_service.py`)

| Function/Class | Line | Purpose |
|----------------|------|---------|
| `send_email(to, subject, body_html)` | 15 | Send email via Resend API → `{id, sent}` |
| `verify_webhook_signature(payload, signature, secret)` | 47 | HMAC-SHA256 webhook verification |
| `build_rfq_html(supplier_name, company_name, body, requirements_summary?)` | 76 | Branded HTML email template |
| `EmailQueue` class | 157 | In-memory queue with rate limiting |
| `EmailQueue.enqueue(to, subject, body_html, metadata?)` | 169 | Add to queue |
| `EmailQueue.process_next()` | 179 | Send next email (rate-limited) |
| `EmailQueue.process_all()` | 213 | Drain entire queue |

### Phone Service (`app/core/phone_service.py`)

| Function | Purpose |
|----------|---------|
| `RetellPhoneService.create_agent(name, prompt, voice_id, max_duration)` | Create Retell AI agent with script |
| `RetellPhoneService.make_call(agent_id, phone_number)` | Initiate outbound call (E.164 format) |
| `RetellPhoneService.get_call_status(call_id)` | Poll call status, transcript, recording |
| `RetellPhoneService.list_calls(limit)` | Get recent calls |

### Progress System (`app/core/progress.py`)

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `emit_progress(stage, substep, detail, progress_pct?)` | 25 | Non-blocking progress event emission |

**Mechanism**: Uses `current_project_id` context var to associate events with projects. Creates asyncio task to persist via project store. Also logs to trigger log stream capture.

### Log Streaming (`app/core/log_stream.py`)

| Component | Line | Purpose |
|-----------|------|---------|
| `current_project_id` | 16 | ContextVar tracking active project |
| `ProjectLogHandler` | 25 | Custom logging.Handler — captures logs per project |
| `install_project_log_handler()` | 52 | Install handler on "app" logger |
| `get_project_logs(project_id)` | 61 | Get stored log entries |
| `subscribe_to_logs(project_id)` | 71 | SSE generator: historical + real-time logs |

**Flow**:
```
Agent code → logger.info("...") → ProjectLogHandler.emit()
  → Stored in _project_logs[project_id]
  → Pushed to _project_queues[project_id] (all SSE listeners)
  → subscribe_to_logs() yields SSE events
  → StreamingResponse to frontend
```

---

## SECTION 13 — PERSISTENCE SERVICES

### Project Store (`app/services/project_store.py`)

Abstract persistence layer with three implementations.

#### Class Hierarchy

```
BaseProjectStore (ABC)
├── InMemoryProjectStore    — dict-based, fast, volatile
├── DatabaseProjectStore    — PostgreSQL via RuntimeProject table
└── FallbackProjectStore    — DB-first with in-memory fallback
```

#### Abstract Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_project(project)` | `async -> None` | Persist new project |
| `get_project(project_id)` | `async -> dict?` | Retrieve project by ID |
| `save_project(project)` | `async -> None` | Update project |
| `list_projects()` | `async -> list[dict]` | List all projects |
| `append_progress_event(project_id, event)` | `async -> None` | Add progress event |
| `find_project_by_email_id(email_id)` | `async -> (dict?, int?)` | Webhook lookup by Resend email ID |
| `find_project_by_call_id(call_id)` | `async -> (dict?, int?)` | Webhook lookup by Retell call ID |
| `upsert_lead(email, sourcing_note, source)` | `async -> (str, bool)` | Save landing page lead |
| `create_event(event_name, session_id, path, project_id, payload?)` | `async -> str` | Log analytics event |
| `recover_stale_runs()` | `async -> int` | Find and recover hung projects |

#### Factory

```python
def get_project_store() -> BaseProjectStore:
    # Returns singleton based on settings.project_store_backend:
    # "inmemory" → InMemoryProjectStore
    # "database" → FallbackProjectStore(DatabaseProjectStore, InMemoryProjectStore)
```

#### FallbackProjectStore Behavior

```
try:
    result = await primary.method()  # DatabaseProjectStore
except Exception:
    if allow_fallback:
        result = await fallback.method()  # InMemoryProjectStore
    else:
        raise StoreUnavailableError()
```

`allow_fallback` is True when: `project_store_fallback_inmemory=True AND app_env != "production"`

### Supplier Memory (`app/services/supplier_memory.py`)

Persistent supplier knowledge base that learns from each pipeline run.

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `search_supplier_memory_candidates(requirements, limit?)` | 60 | `async -> list[DiscoveredSupplier]` | Find previously known suppliers matching requirements |
| `persist_discovered_suppliers(project_id, discovery_results)` | 122 | `async -> dict?` | Save discovered suppliers to DB, backfill IDs |
| `persist_verification_feedback(project_id, discovery_results, verification_results)` | 161 | `async -> dict?` | Update suppliers with verification scores |
| `record_supplier_interaction(project, supplier_index, type, source, details?)` | 200 | `async -> bool` | Log single interaction event |
| `record_supplier_interactions(project, supplier_indices, type, source, details?)` | 217 | `async -> bool` | Log batch interaction events |

#### Memory Relevance Scoring

```python
score = 35.0 + min(verification_score, 100) * 0.45
if is_verified: score += 8.0
score += min(15.0, interaction_count * 1.5)
for term in search_terms:
    if term in supplier_text: score += 3.5
return clamp(score, 20.0, 98.0)
```

---

## SECTION 14 — BACKGROUND SCHEDULER

### File: `app/core/scheduler.py`

The `OutreachScheduler` runs 4 background asyncio loops that power autonomous outreach.

```
┌───────────────────────────────────────────────────────────────────┐
│                    OUTREACH SCHEDULER                              │
│                                                                   │
│  ┌────────────────────┐  ┌────────────────────┐                  │
│  │  Email Queue Loop  │  │  Follow-up Loop    │                  │
│  │  Interval: 30s     │  │  Interval: 1h      │                  │
│  │                    │  │                    │                  │
│  │  Find auto_queued  │  │  Check days since  │                  │
│  │  drafts → send     │  │  sent → generate   │                  │
│  │  via Resend        │  │  follow-ups → send │                  │
│  └────────────────────┘  └────────────────────┘                  │
│                                                                   │
│  ┌────────────────────┐  ┌────────────────────┐                  │
│  │  Inbox Monitor     │  │  Phone Escalation  │                  │
│  │  Interval: 5m      │  │  Interval: 1h      │                  │
│  │                    │  │                    │                  │
│  │  Poll Gmail for    │  │  Identify suppliers │                  │
│  │  supplier replies  │  │  needing calls:     │                  │
│  │  → auto-parse      │  │  - email bounced   │                  │
│  │                    │  │  - 7d+ no response │                  │
│  │                    │  │  → Retell AI call   │                  │
│  └────────────────────┘  └────────────────────┘                  │
│                                                                   │
│  Stats: emails_sent, follow_ups_sent, inbox_checks,              │
│         phone_calls_initiated, responses_parsed, errors[]        │
└───────────────────────────────────────────────────────────────────┘
```

#### Loop Details

**Loop 1: Email Queue (30s)**
- Scans all projects for auto_queued drafts
- Resolves recipient emails from discovery data
- Sends via Resend API
- Updates supplier_statuses (email_id, delivery_status)
- Records OutreachEvent("auto_email_sent")
- Rate limit: 2s between sends

**Loop 2: Follow-up Checker (1h)**
- Schedule: [3, 7, 14] days after initial email
- Only for projects in "auto" mode
- Only for suppliers with email_sent=True, response_received=False
- Generates follow-ups via followup_agent
- Auto-sends via Resend

**Loop 3: Inbox Monitor (5m)**
- Only for projects in "auto" mode with sent emails
- Builds supplier email/domain lists
- Calls Gmail API to check for responses
- Matches replies to suppliers by address/domain
- Auto-parses responses via response_parser
- Records OutreachEvent("auto_response_parsed")

**Loop 4: Phone Escalation (1h)**
- Triggers when: email bounced OR 7+ days with no response + 1+ follow-up sent
- Only for suppliers with phone numbers
- Requires Retell API key
- Creates Retell agent + initiates call
- Records OutreachEvent("auto_phone_escalation")

#### Key Methods

| Method | Line | Signature | Purpose |
|--------|------|-----------|---------|
| `start()` | 68 | `async -> None` | Start all 4 background loops |
| `stop()` | 92 | `async -> None` | Cancel all tasks gracefully |
| `process_project_now(project_id)` | 601 | `async -> dict` | Manual trigger for one project |
| `stats` | 64 | `@property -> dict` | Scheduler health stats |

---

## SECTION 15 — DATA FLOW DIAGRAMS

### Complete Pipeline Data Flow

```
USER INPUT (natural language)
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ POST /api/v1/projects                                    │
│   ProjectCreateRequest { title, product_description }    │
│   → Creates project dict                                 │
│   → Adds background task: _run_pipeline_task()           │
│   → Returns { project_id, status: "started" }            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ _run_pipeline_task(project_id, description)              │
│                                                          │
│  1. parse_node(state)                                    │
│     └─► parse_requirements(raw_description)              │
│         └─► call_llm_structured() [Sonnet]               │
│         └─► Returns: ParsedRequirements                  │
│                                                          │
│  ── If clarifying_questions exist ──                     │
│     Project status = "clarifying"                        │
│     PAUSE (user answers via POST /answer)                │
│     _resume_pipeline_task() continues from discover      │
│                                                          │
│  2. discover_node(state)                                 │
│     └─► discover_suppliers(parsed_requirements)          │
│         ├─► search_google_places() × N queries           │
│         ├─► search_web() × N queries                     │
│         ├─► B2B marketplace searches                     │
│         ├─► Regional searches (multi-language)           │
│         ├─► search_supplier_memory_candidates()          │
│         ├─► detect_intermediary_by_url() per supplier    │
│         └─► Returns: DiscoveryResults (50+ suppliers)    │
│     └─► persist_discovered_suppliers() → DB              │
│                                                          │
│  3. verify_node(state)                                   │
│     └─► verify_suppliers(top 20 by relevance)            │
│         ├─► scrape_website() per supplier                │
│         ├─► call_llm() for website evaluation            │
│         ├─► Google reviews analysis                      │
│         └─► Returns: VerificationResults                 │
│     └─► persist_verification_feedback() → DB             │
│                                                          │
│  4. compare_node(state) [NON-FATAL]                      │
│     └─► compare_suppliers(reqs, suppliers, verifications)│
│         └─► call_llm_structured() [Sonnet]               │
│         └─► Returns: ComparisonResult                    │
│                                                          │
│  5. recommend_node(state)                                │
│     └─► generate_recommendation(reqs, comparison, verif) │
│         └─► call_llm_structured() [Sonnet]               │
│         └─► Returns: RecommendationResult                │
│                                                          │
│  6. outreach_node(state) [OPTIONAL, NON-FATAL]           │
│     └─► Only if auto_outreach=True                       │
│     └─► draft_outreach_emails(top 5 with emails)         │
│     └─► Mark all drafts as "auto_queued"                 │
│     └─► Scheduler sends within 30s                       │
│                                                          │
│  Project status = "complete"                             │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend polls GET /projects/{id}/status                 │
│   PipelineStatusResponse includes all stage outputs      │
└─────────────────────────────────────────────────────────┘
```

### Outreach Lifecycle Flow

```
MANUAL FLOW:
  POST /outreach/start { supplier_indices }
    → draft_outreach_emails() → DraftEmail[]
    → Build SupplierOutreachPlan per supplier
    → Save OutreachState
    │
    ▼
  POST /outreach/approve/{draft_index}
    → Optional edits (subject, body)
    → send_email() via Resend
    → Update supplier_statuses (email_id, sent_at)
    │
    ▼
  Resend webhook → POST /webhooks/resend
    → Update delivery_status (delivered/bounced/opened)
    │
    ▼
  Supplier replies (email)
    │
    ├─► Manual: POST /outreach/parse-response { response_text }
    │     → parse_supplier_response() → ParsedQuote
    │
    └─► Auto: Scheduler inbox_monitor checks Gmail
          → parse_supplier_response() → ParsedQuote

AUTO FLOW:
  POST /outreach/auto-config { mode: "auto", threshold: 80 }
  POST /outreach/auto-start
    → auto_draft_and_queue() → DraftEmail[] (status: "auto_queued")
    → Scheduler Loop 1 sends within 30s
    → Scheduler Loop 2 sends follow-ups (days 3, 7, 14)
    → Scheduler Loop 3 monitors inbox for responses
    → Scheduler Loop 4 escalates to phone if needed
```

### Webhook Integration Flow

```
RESEND WEBHOOK:
  POST /api/v1/webhooks/resend
    │
    ├── Verify signature (HMAC-SHA256)
    ├── Extract email_id from payload
    ├── find_project_by_email_id(email_id) → project, supplier_index
    ├── Map event type → delivery_status
    │     email.sent → "sent"
    │     email.delivered → "delivered"
    │     email.bounced → "bounced"
    │     email.opened → "opened"
    │     email.clicked → "clicked"
    ├── Append EmailDeliveryEvent to supplier_statuses
    ├── record_supplier_interaction()
    └── Save project

RETELL WEBHOOK:
  POST /api/v1/webhooks/retell
    │
    ├── Extract call_id from payload
    ├── find_project_by_call_id(call_id) → project, call_index
    ├── Map event type → call status
    │     call_started/call_connected → "in_progress"
    │     call_ended/call_analyzed → "completed" (+ transcript)
    │     call_failed/call_error → "failed"
    ├── Update phone_calls[call_index]
    ├── Update supplier_statuses[].phone_status
    ├── record_supplier_interaction()
    └── Save project
```

---

## SECTION 16 — FUNCTION REFERENCE INDEX

### Quick Lookup: Where to find key functionality

| Need to... | File | Function | Line |
|------------|------|----------|------|
| Start pipeline | `api/v1/projects.py` | `create_project()` | 98 |
| Run pipeline | `agents/orchestrator.py` | `run_pipeline()` | 451 |
| Parse requirements | `agents/requirements_parser.py` | `parse_requirements()` | — |
| Discover suppliers | `agents/supplier_discovery.py` | `discover_suppliers()` | — |
| Verify suppliers | `agents/supplier_verifier.py` | `verify_suppliers()` | — |
| Compare suppliers | `agents/comparison_agent.py` | `compare_suppliers()` | — |
| Generate recommendations | `agents/recommendation_agent.py` | `generate_recommendation()` | — |
| Draft RFQ emails | `agents/outreach_agent.py` | `draft_outreach_emails()` | — |
| Send email | `core/email_service.py` | `send_email()` | 15 |
| Make phone call | `agents/phone_agent.py` | `initiate_supplier_call()` | — |
| Call LLM | `core/llm_gateway.py` | `call_llm()` | 40 |
| Call LLM (simple) | `core/llm_gateway.py` | `call_llm_structured()` | 98 |
| Stream LLM | `core/llm_gateway.py` | `call_llm_stream()` | 185 |
| Get project | `services/project_store.py` | `get_project_store().get_project()` | — |
| Save project | `services/project_store.py` | `get_project_store().save_project()` | — |
| Search supplier memory | `services/supplier_memory.py` | `search_supplier_memory_candidates()` | 60 |
| Persist suppliers | `services/supplier_memory.py` | `persist_discovered_suppliers()` | 122 |
| Log interaction | `services/supplier_memory.py` | `record_supplier_interaction()` | 200 |
| Emit progress | `core/progress.py` | `emit_progress()` | 25 |
| Stream logs | `core/log_stream.py` | `subscribe_to_logs()` | 71 |
| Get settings | `core/config.py` | `get_settings()` | 90 |
| Get DB session | `core/database.py` | `get_db()` | 47 |
| Create JWT | `core/auth.py` | `create_access_token()` | 27 |
| Authenticate | `core/auth.py` | `get_current_auth_user()` | 77 |

---

## SECTION 17 — ENVIRONMENT VARIABLES

### Required for Basic Operation

```bash
ANTHROPIC_API_KEY=sk-ant-...           # Claude API access (REQUIRED)
DATABASE_URL=postgresql+asyncpg://...   # Async Postgres URL
APP_SECRET_KEY=<random-secret>          # JWT signing key
```

### Required for Full Feature Set

```bash
# Email sending
RESEND_API_KEY=re_...
RESEND_WEBHOOK_SECRET=whsec_...
FROM_EMAIL=sourcing@yourdomain.com

# Supplier discovery
GOOGLE_PLACES_API_KEY=AIza...
FIRECRAWL_API_KEY=fc-...

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Phone calling
RETELL_API_KEY=key_...

# Inbox monitoring
GMAIL_CREDENTIALS_JSON=...
GMAIL_TOKEN_JSON=...
```

### Optional Enhancements

```bash
# Contact enrichment
HUNTER_API_KEY=...
BROWSERLESS_API_KEY=...

# Supabase (for pgvector embeddings)
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...

# Task queue
REDIS_URL=redis://localhost:6379/0
```

### Application Settings

```bash
APP_ENV=development                    # "development" or "production"
FRONTEND_URL=http://localhost:3000     # For CORS
CORS_ALLOW_ORIGINS=                    # Comma-separated additional origins
CORS_ALLOW_ORIGIN_REGEX=https://.*\.up\.railway\.app

PROJECT_STORE_BACKEND=database         # "database" or "inmemory"
PROJECT_STORE_FALLBACK_INMEMORY=true   # Fall back if DB unavailable

AUTH_JWT_TTL_HOURS=720                 # Token lifetime (30 days)
```

---

## SECTION 18 — ERROR HANDLING & RESILIENCE

### Pipeline Error Strategy

```
FATAL ERRORS (stop pipeline):
  - Requirements parsing failure
  - Supplier discovery failure
  - Supplier verification failure
  - Recommendation generation failure

NON-FATAL ERRORS (pipeline continues):
  - Comparison failure → empty ComparisonResult, recommendation uses discovery+verification only
  - Outreach failure → pipeline marked "complete" even if email drafting fails
```

### Timeout Configuration

| Operation | Timeout | Defined In |
|-----------|---------|-----------|
| LLM calls | 120s total, 30s connect | `llm_gateway.py:35` |
| Firecrawl scraping | 30s | `firecrawl_scraper.py` |
| Google Places | 15s | `google_places.py` |
| Basic scraping | 15s | `web_search.py` |
| Google token verify | 10s | `api/v1/auth.py:30` |

### Database Resilience

```
FallbackProjectStore:
  1. Try DatabaseProjectStore (PostgreSQL)
  2. On ANY exception:
     - If allow_fallback=True (non-production): switch to InMemoryProjectStore
     - If allow_fallback=False (production): raise StoreUnavailableError (→ HTTP 503)
  3. Once fallback activates, all subsequent calls go to in-memory (sticky)
```

### JSON Repair

When LLM output is truncated by `max_tokens`, `repair_truncated_json()` attempts recovery:
1. Remove markdown code fences
2. Remove trailing commas
3. Walk string tracking open brackets/braces
4. Close any unterminated strings
5. Close any open brackets/braces in reverse order

### Stale Run Recovery

On server startup, `recover_stale_runs()`:
1. Find all projects with status in `{parsing, clarifying, discovering, verifying, comparing, recommending}`
2. Mark them as `failed` with error `"server_restart: project run interrupted by API restart"`

---

## SECTION 19 — IMPORT DEPENDENCY GRAPH

```
app/main.py
  ├── app/api/v1/router.py
  │     ├── app/api/v1/auth.py
  │     │     ├── app/core/auth.py
  │     │     ├── app/core/database.py
  │     │     ├── app/repositories/user_repository.py
  │     │     └── app/schemas/auth.py
  │     │
  │     ├── app/api/v1/projects.py
  │     │     ├── app/agents/orchestrator.py
  │     │     │     ├── app/agents/requirements_parser.py
  │     │     │     │     ├── app/core/llm_gateway.py
  │     │     │     │     └── app/schemas/agent_state.py
  │     │     │     ├── app/agents/supplier_discovery.py
  │     │     │     │     ├── app/agents/tools/google_places.py
  │     │     │     │     ├── app/agents/tools/firecrawl_scraper.py
  │     │     │     │     ├── app/agents/tools/intermediary_resolver.py
  │     │     │     │     ├── app/agents/tools/contact_enricher.py
  │     │     │     │     ├── app/services/supplier_memory.py
  │     │     │     │     └── app/core/progress.py
  │     │     │     ├── app/agents/supplier_verifier.py
  │     │     │     │     ├── app/agents/tools/firecrawl_scraper.py
  │     │     │     │     ├── app/agents/tools/web_search.py
  │     │     │     │     └── app/core/llm_gateway.py
  │     │     │     ├── app/agents/comparison_agent.py
  │     │     │     ├── app/agents/recommendation_agent.py
  │     │     │     └── app/agents/outreach_agent.py
  │     │     ├── app/core/auth.py
  │     │     ├── app/core/log_stream.py
  │     │     ├── app/services/project_store.py
  │     │     │     ├── app/core/database.py
  │     │     │     ├── app/models/runtime.py
  │     │     │     └── app/repositories/runtime_repository.py
  │     │     └── app/services/supplier_memory.py
  │     │           ├── app/core/database.py
  │     │           └── app/repositories/supplier_repository.py
  │     │
  │     ├── app/api/v1/chat.py
  │     │     ├── app/agents/chat_agent.py
  │     │     └── app/agents/orchestrator.py (rerun_from_stage)
  │     │
  │     ├── app/api/v1/outreach.py
  │     │     ├── app/agents/outreach_agent.py
  │     │     ├── app/agents/followup_agent.py
  │     │     ├── app/agents/response_parser.py
  │     │     └── app/core/email_service.py
  │     │
  │     ├── app/api/v1/phone.py
  │     │     ├── app/agents/phone_agent.py
  │     │     └── app/core/phone_service.py (via phone_agent)
  │     │
  │     └── app/api/v1/webhooks.py
  │           ├── app/core/email_service.py
  │           └── app/services/supplier_memory.py
  │
  ├── app/core/config.py
  ├── app/core/log_stream.py
  └── app/core/scheduler.py
        ├── app/services/project_store.py
        ├── app/core/email_service.py
        ├── app/agents/followup_agent.py
        ├── app/agents/response_parser.py
        ├── app/agents/phone_agent.py
        └── app/agents/inbox_monitor.py
```

---

## APPENDIX: PROJECT STATE DICTIONARY SCHEMA

The project dict is the central data structure passed through the system. Here is its complete shape:

```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "title": "Custom Canvas Bags for Coffee Brand",
  "product_description": "I need 5000 custom printed canvas tote bags...",
  "auto_outreach": false,
  "status": "complete",
  "current_stage": "complete",
  "error": null,

  "parsed_requirements": { /* ParsedRequirements */ },
  "discovery_results": { /* DiscoveryResults */ },
  "verification_results": { /* VerificationResults */ },
  "comparison_result": { /* ComparisonResult */ },
  "recommendation_result": { /* RecommendationResult */ },

  "outreach_state": { /* OutreachState */ },
  "chat_messages": [ /* ChatMessage[] */ ],
  "progress_events": [ /* ProgressEvent[] */ ],

  "clarifying_questions": [ /* ClarifyingQuestion[] */ ],
  "user_answers": { "field": "answer" },

  "created_at": "2026-02-13T10:00:00Z",
  "updated_at": "2026-02-13T10:05:00Z"
}
```

**Status values**: `parsing` → `clarifying` → `discovering` → `verifying` → `comparing` → `recommending` → `outreaching` → `complete` | `failed`
