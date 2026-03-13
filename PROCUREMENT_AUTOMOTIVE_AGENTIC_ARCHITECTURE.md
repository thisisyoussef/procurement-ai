# Procurement AI: Agentic Automotive Procurement Architecture

## Complete System Design for AI-Powered Supplier Discovery, Qualification, and Connection

**Version 1.0 — February 2026**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem: How Automotive Procurement Works Today](#2-the-problem)
3. [Procurement AI's Value Proposition](#3-value-proposition)
4. [User Personas and Journey Maps](#4-user-personas)
5. [End-to-End Workflow Overview](#5-workflow-overview)
6. [Agent Architecture: Design Philosophy](#6-agent-architecture-philosophy)
7. [Agent 1: Requirements Parser](#7-requirements-parser)
8. [Agent 2: Supplier Discovery](#8-supplier-discovery)
9. [Agent 3: Supplier Qualification & Verification](#9-supplier-qualification)
10. [Agent 4: Comparison & Ranking Engine](#10-comparison-ranking)
11. [Agent 5: Intelligence Report Generator](#11-intelligence-report)
12. [Agent 6: RFQ Preparation & Outreach](#12-rfq-outreach)
13. [Agent 7: Response Ingestion & Structuring](#13-response-ingestion)
14. [Human-in-the-Loop Architecture](#14-human-in-the-loop)
15. [UX Script: Screen-by-Screen Walkthrough](#15-ux-script)
16. [State Management & Data Flow](#16-state-management)
17. [Tool Integration Layer](#17-tool-integration)
18. [Memory & Context Engineering](#18-memory-context)
19. [Model Tiering & Cost Strategy](#19-model-tiering)
20. [Reliability, Guardrails, and Error Handling](#20-reliability)
21. [Data Schemas & Contracts](#21-data-schemas)
22. [Infrastructure & Deployment](#22-infrastructure)
23. [Security & Multi-Tenancy](#23-security)
24. [Metrics, Observability, and Evaluation](#24-metrics)
25. [Implementation Roadmap](#25-roadmap)
26. [Appendix A: Automotive Procurement Glossary](#appendix-a)
27. [Appendix B: API Reference Summary](#appendix-b)
28. [Appendix C: Prompt Templates](#appendix-c)

---

## 1. Executive Summary

Procurement AI is an AI-powered procurement copilot purpose-built for the automotive supply chain. It serves buyers at Tier 1–4 suppliers and OEMs who need to find, vet, compare, and connect with suppliers for manufactured components — from metal stampings and die castings to injection-molded plastics and CNC-machined precision parts.

The automotive parts market exceeds $2 trillion globally, yet sourcing still runs on spreadsheets, email threads, tribal knowledge, and multi-month qualification cycles. Suppliers handle approximately 495 RFQs per year at $22K–$61K cost per bid. No existing AI procurement platform handles the industry's unique quality processes (PPAP, APQP, IATF 16949), multi-tier supplier structures, or engineering-specification-driven sourcing.

Procurement AI fills this gap not by replacing the buyer, but by augmenting them — acting as an intelligent copilot that autonomously discovers suppliers across all tiers, verifies their certifications and financial health through real APIs, builds comprehensive comparison matrices, generates structured RFQ packages, and manages the outreach lifecycle. The human buyer remains in command at every critical decision point, but the months of manual research, phone calls, and spreadsheet wrangling are compressed into hours.

**What Procurement AI does:**

- Accepts natural language procurement requests ("I need a Tier 2 supplier for aluminum die-cast EV battery housings, 50K annual volume, IATF 16949 required, preferably in Mexico for USMCA compliance")
- Autonomously searches Thomasnet, Google Places, trade databases, and the web to build a supplier longlist
- Verifies IATF 16949 certification, ISO credentials, financial health via D&B, and corporate registration
- Scrapes supplier websites to extract capabilities, equipment lists, materials expertise, and capacity
- Builds normalized comparison matrices with TCO analysis across qualified suppliers
- Generates professional RFQ packages with OEM-specific cost breakdown templates
- Sends RFQs via authenticated email, tracks responses, and parses incoming quotes into structured data
- Presents the buyer with a complete intelligence package: ranked suppliers, comparison tables, risk assessments, and parsed quotes — ready for the human to make the final decision and initiate direct contact

**What Procurement AI does not do:**

- It does not negotiate on behalf of the buyer
- It does not award contracts or issue purchase orders
- It does not make final supplier selection decisions
- It does not replace the buyer's judgment on fit, relationship, or strategic alignment

Procurement AI connects the human to the supplier with comprehensive intelligence. The human takes it from there.

---

## 2. The Problem: How Automotive Procurement Works Today

### 2.1 The Procurement Lifecycle

Automotive procurement follows a rigid, multi-stage process fundamentally different from general procurement. The typical flow spans 18–48 months from initial sourcing to Start of Production (SOP), with contracts lasting 5–7 years over a vehicle program's life.

**Stage 1 — Need Identification.** Engineering defines part specifications for a new vehicle program or engineering change. Cross-functional teams (procurement, engineering, quality, manufacturing) define requirements collaboratively. This stage produces the engineering drawing package, material specifications, tolerance requirements, and volume projections that drive all subsequent sourcing activity.

**Stage 2 — Supplier Discovery & RFI.** Buyers search Approved Supplier Lists (ASLs) first, then external databases. A Request for Information (RFI) collects capabilities, capacity, quality practices, and financial stability. Today this is overwhelmingly manual — buyers call contacts, email colleagues, search Thomasnet, attend trade shows, and rely on institutional memory. Over 55% of organizations report difficulties sourcing reliable suppliers.

**Stage 3 — Supplier Qualification.** New suppliers undergo financial assessment, capability audits, IATF 16949 certification verification, and often facility visits — a process taking 3–12 months. This is the most time-consuming pre-award phase and the one where tribal knowledge is most critical and most vulnerable to employee turnover.

**Stage 4 — RFQ Distribution.** Formal RFQs sent to 3–8 pre-qualified suppliers with precise specifications, OEM-specific cost breakdown templates, and response windows of 1–8 weeks (typically 2 weeks). Each OEM mandates its own proprietary cost breakdown format, multiplying administrative burden.

**Stage 5 — Quote Evaluation.** OEMs conduct should-cost analysis, compare bids across detailed cost breakdowns (material, labor, overhead, SGA, profit), and evaluate across multiple dimensions: price, quality capability, delivery performance, geographic fit, financial stability, and strategic alignment.

**Stage 6 — Award & Contracting.** The buyer selects a supplier and initiates contract negotiation, tooling orders, and the APQP/PPAP process. This is where Procurement AI's involvement ends — the buyer has been connected to the right supplier with all the intelligence they need.

### 2.2 What Makes Automotive Categorically Different

General procurement platforms fail in automotive because they don't account for:

**Full cost transparency.** Automotive operates on open-book accounting. Suppliers must break down piece prices into material (by weight and commodity price), labor (by operation and rate), overhead, SGA, and profit margin. This isn't optional — it's contractually required and audited.

**Massive tooling investments.** A single stamping die costs $50K–$500K+. Die casting molds run $100K–$1M. These are typically OEM-owned assets housed at the supplier, creating complex ownership and amortization dynamics.

**Extreme switching costs.** Changing suppliers means retooling ($50K–$500K), resubmitting PPAP (3–6 months), requalifying at the OEM (1–3 months), and managing dual-source transition. This makes initial supplier selection enormously consequential.

**USMCA rules of origin.** North American automotive requires 75% Regional Value Content for duty-free treatment, 70% North American steel/aluminum content, and 40–45% high-wage ($16/hr+) labor value content. The share of vehicles from Canada/Mexico paying duties rose from 0.5% ($517M) in 2019 to 8.2% ($8.9B) in 2023. Supplier geography is not just a logistics consideration — it's a trade compliance requirement.

**Customer-Specific Requirements.** Each OEM (GM, Ford, Toyota, VW, Stellantis) mandates its own proprietary requirements layered on top of IATF 16949. A supplier serving three OEMs must maintain three different quality systems, three different cost breakdown templates, and three different reporting formats.

### 2.3 The Supply Pyramid

A modern vehicle contains approximately 30,000 individual parts sourced from hundreds of suppliers across 4–5 tiers:

**Tier 1** (Bosch, Denso, Continental, Magna, ZF, Gestamp): Finished assemblies and systems delivered directly to OEMs — seat modules, powertrain components, electrical systems, ADAS modules. Work JIT/JIS, hold IATF 16949, co-develop with OEMs.

**Tier 2**: Specialized components for Tier 1 — precision stampings, PCBAs, fuel injectors, LED modules, seating foam. The sweet spot for Procurement AI, as these suppliers are numerous, varied in capability, and harder to discover.

**Tier 3**: Basic parts and raw materials — fasteners, wire, basic machined components, seals, gaskets. High volume, lower complexity, but critical for supply chain resilience.

**Tier 4**: Raw materials — steel mills, aluminum smelters, resin producers. Procurement AI serves these users primarily as buyers seeking Tier 3 components for their processing operations.

**OEMs** (GM, Ford, Toyota, VW, Stellantis, BMW, Hyundai-Kia): The apex buyers. Their procurement teams source from Tier 1 directly but increasingly need visibility into Tier 2–4 for supply chain risk management.

### 2.4 Part Categories and Their Sourcing Characteristics

| Category | Typical Tooling Cost | Tooling Lead Time | MOQ Range | Key Sourcing Regions |
|---|---|---|---|---|
| Metal Stampings | $50K–$300K | 12–20 weeks | 1,000–50,000 | US Midwest, Mexico, China |
| Aluminum Die Castings | $100K–$500K | 16–24 weeks | 500–10,000 | Mexico, China, India, US South |
| Plastics Injection Molding | $30K–$200K | 16–20 weeks | 1,000–100,000 | US, Mexico, China |
| CNC Machined Parts | $2K–$20K | 2–6 weeks | 50–500 | US, Germany, Japan, India |
| Electronics/PCBAs | $5K–$50K | 8–16 weeks | 500–5,000 | China, Vietnam, Mexico |
| Wiring Harnesses | $10K–$50K | 8–12 weeks | 1,000–50,000 | Mexico, Morocco, Romania |
| Forgings | $50K–$200K | 12–20 weeks | 500–5,000 | India, China, US, Germany |
| Rubber/Sealing | $20K–$100K | 10–16 weeks | 5,000–100,000 | US, Mexico, Germany |

### 2.5 The Pain Points Procurement AI Addresses

**Discovery is fragmented and manual.** Buyers search Thomasnet, call contacts, email industry peers, attend IMTS or FABTECH, and comb through old supplier files. Finding a qualified Tier 2 aluminum die caster in Guanajuato with IATF 16949 and $50M+ revenue takes weeks of manual research.

**Qualification is slow and paper-heavy.** Verifying a supplier's IATF 16949 certification means accessing the IATF Customer Portal. Checking financial health means pulling D&B reports. Validating capabilities means reviewing their website, requesting capability presentations, and often scheduling facility visits. Each step is manual and sequential.

**Quote comparison is spreadsheet hell.** Each supplier submits quotes in different formats, with different assumptions about volume, tooling, packaging, and logistics. Normalizing 5 quotes into an apples-to-apples comparison takes a senior buyer 4–8 hours per part number.

**Institutional knowledge walks out the door.** Critical pricing benchmarks, supplier relationships, quality history, and market intelligence often exist only in buyers' heads. When experienced buyers retire or change jobs, their knowledge disappears.

**RFQ creation is repetitive.** Writing a professional RFQ package with specifications, quality requirements, commercial terms, and response templates takes 2–4 hours per part number. For a new vehicle program with 200+ sourced parts, this is a crushing administrative burden.

---

## 3. Procurement AI's Value Proposition

### 3.1 The Copilot Model

Procurement AI operates as a copilot, not an autopilot. The distinction is fundamental to the system's design:

**Copilot means:** Procurement AI handles research, verification, analysis, document generation, and outreach logistics. It processes information at a scale and speed impossible for a human buyer — searching dozens of databases, scraping hundreds of supplier websites, verifying certifications via APIs, normalizing quotes across different formats, and generating professional RFQ packages.

**Copilot means:** The human buyer retains all decision authority. They approve the supplier longlist before RFQs go out. They review comparison matrices and add qualitative judgment. They decide which suppliers to pursue. They conduct phone calls, facility visits, and relationship-building. They make the award decision.

**The handoff point is explicit:** Procurement AI's job is to connect the buyer to the right suppliers with comprehensive intelligence. The buyer's job is to evaluate, decide, and build the relationship. Procurement AI stops at connection — it does not negotiate, does not award, does not execute.

### 3.2 The Intelligence Advantage

Procurement AI provides what no human buyer can assemble alone:

- **Exhaustive discovery**: Search Thomasnet (500K+ suppliers), Google Places, trade databases (ImportGenius, Panjiva), industry directories, and the open web simultaneously
- **Real-time verification**: Check IATF 16949 certification status, ISO credentials, D&B financial scores, and corporate registrations via live APIs — not stale databases
- **Structured extraction**: Convert unstructured supplier websites into structured capability profiles using LLM-powered extraction
- **Normalized comparison**: Transform diverse quote formats into standardized TCO matrices with consistent assumptions
- **Institutional memory**: Every search, every supplier profile, every quote comparison is stored and searchable — knowledge never walks out the door
- **Speed**: Compress weeks of manual research into hours of supervised autonomous work

### 3.3 Who Uses Procurement AI

| Persona | Title | Use Case | Value |
|---|---|---|---|
| Commodity Buyer | Purchasing Manager, Commodity Manager | Source specific part categories for new programs or cost reduction | 80% reduction in supplier discovery time |
| Strategic Sourcer | Director of Procurement, VP Supply Chain | Evaluate supply base options for strategic decisions | Comprehensive market intelligence on demand |
| Quality Engineer | SQE, Quality Manager | Pre-screen suppliers for certification and capability | Automated verification of IATF/ISO credentials |
| Program Buyer | Program Procurement Lead | Source full BOM for new vehicle programs | Parallel sourcing across hundreds of part numbers |
| Supply Chain Risk Mgr | Risk Manager, Resilience Lead | Identify alternative suppliers for risk mitigation | Multi-tier supply chain visibility |

---

## 4. User Personas and Journey Maps

### 4.1 Primary Persona: Sarah — Commodity Buyer at a Tier 1 Supplier

**Background:** Sarah is a Commodity Buyer at a Tier 1 automotive supplier (annual revenue $2B) specializing in seating systems. She manages stamped metal brackets, CNC-machined adjustment mechanisms, and injection-molded trim components. She sources from Tier 2 and Tier 3 suppliers across North America and Mexico.

**Current workflow (without Procurement AI):**
1. Receives engineering change notice requiring a new bracket design — Day 1
2. Searches Thomasnet manually, asks colleagues for recommendations — Days 1–5
3. Emails 10 potential suppliers asking for capability information — Day 5
4. Waits for responses, follows up with non-responders — Days 5–15
5. Reviews capability presentations, checks certifications manually — Days 15–20
6. Narrows to 5 qualified suppliers, prepares RFQ package in Excel — Days 20–25
7. Sends RFQs, waits for responses — Days 25–40
8. Receives quotes in various formats, normalizes in spreadsheet — Days 40–45
9. Presents comparison to management, selects shortlist — Days 45–50
10. Initiates supplier visits and detailed technical discussions — Day 50+

**With Procurement AI:**
1. Describes requirement to Procurement AI in natural language — Hour 0
2. Reviews Procurement AI's parsed requirements for accuracy, approves — Hour 1
3. Procurement AI discovers 40+ potential suppliers, presents ranked longlist — Hour 4
4. Sarah reviews longlist, selects 8–10 for RFQ — Hour 5
5. Procurement AI generates RFQ packages, Sarah reviews and approves — Hour 6
6. Procurement AI sends RFQs via authenticated email — Hour 7
7. Supplier responses arrive over 1–2 weeks — Days 7–14
8. Procurement AI parses quotes into structured comparison matrix — Day 14
9. Sarah reviews comparison with full intelligence package — Day 15
10. Sarah contacts top 3 suppliers directly for discussions — Day 16

**Time savings: 50 days → 16 days (68% reduction), with dramatically richer intelligence at each stage.**

### 4.2 Secondary Persona: Carlos — Quality Engineer Supporting Supplier Selection

Carlos is a Supplier Quality Engineer at an OEM. He doesn't initiate sourcing but is a critical stakeholder in qualification. His primary frustration: buyers present him with supplier candidates that lack basic certifications, forcing him to reject late in the process and restart.

**With Procurement AI:** Certification verification happens automatically during discovery. By the time Carlos reviews candidates, every supplier on the shortlist has verified IATF 16949, confirmed ISO 14001 if required, and passed financial health screening. Carlos's review focuses on capability depth and technical fit — the high-value work — rather than certificate chasing.

### 4.3 Tertiary Persona: Miguel — Owner of a Tier 3 Stamping Shop

Miguel owns a 50-person stamping shop in Querétaro, Mexico. He holds IATF 16949 and wants to win more Tier 1 and Tier 2 business, but struggles with visibility — large buyers don't know he exists.

**With Procurement AI (as a discovered supplier):** Procurement AI's discovery engine finds Miguel's company through Thomasnet listings, Google Places results, IATF certificate databases, and web scraping of his company website. His structured capability profile — IATF 16949 certified, 200-ton to 800-ton press range, aluminum and steel, 50M parts/year capacity — enters the comparison matrix alongside larger competitors. Procurement AI levels the playing field by evaluating capability against requirement, not brand recognition.

---

## 5. End-to-End Workflow Overview

### 5.1 The Seven-Stage Pipeline

Procurement AI's procurement pipeline proceeds through seven discrete stages, each handled by a specialized agent. The pipeline is modeled as a LangGraph StateGraph — a directed graph with typed state, conditional edges, and human-in-the-loop interrupt gates.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PROCUREMENT PIPELINE                              │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ REQUIRE- │    │ SUPPLIER │    │ SUPPLIER │    │ COMPARE  │     │
│  │  MENTS   │───▶│ DISCOVER │───▶│ QUALIFY  │───▶│ & RANK   │     │
│  │  PARSER  │    │          │    │          │    │          │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│       │               │               │               │            │
│       ▼               ▼               ▼               ▼            │
│   [Human:         [Human:         [Human:         [Human:          │
│    Confirm]        Review          Review          Review           │
│                    Longlist]       Shortlist]      Rankings]        │
│                                                       │            │
│                                                       ▼            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                     │
│  │ RESPONSE │    │   RFQ    │    │ INTELLI- │                     │
│  │ INGESTION│◀───│ OUTREACH │◀───│  GENCE   │                     │
│  │          │    │          │    │  REPORT  │                     │
│  └──────────┘    └──────────┘    └──────────┘                     │
│       │               │               │                            │
│       ▼               ▼               ▼                            │
│   [Human:         [Human:         [Human:                          │
│    Review          Approve         Review                          │
│    Parsed          Send]           Report]                         │
│    Quotes]                                                         │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────────────────────┐                                  │
│  │   FINAL INTELLIGENCE PACKAGE │                                  │
│  │   → Buyer takes over         │                                  │
│  │   → Direct supplier contact  │                                  │
│  │   → Procurement AI stops here        │                                  │
│  └──────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Stage Summaries

| Stage | Agent | Input | Output | Model | HITL Gate |
|---|---|---|---|---|---|
| 1. Requirements Parsing | Requirements Parser | Natural language request | Structured procurement spec | Haiku 4.5 | Confirm/Edit |
| 2. Supplier Discovery | Discovery Agent | Structured spec | Ranked supplier longlist (20–50) | Sonnet 4.5 | Review/Filter |
| 3. Supplier Qualification | Qualification Agent | Supplier longlist | Verified shortlist (5–15) | Sonnet 4.5 + APIs | Review/Approve |
| 4. Comparison & Ranking | Comparison Engine | Verified suppliers | Normalized ranking matrix | Sonnet 4.5 | Review |
| 5. Intelligence Report | Report Generator | All accumulated data | Per-supplier intelligence briefs | Sonnet 4.5 | Review |
| 6. RFQ & Outreach | Outreach Agent | Approved suppliers + spec | Sent RFQs with tracking | Sonnet 4.5 | Approve Send |
| 7. Response Ingestion | Response Parser | Incoming emails + attachments | Structured quote comparison | Haiku 4.5 + Sonnet 4.5 | Review Parsed Data |

### 5.3 Pipeline Timing

For a typical single-part sourcing request:

- **Stage 1** (Requirements Parsing): 30 seconds – 2 minutes
- **Stage 2** (Supplier Discovery): 5 – 30 minutes (depending on search breadth)
- **Stage 3** (Supplier Qualification): 10 – 60 minutes (API calls, web scraping)
- **Stage 4** (Comparison & Ranking): 2 – 10 minutes
- **Stage 5** (Intelligence Report): 5 – 15 minutes
- **Stage 6** (RFQ Outreach): Minutes to send, days to weeks for responses
- **Stage 7** (Response Ingestion): Minutes per response as they arrive

**Total active processing time (Stages 1–5): 30 minutes to 2 hours.**
**Total calendar time including human reviews and supplier responses: 2–4 weeks.**

This compares to 6–12 weeks for the same process done entirely manually.

---

## 6. Agent Architecture: Design Philosophy

### 6.1 Why Composable Patterns Over Complex Frameworks

Anthropic's research across hundreds of enterprise agent deployments reveals a counterintuitive finding: the most successful production systems use simple, composable patterns rather than complex multi-agent orchestration frameworks. The field has matured from experimental demos to production systems processing billions of tokens monthly, and the lesson is clear — simplicity scales better than sophistication.

Procurement AI's architecture follows this principle rigorously. Rather than deploying a fully autonomous multi-agent swarm, Procurement AI implements a **supervised workflow pipeline** — each stage is a specialized node in a LangGraph StateGraph, connected by deterministic edges with conditional routing and human-in-the-loop interrupt gates.

This is Anthropic's **Prompt Chaining** pattern at its core: a fixed sequence of steps where each LLM call processes the output of the previous one, with programmatic gates between steps to verify intermediate outputs. The tradeoff is predictability and debuggability in exchange for linear latency growth — exactly right for procurement, where correctness matters more than speed and the workflow stages are well-defined.

Where Procurement AI departs from simple chaining is at decision points: if the Qualification Agent finds no qualified suppliers, it routes back to Discovery with expanded criteria (the **Routing** pattern). Within the Discovery Agent, multiple data sources are searched simultaneously (the **Parallelization** pattern, specifically the "sectioning" variant for independent subtasks). The Intelligence Report generation uses the **Orchestrator-Workers** pattern, with a lead agent delegating per-supplier research to parallel worker subagents.

### 6.2 Single-Agent vs. Multi-Agent Decision

Anthropic recommends single agents when the task is focused, context fits one window, fewer than 10–15 tools are needed, and speed matters. Multi-agent systems are warranted when tasks naturally decompose into parallel independent subtasks, when different stages need radically different prompts or tools, or when a single agent has too many tools and makes poor selection decisions.

Procurement AI is a **hybrid**: the overall pipeline is a single orchestrated workflow (not a multi-agent debate), but individual stages may spawn subagents for parallelization. The Discovery Agent, for example, runs parallel subagents for Thomasnet search, Google Places search, trade database queries, and web search — each with focused toolsets and isolated context windows. This follows the emerging architectural convergence observed by practitioners: **Plan agents** (discovery and process optimization), **Execution agents** (building given a plan), and **Task agents** (transient sub-agents for parallel or isolated operations).

### 6.3 LangGraph as the Orchestration Layer

LangGraph provides the strongest production fit for Procurement AI's requirements:

- **Explicit state management**: The `ProcurementState` TypedDict flows through all agents with typed fields and annotated reducers
- **Conditional routing**: `add_conditional_edges` handles branching logic (e.g., insufficient qualified suppliers → expand discovery)
- **Native HITL via `interrupt()`**: The graph pauses at approval gates, persists state to PostgreSQL via `PostgresSaver`, and resumes when human input arrives — this works across machine restarts and can wait days or weeks
- **Production-grade persistence**: `PostgresSaver` with cursor-based pagination and versioned checkpoints enables long-running procurement workflows
- **Subgraph composition**: Complex stages (like qualification with parallel verification steps) are composed as subgraphs with fan-out parallelism using `Send` API
- **LangSmith integration**: Full tracing and debugging for every agent decision

The alternatives were evaluated and rejected for specific reasons. CrewAI's role-based metaphor is intuitive but offers limited persistence and deterministic flow control. AutoGen's conversation-driven approach is less suitable for procurement's rigid stage gates. The Claude Agent SDK was considered for individual agent implementations but LangGraph provides superior workflow orchestration for the multi-stage pipeline.

### 6.4 Context Engineering Over Prompt Engineering

The field has undergone a fundamental shift from prompt engineering (crafting optimal instruction strings) to **context engineering** (curating the entire information environment at each inference step). For Procurement AI, this means:

- **System prompts at the right altitude**: Specific enough to direct procurement-domain behavior, flexible enough for the model to handle novel part categories and supplier configurations. Every token earns its place.
- **Dynamic tool loading**: Not all tools are available to all agents. The Requirements Parser has no web scraping tools. The Discovery Agent has search tools but no email tools. This prevents tool selection confusion — when systems grow beyond 10 tools, selection accuracy degrades.
- **Progressive context disclosure**: Agents receive only the state fields relevant to their stage. The Outreach Agent doesn't need raw search results from Discovery — it needs the approved supplier shortlist and the structured RFQ document.
- **Structured output schemas**: Every agent-to-agent data contract is defined as a Pydantic model, enforced via Claude's structured outputs (beta). This eliminates parsing failures between stages.

### 6.5 The Think Tool for Critical Decisions

For complex agentic tasks, Claude offers a "think" tool for structured reflection during response generation, particularly between tool calls. Anthropic's benchmarks show a 54% improvement on complex domain tasks when the think tool is combined with an optimized prompt instructing the agent to:

1. List the specific rules and criteria that apply to the current decision
2. Check if all required information has been collected
3. Verify that the planned action complies with all procurement policies
4. Iterate over tool results for correctness and completeness

Procurement AI deploys the think tool at three critical junctures:
- **After supplier discovery results arrive**: The agent reflects on coverage, identifies gaps, and decides whether to expand search
- **During qualification assessment**: The agent weighs certification status, financial health, and capability match before rendering a verdict
- **Before RFQ generation**: The agent reviews the complete specification against the supplier's known capabilities to ensure the RFQ is appropriately targeted

---

## 7. Agent 1: Requirements Parser

### 7.1 Purpose

The Requirements Parser transforms natural language procurement requests into structured, machine-readable specifications that drive all downstream agents. It is the front door of the system — the quality of its output determines the quality of everything that follows.

### 7.2 Input

Natural language from the buyer, which may range from highly specific:

> "I need a Tier 2 supplier for progressive-die stamped steel brackets, SPCC material, ±0.1mm tolerances, 75,000 annual volume in lots of 5,000, IATF 16949 required, e-coat finish, preferably within 500 miles of our plant in Chattanooga TN for JIT delivery."

To vague:

> "We need someone to make some aluminum parts for us, probably casting, maybe 10-20 thousand a year."

### 7.3 Processing Logic

The agent uses Claude Haiku 4.5 ($1/$5 per MTok) with a structured output schema. Processing steps:

1. **Extract explicit requirements**: Part type, material, process, volume, tolerances, certifications, geography, timeline
2. **Infer implicit requirements**: If the user mentions "automotive" and doesn't specify certifications, infer IATF 16949 is likely required. If volume exceeds 10,000/year, infer tooled production (not prototype)
3. **Identify ambiguities**: Flag fields that are missing or unclear for human confirmation
4. **Classify complexity**: Simple (single process, standard material) vs. complex (multi-operation, specialty alloy, tight tolerances)
5. **Estimate market parameters**: Based on part category, estimate typical tooling costs, lead times, and MOQ ranges from embedded domain knowledge

### 7.4 Output Schema

```python
class ParsedRequirement(BaseModel):
    # Part identification
    part_description: str
    part_category: Literal["stamping", "die_casting", "injection_molding",
                           "cnc_machining", "forging", "pcba", "wiring_harness",
                           "rubber_sealing", "assembly", "other"]

    # Material
    material_family: str  # e.g., "steel", "aluminum", "plastic"
    material_spec: Optional[str]  # e.g., "SPCC", "A380", "PA66-GF30"

    # Process
    manufacturing_process: str
    secondary_operations: list[str]  # e.g., ["e-coat", "heat treat", "machining"]

    # Volume
    annual_volume: int
    lot_size: Optional[int]
    volume_confidence: Literal["exact", "estimated", "unknown"]

    # Quality
    tolerances: Optional[str]
    surface_finish: Optional[str]
    certifications_required: list[str]  # e.g., ["IATF 16949", "ISO 14001"]
    ppap_level: Optional[Literal["1", "2", "3", "4", "5"]]

    # Geography
    preferred_regions: list[str]
    geographic_constraints: Optional[str]  # e.g., "USMCA compliant"
    max_distance_miles: Optional[int]
    buyer_plant_location: Optional[str]

    # Timeline
    prototype_needed: bool
    prototype_quantity: Optional[int]
    target_sop_date: Optional[str]
    urgency: Literal["standard", "expedited", "urgent"]

    # Supplier preferences
    preferred_tier: Optional[Literal["tier1", "tier2", "tier3", "tier4"]]
    min_revenue: Optional[int]
    min_employees: Optional[int]

    # Meta
    ambiguities: list[str]  # Fields needing human clarification
    complexity_score: Literal["simple", "moderate", "complex"]
    estimated_tooling_range: str  # e.g., "$50K–$150K"
    estimated_lead_time: str  # e.g., "12–16 weeks tooling"
```

### 7.5 Human-in-the-Loop Gate

After parsing, the structured requirement is presented to the buyer for confirmation. The UI shows:
- All extracted fields with source highlighting (which part of the original text each field came from)
- Flagged ambiguities with suggested defaults and prompts for clarification
- Inferred fields clearly marked as "inferred — please confirm"
- An "Edit" capability for every field

The buyer can modify any field before approving. Approval triggers the Discovery Agent.

### 7.6 Prompt Template (Abbreviated)

```xml
<system>
You are an automotive procurement requirements parser. Your job is to extract
structured procurement specifications from natural language buyer requests.

<domain_knowledge>
- Automotive parts are sourced through a tiered supply chain (Tier 1–4)
- IATF 16949 is the automotive quality management standard
- Common manufacturing processes: stamping, die casting, injection molding,
  CNC machining, forging, PCBA assembly, wiring harness
- Standard materials by process: steel (stamping, forging), aluminum (casting,
  machining), engineering plastics (injection molding)
- Typical MOQs range from 50 (CNC) to 100,000+ (fasteners)
</domain_knowledge>

<instructions>
1. Extract every explicit requirement from the user's message
2. Infer implicit requirements based on automotive domain knowledge
3. Flag any critical ambiguities that must be resolved before searching
4. Do NOT hallucinate specifications — if uncertain, flag as ambiguous
5. If the user mentions a specific OEM customer, note their CSR requirements
</instructions>
</system>
```

---

## 8. Agent 2: Supplier Discovery

### 8.1 Purpose

The Discovery Agent is the most tool-intensive agent in the pipeline. It searches multiple databases, directories, and the open web to build a comprehensive longlist of potential suppliers matching the parsed requirements. Its goal is **recall** — cast a wide net to ensure no strong candidate is missed.

### 8.2 Data Sources and Search Strategy

The Discovery Agent orchestrates parallel searches across multiple sources using LangGraph's `Send` API for fan-out parallelism:

**Source 1 — Thomasnet (via Browserbase + Playwright)**
Thomasnet has 500,000+ US suppliers across 78,000+ categories with certification filters. No public API exists, so Procurement AI uses Browserbase cloud browser instances to automate searches. The Browserbase Contexts API persists cookies and browser state across sessions for reliable access. Search queries are constructed from the parsed requirement: `"{manufacturing_process} {material_family}" near "{preferred_region}" IATF 16949`.

**Source 2 — Google Places API**
Google Places Text Search discovers manufacturers by keyword and location. Queries like "CNC machining shop Detroit" or "aluminum die casting manufacturer Guanajuato" return business name, address, phone, website, rating, and reviews. After March 2025 pricing changes, Essentials-tier requests provide 10,000 free per month. This is the broadest geographic search, catching small shops that may not be listed on industrial directories.

**Source 3 — Trade Data (ImportGenius / Panjiva)**
ImportGenius tracks 258M+ import shipments from US customs data. Searching an OEM or Tier 1 name reveals their overseas suppliers with shipment volumes, product descriptions, and shipping routes. This is powerful for identifying proven suppliers who already serve the automotive industry — if a supplier ships automotive stampings to Magna, they're a credible candidate. ImportGenius API starts at ~$149/month; Panjiva (S&P Global) covers 2B+ records across 190+ countries.

**Source 4 — Industry Directories and Marketplaces**
MFG.com connects 26,000+ parts manufacturers with intelligent RFQ routing. Xometry's platform holds IATF 16949 certification and supports PPAP documentation. For Asian sourcing, Alibaba (200,000+ suppliers) and IndiaMART (60M+ products) provide initial leads requiring deeper verification.

**Source 5 — Web Search (via Firecrawl)**
Firecrawl converts websites into clean, LLM-ready markdown with built-in JavaScript rendering and anti-bot handling. The Agent endpoint can autonomously search for "IATF 16949 certified stamping suppliers in Michigan" and extract structured data. This catches suppliers who have web presence but aren't listed on major directories.

**Source 6 — Internal Database**
Procurement AI's own Supabase database of previously discovered and profiled suppliers, searchable via pgvector semantic similarity. Over time, this becomes the most valuable source as the system accumulates institutional knowledge.

### 8.3 Search Orchestration

```python
# Simplified discovery subgraph
discovery_graph = StateGraph(DiscoveryState)

# Parallel source searches
discovery_graph.add_node("thomasnet_search", search_thomasnet)
discovery_graph.add_node("google_places_search", search_google_places)
discovery_graph.add_node("trade_data_search", search_trade_databases)
discovery_graph.add_node("web_search", search_web_firecrawl)
discovery_graph.add_node("internal_db_search", search_internal_database)

# Fan-out: all searches run in parallel
discovery_graph.add_conditional_edges(
    START,
    lambda state: [
        Send("thomasnet_search", state),
        Send("google_places_search", state),
        Send("trade_data_search", state),
        Send("web_search", state),
        Send("internal_db_search", state),
    ]
)

# Fan-in: merge and deduplicate results
discovery_graph.add_node("merge_and_rank", merge_deduplicate_rank)
```

### 8.4 Deduplication and Initial Ranking

Raw results from 5+ sources contain heavy duplication. The merge step:

1. **Normalize company names**: Strip Inc/LLC/Corp suffixes, standardize casing, handle DBA names
2. **Match on multiple signals**: Name similarity (fuzzy matching), address proximity, phone number, website domain
3. **Merge profiles**: Combine information from multiple sources into a single enriched profile
4. **Initial ranking**: Score each supplier on:
   - **Capability match** (0–100): Does the supplier's known process/material/equipment match the requirement?
   - **Certification match** (0/50/100): Has required certifications / has related certifications / unknown
   - **Geographic fit** (0–100): Distance from buyer plant, USMCA eligibility
   - **Scale fit** (0–100): Revenue/employee count appropriate for the volume
   - **Data richness** (0–100): How much information was found (more data = higher confidence)

### 8.5 Output

A ranked longlist of 20–50 suppliers, each with:

```python
class DiscoveredSupplier(BaseModel):
    supplier_id: str  # Internal UUID
    company_name: str
    headquarters: str
    manufacturing_locations: list[str]
    website: Optional[str]
    phone: Optional[str]
    email: Optional[str]

    # Discovery metadata
    sources: list[str]  # Which databases found this supplier
    initial_score: float  # 0–100 composite
    capability_match: float
    certification_match: float
    geographic_fit: float
    scale_fit: float
    data_richness: float

    # Known information (may be partial)
    known_processes: list[str]
    known_materials: list[str]
    known_certifications: list[str]
    employee_count: Optional[int]
    estimated_revenue: Optional[str]

    # Flags
    previously_known: bool  # In internal database
    trade_data_confirmed: bool  # Found in import/export records
```

### 8.6 Human-in-the-Loop Gate

The buyer reviews the longlist in a sortable, filterable table. They can:
- Remove suppliers they know are unsuitable (prior bad experience, conflict of interest, etc.)
- Add suppliers they know about that weren't found
- Adjust ranking weights (e.g., "geographic fit is most important for this project")
- Approve the list to proceed to Qualification

If the buyer finds the list inadequate (too few candidates, wrong region, wrong capability), they can request expanded search with modified parameters, which routes back to Discovery.

---

## 9. Agent 3: Supplier Qualification & Verification

### 9.1 Purpose

The Qualification Agent transforms the buyer-approved longlist into a verified shortlist by checking each supplier against hard criteria (certifications, financial health, legal standing) and soft criteria (website quality, capability depth, industry experience). This is where Procurement AI's API integrations deliver the most value — automating weeks of manual verification into minutes of parallel API calls.

### 9.2 Verification Checks (Parallel Subgraph)

Each supplier undergoes five verification checks, executed in parallel via a LangGraph subgraph:

**Check 1 — IATF 16949 Certification (IATF Customer Portal)**
IATF 16949 certificates are verified exclusively through the IATF Customer Portal (not IAF CertSearch, which only covers ~31% of ISO certificates). The check confirms: certificate exists, certificate is active (not suspended or withdrawn), certified scope covers the required manufacturing process, and the certified site location matches. Result: `verified` / `expired` / `suspended` / `not_found`.

**Check 2 — Financial Health (Dun & Bradstreet Direct+ API)**
D&B provides financial risk assessment via the D&B Direct+ REST API — 500M entities across 220+ countries with 5M daily updates. Key data points: D&B Rating, PAYDEX score (payment behavior), financial stress score, number of employees, estimated revenue, years in business, legal structure, and any bankruptcy/lien filings. Enterprise pricing (~$10K+/year). Result: `low_risk` / `moderate_risk` / `high_risk` / `insufficient_data`.

**Check 3 — Corporate Registration (OpenCorporates API)**
OpenCorporates provides 190M+ companies from 140 jurisdictions via a free REST API. Confirms: company is registered and active, registration date, registered agent, jurisdiction. Cross-reference with D&B data for consistency. Result: `confirmed` / `discrepancy` / `not_found`.

**Check 4 — Website Intelligence (Firecrawl Schema Extraction)**
Firecrawl's schema-driven extraction converts the supplier's website into structured data. Define a Pydantic model:

```python
class WebsiteCapabilities(BaseModel):
    company_description: str
    manufacturing_processes: list[str]
    materials_processed: list[str]
    equipment_list: list[str]  # e.g., "600-ton stamping press", "DMG Mori 5-axis CNC"
    certifications_claimed: list[str]
    industries_served: list[str]
    key_customers: list[str]  # If publicly listed
    capacity_indicators: list[str]  # e.g., "200,000 sq ft facility"
    secondary_operations: list[str]
    prototype_capability: bool
    geographic_notes: str
```

Firecrawl returns structured JSON extracted from the supplier's website, regardless of site complexity. The `/v2/extract` endpoint uses LLM-powered extraction. Result: structured capability profile.

**Check 5 — Review & Reputation (Google Places + Web)**
Google Places provides ratings and review counts. Firecrawl can extract Glassdoor employee reviews, BBB ratings, and industry forum mentions. For automotive specifically, search for the supplier name + "quality issue" or "delivery problem" to surface any publicly known issues. Result: reputation score with supporting evidence.

### 9.3 Qualification Decision Logic

After all five checks complete, the Qualification Agent uses Claude Sonnet 4.5 with the think tool to render a verdict:

```
QUALIFIED: All hard criteria met (active IATF 16949, acceptable financial risk,
           confirmed registration), capability match ≥ 70%, no disqualifying flags

CONDITIONALLY QUALIFIED: Most criteria met but with noted gaps
           (e.g., IATF 16949 covers different scope, moderate financial risk,
           limited capacity for required volume). Flagged for buyer review.

DISQUALIFIED: Hard criteria failed (no IATF 16949, high financial risk,
              company dissolved, capability mismatch). Reason documented.
```

### 9.4 Output

```python
class QualifiedSupplier(BaseModel):
    supplier_id: str
    company_name: str
    qualification_status: Literal["qualified", "conditional", "disqualified"]

    # Verification results
    iatf_status: str  # "verified_active", "expired", "not_found", etc.
    iatf_cert_number: Optional[str]
    iatf_scope: Optional[str]
    iatf_expiry: Optional[str]

    financial_risk: str  # "low", "moderate", "high"
    duns_number: Optional[str]
    paydex_score: Optional[int]
    estimated_revenue: Optional[str]
    employee_count: Optional[int]
    years_in_business: Optional[int]

    corporate_status: str  # "active", "inactive", "not_found"

    capabilities: WebsiteCapabilities  # Extracted from website

    reputation_score: float  # 0–100
    google_rating: Optional[float]
    review_count: Optional[int]

    # Qualification rationale
    strengths: list[str]
    concerns: list[str]
    disqualification_reason: Optional[str]
    overall_confidence: float  # 0–1
```

### 9.5 Human-in-the-Loop Gate

The buyer reviews the qualified shortlist with full verification details. For each supplier, they see:
- Qualification status with traffic-light indicator (green/yellow/red)
- All verification details expandable
- Strengths and concerns summarized
- Option to override: promote a conditional supplier to qualified, or demote a qualified supplier

The buyer approves the shortlist (typically 5–15 suppliers) to proceed to Comparison.

---

## 10. Agent 4: Comparison & Ranking Engine

### 10.1 Purpose

The Comparison Agent normalizes all accumulated supplier intelligence into a structured, side-by-side comparison matrix. Its job is to make the buyer's evaluation as effortless as possible by presenting comparable data in a consistent format with clear differentiation.

### 10.2 Comparison Dimensions

The agent evaluates qualified suppliers across six weighted dimensions:

**Capability Fit (25% default weight)**
- Process match: exact match vs. related capability
- Material expertise: specialty vs. general
- Equipment adequacy: press tonnage, machine envelope, production rate
- Secondary operations: in-house vs. outsourced
- Prototype capability: dedicated prototype shop vs. production tooling only

**Quality Profile (25% default weight)**
- IATF 16949 status and scope coverage
- Additional certifications (ISO 14001, NADCAP, AS9100)
- PPM rates if available from public data or trade records
- Quality management maturity indicators from website analysis

**Geographic & Logistics (20% default weight)**
- Distance from buyer plant
- USMCA compliance (for North American sourcing)
- Proximity to OEM assembly plants
- Regional labor cost benchmarks
- Logistics infrastructure (port access, rail, highway)

**Financial Stability (15% default weight)**
- D&B risk rating
- PAYDEX score
- Revenue adequacy for the contract size
- Years in business
- Ownership structure (private, PE-backed, family-owned, public)

**Scale & Capacity (10% default weight)**
- Employee count relative to volume requirement
- Facility size and number of locations
- Current utilization indicators (if available)
- Growth trajectory indicators

**Market Reputation (5% default weight)**
- Google rating and review volume
- Known industry reputation
- Customer references (if publicly listed)
- Trade show presence and industry engagement

### 10.3 Normalization

All dimensions are scored 0–100 and combined using the weighted formula. The buyer can adjust weights from the UI before the comparison runs. The agent uses Claude Sonnet 4.5 to generate both the quantitative scores and qualitative narratives explaining each score.

### 10.4 Output

```python
class ComparisonMatrix(BaseModel):
    requirement_summary: str
    comparison_date: str
    weight_profile: dict[str, float]  # dimension → weight

    suppliers: list[SupplierComparison]

    overall_ranking: list[str]  # Supplier IDs in ranked order
    top_recommendation: str  # Supplier ID
    recommendation_rationale: str

class SupplierComparison(BaseModel):
    supplier_id: str
    company_name: str

    # Scores by dimension
    capability_score: float
    quality_score: float
    geographic_score: float
    financial_score: float
    scale_score: float
    reputation_score: float
    composite_score: float

    # Narratives
    capability_narrative: str
    quality_narrative: str
    geographic_narrative: str
    financial_narrative: str

    # Differentiation
    unique_strengths: list[str]
    notable_risks: list[str]
    best_fit_for: str  # e.g., "High-volume production with tight tolerances"
```

### 10.5 Human-in-the-Loop Gate

The buyer reviews the comparison matrix in an interactive table with:
- Sortable columns for each dimension
- Adjustable weights with live re-ranking
- Expandable narratives for each score
- Side-by-side supplier cards for detailed comparison
- Ability to exclude suppliers and re-rank

---

## 11. Agent 5: Intelligence Report Generator

### 11.1 Purpose

The Intelligence Report Generator produces a comprehensive, per-supplier intelligence brief that consolidates everything Procurement AI has learned. This is the "analyst report" that gives the buyer confidence to proceed with outreach. It transforms raw data into actionable intelligence.

### 11.2 Report Contents

For each supplier on the approved shortlist, the report includes:

**Executive Summary** (2–3 sentences): Who they are, why they're a fit, key differentiator.

**Company Profile**: Full corporate details, ownership structure, founding date, key contacts (if available), facility locations with sizes, website and key pages.

**Capability Assessment**: Detailed analysis of manufacturing capabilities vs. the specific requirement. Equipment relevant to the part, materials experience, production capacity estimate, secondary operations availability.

**Quality Credentials**: IATF 16949 details (cert number, scope, expiry, certified sites), ISO 14001 status, any additional certifications. Assessment of quality system maturity based on website analysis.

**Financial Health**: D&B summary — risk rating, PAYDEX, revenue range, employee count, years in business. Interpretation in procurement context (e.g., "Revenue of $50M+ indicates capacity for contracts up to $5M annual spend without concentration risk").

**Geographic Analysis**: Distance from buyer plant, USMCA implications, logistics advantages/disadvantages, regional labor cost context.

**Competitive Positioning**: Where this supplier ranks vs. others on the shortlist. Unique strengths and differentiators. Scenarios where this supplier would be the optimal choice.

**Risk Assessment**: Identified risks (financial, geographic, capacity, single-source, geopolitical) with severity ratings. Mitigation suggestions.

**Recommended Next Steps**: Specific questions to ask this supplier, areas to probe during capability review, suggested RFQ focus areas.

### 11.3 Implementation

The Report Generator uses the **Orchestrator-Workers** pattern. A lead agent (Sonnet 4.5) reviews all accumulated data and generates a report outline, then delegates per-supplier report writing to parallel worker subagents. Each worker has access to the full supplier profile, verification results, comparison scores, and the original requirement.

This follows Anthropic's multi-agent research findings: the orchestrator + subagent pattern outperformed single-agent approaches by 90.2% on internal research evaluations. Token usage explains 80% of performance variance, suggesting multi-agent systems work partly because they systematically spend enough tokens to thoroughly explore each supplier's profile.

### 11.4 Human-in-the-Loop Gate

Reports are presented for buyer review. The buyer can request deeper analysis on specific suppliers, flag inaccuracies, add notes from their own knowledge, and approve reports before they inform RFQ generation.

---

## 12. Agent 6: RFQ Preparation & Outreach

### 12.1 Purpose

The RFQ Agent generates professional, industry-standard RFQ packages tailored to the specific requirement and supplier, then manages the email outreach process. This is where Procurement AI transitions from research to action — and where human approval is most critical.

### 12.2 RFQ Document Generation

The agent generates a complete RFQ package consisting of:

**RFQ Cover Letter**: Personalized to each supplier, referencing their specific capabilities that match the requirement. Professional tone, concise, with clear response instructions and deadline.

**Technical Specification Package**: Part description, engineering drawing references (attached separately by the buyer), material specifications, tolerance requirements, surface finish requirements, annual volume with lot sizes, prototype requirements if applicable.

**Commercial Terms**: Response deadline, expected quote format (with OEM-specific cost breakdown template if applicable), tooling ownership terms, payment terms framework, quality requirements (IATF 16949, PPAP level), packaging and shipping requirements, IP/NDA requirements.

**Response Template**: A structured template (Excel or form) that the supplier fills out, ensuring consistent data across all respondents. Fields include: piece price by volume tier, material cost breakdown, tooling cost and lead time, production lead time, MOQ, capacity available, and any exceptions or clarifications.

### 12.3 Email Composition and Delivery

Procurement AI uses **Resend** for email lifecycle management. Key capabilities:

- **Outbound**: Batch sending (up to 100 emails per API call), email scheduling, attachment support (up to 40MB), full DKIM/SPF/DMARC authentication
- **Inbound**: `email.received` webhook events with full metadata and attachment download URLs, enabling automated quote parsing
- **Tracking**: Webhooks for delivered/opened/bounced/clicked events

**Email deliverability requirements:**
- Dedicated subdomain (e.g., `sourcing.procurement.com`) to protect main domain reputation
- Full SPF+DKIM+DMARC enforcement (2.7x higher inbox placement vs. unauthenticated)
- Domain warming for new deployments: 5–10 emails/day weeks 1–2, ramping to 30–50 by weeks 5–6
- Never exceed 50 emails per inbox per day for outreach

**Email structure:**
- Subject line: `RFQ: [Buyer Company] – [Part Type] – [Volume] units` (under 60 characters)
- Body: Concise summary with specs highlights, clear deadline, professional closing
- Attachments: Technical specification PDF, response template Excel, engineering drawings (uploaded by buyer)

### 12.4 Human-in-the-Loop Gate — CRITICAL

This is the most important approval gate in the entire pipeline. Before any email is sent:

1. The buyer reviews each RFQ package (cover letter + specs + template)
2. The buyer attaches engineering drawings and any proprietary documents
3. The buyer confirms the recipient list — every supplier who will receive the RFQ
4. The buyer explicitly approves sending

**No RFQ is ever sent without explicit human approval.** This is a hard constraint, not a configuration option. The system presents a "Review & Send" interface showing exactly what will go to whom, and requires a deliberate confirmation action.

### 12.5 Post-Send Tracking

After sending, Procurement AI tracks:
- Delivery confirmation per supplier
- Open/read tracking
- Bounce handling with automatic notification to buyer
- Response deadline monitoring with reminder scheduling
- Non-response follow-up drafts (requiring buyer approval before sending)

---

## 13. Agent 7: Response Ingestion & Structuring

### 13.1 Purpose

The Response Parser monitors incoming emails, extracts quote data from supplier responses (which arrive in wildly varied formats — PDF quotes, Excel spreadsheets, email body text, scanned documents), and structures everything into a normalized comparison format.

### 13.2 Inbound Email Processing

Resend's `email.received` webhook triggers when a supplier responds. The webhook payload includes:
- Sender email and metadata
- Email body (HTML and plain text)
- Attachment URLs for download

Procurement AI's webhook handler:
1. Identifies the procurement project from the email thread or reference number
2. Downloads and processes all attachments
3. Routes to the appropriate parsing pipeline based on file type

### 13.3 Quote Extraction Pipeline

**Stage 1 — Document Processing**
- PDF attachments: Text extraction via pdfjs-dist; for scanned documents, OCR via Azure Document Intelligence or LlamaParse
- Excel attachments: Direct parsing with column/row mapping
- Email body quotes: Direct text extraction
- Image attachments: OCR processing

**Stage 2 — LLM-Powered Interpretation**
Claude Haiku 4.5 extracts structured quote data using defined Pydantic schemas. The model receives the raw text plus the original RFQ context (what was asked for) and maps the supplier's response to the standard schema.

For critical pricing data, Procurement AI implements **confidence scores** and flags low-confidence extractions for human review. LLMs can hallucinate numbers — a misread "$0.45/piece" as "$4.50/piece" would be catastrophic. Every extracted price above a confidence threshold of 0.95 is auto-accepted; below that, it's flagged.

**Stage 3 — Normalization**
Quotes are normalized to:
- Same currency (using current exchange rates)
- Same Incoterms basis
- Same cost-per-piece at the target volume
- Tooling costs separated from piece price
- Total Cost of Ownership calculated

### 13.4 Output

```python
class ParsedQuote(BaseModel):
    supplier_id: str
    supplier_name: str
    received_date: str

    # Pricing
    piece_price: float
    piece_price_currency: str
    price_breaks: list[dict]  # volume → price

    # Cost breakdown (if provided)
    material_cost: Optional[float]
    labor_cost: Optional[float]
    overhead_cost: Optional[float]
    sga_cost: Optional[float]
    profit_margin: Optional[float]

    # Tooling
    tooling_cost: Optional[float]
    tooling_lead_time_weeks: Optional[int]
    tool_life_shots: Optional[int]
    tooling_ownership: Optional[str]

    # Logistics
    production_lead_time_weeks: Optional[int]
    moq: Optional[int]
    shipping_terms: Optional[str]  # Incoterms

    # Normalized TCO
    normalized_piece_price_usd: float
    estimated_annual_tco_usd: float

    # Meta
    extraction_confidence: float  # 0–1
    low_confidence_fields: list[str]
    raw_document_url: str
    notes: list[str]  # Supplier comments, exceptions, clarifications
```

### 13.5 Quote Comparison Presentation

As quotes arrive (typically over 1–2 weeks), Procurement AI builds a live comparison matrix:

| Field | Supplier A | Supplier B | Supplier C |
|---|---|---|---|
| Piece Price | $0.45 | $0.52 | $0.41 |
| Tooling | $85,000 | $72,000 | $95,000 |
| Production Lead Time | 14 weeks | 12 weeks | 16 weeks |
| MOQ | 5,000 | 2,500 | 10,000 |
| Annual TCO | $118,500 | $124,000 | $115,500 |
| Extraction Confidence | 0.98 | 0.96 | 0.92 ⚠️ |

### 13.6 Human-in-the-Loop Gate

The buyer reviews parsed quotes with:
- Side-by-side comparison of extracted vs. raw data (the original document is always accessible)
- Flags on low-confidence extractions requiring human verification
- Ability to manually correct extracted values
- Notes on each supplier's response (completeness, responsiveness, exceptions)

---

## 14. Human-in-the-Loop Architecture

### 14.1 Design Philosophy

Procurement AI treats human oversight as a **permanent feature, not a temporary crutch**. This follows Anthropic's explicit recommendation: "Start with more HITL than you think necessary and reduce as confidence grows." In procurement specifically, the stakes of autonomous errors are too high — a misdirected RFQ reveals proprietary specifications, a financial health assessment error could lead to a supplier bankruptcy mid-contract, and an incorrectly parsed quote could skew a multi-million-dollar award.

### 14.2 HITL Pattern Taxonomy

Procurement AI implements four of Anthropic's five HITL patterns:

**Approval Gates** (used at every stage transition): The agent prepares an action, pauses for human yes/no. Implemented via LangGraph's `interrupt()` mechanism, which persists state to PostgreSQL and resumes when human input arrives. This works across machine restarts and can wait days or weeks.

```python
# LangGraph interrupt pattern
def send_rfq_node(state: ProcurementState) -> ProcurementState:
    rfq_package = generate_rfq(state)

    # Pause and wait for human approval
    human_decision = interrupt({
        "type": "rfq_approval",
        "rfq_preview": rfq_package,
        "recipients": state["approved_suppliers"],
        "message": "Review and approve RFQ before sending"
    })

    if human_decision["approved"]:
        send_rfqs(rfq_package, state["approved_suppliers"])
        return {"rfq_sent": True, "send_timestamp": now()}
    else:
        return {"rfq_sent": False, "rejection_reason": human_decision["reason"]}
```

**Review and Edit** (used for requirements confirmation and report review): The human can modify agent output before it takes effect. The Requirements Parser output is fully editable. Intelligence reports can be annotated and corrected.

**Confidence-Based Escalation** (used for quote parsing): Below-threshold confidence on extracted data triggers human review. The system presents the raw document alongside extracted fields, highlighting uncertain values.

**Fallback Escalation** (used when agents get stuck): If Discovery finds fewer than 3 candidates, if Qualification can't verify a critical certification, or if the Response Parser can't interpret a quote format, the system escalates to the buyer with a clear explanation of what failed and what options are available.

### 14.3 Approval Gate Summary

| Gate | Trigger | What Human Reviews | Can Human Modify? | Timeout Action |
|---|---|---|---|---|
| Requirements Confirmation | After parsing | Structured spec | Yes — any field | None (blocks) |
| Longlist Approval | After discovery | Supplier table | Yes — add/remove | None (blocks) |
| Shortlist Approval | After qualification | Verified suppliers | Yes — override status | None (blocks) |
| Ranking Review | After comparison | Comparison matrix | Yes — adjust weights | None (blocks) |
| Report Review | After report gen | Intelligence briefs | Yes — annotate | None (blocks) |
| RFQ Send Approval | Before outreach | Full RFQ package | Yes — edit all | None (blocks) |
| Quote Review | After parsing | Parsed vs. raw data | Yes — correct values | Reminder after deadline |

All gates **block** — the pipeline does not proceed without explicit human approval. There are no auto-approvals, no timeouts that default to "yes," and no bypass mechanisms.

### 14.4 Progressive Trust Model

While gates never disappear, their friction can decrease over time:

- **First use**: Full review of every field at every stage
- **After 10 projects**: Buyer can enable "fast-track" mode where fully qualified suppliers (high confidence, all checks passed, previously used) are pre-approved for the shortlist
- **After 50 projects**: Buyer can enable RFQ templates that auto-populate from requirements, requiring only a final review rather than field-by-field editing
- **Never**: Auto-send RFQs. Auto-accept quotes. Auto-select suppliers.

---

## 15. UX Script: Screen-by-Screen Walkthrough

### 15.1 Dashboard (Home Screen)

```
┌─────────────────────────────────────────────────────────────┐
│  PROCUREMENT                                    Sarah Chen ▼      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  + New Procurement Project                               ││
│  │                                                          ││
│  │  "Describe what you need — I'll find the right           ││
│  │   suppliers for you."                                    ││
│  │                                                          ││
│  │  ┌────────────────────────────────────────────────────┐  ││
│  │  │ I need a supplier for aluminum die-cast EV battery │  ││
│  │  │ housings, 50K annual volume, IATF 16949...     ▶   │  ││
│  │  └────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Active Projects                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │ Steel Brackets        │  │ Wiring Harness Assy  │         │
│  │ Stage: Awaiting Quotes│  │ Stage: Discovery     │         │
│  │ 3/5 quotes received   │  │ 28 suppliers found   │         │
│  │ Due: Feb 28           │  │ Started: Feb 14      │         │
│  └──────────────────────┘  └──────────────────────┘         │
│                                                              │
│  Recent Activity                                             │
│  • Supplier A responded to Steel Brackets RFQ — 2 hrs ago   │
│  • IATF check completed for 8 suppliers — 5 hrs ago         │
│  • New project "Wiring Harness Assy" created — 1 day ago    │
└─────────────────────────────────────────────────────────────┘
```

### 15.2 Requirements Confirmation Screen

After the buyer submits their request, the Requirements Parser processes it and presents:

```
┌─────────────────────────────────────────────────────────────┐
│  REQUIREMENTS REVIEW                                         │
│                                                              │
│  Your request:                                               │
│  "I need a supplier for aluminum die-cast EV battery         │
│   housings, 50K annual volume, IATF 16949 required,         │
│   preferably in Mexico for USMCA compliance"                 │
│                                                              │
│  ┌ Parsed Specifications ──────────────────────────────────┐ │
│  │                                                          │ │
│  │  Part Category:     Die Casting               [Edit]     │ │
│  │  Material:          Aluminum (alloy TBD)      [Edit]     │ │
│  │  Process:           High-pressure die casting [Edit]     │ │
│  │  Annual Volume:     50,000                    [Edit]     │ │
│  │  Lot Size:          ⚠️ Not specified — suggest 2,500?    │ │
│  │                                               [Set]      │ │
│  │  Certifications:    IATF 16949               [Edit]     │ │
│  │  Preferred Region:  Mexico                    [Edit]     │ │
│  │  USMCA Compliance:  Required (inferred)       [Confirm]  │ │
│  │  Tolerances:        ⚠️ Not specified          [Set]      │ │
│  │  Surface Finish:    ⚠️ Not specified          [Set]      │ │
│  │  Prototype Needed:  ⚠️ Not specified          [Set]      │ │
│  │                                                          │ │
│  │  ─── Estimates ───                                       │ │
│  │  Tooling Range:     $150K–$400K (typical for HPDC)       │ │
│  │  Tooling Lead Time: 16–24 weeks                          │ │
│  │  Complexity:        Moderate                              │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│        [← Back]                     [Confirm & Search →]     │
└─────────────────────────────────────────────────────────────┘
```

**UX Notes:**
- ⚠️ icons draw attention to ambiguities requiring input
- "Inferred" fields are visually distinct and require explicit confirmation
- Estimates section sets buyer expectations for market parameters
- Every field is directly editable inline

### 15.3 Supplier Discovery Results Screen

```
┌─────────────────────────────────────────────────────────────┐
│  SUPPLIER DISCOVERY                          Searching... ✓  │
│  EV Battery Housing — Aluminum Die Casting                   │
│                                                              │
│  Found 34 potential suppliers across 5 sources               │
│  Thomasnet: 12 | Google: 8 | Trade Data: 6 | Web: 5 | DB: 3│
│                                                              │
│  Sort by: [Score ▼] [Capability] [Geography] [Scale]         │
│  Filter:  [✓ Mexico] [✓ US] [□ China] [□ India]             │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ ☐ 1. Fundición Monterrey S.A.          Score: 92        ││
│  │      Monterrey, NL, Mexico | 450 employees               ││
│  │      HPDC aluminum | IATF ✓ | Revenue: $80M              ││
│  │      Sources: Thomasnet, Trade Data, Web                  ││
│  │      [View Details]                                       ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ ☐ 2. Precision Castings Inc.            Score: 87        ││
│  │      Querétaro, QRO, Mexico | 200 employees               ││
│  │      HPDC aluminum + machining | IATF ✓ | Revenue: $35M  ││
│  │      Sources: Thomasnet, Google, Web                      ││
│  │      [View Details]                                       ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ ☐ 3. Great Lakes Die Cast LLC           Score: 84        ││
│  │      Holland, MI, USA | 320 employees                     ││
│  │      HPDC aluminum & magnesium | IATF ✓ | Revenue: $60M  ││
│  │      Sources: Thomasnet, Trade Data                       ││
│  │      [View Details]                                       ││
│  ├──────────────────────────────────────────────────────────┤│
│  │      ... 31 more suppliers                                ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  [+ Add Supplier Manually]                                   │
│                                                              │
│  Selected: 0 of 34                                           │
│  [Select Top 10]  [Select All Qualified]  [Proceed →]        │
└─────────────────────────────────────────────────────────────┘
```

### 15.4 Qualification Progress Screen

```
┌─────────────────────────────────────────────────────────────┐
│  SUPPLIER QUALIFICATION                                      │
│  Verifying 10 selected suppliers...                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Fundición Monterrey S.A.                                  ││
│  │ ✅ IATF 16949: Verified (Cert #0123456, exp. 2027-03)    ││
│  │ ✅ Financial: Low Risk (D&B: 4A2, PAYDEX: 78)            ││
│  │ ✅ Registration: Confirmed (RFC: FMO950315...)            ││
│  │ ✅ Website: Capabilities extracted                        ││
│  │ ✅ Reputation: 4.3/5 (28 reviews)                        ││
│  │ Status: QUALIFIED                                         ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Precision Castings Inc.                                   ││
│  │ ✅ IATF 16949: Verified                                   ││
│  │ ⏳ Financial: Checking...                                 ││
│  │ ✅ Registration: Confirmed                                ││
│  │ ✅ Website: Capabilities extracted                        ││
│  │ ⏳ Reputation: Checking...                                ││
│  │ Status: IN PROGRESS                                       ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Allied Manufacturing Corp.                                ││
│  │ ❌ IATF 16949: NOT FOUND                                  ││
│  │ Status: DISQUALIFIED — Missing required certification     ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  Qualified: 6 | Conditional: 2 | Disqualified: 2            │
│                                                              │
│  [Override: Promote Conditional ↑] [Proceed with Qualified →]│
└─────────────────────────────────────────────────────────────┘
```

### 15.5 Comparison Matrix Screen

```
┌─────────────────────────────────────────────────────────────┐
│  SUPPLIER COMPARISON                                         │
│  EV Battery Housing — 6 Qualified Suppliers                  │
│                                                              │
│  Weights: Capability [25%▼] Quality [25%▼] Geo [20%▼]       │
│           Financial [15%▼] Scale [10%▼] Reputation [5%▼]    │
│                                                              │
│  ┌────────────┬───────┬───────┬───────┬───────┬───────┐     │
│  │            │Fund.  │Prec.  │Great  │Apex   │Toluca │     │
│  │            │Mty.   │Cast.  │Lakes  │Metals │HPDC   │     │
│  ├────────────┼───────┼───────┼───────┼───────┼───────┤     │
│  │ COMPOSITE  │  92   │  87   │  84   │  81   │  79   │     │
│  ├────────────┼───────┼───────┼───────┼───────┼───────┤     │
│  │ Capability │  95   │  88   │  90   │  82   │  78   │     │
│  │ Quality    │  90   │  85   │  92   │  80   │  75   │     │
│  │ Geography  │  95   │  90   │  70   │  85   │  95   │     │
│  │ Financial  │  88   │  82   │  85   │  78   │  72   │     │
│  │ Scale      │  90   │  80   │  88   │  82   │  75   │     │
│  │ Reputation │  85   │  80   │  82   │  78   │  70   │     │
│  └────────────┴───────┴───────┴───────┴───────┴───────┘     │
│                                                              │
│  💡 Top Pick: Fundición Monterrey S.A.                       │
│     Strongest overall match — HPDC aluminum specialist in    │
│     Monterrey with verified IATF, strong financials, and     │
│     proven automotive EV experience.                         │
│                                                              │
│  [View Full Reports]  [Adjust Weights]  [Proceed to RFQ →]  │
└─────────────────────────────────────────────────────────────┘
```

### 15.6 RFQ Review & Send Screen

```
┌─────────────────────────────────────────────────────────────┐
│  RFQ REVIEW & SEND                                           │
│  ⚠️  Review carefully — emails will be sent to 6 suppliers   │
│                                                              │
│  ┌ RFQ Preview ────────────────────────────────────────────┐ │
│  │ Subject: RFQ: [Your Company] – AL HPDC Battery Housing  │ │
│  │          – 50,000 units/yr                               │ │
│  │                                                          │ │
│  │ Dear [Supplier Contact],                                 │ │
│  │                                                          │ │
│  │ [Your Company] is sourcing aluminum high-pressure die    │ │
│  │ cast EV battery housings for a new vehicle program...    │ │
│  │                                                          │ │
│  │ [Full preview expandable]                                │ │
│  │                                                          │ │
│  │ Attachments:                                             │ │
│  │ 📎 Technical_Specification_BH-2026-001.pdf               │ │
│  │ 📎 Quote_Response_Template.xlsx                          │ │
│  │ 📎 [+ Attach Engineering Drawing]  ← Required           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  Recipients:                                                 │
│  ✅ Fundición Monterrey — rfq@fundicionmty.com              │
│  ✅ Precision Castings — sales@precisioncastings.mx          │
│  ✅ Great Lakes Die Cast — quotes@greatlakesdc.com           │
│  ✅ Apex Metals — sourcing@apexmetals.com                    │
│  ✅ Toluca HPDC — ventas@tolucahpdc.com                     │
│  ✅ Saltillo Castings — rfq@saltillocastings.com            │
│                                                              │
│  Response Deadline: March 1, 2026                            │
│                                                              │
│  [← Edit RFQ]  [Edit Recipients]  [🔒 Approve & Send →]     │
└─────────────────────────────────────────────────────────────┘
```

### 15.7 Quote Tracking Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  QUOTE TRACKING                                              │
│  EV Battery Housing — RFQs sent Feb 15 | Due: Mar 1         │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Fundición Monterrey    ✅ Quote received   Feb 22        ││
│  │   $0.45/pc | Tooling: $185K | Lead: 18 wks              ││
│  │   [View Parsed Quote] [View Original PDF]                ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Great Lakes Die Cast   ✅ Quote received   Feb 24        ││
│  │   $0.52/pc | Tooling: $165K | Lead: 16 wks              ││
│  │   [View Parsed Quote] [View Original PDF]                ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Precision Castings     📧 Opened (2x)      —            ││
│  │   [Send Reminder]                                        ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Apex Metals            📧 Delivered         —            ││
│  │   [Send Reminder]                                        ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Toluca HPDC            📧 Delivered         —            ││
│  ├──────────────────────────────────────────────────────────┤│
│  │ Saltillo Castings      ❌ Bounced                        ││
│  │   ⚠️ Email undeliverable — verify contact                ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  2 of 6 responses received | 4 days until deadline           │
│                                                              │
│  [View Comparison Matrix]  [Download All]  [Contact Info →]  │
└─────────────────────────────────────────────────────────────┘
```

### 15.8 Final Intelligence Package Screen

```
┌─────────────────────────────────────────────────────────────┐
│  FINAL INTELLIGENCE PACKAGE                                  │
│  EV Battery Housing — Ready for your decision                │
│                                                              │
│  You have 4 quotes from 6 solicited suppliers.               │
│                                                              │
│  ┌ Quote Comparison ───────────────────────────────────────┐ │
│  │          │ Fund.Mty │ G.Lakes │ Prec.Cast│ Toluca      │ │
│  │ Piece $  │ $0.45    │ $0.52   │ $0.48    │ $0.41       │ │
│  │ Tooling  │ $185K    │ $165K   │ $195K    │ $210K       │ │
│  │ Lead Wks │ 18       │ 16      │ 20       │ 22          │ │
│  │ MOQ      │ 2,500    │ 1,000   │ 5,000    │ 5,000       │ │
│  │ Ann. TCO │ $122K    │ $131K   │ $129K    │ $120K       │ │
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  📊 Full Comparison Matrix | 📋 Intelligence Reports         │
│  📎 All Original Quotes   | 📈 TCO Analysis                 │
│                                                              │
│  Recommended Next Steps:                                     │
│  1. Contact Fundición Monterrey and Toluca HPDC for          │
│     detailed capability discussions                          │
│  2. Request facility visit for top 2 candidates              │
│  3. Verify tooling capacity and timeline commitments         │
│                                                              │
│  ┌ Supplier Contact Cards ─────────────────────────────────┐ │
│  │ Fundición Monterrey S.A.                                 │ │
│  │ 📞 +52 81 1234 5678 | 📧 ventas@fundicionmty.com       │ │
│  │ 📍 Av. Industrial 456, Monterrey, NL 64000              │ │
│  │ 🔗 www.fundicionmonterrey.com                           │ │
│  │ [Open Full Report]                                       │ │
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  [Export to Excel]  [Share with Team]  [Archive Project]     │
└─────────────────────────────────────────────────────────────┘
```

**This is where Procurement AI stops. The buyer now has everything they need: verified suppliers, parsed quotes, intelligence reports, and direct contact information. The human takes over for negotiations, facility visits, and the final award.**

---

## 16. State Management & Data Flow

### 16.1 Core State Schema

All agent state flows through a centralized `ProcurementState` TypedDict with annotated reducers:

```python
from typing import TypedDict, Annotated
from langgraph.graph import add

class ProcurementState(TypedDict):
    # Immutable context
    project_id: str
    org_id: str
    created_by: str
    created_at: str

    # Messages (append-only via reducer)
    messages: Annotated[list, add]

    # Stage outputs
    raw_request: str                          # User's original text
    parsed_requirement: ParsedRequirement     # Agent 1 output
    discovered_suppliers: list[DiscoveredSupplier]  # Agent 2 output
    qualified_suppliers: list[QualifiedSupplier]    # Agent 3 output
    comparison_matrix: ComparisonMatrix       # Agent 4 output
    intelligence_reports: list[IntelligenceReport]  # Agent 5 output
    rfq_document: RFQPackage                  # Agent 6 output
    outreach_status: list[OutreachRecord]     # Agent 6 tracking
    parsed_quotes: list[ParsedQuote]          # Agent 7 output

    # Pipeline control
    current_stage: str
    approvals: dict  # stage → {approved: bool, by: str, at: str, notes: str}
    errors: Annotated[list[dict], add]

    # Human modifications
    human_overrides: dict  # stage → modifications made by human
```

### 16.2 Persistence Strategy

LangGraph's `PostgresSaver` provides production-grade checkpoint persistence:

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@host:5432/procurement"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)

    # Each procurement project gets a unique thread_id
    config = {"configurable": {"thread_id": project_id}}

    # Run until next interrupt
    result = graph.invoke(initial_state, config)

    # Later, resume with human input
    result = graph.invoke(
        Command(resume={"approved": True, "notes": "Looks good"}),
        config
    )
```

Checkpoints are versioned, enabling:
- **Time-travel debugging**: Replay any stage of any procurement project
- **State inspection**: View exactly what data each agent received and produced
- **Recovery**: Resume from any checkpoint after system failures
- **Audit trail**: Complete record of every state transition and human decision

### 16.3 Async Email Workflow Pattern

Procurement's inherently async nature (send RFQ, wait days for response) requires a specific pattern:

```
User triggers RFQ send
    → LangGraph executes send_rfq_node
    → Emails sent via Resend API
    → Graph reaches "await_responses" node with interrupt()
    → State checkpointed to PostgreSQL
    → Graph pauses (can wait weeks)

Supplier replies via email
    → Resend webhook fires email.received event
    → Webhook handler extracts project_id from email thread
    → Handler calls graph.invoke(Command(resume={...}), config)
    → Graph resumes from checkpoint
    → Response Parser processes the new quote
    → If more responses expected, graph interrupts again
    → If deadline reached or all responses in, proceed to comparison
```

---

## 17. Tool Integration Layer

### 17.1 Tool Registry

Each agent has access to a curated set of tools. Following Anthropic's guidance, tools are not globally available — they're scoped per agent to prevent selection confusion.

| Agent | Tools Available |
|---|---|
| Requirements Parser | think_tool, structured_output |
| Discovery | thomasnet_browser, google_places_api, importgenius_api, firecrawl_search, firecrawl_extract, internal_db_query, think_tool |
| Qualification | iatf_portal_check, dnb_api, opencorporates_api, firecrawl_extract, google_places_details, think_tool |
| Comparison | think_tool, structured_output, calculator |
| Intelligence Report | all_read_tools (no write tools), think_tool, structured_output |
| RFQ Outreach | resend_email_api, document_generator, think_tool |
| Response Parser | attachment_downloader, pdf_extractor, excel_parser, ocr_service, think_tool, structured_output |

### 17.2 Firecrawl Integration Details

Firecrawl is the primary web intelligence tool. Three endpoints are used:

**`/v1/scrape`** — Single page to markdown. Used for extracting content from known supplier URLs.

**`/v2/extract`** — Schema-driven extraction. Define a Pydantic model and Firecrawl returns structured JSON from any supplier website. This is the workhorse for building capability profiles.

**Agent Endpoint** — Autonomous search and extraction. Describe the task and Firecrawl navigates, searches, and extracts. Used for broad discovery queries.

Pricing: Standard plan at $83/month for 100K page credits.

### 17.3 Browserbase Integration Details

Browserbase provides cloud-native headless Chrome for dynamic supplier portal automation:

- **Contexts API**: Persists cookies and browser state across sessions for maintained access to Thomasnet
- **CAPTCHA solving**: Built-in on Startup plan ($99/month)
- **Stealth mode**: Residential proxies for anti-bot measures
- **Live View**: Human-in-the-loop browser control for complex interactions
- **Playwright/Puppeteer compatible**: Standard automation via CDP

### 17.4 Resend Email Configuration

```python
# Domain authentication
resend.domains.create({
    "name": "sourcing.procurement.com"  # Dedicated subdomain
})
# Returns DNS records for DKIM, SPF, DMARC setup

# Webhook for inbound emails
resend.webhooks.create({
    "url": "https://api.procurement.com/webhooks/email",
    "events": ["email.received", "email.delivered", "email.bounced", "email.opened"]
})
```

### 17.5 Tool Design Best Practices Applied

Following Anthropic's finding that their SWE-bench team spent more time optimizing tool definitions than system prompts:

- **Unambiguous parameter names**: `supplier_website_url` not `url`, `iatf_certificate_number` not `cert_id`
- **Semantically meaningful returns**: Return `company_name`, `certification_status` not raw UUIDs
- **Response format control**: `response_format` enum ("concise" vs "detailed") on search tools — cut token usage by approximately two-thirds in testing
- **Examples in tool definitions**: Using Claude's tool use examples beta to provide concrete input/output examples improved accuracy from 72% to 90% on complex parameter handling
- **Structural error prevention**: Requiring absolute file paths instead of relative ones eliminated path-related errors

---

## 18. Memory & Context Engineering

### 18.1 Two-Tier Memory Architecture

**Short-term memory (in-context):** The current LangGraph state — system prompt, recent agent messages, tool results, and current stage context. Fast and essential but temporary and size-limited.

**Long-term memory (Supabase + pgvector):** Persists across sessions and projects:

- **Semantic memory**: Supplier profiles, capability data, pricing benchmarks, certification records — facts that improve with every project
- **Episodic memory**: Past procurement projects, search strategies that worked, suppliers that were disqualified and why — experience that prevents repeating mistakes
- **Procedural memory**: Learned strategies — which search queries find the best results for stamping vs. casting, which RFQ templates get the highest response rates, which qualification checks are most predictive

### 18.2 Context Window Management

For long-running procurement workflows that span weeks:

**Observation masking**: Replace verbose tool outputs (raw HTML from Firecrawl, full D&B reports, complete Thomasnet search results) with compact structured summaries. JetBrains Research (December 2025) found this matched or beat LLM summarization in 4 of 5 test settings while being 52% cheaper.

**Progressive state disclosure**: Each agent receives only the state fields relevant to its stage. The RFQ Agent doesn't need raw discovery search results — it needs the approved supplier shortlist and the structured requirement.

**Claude's built-in compaction**: For within-stage processing that approaches context limits, Claude's automatic compaction summarizes previous messages while preserving critical details.

**Initializer agent pattern**: For procurement projects that span multiple sessions, the first context window of a new session reads a comprehensive `project_state.json` file that captures all decisions, approvals, and current status — analogous to engineers working in shifts with detailed handover notes.

### 18.3 Institutional Knowledge Accumulation

Every completed procurement project enriches Procurement AI's long-term memory:

- New supplier profiles are stored with full verification data
- Pricing benchmarks are updated with actual quote data (anonymized across organizations)
- Search strategies that produced high-quality results are reinforced
- Suppliers that were disqualified have their disqualification reasons recorded, preventing future false positives
- RFQ response rates by template, timing, and supplier segment inform future outreach optimization

This creates a compounding advantage: Procurement AI's 100th procurement project is dramatically faster and more accurate than its first, because it's drawing on the institutional knowledge of all 99 prior projects.

---

## 19. Model Tiering & Cost Strategy

### 19.1 Claude Model Allocation

Procurement AI implements aggressive model tiering to balance quality and cost:

| Task | Model | Cost (Input/Output per MTok) | Rationale |
|---|---|---|---|
| Requirements parsing | Haiku 4.5 | $1 / $5 | Simple classification and extraction |
| Search query generation | Haiku 4.5 | $1 / $5 | Template-driven, low complexity |
| Supplier data extraction (Firecrawl) | Haiku 4.5 | $1 / $5 | High volume structured extraction |
| Qualification assessment | Sonnet 4.5 | $3 / $15 | Multi-factor reasoning |
| Comparison and ranking | Sonnet 4.5 | $3 / $15 | Nuanced multi-variable analysis |
| Intelligence report writing | Sonnet 4.5 | $3 / $15 | Quality writing with domain expertise |
| RFQ generation | Sonnet 4.5 | $3 / $15 | Professional communication |
| Quote parsing (standard) | Haiku 4.5 | $1 / $5 | Structured extraction |
| Quote parsing (complex/low confidence) | Sonnet 4.5 | $3 / $15 | Escalation for difficult formats |
| Think tool reflections | Same as parent agent | — | Inherits parent model |

**Approximately 70% of API calls use Haiku, 30% use Sonnet.** Opus is not needed in the current pipeline since negotiation is excluded and no task requires the deepest reasoning tier.

### 19.2 Prompt Caching

Prompt caching is the single largest cost optimization lever. Static content placed at the beginning of prompts and marked with `cache_control` includes:

- Automotive procurement domain knowledge
- Part category reference data (materials, processes, typical parameters)
- RFQ templates and evaluation criteria
- Tool definitions and usage instructions
- Structured output schemas

Cached reads cost only 0.1x base input price — a 90% savings. For a system processing dozens of procurement workflows daily, this reduces Claude API costs by 60–75%.

### 19.3 Batch API for Non-Time-Sensitive Tasks

The Batch API provides a 50% discount for tasks that can wait hours:

- Overnight supplier analysis across multiple geographies
- Bulk certification verification for supplier database maintenance
- Historical quote pattern analysis for pricing intelligence
- Periodic re-evaluation of previously qualified suppliers

### 19.4 Estimated Monthly Costs

| Component | Monthly Cost |
|---|---|
| Claude API (with caching) | $50–200 |
| Firecrawl Standard | $83 |
| Browserbase Startup | $99 |
| Resend Pro | $20 |
| Google Places API | $0–50 |
| Supabase Pro | $25 |
| D&B Direct+ API | ~$800 (annual / 12) |
| ImportGenius | $149 |
| **Total** | **$425–625/month** |

This is remarkably lean for an enterprise-grade procurement intelligence platform. A single buyer's time savings on one procurement project easily exceeds the monthly platform cost.

---

## 20. Reliability, Guardrails, and Error Handling

### 20.1 Error Classification and Handling

Following Anthropic's five-tier error hierarchy:

**Tier 1 — Transient Errors** (API timeouts, rate limits)
- Handler: Exponential backoff retries (max 3 attempts)
- Examples: Firecrawl timeout, D&B API rate limit, Google Places quota
- User impact: None if retry succeeds; notification if all retries fail

**Tier 2 — Tool Errors** (malformed API responses, service outages)
- Handler: Fallback to alternative data source or cached data
- Examples: Thomasnet layout change breaks scraper, D&B returns incomplete data
- User impact: Reduced data quality for affected suppliers, flagged in UI

**Tier 3 — Reasoning Errors** (agent takes wrong path, misclassifies a supplier)
- Handler: Think tool reflection checkpoint, replan with accumulated context
- Examples: Discovery Agent generates irrelevant search queries, Qualification Agent misinterprets certification scope
- User impact: Caught at HITL review gates; buyer corrects before proceeding

**Tier 4 — Safety Errors** (constraint violations, data leakage risks)
- Handler: Hard stop with human escalation
- Examples: Attempting to send RFQ without approval, accessing competitor's confidential data
- User impact: Workflow paused, buyer notified of the constraint violation

**Tier 5 — Systemic Errors** (context overflow, budget exceeded)
- Handler: Graceful termination with state preservation
- Examples: Discovery returns 500+ results overwhelming context, API costs spike unexpectedly
- User impact: Project saved at last checkpoint, buyer notified to resume

### 20.2 Self-Correction Mechanism

The Evaluator-Optimizer pattern is deployed within the Qualification Agent:

1. Agent performs verification checks and renders qualification verdict
2. Evaluator reviews the verdict against the original requirement criteria
3. If inconsistencies detected (e.g., supplier marked qualified but missing a required certification), the evaluator feeds error context back for re-assessment
4. Maximum 2 correction iterations before escalating to human review
5. Deterministic exit condition: all required fields populated with confidence > 0.9

### 20.3 Guardrail Layers

**Input guardrails**: Validate requirement text for completeness, detect nonsensical inputs, sanitize any injection attempts.

**Processing guardrails**: Tool allowlists per agent (Discovery can't send emails, Outreach can't modify supplier profiles), rate limits on API calls, cost caps per project.

**Output guardrails**: Verify structured outputs conform to schemas, check for PII leakage in generated RFQ documents, validate email addresses before sending.

**Logging**: Every agent decision, tool call, human interaction, and state transition is logged to LangSmith for observability and debugging.

---

## 21. Data Schemas & Contracts

### 21.1 RFQ Document Schema

```python
class RFQPackage(BaseModel):
    # Header
    rfq_id: str
    rfq_date: str
    response_deadline: str
    buyer_company: str
    buyer_contact_name: str
    buyer_contact_email: str
    program_name: Optional[str]

    # Line items
    line_items: list[RFQLineItem]

    # Quality requirements
    quality_block: QualityRequirements

    # Delivery
    delivery_schedule: DeliverySchedule

    # Packaging
    packaging_requirements: PackagingRequirements

    # Tooling
    tooling_terms: ToolingTerms

    # Terms and conditions
    terms_reference: str  # Link to standard T&C
    nda_required: bool

class RFQLineItem(BaseModel):
    part_number: str
    description: str
    revision: str
    drawing_reference: str
    material_spec: str
    process_type: str
    annual_volume: int
    lot_size: int
    price_break_volumes: list[int]

class QualityRequirements(BaseModel):
    iatf_16949_required: bool
    ppap_level: Literal["1", "2", "3", "4", "5"]
    special_characteristics: list[str]
    inspection_requirements: list[str]
    gauge_requirements: Optional[str]
```

### 21.2 Supplier Profile Schema (Comprehensive)

```python
class SupplierProfile(BaseModel):
    # Identity
    supplier_id: str
    company_name: str
    dba_names: list[str]
    duns_number: Optional[str]

    # Locations
    headquarters: Address
    manufacturing_sites: list[ManufacturingSite]

    # Capabilities
    processes: list[ManufacturingProcess]
    materials: list[str]
    equipment: list[Equipment]
    secondary_operations: list[str]
    prototype_capability: bool
    design_capability: bool

    # Certifications
    certifications: list[Certification]

    # Financial
    financial_profile: FinancialProfile

    # Quality metrics (if available)
    quality_metrics: Optional[QualityMetrics]

    # Metadata
    data_sources: list[str]
    last_updated: str
    data_completeness: float  # 0–1

class ManufacturingSite(BaseModel):
    address: Address
    square_footage: Optional[int]
    employees: Optional[int]
    processes_at_site: list[str]
    iatf_certified_site: bool

class Certification(BaseModel):
    standard: str  # "IATF 16949", "ISO 9001", etc.
    certificate_number: Optional[str]
    certifying_body: Optional[str]
    scope: Optional[str]
    expiry_date: Optional[str]
    verification_status: Literal["verified", "claimed", "expired", "not_found"]
    verification_source: str
    verified_date: str
```

### 21.3 Inter-Agent Data Contracts

| From Agent | To Agent | Contract | Key Fields |
|---|---|---|---|
| Parser → Discovery | `ParsedRequirement` | part_category, material, process, volume, geography, certifications |
| Discovery → Qualification | `list[DiscoveredSupplier]` | company_name, website, sources, initial_score |
| Qualification → Comparison | `list[QualifiedSupplier]` | qualification_status, capabilities, financial_risk, iatf_status |
| Comparison → Report | `ComparisonMatrix` | supplier rankings, dimension scores, narratives |
| Report → RFQ | `list[IntelligenceReport]` + `ParsedRequirement` | contact info, capability match, requirement spec |
| RFQ → Response Parser | `RFQPackage` + `list[OutreachRecord]` | what was asked, who was asked, response template |
| Response Parser → Final | `list[ParsedQuote]` | structured pricing, TCO, confidence scores |

All contracts are enforced via Claude's structured outputs beta (`client.beta.messages.parse()` with `output_format=PydanticModel`), guaranteeing JSON schema conformance via constrained decoding.

---

## 22. Infrastructure & Deployment

### 22.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                             │
│               Next.js + Tailwind CSS                     │
│          Real-time updates via Supabase Realtime          │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                   API GATEWAY                            │
│                    FastAPI                                │
│         Auth (Supabase JWT) + Rate Limiting               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              LANGGRAPH EXECUTION ENGINE                   │
│    StateGraph + PostgresSaver + Conditional Routing        │
│                                                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
│  │ Parse  │ │Discover│ │Qualify │ │Compare │ │ Report ││
│  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  ││
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘│
│  ┌────────┐ ┌────────┐                                   │
│  │  RFQ   │ │Response│                                   │
│  │ Agent  │ │ Parser │                                   │
│  └────────┘ └────────┘                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        │              │                  │
┌───────▼──────┐ ┌─────▼─────┐ ┌──────────▼──────┐
│   SUPABASE   │ │  CLAUDE   │ │  EXTERNAL APIs  │
│  PostgreSQL  │ │  API      │ │  Firecrawl      │
│  pgvector    │ │  Haiku    │ │  Browserbase    │
│  Realtime    │ │  Sonnet   │ │  Resend         │
│  Storage     │ │           │ │  Google Places  │
│  Auth        │ │           │ │  D&B, IATF, etc │
└──────────────┘ └───────────┘ └─────────────────┘
```

### 22.2 Supabase Configuration

**Database**: PostgreSQL with pgvector extension for semantic supplier search. Row-Level Security for multi-tenant isolation: `USING (org_id = (SELECT org_id FROM profiles WHERE id = auth.uid()))`.

**Realtime**: Subscriptions on `procurement_projects`, `quotes`, and `outreach_records` tables enable live dashboard updates as supplier responses arrive.

**Storage**: S3-compatible storage for RFQ documents, supplier attachments, engineering drawings, and parsed quote originals.

**Edge Functions**: Webhook processing for Resend email events and background tasks.

**Auth**: JWT-based authentication with organization-level multi-tenancy.

### 22.3 Deployment

- **Backend**: Containerized FastAPI on Railway or AWS ECS
- **Frontend**: Next.js on Vercel
- **Database**: Supabase managed PostgreSQL
- **LangGraph checkpointer**: Connects to the same PostgreSQL instance
- **Worker processes**: Celery + Redis for async email monitoring and background supplier analysis
- **Monitoring**: LangSmith for agent tracing, Sentry for application errors

---

## 23. Security & Multi-Tenancy

### 23.1 Data Isolation

Every organization's data is strictly isolated:

- **Database**: RLS policies on every table ensure queries only return rows belonging to the authenticated user's organization
- **Storage**: Bucket-level policies prevent cross-organization file access
- **Agent context**: Each procurement project's LangGraph state includes `org_id`, and all tool calls are scoped to that organization's data
- **Supplier profiles**: Shared supplier master data (publicly available information) is accessible to all organizations. Organization-specific notes, pricing data, and relationship history are private.

### 23.2 API Key Management

External API keys (Firecrawl, Browserbase, Resend, D&B, Google Places) are stored encrypted in Supabase Vault and injected into agent context at runtime. Organization-specific keys (for D&B, etc.) are segregated per tenant.

### 23.3 Email Security

- All outbound emails use DKIM-signed, SPF-verified, DMARC-enforced sender addresses on the organization's configured subdomain
- Inbound email processing validates sender domain against expected supplier contacts
- Attachment scanning before processing
- No credentials or sensitive buyer data in email body — engineering drawings are attached, not linked

### 23.4 Audit Trail

Every action is logged with: timestamp, user/agent identity, action type, input data hash, output data hash, approval status. Logs are immutable and retained for the duration required by the organization's compliance policies. LangSmith traces provide complete agent decision audit trails.

---

## 24. Metrics, Observability, and Evaluation

### 24.1 System Metrics

| Metric | Target | Measurement |
|---|---|---|
| Requirements parse accuracy | > 95% | Human correction rate at Stage 1 gate |
| Discovery recall | > 80% of relevant suppliers found | Comparison against manual search baseline |
| Qualification accuracy | > 90% correct verdicts | Human override rate at Stage 3 gate |
| Quote extraction accuracy | > 95% on numeric fields | Human correction rate at Stage 7 gate |
| RFQ response rate | > 60% | Responses received / RFQs sent |
| End-to-end time (to RFQ send) | < 1 business day | Project creation to RFQ approval |
| End-to-end time (to final package) | < 3 weeks | Project creation to all quotes parsed |
| Cost per procurement project | < $50 in API costs | Claude + external API costs |

### 24.2 LangSmith Observability

Every agent run is traced in LangSmith with:
- Full input/output for each node
- Tool call details with latency
- Token usage per model per stage
- Error traces with full context
- Human decision records at approval gates

### 24.3 Evaluation Strategy

Following Anthropic's recommendation to start with 20–50 evaluation cases drawn from real failures:

**Phase 1**: Manual evaluation on 30 procurement scenarios across part categories (stamping, casting, machining, molding, electronics), geographies (US, Mexico, China, India, Europe), and complexity levels (simple single-process, complex multi-operation).

**Phase 2**: Automated regression tests checking that known-good suppliers are discovered, known-bad suppliers are disqualified, and known quote formats are correctly parsed.

**Phase 3**: A/B testing of prompt variations, tool configurations, and search strategies with human-scored quality assessments.

---

## 25. Implementation Roadmap

### Phase 1: Core Pipeline (Weeks 1–6)

**Goal**: Requirements Parser → Supplier Discovery → Basic Qualification → RFQ Generation

- Implement LangGraph StateGraph with 4 agent nodes
- Integrate Google Places API for geographic supplier discovery
- Integrate Firecrawl for website scraping and capability extraction
- Build Requirements Parser with structured outputs
- Build RFQ document generator
- Implement HITL approval gates at every stage
- Frontend: Input form, requirements review, supplier list, RFQ preview
- Deploy on Supabase + Railway

**Milestone**: A buyer can describe a need, review discovered suppliers, and generate an RFQ package.

### Phase 2: Verification & Intelligence (Weeks 7–12)

**Goal**: Full qualification pipeline + intelligence reports + comparison matrix

- Integrate D&B Direct+ API for financial health checks
- Integrate IATF Customer Portal for certification verification
- Integrate OpenCorporates for corporate registration
- Build Qualification Agent subgraph with parallel verification
- Build Comparison Engine with weighted scoring
- Build Intelligence Report Generator with orchestrator-workers pattern
- Frontend: Qualification progress, comparison matrix, report viewer
- Implement long-term memory in Supabase pgvector

**Milestone**: Complete supplier intelligence package from discovery through comparison.

### Phase 3: Email Lifecycle (Weeks 13–18)

**Goal**: Automated RFQ outreach + response ingestion + quote parsing

- Integrate Resend for outbound email with DKIM/SPF/DMARC
- Implement inbound email webhook processing
- Build quote extraction pipeline (PDF, Excel, email body)
- Build quote normalization and TCO calculation
- Implement async workflow pattern (send → wait → resume on response)
- Frontend: RFQ send approval, quote tracking dashboard, parsed quote review
- Domain warming for email deliverability

**Milestone**: End-to-end workflow from natural language input to parsed quote comparison.

### Phase 4: Scale & Polish (Weeks 19–24)

**Goal**: Multi-part sourcing, team collaboration, institutional knowledge

- Integrate Thomasnet via Browserbase for deep industrial directory search
- Integrate ImportGenius/Panjiva for trade data intelligence
- Build batch processing for multi-part program sourcing
- Implement team collaboration features (shared projects, assignments)
- Build pricing intelligence from accumulated quote data
- Implement prompt caching and Batch API optimizations
- Performance tuning and cost optimization
- Comprehensive evaluation suite

**Milestone**: Production-ready platform with full tool stack and institutional memory.

---

## Appendix A: Automotive Procurement Glossary

**APQP** — Advanced Product Quality Planning. A structured framework for developing products and processes in the automotive industry, consisting of five phases from planning through production.

**ASL** — Approved Supplier List. A company's pre-vetted list of suppliers authorized to bid on new business.

**CSR** — Customer-Specific Requirements. Additional quality and process requirements that each OEM mandates beyond IATF 16949.

**ECN** — Engineering Change Notice. A formal document initiating a change to a part design or specification.

**FMEA** — Failure Mode and Effects Analysis. A systematic method for identifying potential failure modes in a design or process and their consequences.

**GD&T** — Geometric Dimensioning and Tolerancing. A system for defining and communicating engineering tolerances using symbolic language on engineering drawings.

**HPDC** — High Pressure Die Casting. A manufacturing process where molten metal is injected into a steel mold under high pressure.

**IATF 16949** — The automotive quality management system standard, published by the International Automotive Task Force. Required by virtually all OEMs and Tier 1 suppliers.

**Incoterms** — International Commercial Terms. Standardized trade terms (FOB, CIF, DDP, etc.) defining responsibilities for shipping, insurance, and duties.

**JIT/JIS** — Just-In-Time / Just-In-Sequence. Delivery methods where parts arrive at the assembly plant exactly when needed, sometimes in the exact sequence of vehicles on the assembly line.

**MOQ** — Minimum Order Quantity. The smallest batch a supplier will produce.

**PPAP** — Production Part Approval Process. A standardized 18-element documentation package that demonstrates a supplier can consistently produce parts meeting all customer requirements. Five submission levels, with Level 3 (complete data package) being most common.

**PPM** — Parts Per Million. The standard quality metric for defect rates in automotive. World-class is < 10 PPM.

**PSW** — Part Submission Warrant. The cover sheet of a PPAP package, signed by both supplier and customer to authorize production.

**RFI** — Request for Information. A preliminary inquiry to gauge supplier capability and interest before a formal RFQ.

**RFQ** — Request for Quotation. A formal document inviting suppliers to submit pricing and commercial terms for specified parts.

**RVC** — Regional Value Content. The percentage of a product's value that originates within a trade agreement region (e.g., USMCA requires 75% RVC for automotive).

**SGA** — Selling, General, and Administrative expenses. An overhead category in automotive cost breakdowns.

**SOP** — Start of Production. The date when a new vehicle program begins volume manufacturing.

**SPC** — Statistical Process Control. The use of statistical methods to monitor and control manufacturing processes.

**TCO** — Total Cost of Ownership. The complete cost of a part including purchase price, shipping, duties, quality costs, inventory carrying costs, and risk costs.

**USMCA** — United States-Mexico-Canada Agreement. The trade agreement replacing NAFTA, with more stringent automotive rules of origin.

---

## Appendix B: API Reference Summary

### External APIs

| API | Purpose | Auth | Rate Limit | Pricing |
|---|---|---|---|---|
| Claude API | LLM inference | API key | Varies by tier | Haiku: $1/$5; Sonnet: $3/$15 per MTok |
| Firecrawl | Web scraping & extraction | API key | Plan-dependent | $83/mo (Standard) |
| Browserbase | Cloud browser automation | API key | Plan-dependent | $99/mo (Startup) |
| Resend | Email send/receive | API key | 2 req/sec | $20/mo (Pro) |
| Google Places | Geographic business search | API key | 10K free/mo | Pay per use after free tier |
| D&B Direct+ | Financial risk assessment | API key | Plan-dependent | ~$10K/yr (enterprise) |
| OpenCorporates | Corporate registration | API key | Rate-limited | Free (public benefit) |
| ImportGenius | US customs/trade data | API key | Plan-dependent | $149/mo |
| IATF Customer Portal | Certification verification | Credentials | Manual/limited | Subscription |

### Internal APIs (Procurement AI)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/projects` | POST | Create new procurement project |
| `/api/v1/projects/{id}` | GET | Get project status and current stage |
| `/api/v1/projects/{id}/approve` | POST | Submit human approval for current gate |
| `/api/v1/projects/{id}/suppliers` | GET | List suppliers at current stage |
| `/api/v1/projects/{id}/comparison` | GET | Get comparison matrix |
| `/api/v1/projects/{id}/reports/{supplier_id}` | GET | Get intelligence report for supplier |
| `/api/v1/projects/{id}/rfq` | GET | Get RFQ package for review |
| `/api/v1/projects/{id}/quotes` | GET | Get parsed quotes |
| `/api/v1/webhooks/email` | POST | Handle inbound email events from Resend |

---

## Appendix C: Prompt Templates

### C.1 Requirements Parser System Prompt

```xml
<system>
You are Procurement AI's Requirements Parser — an expert automotive procurement analyst.
Your role is to convert natural language procurement requests into structured
specifications that will drive supplier discovery and RFQ generation.

<domain_expertise>
You have deep knowledge of:
- Automotive manufacturing processes (stamping, casting, machining, molding,
  forging, PCBA, wiring harness)
- Material specifications (steel grades, aluminum alloys, engineering plastics)
- Quality standards (IATF 16949, ISO 9001, PPAP levels 1-5)
- Trade compliance (USMCA rules of origin, duty classifications)
- Industry norms (typical MOQs, tooling costs, lead times by part category)
</domain_expertise>

<instructions>
1. Extract every explicit requirement from the buyer's message
2. Infer implicit requirements based on automotive context:
   - If "automotive" is mentioned → IATF 16949 likely required
   - If volume > 10K/year → tooled production, not prototype
   - If "EV" or "electric vehicle" → consider thermal management requirements
3. Flag critical ambiguities that MUST be resolved before searching
4. Never hallucinate specifications — if uncertain, flag as ambiguous
5. Estimate market parameters to set buyer expectations
6. Use the think tool to verify your parsing is complete and consistent
</instructions>

<output_format>
Return a ParsedRequirement JSON object conforming to the provided schema.
Every field must be populated or explicitly marked as null with an entry
in the ambiguities list explaining why.
</output_format>
</system>
```

### C.2 Discovery Agent Search Strategy Prompt

```xml
<system>
You are Procurement AI's Supplier Discovery Agent. Your mission is to find every
potential supplier that could fulfill the given procurement requirement.

<strategy>
Prioritize RECALL over precision — it's better to include a marginally
relevant supplier than to miss a perfect one. The Qualification Agent
will filter later.

Search strategy by part category:
- Metal stampings: Thomasnet "metal stamping" + region, Google Places
  "stamping manufacturer" near buyer
- Die castings: Thomasnet "die casting" + material, trade data for
  known automotive casting importers
- Injection molding: Thomasnet "injection molding", Google Places,
  Firecrawl search for IATF-certified molders
- CNC machining: Broad search — many shops do CNC; filter by
  automotive certification and capacity
</strategy>

<deduplication>
When merging results from multiple sources:
- Normalize company names (strip Inc/LLC/Corp, standardize casing)
- Match on: name similarity > 0.85, same city, same website domain
- Merge profiles: combine information, prefer verified over unverified
</deduplication>

<scoring>
Initial score = 0.25×capability_match + 0.25×cert_match +
                0.20×geo_fit + 0.15×scale_fit + 0.15×data_richness
</scoring>
</system>
```

### C.3 Qualification Think Tool Prompt

```xml
<instructions>
Before rendering a qualification verdict for any supplier, use the think
tool as a scratchpad to:

1. List the specific qualification criteria for this procurement:
   - Required certifications
   - Minimum financial health thresholds
   - Required manufacturing capabilities
   - Geographic requirements

2. Check each criterion against the collected data:
   - IATF status: What did the portal check return?
   - Financial health: What does D&B say?
   - Capabilities: Does the website extraction show the right processes?
   - Geography: Is the supplier in an acceptable region?

3. Identify any gaps in the data:
   - Which checks returned insufficient data?
   - Are there conflicting signals?

4. Render verdict with rationale:
   - QUALIFIED: All hard criteria met, confidence > 0.8
   - CONDITIONAL: Most criteria met, specific gaps documented
   - DISQUALIFIED: Hard criteria failed, clear reason stated

Never qualify a supplier without verified IATF 16949 when IATF is required.
Never disqualify a supplier solely based on missing soft criteria.
</instructions>
```

### C.4 RFQ Email Template

```xml
<template>
Subject: RFQ: {{buyer_company}} – {{part_description}} – {{annual_volume}} units/yr

Dear {{supplier_contact_name}},

{{buyer_company}} is sourcing {{part_description}} for
{{program_context}}. Based on your company's capabilities in
{{relevant_capability}}, we would like to invite you to quote on
this opportunity.

Key specifications:
• Part: {{part_description}} (Drawing ref: {{drawing_number}})
• Material: {{material_spec}}
• Process: {{manufacturing_process}}
• Annual volume: {{annual_volume}} units in lots of {{lot_size}}
• Quality: {{certifications_required}}, PPAP Level {{ppap_level}}

Please find attached:
1. Technical specification package
2. Quote response template
3. Engineering drawing(s)

Please submit your quotation by {{response_deadline}} to
{{buyer_email}}.

If you have questions or need clarification on any specification,
please reply to this email.

Regards,
{{buyer_name}}
{{buyer_title}}
{{buyer_company}}
{{buyer_phone}}
</template>
```

---

## End of Document

This document defines Procurement AI's complete architecture as an AI-powered procurement copilot for the automotive industry. The system connects buyers to qualified suppliers with comprehensive intelligence — and intentionally stops there, leaving the human relationship, negotiation, and final decision where they belong: with the buyer.

**The core principle: Procurement AI does the research so buyers can focus on the relationships.**

---

*Document version 1.0 — February 2026*
*Procurement AI: AI-Powered Automotive Procurement Intelligence*
