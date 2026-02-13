# Tamkin — AI-Powered Procurement for Small Businesses

## What This Is
An AI agent system that finds, vets, and compares suppliers for small business founders.
Users describe what they need → AI discovers suppliers → verifies them → compares → recommends.

## Architecture
- **Backend**: FastAPI + LangGraph orchestrator
- **Agents**: 5 core agents (Parse → Discover → Verify → Compare → Recommend)
- **Frontend**: Next.js + Tailwind
- **Database**: Supabase (PostgreSQL + pgvector) — currently in-memory for MVP
- **LLM**: Anthropic Claude (Haiku for cheap tasks, Sonnet for reasoning)

## Key Files
- `app/agents/orchestrator.py` — LangGraph pipeline definition
- `app/schemas/agent_state.py` — All typed state models between agents
- `app/api/v1/projects.py` — API endpoints (create project, get status)
- `frontend/src/app/page.tsx` — Main UI page

## Running
```bash
# Backend
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Agent Pipeline
1. **Requirements Parser** (Haiku) — NL → structured specs
2. **Supplier Discovery** (Sonnet) — Google Places + Firecrawl → ranked suppliers
3. **Supplier Verifier** (Haiku+Sonnet) — website, reviews, registration checks
4. **Comparison Agent** (Sonnet) — side-by-side analysis
5. **Recommendation Agent** (Sonnet) — final ranked picks with confidence scores
