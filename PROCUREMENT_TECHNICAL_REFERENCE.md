# Procurement AI — Complete Technical Reference

> **AI-Powered Procurement for Small Businesses**
> Last updated: February 14, 2026

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Configuration & Environment](#5-configuration--environment)
6. [Application Entry Point](#6-application-entry-point)
7. [Core Infrastructure Layer](#7-core-infrastructure-layer)
8. [Database & Persistence Layer](#8-database--persistence-layer)
9. [Data Models (Pydantic Schemas)](#9-data-models-pydantic-schemas)
10. [ORM Models (SQLAlchemy)](#10-orm-models-sqlalchemy)
11. [Agent Pipeline — Complete Play-by-Play](#11-agent-pipeline--complete-play-by-play)
12. [Agent Tools](#12-agent-tools)
13. [Orchestrator — LangGraph Pipeline](#13-orchestrator--langgraph-pipeline)
14. [Post-Pipeline Agents](#14-post-pipeline-agents)
15. [API Layer](#15-api-layer)
16. [Background Scheduler](#16-background-scheduler)
17. [Services Layer](#17-services-layer)
18. [Repository Layer](#18-repository-layer)
19. [Frontend Architecture](#19-frontend-architecture)
20. [End-to-End Data Flow](#20-end-to-end-data-flow)
21. [Deployment & Infrastructure](#21-deployment--infrastructure)
22. [Agentic Test Suite](#22-agentic-test-suite)
23. [Key Design Decisions & Trade-offs](#23-key-design-decisions--trade-offs)
24. [Known Limitations & Future Work](#24-known-limitations--future-work)

---

## 1. Product Overview

Procurement AI is an AI agent system that automates the end-to-end supplier procurement workflow for small business founders. The user describes what they need to source in natural language. Procurement AI then discovers potential suppliers worldwide, verifies their legitimacy, compares them side-by-side, generates ranked recommendations, and autonomously drafts and sends RFQ (Request for Quote) emails — all with human oversight at key decision points.

The core value proposition is transforming what would typically take a founder weeks of manual research, emailing, and spreadsheet management into an automated pipeline that completes in minutes, with AI handling the grunt work and the human making the final calls.

### Core User Journey

1. The user types a natural language description of what they need: "I need 500 heavyweight hoodies with custom embroidery for my streetwear brand."
2. The system parses this into structured requirements, asking clarifying questions if needed.
3. It searches globally across Google Places, Firecrawl web scraping, marketplace directories, and its own supplier memory database.
4. Each discovered supplier gets verified through website analysis, Google reviews, business registration checks, and contact enrichment.
5. Verified suppliers are compared on price, quality, shipping cost, lead time, MOQ, and certifications.
6. A ranked recommendation is generated with decision lanes: best overall, best low-risk, best speed-to-order.
7. Personalized RFQ emails are auto-drafted (in the supplier's native language if applicable) and queued for user approval.
8. The system monitors the inbox for replies, parses quotes, handles follow-ups for non-responsive suppliers, and supports AI-powered negotiation.

---

## 2. System Architecture

Procurement AI follows a layered architecture with clear separation between the API surface, agent orchestration, persistence, and external service integrations.

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                     │
│  Landing Page ←→ Dashboard ←→ Workspace ←→ Chat Panel    │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼──────────────────────────────────┐
│                  API LAYER (FastAPI v1)                    │
│  /projects  /chat  /outreach  /dashboard  /auth  /phone   │
│  /intake    /leads /events   /webhooks   /supplier-profile│
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│              ORCHESTRATOR (LangGraph)                      │
│  Parse → Discover → Verify → Compare → Recommend          │
│                        ↓                                  │
│          Post-pipeline: Outreach → Follow-up               │
│          On-demand: Chat, Negotiate, Phone                 │
└──────┬────────────┬────────────┬─────────────────────────┘
       │            │            │
┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────────────────────────┐
│  CORE       │ │ TOOLS   │ │  EXTERNAL SERVICES           │
│  LLM Gateway│ │ Google  │ │  Anthropic Claude API        │
│  Email Svc  │ │ Places  │ │  Google Places API           │
│  Phone Svc  │ │ Firecrawl│ │  Firecrawl (scraping)       │
│  Progress   │ │ Browser │ │  Resend (email delivery)     │
│  Scheduler  │ │ Contact │ │  Retell AI (phone calls)     │
│  Auth       │ │ Enricher│ │  Browserbase (cloud browser) │
│  Log Stream │ │ Web     │ │  Hunter.io (email finding)   │
│             │ │ Search  │ │  Gmail API (inbox monitor)   │
│             │ │ Image   │ │  Supabase (auth + DB)        │
│             │ │ Extract │ │  Redis (queue)               │
└──────┬──────┘ └─────────┘ └─────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│              PERSISTENCE LAYER                            │
│  Repositories → SQLAlchemy ORM → Supabase PostgreSQL      │
│  InMemoryProjectStore (fallback) ←→ DatabaseProjectStore  │
│  Supplier Memory (pgvector-ready)                         │
└─────────────────────────────────────────────────────────┘
```

The system uses a dual-store persistence strategy: a primary `DatabaseProjectStore` backed by Supabase PostgreSQL for production, with an `InMemoryProjectStore` as a development fallback. A `FallbackProjectStore` wrapper tries the database first and degrades gracefully to in-memory if the database is unavailable.

---

## 3. Technology Stack

**Backend:**
- Python 3.12 with FastAPI
- LangGraph for agent pipeline orchestration (with sequential fallback mode)
- Anthropic Claude API (Haiku for cheap/fast tasks, Sonnet for reasoning)
- SQLAlchemy 2.x async ORM with asyncpg driver
- Pydantic v2 for all data validation and schemas
- Alembic for database migrations

**Frontend:**
- Next.js 15 with React 19
- Tailwind CSS for styling
- Framer Motion / GSAP for animations
- TypeScript throughout

**External Services:**
- Supabase: PostgreSQL database + auth (Google OAuth)
- Resend: transactional email delivery with webhook tracking
- Retell AI: automated phone calls to suppliers
- Firecrawl: web scraping and search
- Google Places API: local business discovery
- Hunter.io: email address finding
- Browserbase: cloud browser sessions (Playwright-based)
- Redis: background task queue

**Infrastructure:**
- Docker Compose for local development
- Railway for deployment (both backend and frontend)
- Alembic migrations for schema management

---

## 4. Directory Structure

```
procurement/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point, CORS, lifespan
│   ├── agents/                   # AI agent implementations
│   │   ├── orchestrator.py       # LangGraph pipeline definition
│   │   ├── requirements_parser.py # Agent A: NL → structured specs
│   │   ├── supplier_discovery.py  # Agent B: multi-source supplier search
│   │   ├── supplier_verifier.py   # Agent C: legitimacy verification
│   │   ├── comparison_agent.py    # Agent D: side-by-side comparison
│   │   ├── recommendation_agent.py# Agent E: ranked recommendations
│   │   ├── outreach_agent.py      # Agent F: RFQ email drafting
│   │   ├── followup_agent.py      # Agent G: follow-up emails
│   │   ├── negotiation_agent.py   # Agent H: quote evaluation
│   │   ├── phone_agent.py         # Agent I: automated phone calls
│   │   ├── chat_agent.py          # Agent J: conversational advisor
│   │   ├── inbox_monitor.py       # Gmail inbox monitoring
│   │   ├── response_parser.py     # Agent K: supplier email parsing
│   │   ├── prompts/               # Markdown prompt templates per agent
│   │   └── tools/                 # External service integrations
│   │       ├── google_places.py
│   │       ├── firecrawl_scraper.py
│   │       ├── web_search.py
│   │       ├── contact_enricher.py
│   │       ├── intermediary_resolver.py
│   │       ├── browser_service.py
│   │       ├── browserbase_service.py
│   │       ├── image_extractor.py
│   │       └── form_filler.py
│   ├── api/v1/                   # REST API endpoints
│   │   ├── router.py             # Route aggregation
│   │   ├── projects.py           # Pipeline CRUD + status
│   │   ├── chat.py               # Conversational AI (SSE streaming)
│   │   ├── outreach.py           # Email/phone outreach management
│   │   ├── dashboard.py          # Dashboard summary + activity
│   │   ├── auth.py               # Google OAuth + profiles
│   │   ├── intake.py             # Landing page intake form
│   │   ├── leads.py              # Lead capture
│   │   ├── events.py             # Analytics events
│   │   ├── phone.py              # Phone call management
│   │   ├── webhooks.py           # Resend + Retell webhooks
│   │   └── supplier_profile.py   # Supplier profile aggregation
│   ├── core/                     # Infrastructure services
│   │   ├── config.py             # Pydantic Settings (env vars)
│   │   ├── llm_gateway.py        # Anthropic SDK wrapper
│   │   ├── email_service.py      # Resend SDK integration
│   │   ├── phone_service.py      # Retell AI SDK wrapper
│   │   ├── database.py           # Async SQLAlchemy engine
│   │   ├── auth.py               # JWT + FastAPI auth deps
│   │   ├── progress.py           # Granular progress events
│   │   ├── scheduler.py          # Background task loops
│   │   └── log_stream.py         # Per-project SSE log streaming
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── project.py            # SourcingProject + Quote
│   │   ├── supplier.py           # Supplier + SupplierInteraction
│   │   ├── runtime.py            # RuntimeProject + Lead + Event
│   │   ├── dashboard.py          # ProjectEvent
│   │   └── user.py               # User (Supabase Auth)
│   ├── schemas/                  # Pydantic request/response models
│   │   ├── agent_state.py        # All inter-agent typed state
│   │   ├── project.py            # API request/response schemas
│   │   ├── supplier.py           # Supplier API response
│   │   ├── supplier_profile.py   # Full supplier profile response
│   │   ├── dashboard.py          # Dashboard API schemas
│   │   └── auth.py               # Auth + business profile schemas
│   ├── services/                 # Business logic services
│   │   ├── project_store.py      # Abstract project persistence
│   │   ├── supplier_memory.py    # Supplier memory service
│   │   ├── project_events.py     # Timeline event recording
│   │   ├── project_contact.py    # Project owner resolution
│   │   ├── dashboard_service.py  # Dashboard orchestration
│   │   └── communication_monitor.py # Outreach tracking
│   ├── repositories/             # Database query layer
│   │   ├── supplier_repository.py # Supplier upsert + memory search
│   │   ├── runtime_repository.py  # Runtime project CRUD
│   │   ├── dashboard_repository.py # Events + contacts queries
│   │   └── user_repository.py     # User CRUD
│   ├── tasks/                    # (Reserved for Celery workers)
│   └── utils/                    # Shared utilities
├── frontend/                     # Next.js frontend
│   └── src/
│       ├── app/                  # Pages (landing, dashboard)
│       ├── components/           # UI components
│       │   ├── workspace/        # Main workspace layout
│       │   │   ├── phases/       # Phase-specific views
│       │   │   └── supplier-profile/ # Supplier detail views
│       │   └── animation/        # Pipeline stage animations
│       ├── contexts/             # React context (WorkspaceContext)
│       ├── hooks/                # Custom hooks (polling, chat, outreach)
│       ├── lib/                  # API clients, auth, contracts
│       └── types/                # TypeScript type definitions
├── alembic/                      # Database migrations
│   └── versions/                 # Sequential migration files
├── agentic_suite/                # External evaluation runner
├── tests/                        # Pytest test suite
├── docs/                         # Architecture documentation
├── docker-compose.yml            # Local dev (backend + Redis)
├── .env.example                  # Environment variable template
└── railway.json                  # Railway deployment config
```

---

## 5. Configuration & Environment

All configuration is centralized in `app/core/config.py` using Pydantic `BaseSettings`. Environment variables are loaded from a `.env` file.

### Required Environment Variables

**LLM:**
- `ANTHROPIC_API_KEY` — Anthropic Claude API key (required)

**Database:**
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anonymous key
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `DATABASE_URL` — PostgreSQL connection string (async: `postgresql+asyncpg://...`)

**Email:**
- `RESEND_API_KEY` — Resend transactional email API key
- `RESEND_WEBHOOK_SECRET` — Webhook signature verification secret

**Phone:**
- `RETELL_API_KEY` — Retell AI API key for automated calls

**Web Scraping:**
- `FIRECRAWL_API_KEY` — Firecrawl scraping/search API key
- `GOOGLE_PLACES_API_KEY` — Google Places API key

**Contact Enrichment:**
- `HUNTER_API_KEY` — Hunter.io email finding API key
- `BROWSERLESS_API_KEY` — Browserless headless browser API key

**Auth:**
- `GOOGLE_CLIENT_ID` — Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` — Google OAuth client secret
- `AUTH_JWT_SECRET` — JWT signing secret
- `AUTH_JWT_TTL_HOURS` — Token expiry (default: 720 hours)

**Gmail Monitoring:**
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`

**App:**
- `ENVIRONMENT` — `development` or `production`
- `SECRET_KEY` — General app secret
- `FRONTEND_URL` — Frontend URL for CORS
- `CORS_ORIGINS` — Comma-separated allowed origins

### Model Routing

The LLM Gateway (`app/core/llm_gateway.py`) wraps the Anthropic SDK and routes calls to different models based on task complexity:

- **Haiku** (`claude-3-5-haiku-20241022`): Used for cheap, fast tasks — requirements parsing of simple inputs, response email parsing, basic verification checks, contact enrichment analysis
- **Sonnet** (`claude-sonnet-4-20250514`): Used for reasoning-heavy tasks — supplier discovery scoring, detailed verification analysis, comparison analysis, recommendations, outreach email drafting, negotiation evaluation, chat conversations

The gateway includes token usage tracking and cost estimation per call.

---

## 6. Application Entry Point

`app/main.py` creates the FastAPI application with:

1. **CORS middleware** configured from `CORS_ORIGINS` env var, allowing the frontend to make cross-origin requests.
2. **Lifespan hooks** that on startup: initialize the database engine and session factory, recover any stale running projects (marking them as failed after a server restart), start the background scheduler, and create the project store (Database → InMemory fallback chain). On shutdown: stop the scheduler and dispose of the DB engine.
3. **Route registration** mounting all v1 API routes under the `/api/v1` prefix.
4. The project store is attached to `app.state.project_store` so all route handlers can access it.

---

## 7. Core Infrastructure Layer

### 7.1 LLM Gateway (`app/core/llm_gateway.py`)

A thin wrapper around `anthropic.AsyncAnthropic` that provides:

- `call_llm(prompt, system_prompt, model, max_tokens, temperature)` — makes a single Claude API call and returns the text response.
- Model aliasing: accepts `"haiku"` or `"sonnet"` and resolves to the full model ID.
- Token tracking: logs input/output token counts and estimates cost per call.
- Error handling: wraps Anthropic API errors with context.

### 7.2 Email Service (`app/core/email_service.py`)

Wraps the Resend SDK for transactional email:

- `send_email(to, subject, html_body, from_address, reply_to)` — sends an email via Resend and returns the email ID for tracking.
- HTML email templates with responsive design.
- Webhook signature verification for delivery events.
- Rate limiting awareness.

### 7.3 Phone Service (`app/core/phone_service.py`)

Wraps the Retell AI SDK for automated phone calls:

- `create_retell_agent(conversation_script, voice_id, max_duration)` — creates a Retell agent with a custom conversation script.
- `initiate_call(agent_id, phone_number)` — starts a phone call.
- `get_call_status(call_id)` — retrieves call status and transcript.
- Voice selection and max duration configuration.

### 7.4 Progress System (`app/core/progress.py`)

A granular event emission system that pushes real-time progress updates to the frontend:

- Each agent emits progress events with: `stage`, `substep`, `detail` (human-readable message), `progress_pct` (0-100 for the current stage), and `timestamp`.
- Events are appended to the project state's `progress_events` array.
- The frontend polls for these events and displays them in a live feed.

### 7.5 Auth (`app/core/auth.py`)

JWT-based authentication:

- `create_access_token(user_id, email)` — creates a signed JWT.
- `get_current_user(token)` — FastAPI dependency that extracts and validates the JWT from the Authorization header.
- Optional auth dependency (`get_optional_user`) for endpoints that work with or without auth.

### 7.6 Log Stream (`app/core/log_stream.py`)

Per-project log capture that streams structured log entries to the frontend via SSE (Server-Sent Events). Each log entry includes a timestamp, level, source agent, and message. The frontend's `LogViewer` component subscribes to these streams for real-time visibility into what the agents are doing.

### 7.7 Scheduler (`app/core/scheduler.py`)

Background task loops that run independently of API requests:

1. **Email Queue Processor** — periodically checks for queued outreach emails and sends them via Resend.
2. **Follow-up Loop** — checks for non-responsive suppliers and triggers the follow-up agent at appropriate intervals (day 3, 7, 14).
3. **Inbox Monitor Loop** — polls Gmail for supplier responses and triggers the response parser.
4. **Phone Escalation Loop** — escalates to phone calls for high-priority suppliers that haven't responded to emails.

Each loop runs on a configurable interval and is started/stopped with the application lifespan.

---

## 8. Database & Persistence Layer

### 8.1 Database Engine (`app/core/database.py`)

Async SQLAlchemy setup:

- Creates an `AsyncEngine` from `DATABASE_URL` with connection pooling.
- Provides an `async_session_factory` (sessionmaker) for creating database sessions.
- The `get_db_session` async generator is used as a FastAPI dependency for request-scoped sessions.

### 8.2 Project Store (`app/services/project_store.py`)

An abstract persistence layer for project state with three implementations:

**`BaseProjectStore` (ABC):** Defines the interface — `get(id)`, `save(project)`, `list_all()`, `delete(id)`, plus methods for leads, events, and email/call ID lookups.

**`InMemoryProjectStore`:** Development-only in-memory dict store. All data is lost on restart. Used as a fallback when the database is unavailable.

**`DatabaseProjectStore`:** Production store backed by PostgreSQL via SQLAlchemy. Persists full project state as a JSONB blob in the `runtime_projects` table. Supports email ID and call ID reverse lookups across all projects.

**`FallbackProjectStore`:** Wraps a primary store (Database) and a fallback (InMemory). On any primary operation failure, it transparently degrades to the fallback store. This ensures the application remains functional even if the database goes down.

### 8.3 Migrations (Alembic)

Six sequential migration files establish the database schema:

1. `0001_core_baseline` — `suppliers`, `supplier_interactions`, `sourcing_projects`, `quotes` tables
2. `0002_runtime_growth` — `runtime_projects`, `landing_leads`, `analytics_events` tables
3. `0003_supplier_memory_history` — Adds `pgvector` embedding column, interaction history tracking
4. `0004_google_auth_users` — `users` table mapping to Supabase Auth
5. `0005_dashboard_project_events` — `project_events` table for timeline/activity feed
6. `0006_business_profile` — Adds business profile fields to `users` (company, address, phone, etc.)

---

## 9. Data Models (Pydantic Schemas)

### 9.1 Agent State (`app/schemas/agent_state.py`)

This is the canonical data contract between all agents. Every model in this file is a Pydantic `BaseModel` with strict typing.

**Input Parsing Models:**

- `RegionalSearchConfig` — A single region's search strategy: `region` (e.g., "China"), `languages` (e.g., ["zh", "en"]), `search_queries` (localized queries like "深圳刺绣帽衫工厂"), `marketplaces` (e.g., ["alibaba.com", "1688.com"]).
- `ClarifyingQuestion` — A question the parser wants to ask the user: `field` (which requirement it pertains to), `question` (human-readable), `importance` ("critical" | "helpful" | "optional"), `suggestions` (example answers), `why` (why this matters), `if_skipped` (what happens if unanswered), `default` (fallback value).
- `ParsedRequirements` — The structured output of the requirements parser: `product_type`, `material`, `dimensions`, `quantity`, `customization`, `delivery_location`, `deadline`, `certifications_needed`, `budget_range`, `search_queries` (generated search strings), `risk_tolerance` ("low" | "medium" | "high"), `priority_tradeoff` ("cost" | "quality" | "speed"), `minimum_supplier_count`, `evidence_strictness`, `sourcing_preference`, `regional_strategies` (list of `RegionalSearchConfig`), `clarifying_questions` (list of `ClarifyingQuestion`), plus a `missing_fields` list.

**Agent Output Models:**

- `DiscoveredSupplier` — A supplier found during discovery: `supplier_id` (database ID, populated after persistence), `name`, `website`, `email`, `phone`, `address`, `city`, `country`, `description`, `categories`, `certifications`, `source` (where found: "google_places", "firecrawl", "marketplace", "memory", etc.), `relevance_score` (0-100), `google_rating`, `google_review_count`, `is_intermediary`, `language_discovered`, `contact_form_url`, `logo_url`, `product_image_urls`.

- `SupplierVerification` — Result of verifying one supplier: `supplier_index` (position in the discovered list), `supplier_name`, `composite_score` (0-100 weighted), `risk_level` ("low" | "medium" | "high"), `checks` (list of individual check results: website quality, reviews, registration), `summary`, `recommendation` ("proceed" | "caution" | "avoid"), `preferred_contact_method` ("email" | "phone" | "form" | "unknown").

- `SupplierComparison` — Side-by-side analysis of one supplier: `supplier_index`, `supplier_name`, `overall_score` (0-100), `estimated_unit_price`, `currency`, `estimated_moq`, `estimated_lead_time`, `estimated_shipping_cost`, `estimated_landed_cost`, `certifications`, `strengths`, `weaknesses`, `price_score`, `quality_score`, `shipping_score`, `review_score`, `lead_time_score` (all 0.0-5.0 star ratings), plus `best_value`, `best_quality`, `best_speed` flags.

- `SupplierRecommendation` — A single ranked recommendation: `rank`, `supplier_name`, `supplier_index`, `overall_score`, `confidence` (0-100), `reasoning` (why this supplier), `best_for` (short label like "Best Overall Value"), `lane` ("best_overall" | "best_low_risk" | "best_speed_to_order" | "alternative"), `why_trust` (trust signals), `uncertainty_notes`, `verify_before_po` (checklist items), `needs_manual_verification` (boolean for technical products).

**Communication Models:**

- `CommunicationMessage` — A single message in the communication log: `direction` ("outbound" | "inbound"), `channel` ("email" | "phone" | "form"), `supplier_index`, `supplier_name`, `subject`, `body`, `timestamp`, `resend_email_id`, `status` ("sent" | "delivered" | "bounced" | "opened" | "clicked" | "replied").

- `SupplierOutreachStatus` — Outreach state for one supplier: `supplier_index`, `supplier_name`, `email_status` ("draft" | "auto_queued" | "pending_approval" | "approved" | "sent" | "failed"), `email_subject`, `email_body`, `email_id`, `follow_up_count`, `last_follow_up_at`, `response_received`, `quote_parsed`.

- `OutreachState` — Global outreach state across all suppliers: `supplier_statuses` (list of `SupplierOutreachStatus`), `auto_outreach_enabled`, `phone_calls` (list of `PhoneCallStatus`), `form_fills` (list of `FormFillResult`), `communication_monitor` (`CommunicationMonitorState`).

- `PhoneCallStatus` — State of a phone call: `supplier_index`, `call_id`, `status` ("pending" | "in_progress" | "completed" | "failed"), `transcript`, `extracted_data` (pricing, MOQ, lead time), `key_findings`.

**Master Pipeline State:**

- `PipelineState` — The top-level state object that flows through the entire pipeline and is persisted as the project's canonical state. Contains: `id`, `user_id`, `product_description`, `title`, `status` (pipeline stage), `current_stage`, `error`, `parsed_requirements` (`ParsedRequirements`), `suppliers` (list of `DiscoveredSupplier`), `verification_results` (list of `SupplierVerification`), `comparison_results` (list of `SupplierComparison`), `comparison_analysis` (narrative text), `recommendations` (list of `SupplierRecommendation`), `recommendation_result` (full recommendation output), `outreach_state` (`OutreachState`), `progress_events` (list of progress updates), `timeline_events` (list of timeline entries), `decision_preferences` (user-adjustable weights), `business_profile` (buyer company info), and `payload` (arbitrary metadata).

### 9.2 Project Schemas (`app/schemas/project.py`)

API-facing request/response models:

- `ProjectCreateRequest` — `product_description` (string), optional `user_id`
- `ProjectResponse` — `id`, `title`, `status`, `product_description`, `created_at`
- `ProjectDetailResponse` — Full project with all pipeline data
- `PipelineStatusResponse` — Lightweight polling response with status, stage, progress events, suppliers, verifications, comparisons, recommendations, outreach state
- `ClarifyingAnswerRequest` — User's answers to clarifying questions
- `ProjectRestartRequest` — Restart pipeline from a specific stage with optional parameter overrides
- Various outreach request schemas for email approval, sending, phone calls

### 9.3 Dashboard Schemas (`app/schemas/dashboard.py`)

- `DashboardGreeting` — Personalized greeting with time-of-day awareness
- `DashboardAttentionItem` — Items requiring user action (clarifying questions pending, outreach needing approval, failed sends, quotes ready for review)
- `DashboardProjectCard` — Summary card per project with phase, supplier count, stats, progress percentage
- `DashboardActivityItem` — Activity feed entry (event type, title, description, timestamp, project ID)
- `DashboardSummaryResponse` — Complete dashboard payload

### 9.4 Auth Schemas (`app/schemas/auth.py`)

- `GoogleSignInRequest` — Google OAuth credential (ID token)
- `AuthUserResponse` — User profile with auth token
- `BusinessProfileRequest` — Company name, website, address, phone, contact person, job title

---

## 10. ORM Models (SQLAlchemy)

### 10.1 Supplier (`app/models/supplier.py`)

```
suppliers
├── id (UUID, PK)
├── name (String, not null)
├── website (String)
├── email (String)
├── phone (String)
├── address (String)
├── city (String)
├── country (String)
├── description (Text)
├── categories (ARRAY[String])
├── certifications (ARRAY[String])
├── source (String: "google_places", "firecrawl", "memory", etc.)
├── google_rating (Float)
├── google_review_count (Integer)
├── verification_score (Float)
├── is_verified (Boolean)
├── verification_data (JSONB)
├── embedding (Vector — pgvector, reserved for future semantic search)
├── created_at (DateTime)
└── updated_at (DateTime)

supplier_interactions
├── id (UUID, PK)
├── supplier_id (UUID, FK → suppliers.id)
├── project_id (UUID, FK → runtime_projects.id, nullable)
├── interaction_type (String: "discovered", "verified", "contacted", "quoted", etc.)
├── source (String)
├── details (JSONB)
└── created_at (DateTime)
```

### 10.2 Runtime Project (`app/models/runtime.py`)

```
runtime_projects
├── id (UUID, PK)
├── user_id (UUID, FK → users.id)
├── title (String)
├── product_description (Text)
├── status (String: "parsing", "discovering", "verifying", etc.)
├── current_stage (String)
├── error (Text)
├── state (JSONB — full PipelineState serialized)
├── created_at (DateTime)
└── updated_at (DateTime)

landing_leads
├── id (UUID, PK)
├── email (String, unique)
├── sourcing_note (Text)
├── source (String)
├── first_seen_at (DateTime)
└── last_seen_at (DateTime)

analytics_events
├── id (UUID, PK)
├── event_name (String)
├── session_id (String)
├── path (String)
├── project_id (UUID, FK → runtime_projects.id, nullable)
├── payload (JSONB)
└── created_at (DateTime)
```

### 10.3 User (`app/models/user.py`)

```
users
├── id (UUID, PK — maps to Supabase Auth user ID)
├── email (String, unique)
├── full_name (String)
├── avatar_url (String)
├── company_name (String)
├── company_website (String)
├── company_address (String)
├── company_phone (String)
├── contact_person (String)
├── job_title (String)
├── onboarding_completed (Boolean)
├── created_at (DateTime)
└── updated_at (DateTime)
```

### 10.4 Project Event (`app/models/dashboard.py`)

```
project_events
├── id (UUID, PK)
├── user_id (UUID, FK → users.id)
├── project_id (UUID, FK → runtime_projects.id)
├── event_type (String: "pipeline_stage", "outreach_sent", "quote_received", etc.)
├── priority (String: "info", "warning", "action_required")
├── phase (String: "brief", "search", "outreach", "compare", etc.)
├── title (String)
├── description (Text)
├── payload (JSONB)
└── created_at (DateTime)
```

### 10.5 Sourcing Project & Quote (`app/models/project.py`)

These are legacy ORM models from an earlier architecture. `SourcingProject` has a `ProjectStatus` enum (DRAFT, PARSING, SEARCHING, VERIFYING, QUOTING, COMPARING, COMPLETED, FAILED). The `Quote` model stores parsed supplier quotes with unit price, MOQ, lead time, and the full parsed payload. These models are largely superseded by `RuntimeProject` and the `PipelineState` JSONB blob for the current implementation, but remain in the schema for backward compatibility.

---

## 11. Agent Pipeline — Complete Play-by-Play

This section walks through every agent in the core pipeline in the order they execute, describing exactly what happens at each step.

### 11.1 Agent A: Requirements Parser (`app/agents/requirements_parser.py`)

**Purpose:** Convert the user's natural language input into a structured `ParsedRequirements` object.

**Model used:** Sonnet (upgraded from Haiku for enhanced reasoning)

**Input:** Raw `product_description` string from the user.

**Step-by-step execution:**

1. **Load prompt template** from `app/agents/prompts/requirements_parser.md`.
2. **Call LLM** with the product description and the system prompt. The prompt instructs the LLM to extract: product type, material, dimensions, quantity, customization needs, delivery location, deadline, certifications, budget range, risk tolerance, and priority tradeoff.
3. **Parse JSON response** from the LLM. Handle truncated JSON with a recovery mechanism.
4. **Generate regional search strategies.** Based on the parsed product type and materials, the LLM identifies 2-4 optimal sourcing regions with language-specific search queries. For example, for "cotton hoodies" it might generate Chinese queries (深圳刺绣帽衫工厂), Turkish queries (istanbul nakışlı kapüşonlu üretici), and English queries.
5. **Generate clarifying questions** proportional to input ambiguity: very detailed inputs get 0-1 questions, moderate inputs get 1-2, vague inputs get 3-4. Each question has an importance level (critical/helpful/optional), suggestions, and a default value if skipped.
6. **Domain guardrails** — detect and fix "example leakage" where the LLM might use example data from its prompt instead of the actual user input. Check for automotive-specific enhancements (IATF 16949, PPAP, etc.) and add appropriate certifications.
7. **Emit progress events** at each substep.
8. **Return** `ParsedRequirements` object with all extracted fields.

**If clarifying questions are generated:** The pipeline pauses at "clarifying" status. The frontend displays the questions. When the user answers, their responses are merged into the existing `ParsedRequirements` and the pipeline resumes from discovery.

### 11.2 Agent B: Supplier Discovery (`app/agents/supplier_discovery.py`)

**Purpose:** Search multiple sources in parallel to build a comprehensive list of potential suppliers.

**Model used:** Sonnet (for scoring/ranking), tools use their own APIs.

**Input:** `ParsedRequirements` from the parser.

**Step-by-step execution:**

1. **Memory-first hybrid retrieval.** Query the supplier memory database (PostgreSQL) using the `supplier_memory` service. This finds previously discovered suppliers that match the current requirements based on product type, material, categories, and location. Memory hits get a relevance boost.

2. **Parallel multi-source search.** Launch concurrent searches across:
   - **Google Places API** — search for manufacturers near the delivery location and in target sourcing regions. Query format: `"{product_type} manufacturer near {region}"`. Returns business name, address, phone, website, rating, review count.
   - **Firecrawl web search** — run the generated search queries through Firecrawl's search endpoint. Returns scraped web page content with supplier information.
   - **Marketplace search** — for each regional strategy's marketplaces (Alibaba, 1688, IndiaMART, ThomasNet, etc.), search for relevant listings.
   - **Regional language search** — run the localized queries (Chinese, Turkish, Vietnamese, etc.) to find suppliers that only have non-English web presence.

3. **Intermediary detection and resolution.** The `intermediary_resolver` tool analyzes each result to detect if it's a marketplace listing, trading company, or directory rather than a direct manufacturer. Signals include: multiple unrelated product categories, "trading company" in name, marketplace URL patterns, lack of factory images. Detected intermediaries are flagged with `is_intermediary=true` and the system attempts to resolve them to the actual manufacturer.

4. **LLM scoring and deduplication.** Pass all raw results to Claude Sonnet with the discovery prompt. The LLM scores each supplier 0-100 based on: product type match (35%), direct manufacturer vs. intermediary (20%), location preference (15%), certifications (10%), reviews (10%), MOQ fit (10%). The LLM also deduplicates suppliers that appear in multiple sources.

5. **Lightweight contact enrichment.** For the top-scoring suppliers, run a quick contact enrichment pass using the `contact_enricher` tool to find email addresses, phone numbers, and contact form URLs. This is a lightweight first pass — more aggressive enrichment happens during verification.

6. **Iterative search expansion.** If the result set is below `minimum_supplier_count` (default 5), re-score with relaxed thresholds and optionally expand the search with broader queries.

7. **Industrial/OEM guardrails.** Detect and filter out consumer retail results (Amazon listings, eBay sellers, general retail stores) that don't match the B2B manufacturing context.

8. **Persist to supplier memory.** All discovered suppliers are upserted into the `suppliers` table via the supplier repository, with `SupplierInteraction` records logging the discovery.

9. **Emit progress events** with counts (e.g., "Found 23 potential suppliers, scoring...").

10. **Return** a list of `DiscoveredSupplier` objects, sorted by relevance score descending.

### 11.3 Agent C: Supplier Verifier (`app/agents/supplier_verifier.py`)

**Purpose:** Verify the legitimacy and quality of each discovered supplier through multiple automated checks.

**Model used:** Haiku for basic checks, Sonnet for website quality analysis.

**Input:** List of `DiscoveredSupplier` objects from discovery.

**Step-by-step execution (per supplier, executed in parallel batches):**

1. **Contact enrichment pre-step.** Before any verification, run aggressive contact finding for each supplier using the full 5-tier waterfall in `contact_enricher`:
   - Tier 1: Scrape the supplier's website for contact info.
   - Tier 2: Browserbase screenshot + LLM vision analysis of the contact page.
   - Tier 3: Google search for "{company name} email contact."
   - Tier 4: Hunter.io domain email search.
   - Tier 5: Generate common email patterns (sales@, info@, contact@).

2. **Website quality check.** Scrape the supplier's website using Firecrawl. Pass the content to Claude Sonnet with the verification prompt. The LLM evaluates: professional design, product catalog presence, about page, SSL certificate, contact information, manufacturing capabilities described, certifications mentioned. Score: 0-100.

3. **Google reviews analysis.** Use the Google Places data (rating and review count) to score the supplier's reputation. Scoring formula: `(rating / 5.0) * 50 + min(review_count / 100, 1.0) * 50`. Adjustments for very low review counts.

4. **Business registration indicators.** Check for: physical address present, phone number present, email present (and not a generic freemail), SSL certificate, business registration numbers mentioned on website, certifications (ISO, IATF, etc.).

5. **Image extraction (best-effort).** Use Browserbase to take a screenshot of the supplier's website and extract: company logo URL, product image URLs. This is non-blocking and failures are silently handled.

6. **Composite scoring.** Combine all checks with weights: website quality (35%), Google reviews (35%), business registration (30%). This produces a `composite_score` (0-100).

7. **Risk classification.**
   - Low risk: composite_score ≥ 70
   - Medium risk: 40 ≤ composite_score < 70
   - High risk: composite_score < 40

8. **Preferred contact method determination.** Based on enriched contact data, determine whether email, phone, or web form is the best way to reach the supplier.

9. **Persist verification feedback.** Update the `suppliers` table with `verification_score`, `is_verified`, and `verification_data` via `apply_verification_feedback` in the supplier repository.

10. **Emit progress** per supplier verified.

11. **Return** a list of `SupplierVerification` objects.

### 11.4 Agent D: Comparison Agent (`app/agents/comparison_agent.py`)

**Purpose:** Create a detailed side-by-side comparison of all verified suppliers.

**Model used:** Sonnet

**Input:** `ParsedRequirements`, list of `DiscoveredSupplier`, list of `SupplierVerification`.

**Step-by-step execution:**

1. **Second-pass relevance gate.** Before comparison, re-evaluate each supplier against the product requirements. Suppliers that don't actually make the requested product type (e.g., a packaging company appearing in a search for hoodies) get filtered out with a score of 0. This catches false positives from discovery.

2. **Build supplier profiles.** For each supplier, combine discovery data (name, location, source, capabilities) with verification data (composite score, risk level, checks) into a rich profile string.

3. **Shipping sanity guard.** For heavy commodities (metals, machinery, bulk goods), check if estimated per-unit freight is unrealistically low. Flag suspiciously cheap shipping estimates. This prevents the comparison from being skewed by suppliers who quote ex-works prices without realistic shipping costs.

4. **LLM comparison analysis.** Pass all supplier profiles and requirements to Claude Sonnet with the comparison prompt. The LLM generates for each supplier:
   - `estimated_unit_price` + `currency`
   - `estimated_moq`
   - `estimated_lead_time`
   - `estimated_shipping_cost` (domestic vs. international, considering weight/volume)
   - `estimated_landed_cost`
   - `certifications` held
   - `strengths` and `weaknesses` (arrays of strings)
   - Sub-category star ratings (0.0-5.0): `price_score`, `quality_score`, `shipping_score`, `review_score`, `lead_time_score`
   - `overall_score` (0-100) computed from weights: total cost (30%), lead time (20%), MOQ fit (15%), payment terms (10%), certifications (10%), verification score (15%)
   - Boolean flags: `best_value`, `best_quality`, `best_speed`

5. **Generate analysis narrative.** The LLM also produces a human-readable analysis explaining trade-offs in plain language for a small business founder.

6. **Handle truncated JSON.** If the LLM response is truncated (happens with large supplier sets), attempt recovery by parsing partial JSON.

7. **Return** a list of `SupplierComparison` objects plus the narrative `comparison_analysis` string.

### 11.5 Agent E: Recommendation Agent (`app/agents/recommendation_agent.py`)

**Purpose:** Produce a final ranked recommendation with decision lanes and confidence scores.

**Model used:** Sonnet

**Input:** `ParsedRequirements`, all discovery + verification + comparison data.

**Step-by-step execution:**

1. **Build comprehensive context.** Assemble all data from previous agents into a structured context: requirements, each supplier's discovery info, verification results, and comparison scores.

2. **Call LLM** with the recommendation prompt. The LLM generates:
   - `executive_summary` (2-3 sentences)
   - `decision_checkpoint_summary` (1-2 sentences)
   - `recommendations` (ranked list, up to 12 suppliers, each with):
     - `rank`, `supplier_name`, `supplier_index`
     - `overall_score` (0-100)
     - `confidence` (0-100)
     - `reasoning` (why this supplier)
     - `best_for` (short label)
     - `lane`: one of `best_overall`, `best_low_risk`, `best_speed_to_order`, `alternative`
     - `why_trust` (trust signals like "ISO certified, 4.5★ Google rating, 200+ reviews")
     - `uncertainty_notes` (what's unknown)
     - `verify_before_po` (checklist: "Request product samples", "Verify IATF certification", etc.)
     - `needs_manual_verification` (boolean)
   - `elimination_rationale` (why certain suppliers were excluded)
   - `caveats` (general warnings)

3. **Decision lane logic.** Ensure coverage across all three primary lanes. If no supplier naturally fits a lane, apply fallback logic: promote the next-best supplier from the overall ranking.

4. **Manual verification defaults.** For technical product categories (PCB, medical devices, aerospace, automotive), automatically set `needs_manual_verification = true` and populate `verify_before_po` with industry-specific checklist items.

5. **Recommendation floor.** Ensure at least 3 suppliers are recommended (if that many exist) to give the user meaningful choice.

6. **Lane coverage report.** Log which lanes are covered and any gaps.

7. **Return** a `RecommendationResult` containing the full recommendation payload.

---

## 12. Agent Tools

### 12.1 Google Places (`app/agents/tools/google_places.py`)

Wraps the Google Places API (New) for discovering local manufacturers:

- `search_nearby(query, location, radius)` — finds businesses matching a text query within a geographic radius.
- `search_text(query)` — broader text search without location constraint.
- Returns: `name`, `address`, `phone`, `website`, `rating`, `review_count`, `place_id`, `types`.
- Handles pagination for large result sets.
- Filters results by relevant place types (manufacturing, industrial, wholesale).

### 12.2 Firecrawl Scraper (`app/agents/tools/firecrawl_scraper.py`)

Wraps Firecrawl for web scraping and search:

- `scrape_url(url)` — scrapes a single URL and returns markdown content.
- `search(query, limit)` — runs a web search and returns scraped results.
- `crawl(url, max_pages)` — crawls a website starting from a URL.
- Handles rate limiting, retries, and content extraction.
- Falls back to basic `httpx` + BeautifulSoup scraping if Firecrawl is unavailable.

### 12.3 Web Search (`app/agents/tools/web_search.py`)

Fallback basic web scraping using `httpx` and `BeautifulSoup`:

- `fetch_page(url)` — downloads a page and extracts text content.
- `extract_contact_info(html)` — regex-based extraction of emails, phones, addresses.
- Used when Firecrawl is unavailable or for simple page fetches.

### 12.4 Contact Enricher (`app/agents/tools/contact_enricher.py`)

Multi-tier waterfall for finding supplier contact information:

- **Tier 1: Website scraping** — Firecrawl scrape of the supplier's website, regex extraction of emails/phones.
- **Tier 2: Visual analysis** — Browserbase screenshot of the contact page + LLM vision analysis using the `contact_enrichment.md` prompt.
- **Tier 3: Google search** — Search for "{company name} email contact" and extract from results.
- **Tier 4: Hunter.io** — Domain-based email search via Hunter.io API.
- **Tier 5: Pattern generation** — Generate common email patterns (sales@domain, info@domain, contact@domain).

Each tier is attempted in order. Once sufficient contact info is found (at least one email or phone), the waterfall stops. Results from all tiers are merged with deduplication.

### 12.5 Intermediary Resolver (`app/agents/tools/intermediary_resolver.py`)

Detects and resolves middlemen in the supply chain:

- **Detection signals:** Multiple unrelated product categories, "trading company" in name/description, marketplace URL patterns (alibaba.com, amazon.com), lack of factory/production imagery, generic product descriptions.
- **Resolution:** If an intermediary is detected, attempt to find the actual manufacturer by: scraping the listing for manufacturer mentions, searching for the product brand + "manufacturer", looking for "Made by" or "Manufactured by" text.
- Returns: `is_intermediary` (boolean), `intermediary_type` (marketplace/trading/directory), `resolved_manufacturer` (if found).

### 12.6 Browser Service (`app/agents/tools/browser_service.py`)

Headless browser integration via Browserless API:

- `take_screenshot(url)` — captures a PNG screenshot of a webpage.
- Used for visual analysis of supplier websites during verification and contact enrichment.

### 12.7 Browserbase Service (`app/agents/tools/browserbase_service.py`)

Cloud browser sessions via Browserbase + Playwright:

- `create_session()` — creates a cloud browser session.
- `navigate(session_id, url)` — navigates to a URL.
- `screenshot(session_id)` — captures the current page.
- `get_page_content(session_id)` — extracts page text.
- Used for more complex browser interactions (form filling, multi-page navigation).

### 12.8 Image Extractor (`app/agents/tools/image_extractor.py`)

Extracts visual assets from supplier websites:

- `extract_logo(url)` — finds the company logo (looks for common patterns: header img, og:image, favicon).
- `extract_product_images(url, product_type)` — finds product images relevant to the sourced item.
- Uses Browserbase for rendering JavaScript-heavy sites.
- Returns URLs of found images.

### 12.9 Form Filler (`app/agents/tools/form_filler.py`)

Automated web form detection and filling:

- `detect_forms(url)` — finds contact/inquiry forms on a supplier's website.
- `fill_form(url, form_data)` — fills and submits a form with the RFQ data.
- Uses Browserbase + Playwright for form interaction.
- Handles: text inputs, textareas, selects, checkboxes, file uploads.

---

## 13. Orchestrator — LangGraph Pipeline (`app/agents/orchestrator.py`)

The orchestrator defines the LangGraph state machine that wires the 5 core agents together with conditional routing.

### Pipeline Graph

```
START
  │
  ▼
[Parse Requirements]
  │
  ├── (has clarifying questions) → PAUSE → wait for user answers → resume
  │
  ▼
[Discover Suppliers]
  │
  ▼
[Verify Suppliers]
  │
  ▼
[Compare Suppliers]
  │
  ▼
[Recommend]
  │
  ├── (auto_outreach enabled) → [Draft Outreach] → END
  │
  ▼
END
```

### State Management

The orchestrator maintains the full `PipelineState` dict as its LangGraph state. Each agent node receives the current state, performs its work, and returns a partial state update that gets merged into the canonical state.

### Conditional Routing

After the parser runs, the orchestrator checks `parsed_requirements.clarifying_questions`. If there are questions with importance "critical", the pipeline status is set to "clarifying" and execution pauses. When the user answers (via the API), the orchestrator resumes by injecting the answers into the parsed requirements and continuing from discovery.

### Re-run Capability

The API supports restarting the pipeline from any stage. For example, if the user adjusts their requirements after seeing results, the orchestrator can re-run from discovery with the updated parameters, preserving the project ID and any outreach state.

### Auto-Outreach

After recommendations are generated, if `auto_outreach` is enabled, the outreach agent automatically drafts RFQ emails for the top-recommended suppliers. These drafts are queued with status "auto_queued" for user review before sending.

### Sequential Fallback

If LangGraph is not available or encounters an error, the orchestrator falls back to a simple sequential execution mode that runs each agent function in order without the graph framework.

### Error Handling

Each agent node is wrapped in a try/except. If an agent fails:
- The error is logged.
- The pipeline status is set to "failed" with the error message.
- The project state is persisted so the user can see where it failed.
- The pipeline can be restarted from the failed stage.

---

## 14. Post-Pipeline Agents

These agents operate after the core pipeline completes and handle the supplier communication lifecycle.

### 14.1 Agent F: Outreach Agent (`app/agents/outreach_agent.py`)

**Purpose:** Draft personalized RFQ (Request for Quote) emails for recommended suppliers.

**Model used:** Sonnet

**Flow:**

1. For each recommended supplier, build a context package: parsed requirements, supplier capabilities (from discovery), verification data, buyer's business profile.
2. Call Claude Sonnet with the outreach prompt to generate a personalized email. The email includes: buyer introduction, specific product requirements, certifications needed, information requested (pricing, MOQ, samples, payment terms), and a 5-7 business day response deadline.
3. **Language localization.** If the supplier's `language_discovered` field is set and isn't English, the entire email (including subject line) is written in the supplier's native language with culturally appropriate conventions.
4. **Personalization.** Reference the supplier's specific capabilities ("We noticed your ISO 9001 certification and experience with custom embroidery...").
5. **Business profile integration.** If the user has completed their business profile, include real company name, contact person, phone, and website in the email signature.
6. Set email status to either "draft" (manual mode) or "auto_queued" (auto-outreach mode).
7. Store drafts in `outreach_state.supplier_statuses`.

### 14.2 Agent G: Follow-up Agent (`app/agents/followup_agent.py`)

**Purpose:** Generate follow-up emails for non-responsive suppliers at escalating urgency levels.

**Model used:** Sonnet

**Cadence:**
- Day 3: Gentle reminder ("Just following up on our inquiry...")
- Day 7: More direct with urgency ("We're finalizing our supplier selection and would appreciate hearing from you...")
- Day 14: Final notice ("This will be our last follow-up regarding this inquiry...")

**Rules:**
- Maximum 3 follow-ups per supplier.
- Only targets suppliers with status "sent" and no response received.
- Follow-up emails reference the original RFQ subject line.
- Tone varies by follow-up number.
- Emails are under 150 words.

### 14.3 Agent H: Negotiation Agent (`app/agents/negotiation_agent.py`)

**Purpose:** Evaluate incoming quotes from suppliers and draft negotiation responses.

**Model used:** Sonnet

**Decision framework:**
- **ACCEPT:** Price ≤ budget, all fields present, high verification score, best quote among received.
- **CLARIFY:** Missing fields, unclear terms, need proforma invoice.
- **COUNTER:** Price 10-30% above budget, high MOQ, long lead time, better quotes exist from other suppliers.
- **REJECT:** Price >50% above budget, cannot meet requirements, high risk supplier.

**Competitive context:** The agent has anonymized data about other quotes received (price ranges, lead times) to strengthen negotiation positions without revealing specific competitor details.

### 14.4 Agent I: Phone Agent (`app/agents/phone_agent.py`)

**Purpose:** Make automated phone calls to suppliers using Retell AI.

**Flow:**

1. Generate a customized conversation script per supplier using the `phone_agent.md` prompt.
2. Create a Retell agent with the script, configured voice, and max call duration.
3. Initiate the call via Retell API.
4. After the call completes, parse the transcript to extract: pricing quotes, MOQ, lead time, customization capabilities, certifications, follow-up contact info.
5. Store extracted data in the project's outreach state.

### 14.5 Agent J: Chat Agent (`app/agents/chat_agent.py`)

**Purpose:** Conversational AI advisor with full project context for post-pipeline interactions.

**Model used:** Sonnet

**Capabilities:**
- Answers questions about the sourcing results.
- Streaming SSE response generation.
- **ACTION block parsing.** When the LLM's response includes an ACTION block (e.g., `ACTION: rescore`, `ACTION: research "wider search for suppliers in Vietnam"`, `ACTION: draft_outreach 0,1,3`), the chat endpoint parses and executes these actions.
- Context summarization: builds a compact representation of the full pipeline state to fit within the LLM context window.
- Conversation history management with windowing for long conversations.

### 14.6 Agent K: Response Parser (`app/agents/response_parser.py`)

**Purpose:** Extract structured data from supplier email responses (quotes).

**Model used:** Haiku (cheap, fast)

**Extracts:** unit_price, currency, MOQ, lead_time, payment_terms, shipping_terms, validity_period, notes, can_fulfill, fulfillment_note.

**Confidence scoring:** 90-100 (all key fields clearly stated), 70-89 (most present, some inferred), 50-69 (partial, several missing), <50 (very incomplete). Fields are set to null if undetermined rather than guessed.

### 14.7 Inbox Monitor (`app/agents/inbox_monitor.py`)

**Purpose:** Monitor the user's email inbox for supplier responses.

**Implementation:**
- `GmailMonitor` class using Google Gmail API with OAuth2.
- Searches for unread messages matching RFQ response patterns within a 7-day window.
- Matches incoming emails to known suppliers by domain and email address.
- Returns structured message data: sender, subject, body, received_at, matched_supplier.
- Triggered periodically by the background scheduler.

---

## 15. API Layer

All endpoints are under `/api/v1/` and are defined in `app/api/v1/`.

### 15.1 Projects (`/api/v1/projects/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/` | Create a new sourcing project. Accepts `product_description`. Kicks off the pipeline in a background task. Returns `project_id`. |
| GET | `/projects/{id}` | Get full project details including all pipeline data. |
| GET | `/projects/{id}/status` | Lightweight polling endpoint. Returns current status, stage, progress events, and whatever results are available so far. |
| GET | `/projects/` | List all projects for the authenticated user. |
| POST | `/projects/{id}/clarify` | Submit answers to clarifying questions. Resumes the pipeline. |
| POST | `/projects/{id}/restart` | Restart pipeline from a specific stage with optional parameter overrides. |
| POST | `/projects/{id}/cancel` | Cancel a running pipeline. |
| PUT | `/projects/{id}/preferences` | Update decision preferences (priority weights). |

### 15.2 Chat (`/api/v1/chat/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/{project_id}` | Send a message to the AI advisor. Returns SSE stream of the response. Parses ACTION blocks and executes them. |
| GET | `/chat/{project_id}/history` | Get conversation history for a project. |

### 15.3 Outreach (`/api/v1/outreach/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/outreach/{project_id}/draft` | Trigger outreach email drafting for specified suppliers. |
| POST | `/outreach/{project_id}/approve` | Approve a draft email for sending. |
| POST | `/outreach/{project_id}/approve-all` | Approve all pending drafts. |
| POST | `/outreach/{project_id}/send` | Send an approved email via Resend. |
| POST | `/outreach/{project_id}/send-all` | Send all approved emails. |
| GET | `/outreach/{project_id}/status` | Get outreach status for all suppliers. |
| POST | `/outreach/{project_id}/follow-up` | Trigger follow-up generation for non-responsive suppliers. |
| POST | `/outreach/{project_id}/parse-quote` | Parse a supplier's email response to extract quote data. |

### 15.4 Dashboard (`/api/v1/dashboard/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/summary` | Returns personalized greeting, attention items, project cards, recent activity. |
| GET | `/dashboard/contacts` | List all supplier contacts the user has interacted with. |
| POST | `/dashboard/quick-start` | Start a new project directly from the dashboard. |

### 15.5 Auth (`/api/v1/auth/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/google` | Google OAuth sign-in. Accepts Google ID token, verifies, creates/updates user, returns JWT. |
| GET | `/auth/me` | Get current user profile. |
| PUT | `/auth/profile` | Update user profile. |
| PUT | `/auth/business-profile` | Update business profile (company info). |
| POST | `/auth/complete-onboarding` | Mark onboarding as completed. |

### 15.6 Phone (`/api/v1/phone/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/phone/{project_id}/call` | Initiate an AI phone call to a supplier. |
| GET | `/phone/{project_id}/calls` | List all phone calls for a project. |
| GET | `/phone/call/{call_id}` | Get status and transcript of a specific call. |

### 15.7 Webhooks (`/api/v1/webhooks/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/resend` | Resend delivery webhooks (delivered, bounced, opened, clicked). Updates communication monitor state. |
| POST | `/webhooks/retell` | Retell AI call webhooks (call started, ended, transcript ready). Triggers transcript parsing. |

### 15.8 Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/intake/start` | Landing page intake form → creates a project. |
| POST | `/leads/` | Capture a lead email + optional sourcing note. |
| POST | `/events/` | Log a first-party analytics event. |
| GET | `/supplier-profile/{project_id}/{supplier_index}` | Aggregated supplier profile combining all pipeline data. |

---

## 16. Background Scheduler

The scheduler (`app/core/scheduler.py`) runs four background loops:

### 16.1 Email Queue Processor
- **Interval:** Every 30 seconds.
- **Logic:** Scans all projects for `SupplierOutreachStatus` entries with status "auto_queued" or "approved". Sends the email via Resend, updates status to "sent" or "failed", records the `email_id` for tracking.

### 16.2 Follow-up Loop
- **Interval:** Every 15 minutes.
- **Logic:** For each project in "outreach" phase, check for suppliers with status "sent" and no response. If enough time has elapsed since the last email (3, 7, or 14 days), trigger the follow-up agent to generate and queue a follow-up email.

### 16.3 Inbox Monitor Loop
- **Interval:** Every 5 minutes.
- **Logic:** For each project with active outreach, poll the user's Gmail inbox (via `GmailMonitor`) for new supplier responses. Match incoming emails to known suppliers. Trigger the response parser to extract quote data. Update the communication monitor state.

### 16.4 Phone Escalation Loop
- **Interval:** Every 30 minutes.
- **Logic:** For high-priority suppliers that haven't responded to emails after multiple follow-ups, suggest phone call escalation. (Currently suggests rather than auto-initiates, requiring user confirmation.)

---

## 17. Services Layer

### 17.1 Supplier Memory (`app/services/supplier_memory.py`)

Manages the cross-project supplier database:

- `query_memory(requirements)` — searches the supplier table using relevance scoring and product anchor terms. Combines SQL `LIKE` queries with interaction history weighting.
- `persist_suppliers(suppliers, project_id)` — upserts discovered suppliers into the database with deduplication.
- `record_interaction(supplier_id, type, details)` — logs supplier interactions (discovered, verified, contacted, quoted, etc.) for building relationship history.

### 17.2 Project Events (`app/services/project_events.py`)

Records timeline events for the activity feed:

- `record_event(project_id, user_id, event_type, title, description, phase, payload)` — persists to both the project state's `timeline_events` array and the `project_events` database table.
- Events are categorized by type (pipeline_stage, outreach_sent, quote_received, etc.) and priority (info, warning, action_required).

### 17.3 Communication Monitor (`app/services/communication_monitor.py`)

Tracks all outbound and inbound communications:

- Records outbound emails with Resend IDs for delivery tracking.
- Records inbound emails from suppliers matched by domain.
- Tracks delivery events (delivered, bounced, opened, clicked) from Resend webhooks.
- Manages message threading.
- Tracks response parsing status (whether a quote has been extracted from a reply).

### 17.4 Dashboard Service (`app/services/dashboard_service.py`)

Orchestrates the dashboard summary:

- **Greeting:** Time-of-day aware ("Good morning, Youssef") with contextual message based on project status.
- **Attention items:** Surfaces things that need the user's action — clarifying questions pending, outreach needing approval, failed email sends, quotes ready for review.
- **Project cards:** For each project, shows: title, current phase, supplier count, progress percentage, key stats (recommendations count, emails sent, quotes received).
- **Activity feed:** Merges timeline events from project state with database `ProjectEvent` records, sorted by recency.
- **Contacts:** Lists all suppliers the user has interacted with across all projects.

### 17.5 Project Contact (`app/services/project_contact.py`)

Helper service to resolve the project owner's email address from their user ID. Uses a cache in the project's payload to avoid repeated database lookups.

---

## 18. Repository Layer

### 18.1 Supplier Repository (`app/repositories/supplier_repository.py`)

- `upsert_discovered_suppliers(session, suppliers, project_id)` — Upserts suppliers with intelligent deduplication: matches by UUID, then email, then domain+name. Merges data from new discoveries into existing records (longer descriptions win, lists are merged, ratings take the max).
- `search_supplier_memory(session, requirements, limit)` — Searches for relevant suppliers using tokenized product terms, interaction history counts, and verification scores. Filters generic procurement terms ("manufacturer", "factory") to focus on product-specific matches.
- `apply_verification_feedback(session, project_id, suppliers, verifications)` — Updates supplier records with verification results (scores, risk level, verified status).
- `create_supplier_interaction(session, supplier_id, type, source, details)` — Logs a supplier interaction event.

### 18.2 Runtime Repository (`app/repositories/runtime_repository.py`)

- `get_runtime_project(session, id)` — Loads a project by ID.
- `list_runtime_projects(session)` — Lists all projects ordered by creation date.
- `upsert_runtime_project(session, project)` — Creates or updates a project record, serializing the full state as JSONB.
- `find_project_by_email_id(session, email_id)` — Reverse lookup: given a Resend email ID, find the project and supplier index it belongs to. Used by webhook handlers.
- `find_project_by_call_id(session, call_id)` — Same for Retell call IDs.
- `recover_stale_running_projects(session)` — On server restart, mark any projects stuck in running states as "failed" with a recovery note.

### 18.3 Dashboard Repository (`app/repositories/dashboard_repository.py`)

- `create_project_event(session, user_id, project_id, event_type, title, ...)` — Persists a timeline event.
- `list_project_events(session, user_id, limit, before)` — Paginated event listing.
- `list_supplier_contacts_for_user(session, user_id)` — Aggregates all suppliers a user has interacted with across projects, ranked by interaction count. Uses window functions to find the most recent project per supplier.

---

## 19. Frontend Architecture

### 19.1 Pages

**Landing Page (`src/app/page.tsx`):** Marketing/demo page showing Procurement AI in action. Displays animated conversation blocks demonstrating example sourcing scenarios ("500 heavyweight hoodies with embroidery"). Uses Framer Motion for animations and tracks telemetry events for analytics.

**Dashboard (`src/app/dashboard/page.tsx`):** The main authenticated experience. Components: navigation tabs (Home, Projects, Contacts), search bar, attention items requiring action, project grid showing all sourcing projects, recent activity feed, and contacts table. Refreshes every 25 seconds. Includes auth gate and onboarding flow.

**Product/Workspace Page (`src/app/product/page.tsx`):** The workspace where users interact with an active sourcing project. Contains the `WorkspaceShell` component.

### 19.2 Workspace Architecture

**WorkspaceShell (`src/components/workspace/WorkspaceShell.tsx`):** Layout wrapper containing `PhaseTabBar` (navigation between pipeline phases) and `CenterStage` (main content area).

**Phase Tab Bar:** Six phases — Brief, Search, Outreach, Compare, Samples, Order. Tabs unlock progressively as the pipeline advances. Inaccessible phases are dimmed.

**Phase Views (`src/components/workspace/phases/`):**
- `BriefPhase` — Shows parsed requirements, clarifying questions, and allows editing.
- `SearchPhase` — Displays discovered suppliers during and after search.
- `OutreachPhase` — Email drafting, approval, sending interface.
- `ComparePhase` — Side-by-side supplier comparison view.
- `SamplesPhase` — Sample tracking (planned feature).
- `OrderPhase` — Order management (planned feature).

**Supplier Profile View (`src/components/workspace/supplier-profile/`):** Detailed per-supplier view aggregating: company details, verification results, capabilities, portfolio images, communication log, quote data, and assessment.

### 19.3 State Management

**WorkspaceContext (`src/contexts/WorkspaceContext.tsx`):** React context + reducer managing all workspace state:

- `projectId` — currently active project
- `status` — full `PipelineStatus` object
- `activePhase` — which phase tab is selected
- `authUser` — authenticated user
- `loading` / `polling` flags

Actions include: `openProject`, `startNewProject`, `cancelCurrentProject`, `restartCurrentProject`, `setDecisionPreference`, `refreshStatus`.

URL sync via Next.js `useRouter`/`useSearchParams` ensures the project ID is reflected in the URL.

### 19.4 Pipeline Polling

**usePipelinePolling (`src/hooks/usePipelinePolling.ts`):** Custom hook that:

- Polls `GET /projects/{id}/status` on a regular interval.
- Handles stale responses (project switched mid-poll, out-of-order responses).
- Stops polling on terminal statuses (complete, failed, canceled, clarifying).
- Exposes: `status`, `polling`, `loading`, `startPolling`, `stopPolling`.

### 19.5 Animations

Pipeline stage animations (`src/components/animation/`) provide visual feedback during long-running agent operations:

- **Parsing:** Text morphing animation showing requirements being structured.
- **Discovery:** Interactive globe visualization with dots appearing in sourcing regions.
- **Verification:** Shield/checkmark animations per supplier.
- **Comparison:** Side-by-side card stacking animation.
- **Recommending:** Ranking animation with scores appearing.

These use a combination of Framer Motion, GSAP, and SVG.

### 19.6 API Client

**procurementClient (`src/lib/api/procurementClient.ts`):** API client wrapper with methods for intake, lead capture, and analytics event tracking. Uses `authFetch` for JWT-authenticated requests.

**Type Contracts (`src/lib/contracts/procurement.ts`):** TypeScript interfaces defining the API request/response shapes.

---

## 20. End-to-End Data Flow

Here is the complete data flow from user input to final recommendation, tracing every system interaction:

### Phase 1: Project Creation

```
User types: "I need 500 heavyweight hoodies with custom embroidery"
    │
    ▼
Frontend: POST /api/v1/projects/ { product_description: "..." }
    │
    ▼
Backend: Create project in RuntimeProject table
    │   Generate project UUID
    │   Set status = "parsing"
    │   Persist initial PipelineState
    │
    ▼
Backend: Launch pipeline in background task (asyncio.create_task)
    │
    ▼
Frontend: Start polling GET /api/v1/projects/{id}/status
```

### Phase 2: Requirements Parsing

```
Orchestrator: Enter "parse" node
    │
    ▼
Requirements Parser:
    │ Load requirements_parser.md prompt
    │ Call Claude Sonnet with product_description
    │ Parse JSON response
    │
    │ Result:
    │   product_type: "hoodies"
    │   material: "heavyweight cotton"
    │   quantity: 500
    │   customization: "custom embroidery"
    │   regional_strategies: [
    │     { region: "China", queries: ["深圳刺绣帽衫工厂", ...] },
    │     { region: "Turkey", queries: ["istanbul nakışlı kapüşonlu", ...] },
    │     { region: "Portugal", queries: ["Portugal custom hoodie manufacturer", ...] }
    │   ]
    │   clarifying_questions: [
    │     { field: "budget_range", question: "What's your target price per unit?", importance: "helpful" }
    │   ]
    │
    ▼
Orchestrator: Check clarifying questions
    │ Has "helpful" question → set status = "clarifying"
    │ Persist state
    │ PAUSE
    │
    ▼
Frontend: Display clarifying questions
User: Answers "$15-25 per unit"
Frontend: POST /api/v1/projects/{id}/clarify { answers: [...] }
    │
    ▼
Backend: Merge answers into ParsedRequirements
    │ Set status = "discovering"
    │ Resume pipeline
```

### Phase 3: Supplier Discovery

```
Orchestrator: Enter "discover" node
    │
    ▼
Supplier Discovery:
    │
    ├── [Parallel] Memory query → 3 past suppliers found
    ├── [Parallel] Google Places "hoodie manufacturer China" → 8 results
    ├── [Parallel] Firecrawl search queries → 12 results
    ├── [Parallel] Marketplace search (Alibaba, 1688) → 6 results
    ├── [Parallel] Regional language search → 4 results
    │
    ▼
    │ Total raw results: 33
    │ Intermediary check → 5 flagged as marketplaces/traders
    │ LLM scoring + deduplication → 18 unique suppliers scored
    │ Contact enrichment (top 12) → emails/phones found
    │ Persist to suppliers table → 18 rows upserted
    │
    ▼
    │ Return: 18 DiscoveredSupplier objects (sorted by relevance)
    │ Emit progress: "Discovered 18 suppliers across 4 regions"
```

### Phase 4: Verification

```
Orchestrator: Enter "verify" node
    │
    ▼
Supplier Verifier: (parallel batches of 4)
    │
    For each supplier:
    │ ├── Contact enrichment waterfall (5 tiers)
    │ ├── Firecrawl website scrape → LLM website quality check
    │ ├── Google Places rating + review count scoring
    │ ├── Business registration indicator check
    │ └── Image extraction (logo + product images)
    │
    │ Composite score = 35% website + 35% reviews + 30% registration
    │ Risk classification: Low ≥ 70, Medium 40-69, High < 40
    │
    ▼
    │ Persist verification feedback to suppliers table
    │ Return: 18 SupplierVerification objects
    │ Emit progress: "Verified 18 suppliers: 7 low risk, 8 medium, 3 high"
```

### Phase 5: Comparison

```
Orchestrator: Enter "compare" node
    │
    ▼
Comparison Agent:
    │ Second-pass relevance gate → 2 off-category suppliers filtered
    │ Build supplier profiles (discovery + verification)
    │ Shipping sanity check for heavyweight items
    │
    │ LLM analysis:
    │   For each of 16 remaining suppliers:
    │   - Estimated unit price, MOQ, lead time
    │   - Shipping cost (international freight for hoodies)
    │   - Landed cost
    │   - Star ratings (price, quality, shipping, reviews, lead time)
    │   - Strengths / weaknesses
    │   - Overall score
    │   - Best value / quality / speed flags
    │
    │ Narrative: "For 500 heavyweight hoodies with embroidery, Supplier X
    │   offers the best balance of price ($18/unit) and quality (ISO certified)
    │   but has a 6-week lead time. Supplier Y is faster (3 weeks) but more
    │   expensive ($24/unit)..."
    │
    ▼
    │ Return: 16 SupplierComparison objects + analysis narrative
```

### Phase 6: Recommendation

```
Orchestrator: Enter "recommend" node
    │
    ▼
Recommendation Agent:
    │ Build comprehensive context (all previous data)
    │
    │ Output:
    │   executive_summary: "Based on analyzing 16 verified suppliers..."
    │   recommendations: [
    │     { rank: 1, name: "Guangzhou TextilePro", lane: "best_overall",
    │       score: 87, confidence: 82, best_for: "Best Overall Value" },
    │     { rank: 2, name: "Istanbul Embroidery Co", lane: "best_speed_to_order",
    │       score: 79, confidence: 75, best_for: "Fastest Delivery" },
    │     { rank: 3, name: "Porto Custom Wear", lane: "best_low_risk",
    │       score: 74, confidence: 88, best_for: "Lowest Risk" },
    │     ...
    │   ]
    │   elimination_rationale: "3 suppliers excluded: 2 off-category, 1 high-risk"
    │
    ▼
    │ Set status = "complete"
    │ Persist final state
```

### Phase 7: Auto-Outreach (if enabled)

```
Outreach Agent:
    │ For top 5 recommended suppliers:
    │   Draft personalized RFQ email
    │   Localize to supplier's language
    │   Include buyer business profile
    │   Set status = "auto_queued"
    │
    ▼
Scheduler (Email Queue):
    │ Every 30s: check for "auto_queued" emails
    │ Send via Resend API
    │ Record email_id
    │ Update status to "sent"
    │
    ▼
Scheduler (Inbox Monitor):
    │ Every 5m: poll Gmail for responses
    │ Match to known suppliers
    │ Parse quotes via Response Parser
    │ Update communication monitor
    │
    ▼
Scheduler (Follow-up Loop):
    │ Day 3, 7, 14: generate follow-ups for non-responsive
```

---

## 21. Deployment & Infrastructure

### Docker Compose (Local Development)

```yaml
services:
  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    volumes: ["./app:/app/app"]  # Hot reload
    env_file: .env
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

### Railway (Production)

Both backend and frontend deploy to Railway:
- Backend: `railway.json` in root configures the FastAPI service.
- Frontend: `railway.json` in `frontend/` configures the Next.js service.
- Database: Supabase-hosted PostgreSQL (external).

### Running Locally

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # Starts on port 3000

# Database migrations
alembic upgrade head

# Tests
pytest tests/
```

---

## 22. Agentic Test Suite

The `agentic_suite/` directory contains an external evaluation framework for testing the pipeline end-to-end:

- **`cli.py`** — CLI entry point for running evaluation suites.
- **`runner.py`** — Executes multiple pipeline runs with different scenarios.
- **`agents.py`** — Wraps the pipeline agents for evaluation.
- **`aggregate.py`** — Aggregates results across runs for variance analysis.
- **`models.py`** — Evaluation data models.
- **`prd.py`** — PRD generation from evaluation results.
- **`scenarios/default_scenarios.json`** — Pre-configured test scenarios.

Evaluation outputs are saved to `agentic_suite_outputs/` with timestamped directories containing: run results, aggregate reports, structured PRDs, and suite manifests.

---

## 23. Key Design Decisions & Trade-offs

### Why LangGraph (with sequential fallback)?
LangGraph provides a clean state machine abstraction for the agent pipeline, with built-in support for conditional routing (e.g., pausing for clarifying questions) and partial state updates. The sequential fallback ensures the system works even without LangGraph, reducing a hard dependency.

### Why JSONB state blob instead of normalized tables?
The `PipelineState` is stored as a single JSONB column in `runtime_projects`. This trades query performance for development velocity — the schema can evolve without migrations, and the full state is always atomically consistent. The supplier memory system uses normalized tables for cross-project queries.

### Why dual persistence (Database + InMemory)?
The `FallbackProjectStore` ensures the application works during database outages or for development without a database. The in-memory store is feature-complete but ephemeral.

### Why Haiku vs. Sonnet routing?
Haiku is 10-20x cheaper than Sonnet. Tasks that need pattern matching but not deep reasoning (parsing simple emails, basic verification checks) use Haiku. Tasks requiring judgment (supplier scoring, comparison analysis, recommendations) use Sonnet. This keeps per-project costs manageable.

### Why multiple search sources?
No single source has comprehensive supplier coverage. Google Places excels at local businesses with reviews. Firecrawl finds web-only manufacturers. Marketplace searches tap into B2B platforms. Regional language searches find suppliers invisible to English-only queries. The parallel approach maximizes recall while LLM scoring handles precision.

### Why intermediary detection?
A naive search often returns trading companies, Amazon resellers, and directory listings instead of actual manufacturers. Detecting and resolving intermediaries is critical for finding direct suppliers with better pricing and accountability.

### Why language-localized outreach?
Many manufacturers, especially in China, Turkey, and Southeast Asia, respond faster and more positively to emails in their native language. Localized emails also demonstrate seriousness to the supplier.

---

## 24. Known Limitations & Future Work

### Current Limitations

1. **Pgvector semantic search is reserved but not active.** The supplier embedding column exists but suppliers are currently found via SQL `LIKE` queries on tokenized terms. Vector similarity search would significantly improve memory recall quality.

2. **Gmail monitoring requires OAuth refresh token.** The inbox monitor works with a single Gmail account's refresh token configured in environment variables. Multi-user Gmail integration (per-user OAuth) is not yet implemented.

3. **Phone calls are semi-autonomous.** The phone escalation loop suggests calls but doesn't auto-initiate without user confirmation. Fully autonomous call campaigns are planned.

4. **Samples and Order phases are frontend placeholders.** The pipeline covers through recommendation and outreach. Sample tracking and order management are UI shells for future development.

5. **No real-time WebSocket updates.** The frontend uses HTTP polling (every few seconds) rather than WebSocket push. This adds latency to the user experience during pipeline execution.

6. **Single-user per deployment.** While auth is implemented, the system is optimized for a single small business founder per deployment. Multi-tenant features (workspace isolation, usage limits) are not built.

7. **Cost tracking is per-call, not aggregated.** The LLM gateway tracks token usage per API call but doesn't aggregate costs per project or per user for billing purposes.

### Planned Improvements

1. Activate pgvector embeddings for semantic supplier memory search.
2. Per-user Gmail OAuth integration via Supabase Auth.
3. WebSocket push for real-time pipeline progress.
4. Sample tracking workflow (request, receive, evaluate, approve).
5. Order management (PO generation, payment tracking, shipment tracking).
6. Multi-tenant workspace isolation.
7. Usage-based billing with LLM cost aggregation.
8. Supplier relationship scoring based on interaction history.
9. Automated re-sourcing alerts when supplier conditions change.
10. Mobile app for on-the-go supplier management.

---

*This document was generated from a comprehensive analysis of the Procurement AI codebase on February 14, 2026. It covers the complete system as implemented, including all agents, tools, APIs, models, and infrastructure. Use it as a reference for understanding the current architecture and as a starting point for planning improvements.*
