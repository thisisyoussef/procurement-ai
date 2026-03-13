# Procurement AI — Master Logic Document

## What This Document Is

This is a complete, logic-first reference of how Procurement AI works as a product. It documents every decision the system makes, every step it takes, every prompt it uses, and every data handoff between stages. It is written for a non-technical audience (or a consultant/architect) who needs to understand the *intent and behavior* of the system — not the code.

Use this document to reshape, improve, and recreate the project under any technical architecture.

---

## Table of Contents

1. [Product Intent & Core Value Proposition](#1-product-intent--core-value-proposition)
2. [End-to-End User Journey](#2-end-to-end-user-journey)
3. [The Pipeline: Overview](#3-the-pipeline-overview)
4. [Stage 1: Requirements Parsing](#4-stage-1-requirements-parsing)
5. [Stage 2: Supplier Discovery](#5-stage-2-supplier-discovery)
6. [Stage 3: Supplier Verification](#6-stage-3-supplier-verification)
7. [Stage 4: Supplier Comparison](#7-stage-4-supplier-comparison)
8. [Stage 5: Recommendation](#8-stage-5-recommendation)
9. [Stage 6: Outreach (Optional)](#9-stage-6-outreach-optional)
10. [Post-Pipeline Agents](#10-post-pipeline-agents)
11. [The Discovery Sub-System (Multi-Team)](#11-the-discovery-sub-system-multi-team)
12. [Checkpoints & User Steering](#12-checkpoints--user-steering)
13. [Buyer Context & Personalization](#13-buyer-context--personalization)
14. [Supplier Memory & Learning](#14-supplier-memory--learning)
15. [Chat Agent (Interactive Advisor)](#15-chat-agent-interactive-advisor)
16. [Data Contracts Between Stages](#16-data-contracts-between-stages)
17. [All Prompts: Full Text & Intent](#17-all-prompts-full-text--intent)
18. [Error Handling & Recovery Patterns](#18-error-handling--recovery-patterns)
19. [Evaluation & Quality Assurance Suite](#19-evaluation--quality-assurance-suite)
20. [Deviations from the Original Brief](#20-deviations-from-the-original-brief)
21. [Outreach Orchestration (Detailed)](#21-outreach-orchestration-detailed)
22. [Communication Monitoring](#22-communication-monitoring)
23. [Dashboard Intelligence](#23-dashboard-intelligence)
24. [Authentication & Lead Capture](#24-authentication--lead-capture)
25. [Frontend Architecture Overview](#25-frontend-architecture-overview)
26. [LLM Gateway Details](#26-llm-gateway-details)

---

## 1. Product Intent & Core Value Proposition

**What Procurement AI does:** A small business founder describes what product they need to source. Procurement AI's AI agents then automatically find suppliers worldwide, verify their legitimacy, compare them side-by-side, and recommend the best options — with the option to auto-draft outreach emails.

**The core promise:** "Describe what you need → Get a vetted, ranked shortlist of real suppliers in 2-5 minutes."

**Who it's for:** Small business founders, DTC brand owners, and first-time importers who lack procurement expertise, supplier networks, or the time to manually search, vet, and compare dozens of potential suppliers.

**What makes it different from manual sourcing:**
- Searches 6+ data sources simultaneously (Google Places, Firecrawl web search, B2B marketplaces like Alibaba/Thomasnet/IndiaMART, regional/multilingual searches, and an internal supplier memory database)
- Automatically detects and filters out intermediaries, trading companies, and retail stores — surfacing only direct manufacturers
- Verifies each supplier across multiple dimensions (website quality, business registration, certifications, reviews, social presence)
- Calculates estimated landed costs (unit price + shipping + duties) not just unit prices
- Generates personalized, multilingual outreach emails
- Learns from past projects to improve future recommendations

---

## 2. End-to-End User Journey

### Happy Path (No Checkpoints)

1. **User submits a brief** — Free-text description like "I need 500 custom canvas tote bags, 14x16 inches, 12oz cotton canvas, screen printed with my logo in 2 colors, delivered to LA by March"
2. **System parses requirements** (~5-10 seconds) — Extracts product type, material, quantity, deadline, certifications, delivery location, budget. Generates search queries. May ask clarifying questions if critical info is missing.
3. **User answers clarifying questions** (if any) — e.g., "What's your budget range?" or "Any certification requirements?"
4. **System discovers suppliers** (~30-60 seconds) — Searches Google Places, web scraping, B2B marketplaces, regional directories, and internal memory in parallel. Finds 50-150 raw results, deduplicates and filters to 20-40 viable candidates.
5. **System verifies suppliers** (~60-120 seconds) — Scrapes each supplier's website, checks business registration, validates certifications, analyzes reviews. Scores each 0-100.
6. **System compares suppliers** (~10-20 seconds) — Side-by-side analysis of pricing, shipping costs, lead times, MOQs, certifications. Calculates landed costs.
7. **System recommends** (~10-20 seconds) — Ranks suppliers into decision lanes (Best Overall, Best Low-Risk, Best Speed-to-Order). Provides reasoning, trust signals, uncertainty notes, and pre-PO checklist per supplier.
8. **User reviews results** — Browses comparison table, reads recommendation narratives, drills into individual supplier details.
9. **User can chat** — Ask follow-up questions, request re-ranking with different priorities, trigger additional research.
10. **User triggers outreach** (optional) — System drafts personalized RFQ emails for selected suppliers, user reviews and approves, emails are sent.
11. **Post-outreach** — System monitors for responses, parses incoming quotes, can draft follow-ups or negotiation emails, and can make phone calls via AI voice agent.

### With Checkpoints (Steering Mode)

Between each major stage, the system can pause and present a "checkpoint" where the user can:
- Confirm or edit parsed requirements
- Review discovered suppliers before verification
- Set a confidence gate (minimum score to proceed)
- Adjust comparison weights (price vs. speed vs. risk)
- Set outreach preferences before emails are drafted

Checkpoints have auto-continue timers (default 30 seconds) so the pipeline doesn't stall if the user doesn't engage.

---

## 3. The Pipeline: Overview

The system runs as a directed graph (state machine) with 5-6 sequential stages. Each stage reads from and writes to a shared state object.

```
User Input
    │
    ▼
┌─────────────────┐
│  STAGE 1: PARSE │  Convert natural language → structured requirements
│  (5-10 sec)     │  Model: Sonnet (reasoning needed for regional strategy)
└────────┬────────┘
         │ Outputs: ParsedRequirements
         ▼
┌─────────────────────┐
│  STAGE 2: DISCOVER  │  Search 6+ sources in parallel → deduplicate → filter → rank
│  (30-60 sec)        │  Model: Sonnet (relevance scoring needs reasoning)
└────────┬────────────┘
         │ Outputs: DiscoveryResults (20-40 suppliers)
         ▼
┌─────────────────────┐
│  STAGE 3: VERIFY    │  5 parallel checks per supplier → composite score
│  (60-120 sec)       │  Model: Haiku (extraction) + Sonnet (assessment)
└────────┬────────────┘
         │ Outputs: VerificationResults (scored suppliers)
         ▼
┌─────────────────────┐
│  STAGE 4: COMPARE   │  Side-by-side analysis → landed cost → scoring
│  (10-20 sec)        │  Model: Sonnet (reasoning for trade-off analysis)
└────────┬────────────┘
         │ Outputs: ComparisonResult (ranked comparisons)
         ▼
┌─────────────────────┐
│  STAGE 5: RECOMMEND │  Final ranked picks → decision lanes → confidence
│  (10-20 sec)        │  Model: Sonnet (highest-stakes synthesis)
└────────┬────────────┘
         │ Outputs: RecommendationResult
         ▼
┌─────────────────────┐
│  STAGE 6: OUTREACH  │  (Optional) Draft + send personalized RFQ emails
│  (5-10 sec)         │  Model: Sonnet (email drafting needs nuance)
└─────────────────────┘
```

**Key architectural decision:** Each stage is independent and idempotent. The pipeline can be re-run from any stage forward with modified inputs. If Stage 5 produces weak results, the system can automatically loop back to Stage 2 with expanded search queries.

---

## 4. Stage 1: Requirements Parsing

### Intent
Convert a free-text product sourcing request into a structured, machine-readable specification that all downstream agents can use consistently.

### Input
- `raw_description`: Free-text string from the user (e.g., "I need 500 custom canvas tote bags...")
- `buyer_context` (optional): Persistent buyer profile with logistics, financial, and quality preferences
- `user_sourcing_profile` (optional): Historical preferences from past projects

### What the AI Does

The LLM receives a system prompt that positions it as a "Master Procurement Sourcer and Requirements Analyst" with instructions to:

1. **Extract 14 structured fields** from the natural language:
   - `product_type` — What the product IS (e.g., "canvas tote bag")
   - `material` — What it's MADE OF (e.g., "12oz cotton canvas")
   - `dimensions` — Size specifications
   - `quantity` — How many units
   - `customization` — Custom work needed (printing, embossing, etc.)
   - `delivery_location` — Where to ship the finished goods
   - `deadline` — When they're needed by
   - `certifications_needed` — Required certifications (ISO, OEKO-TEX, etc.)
   - `budget_range` — Price expectations
   - `search_queries` — 5+ B2B-oriented search queries for discovery
   - `regional_searches` — 2-4 optimal sourcing regions with multilingual queries
   - `clarifying_questions` — Questions for missing critical information
   - `sourcing_strategy` — Narrative approach for this particular sourcing need
   - `risk_tolerance`, `priority_tradeoff`, `evidence_strictness` — Decision preferences

2. **Separate product type from material and geography** — This is a critical guardrail. "Egyptian cotton hoodies" means the product is HOODIES, the material is Egyptian cotton. Egypt is a material source, not necessarily where to manufacture. The system explicitly disambiguates sourcing location (where things are MADE) from delivery location (where things are SHIPPED TO).

3. **Generate regional search strategies** — For each promising region (e.g., China, Turkey, India), generate:
   - Multilingual search queries (Chinese characters for Chinese searches, Turkish for Turkish searches)
   - Region-specific platforms to search (e.g., 1688.com for China, IndiaMART for India)
   - Expected strengths of that region for the product type

4. **Generate clarifying questions** — Based on input completeness:
   - Very detailed input → 0-1 questions
   - Moderate detail → 1-2 questions
   - Vague input → 3-4 questions
   - Each question includes: `why_this_question`, `if_skipped_impact`, `suggested_default`, and `suggestions` (multiple choice options)

### Post-LLM Guardrails (Code-Level)

After the LLM responds, the system applies several programmatic safety checks:

1. **Example leak detection** — Checks if the LLM hallucinated a product type from its training examples rather than the actual user input. Compares tokens in the raw input against tokens in the parsed output; if they share no overlap, it rebuilds the product type from the raw input.

2. **Automotive domain detection** — If the input contains automotive signals (OEM, IATF, PPAP, stamping, etc.), automatically injects automotive-specific certifications and generates industry-specific search queries.

3. **Empty field fallbacks** — If product_type is empty, extracts it from the raw input using regex patterns. If search_queries is empty, generates default queries from the product type.

4. **Clarifying question enhancement** — Enriches each question with standardized `why_this_question`, `if_skipped_impact`, and `suggested_default` fields from templates for common fields (quantity, budget, delivery location, certifications, deadline, trade-off priority).

### Output
`ParsedRequirements` — A structured object containing all 14+ fields, ready for the discovery stage.

### LLM Model Choice
**Sonnet** (not Haiku) — The brief planned to use Haiku for parsing, but the actual build uses Sonnet because regional strategy generation and intelligent clarifying questions require stronger reasoning.

---

## 5. Stage 2: Supplier Discovery

### Intent
Search multiple data sources simultaneously to find 20-40 real, relevant suppliers matching the parsed requirements.

### Input
- `ParsedRequirements` from Stage 1
- `buyer_context` (optional)
- `user_sourcing_profile` (optional)

### The Discovery Process (Step by Step)

#### Step 1: Internal Memory Search
Before searching external sources, check the internal supplier database for previously discovered and verified suppliers matching the product type. This uses keyword + semantic hybrid search.

#### Step 2: Generate Search Queries
Build multiple search query sets:
- **Core product queries** — From parsed requirements' `search_queries` field (e.g., "canvas tote bag manufacturer", "cotton tote supplier OEM")
- **Marketplace-specific queries** — For each relevant B2B marketplace (Alibaba, Thomasnet, IndiaMART, etc.), generate site-targeted searches
- **Regional/multilingual queries** — From the `regional_searches` field, queries in local languages

#### Step 3: Parallel Search Execution
Fire off searches to multiple sources simultaneously:

1. **Google Places API** — Queries like "[product] manufacturer near [location]". Returns business name, address, phone, website, Google rating, reviews. Free tier: 10,000 calls/month.

2. **Firecrawl Web Search** — General web search optimized for B2B results. Each query returns web pages which are scraped for supplier information. Multiple queries run in parallel.

3. **B2B Marketplace Searches** — Site-targeted searches on relevant platforms:
   - Alibaba (for China-centric manufacturing)
   - Thomasnet (US industrial)
   - IndiaMART (Indian manufacturers)
   - Europages (European suppliers)
   - GlobalSources (Asian electronics/hardware)
   - Made-in-China
   - Faire (artisan/DTC wholesale)

   The system selects the 3 most relevant marketplaces based on product type tag matching.

4. **Regional Searches** — Multilingual queries targeting specific geographic regions identified in Stage 1.

5. **Common Consumer Marketplace Searches** — Targeted searches on Etsy, Amazon, Alibaba with product-specific queries (useful for finding smaller/artisan manufacturers).

#### Step 4: LLM-Powered Result Analysis
All raw search results are batched and sent to the LLM (Sonnet) with a prompt that instructs it to:

- **Score each supplier 0-100** using these weights:
  - Product TYPE match: 35%
  - Direct manufacturer evidence: 20%
  - Location preference match: 15%
  - Certification match: 10%
  - Reviews/reputation: 10%
  - MOQ fit: 10%

- **Detect intermediaries** — Flag trading companies, marketplace aggregators, and directory sites. Apply a -20 relevance penalty.

- **Detect retail stores** — Identify consumer-facing stores (Etsy shops, Amazon sellers, boutiques) and penalize them unless specifically searching for small-batch artisan producers.

- **Separate product type from material** — A hoodie manufacturer using Egyptian cotton scores HIGH for "Egyptian cotton hoodies". A pajama store using Egyptian cotton scores LOW.

- **Extract key data per supplier**: name, website, email, phone, location, description, estimated MOQ, estimated pricing, certifications, product page URLs, shipping estimates, language discovered in

- **Provide market intelligence** — Overall landscape assessment, common pricing ranges, typical MOQs, recommended regions, supply chain risks.

#### Step 5: Intermediary Resolution
For suppliers flagged as intermediaries (directories, trading companies), the system attempts to resolve the actual manufacturer:
- **URL pattern detection** — Known intermediary domains (alibaba.com, thomasnet.com, indiamart.com, etc.)
- **LLM classification** — If URL pattern is ambiguous, sends website content to LLM for classification
- **Direct website resolution** — Attempts to find the manufacturer's actual website through the intermediary listing

#### Step 6: Deduplication
Suppliers found across multiple sources are merged using a priority-based key system:
1. Domain match (highest priority)
2. Email match
3. Source ID match
4. Fuzzy name match (lowest priority)

When merging, the system preserves the richer record and boosts the relevance score for suppliers found in multiple sources (cross-reference boost).

#### Step 7: Product Anchor Filtering
After scoring, the system validates each supplier against "anchor terms" extracted from the product type and material:
- For 1-2 anchor terms: at least 1 must match (OR logic)
- For 3+ anchor terms: at least 2 must match (AND logic)
- Generic B2B terms (manufacturer, supplier, wholesale, etc.) are excluded from anchor matching
- Suppliers failing anchor matching are moved to a `filtered_suppliers` list with a reason tag

#### Step 8: Volume Expansion (If Needed)
If the initial search returns fewer than 8 viable suppliers OR fewer than 3 high-quality suppliers:
- Generate new search queries (OEM manufacturer, certified supplier, export factory, wholesale producer variations)
- Increase the minimum supplier count target
- Re-run discovery with expanded queries
- Maximum 2-3 expansion rounds

### Output
`DiscoveryResults` containing:
- `suppliers` — List of 20-40 `DiscoveredSupplier` objects (scored, deduplicated, filtered)
- `filtered_suppliers` — Suppliers that were removed with reasons (wrong industry, intermediary, retail store, etc.)
- `sources_searched` — Which sources were queried
- `market_intelligence` — Overall market landscape assessment
- `total_raw_found` — How many raw results before deduplication
- `deduplicated_count` — How many unique suppliers after merging

### LLM Model Choice
**Sonnet** — Relevance scoring and intermediary detection require reasoning about supplier business models and product categories.

---

## 6. Stage 3: Supplier Verification

### Intent
Verify the legitimacy and quality of each discovered supplier through multiple independent checks, producing a trust score.

### Input
- Top 40 suppliers from discovery (sorted by relevance score)
- If fewer than 25 top suppliers exist, borderline candidates from `filtered_suppliers` are backfilled (except those filtered for `wrong_industry`)
- `ParsedRequirements`
- `buyer_context`

### What Happens

For each supplier, 5 verification checks run in parallel:

#### Check 1: Website Analysis (Weight: 35% of composite)
- **Tool used:** Firecrawl scrapes the supplier's website
- **What's evaluated:** Professional design, product pages exist, about/company history, contact information completeness, SSL certificate present
- **Score:** 0-100 based on completeness and professionalism
- **Enrichment:** During scraping, the system also extracts contact information (emails, phones, addresses) using a dedicated contact enrichment prompt

#### Check 2: Review & Reputation Check (Weight: 25%)
- **Tool used:** Google Places API for ratings and review counts
- **What's evaluated:** Google rating (1-5 stars), review count, sentiment of recent reviews
- **Score:** Based on rating threshold and review volume

#### Check 3: Business Registration (Weight: 20%)
- **What's evaluated:** Whether the company appears in business registries, years in operation, registered agent, active status
- **Score:** Based on verification completeness and company age

#### Check 4: Contact Enrichment (Weight: 10%)
- **Tool used:** Website screenshot analysis, Hunter.io email verification
- **What's evaluated:** Whether valid sales/procurement email addresses were found, phone numbers, physical address
- **Score:** Based on contact completeness

#### Check 5: Image/Visual Analysis (Weight: 10%)
- **Tool used:** Image extraction from website
- **What's evaluated:** Product photos, factory photos, certification images
- **Score:** Based on visual evidence of manufacturing capability

### Composite Score Calculation
Each check produces a sub-score (0-100). The composite is a weighted average:

```
composite = (website × 0.35) + (reviews × 0.25) + (registration × 0.20) + (enrichment × 0.10) + (images × 0.10)
```

### Risk Level Assignment
- **Low risk** (composite ≥ 70): Strong evidence of legitimacy
- **Medium risk** (composite 40-70): Some evidence but gaps exist
- **High risk** (composite < 40): Insufficient evidence or red flags

### Verification Recommendation
- **Proceed** (score ≥ 60): Safe to include in comparison
- **Caution** (score 40-60): Include but flag concerns
- **Reject** (score < 40): Exclude from comparison unless no better options

### Contact Information Merge-Back
After verification, any newly discovered contact information (emails, phones from website scraping) is merged back into the discovery results, enriching the supplier records for outreach.

### Output
`VerificationResults` containing:
- `verifications` — List of `SupplierVerification` objects, each with: supplier name, individual check results, composite score, risk level, recommendation, and any enriched contact data

### LLM Model Choice
**Haiku** for data extraction (contact info, basic classification), **Sonnet** for quality assessment and risk reasoning.

---

## 7. Stage 4: Supplier Comparison

### Intent
Generate a side-by-side comparison of all verified suppliers with weighted scoring and narrative trade-off analysis.

### Input
- `ParsedRequirements`
- Verified suppliers (filtered by confidence gate — default minimum score 30)
- `VerificationResults`
- `buyer_context` and `user_sourcing_profile`

### Confidence Gate
Before comparison, suppliers are filtered through a confidence gate:
- Default threshold: 30 (composite verification score)
- User can adjust this at checkpoint
- Suppliers below the gate are logged as "gated" with their score and reason
- If ALL suppliers fail the gate, the top 10 from discovery are used as fallback

### What the AI Does

The LLM receives all supplier data and is instructed to produce a comparison analyzing each supplier on:

1. **Estimated pricing** — Unit price, volume discounts
2. **Estimated shipping cost** — Based on origin → delivery location, freight method, weight/volume estimates, Incoterms
3. **Estimated landed cost** — unit_price + shipping_per_unit + duties/tariffs (THIS IS THE KEY METRIC, not just unit price)
4. **MOQ requirements** vs. buyer's desired quantity
5. **Lead time estimates** — Production + shipping time
6. **Certifications** — Which required certs they hold
7. **Strengths and weaknesses** — Qualitative assessment

### Scoring Formula
Each supplier gets an `overall_score` (0-100) computed as:

```
overall_score = (
    total_cost_competitiveness × 0.30 +    # Landed cost, not just unit price
    lead_time × 0.20 +
    moq_fit × 0.15 +
    payment_terms_flexibility × 0.10 +
    certifications × 0.10 +
    verification_score × 0.15
)
```

### Sub-Category Star Ratings (0-5 scale)
Each supplier also gets granular ratings:
- `price_score` — Cost competitiveness
- `quality_score` — Quality signals and certifications
- `shipping_score` — Shipping cost and logistics fit
- `review_score` — Reputation and reviews
- `lead_time_score` — Speed of delivery

### Category Tags
The comparison identifies:
- `best_value` — Lowest total landed cost
- `best_quality` — Highest quality signals
- `best_speed` — Fastest lead time

### Relevance Guard
Suppliers in completely different industries (e.g., a plumbing supply company appearing in a textile search) receive a score of 0 and are excluded from the comparison narrative.

### Analysis Narrative
A 2-3 paragraph plain-language analysis written for non-technical small business founders, explaining:
- The trade-offs between suppliers
- When cheaper unit price is offset by higher shipping costs
- Which certifications matter for their use case
- Any red flags or limitations in the data

### Output
`ComparisonResult` containing:
- `comparisons` — List of `SupplierComparison` objects with all scores and analysis
- `analysis_narrative` — Plain-language summary
- `best_value`, `best_quality`, `best_speed` identifiers

### Error Handling
If comparison fails entirely, the pipeline continues with an empty comparison result and a note that recommendations are based on discovery and verification data only. This is a "non-fatal" failure.

### LLM Model Choice
**Sonnet** — Trade-off analysis and cost reasoning require strong analytical capabilities.

---

## 8. Stage 5: Recommendation

### Intent
Synthesize all data into a final ranked recommendation with confidence scores, organized into decision lanes so the user can quickly identify the best option for their specific priority.

### Input
- `ParsedRequirements`
- `ComparisonResult`
- `VerificationResults`
- `buyer_context` and `user_sourcing_profile`

### What the AI Produces

#### 1. Executive Summary (2-3 sentences)
Overview of the sourcing landscape, confidence level, and total cost perspective. Sets expectations for what follows.

#### 2. Decision Checkpoint Summary (1-2 sentences)
Whether the user is ready to make an outreach decision or if more research is needed.

#### 3. Ranked Recommendations (up to 12 suppliers)
Each recommendation includes:

| Field | Description |
|-------|-------------|
| `rank` | Position in overall ranking |
| `supplier_name` | Full supplier name |
| `supplier_index` | Reference to discovery array position |
| `overall_score` | 0-100 composite score |
| `confidence` | How confident the system is in this recommendation |
| `reasoning` | 2-3 sentences including unit price + shipping = landed cost analysis |
| `best_for` | Category tag (e.g., "Lowest landed cost", "Most responsive") |
| `lane` | Decision lane assignment (see below) |
| `why_trust` | 1-3 compact bullets with proof signals |
| `uncertainty_notes` | 1-3 bullets on unresolved uncertainty |
| `verify_before_po` | 1-4 checklist items before placing a purchase order |
| `needs_manual_verification` | Boolean flag |
| `manual_verification_reason` | Why manual checks are needed |

#### 4. Decision Lanes
Suppliers are assigned to one of four lanes:

- **`best_overall`** — Highest combined score across all dimensions. The "if you could only pick one" option.
- **`best_low_risk`** — Highest verification score (≥70). For risk-averse buyers who prioritize trust over price.
- **`best_speed_to_order`** — Fastest lead time. For buyers with urgent deadlines.
- **`alternative`** — Strong options that don't top any lane but are worth considering.

#### 5. Elimination Rationale
Explains why the recommendation set is narrower than the discovery set (e.g., "34 suppliers found → 18 verified → 8 scored above confidence gate → 5 recommended").

#### 6. Caveats
Warnings about data limitations, shipping cost disclaimers, market conditions, and suggested next steps.

### Auto-Recovery Logic
After generating recommendations, the system checks quality:

```
IF (lanes_covered < 2) OR (avg_confidence < 50) OR (total_recommendations < 3):
    → Trigger expanded search with broader queries
    → Re-run verify → compare → recommend with combined results
    → If recovery produces better results, use them
    → If not, append caveat: "Recommendation quality was low"
```

This auto-recovery loop runs once and uses expanded search queries (OEM manufacturer, certified supplier, export factory, wholesale producer variations).

### Output
`RecommendationResult` containing:
- `executive_summary`
- `decision_checkpoint_summary`
- `recommendations` — Ranked list with full detail
- `elimination_rationale`
- `caveats`

### LLM Model Choice
**Sonnet** — This is the highest-stakes synthesis step. Clear writing, accurate cost analysis, and sound judgment are critical.

---

## 9. Stage 6: Outreach (Optional)

### Intent
Auto-draft personalized RFQ (Request for Quotation) emails for the top recommended suppliers and queue them for sending.

### Trigger
Only runs if `auto_outreach_enabled` is true. Otherwise, the user can manually trigger outreach from the UI.

### Input
- Top 5 recommended suppliers (must have email addresses)
- `ParsedRequirements`
- `RecommendationResult`
- Business profile (company name, contact person, phone, website)
- `buyer_context` and `user_sourcing_profile`

### Email Drafting Logic

Each email follows this structure:
1. **Subject line** — Clear, includes product type (e.g., "RFQ: Custom Canvas Tote Bags — 500 Units")
2. **Opening** — Buyer company intro using REAL company name and description (1-2 sentences)
3. **Product requirements** — Specs, quantity, material, customization, certifications
4. **Information requested** — Specific asks: unit pricing, volume discounts, MOQ, lead time, sample availability/cost, payment terms, shipping options
5. **Deadline** — 5-7 business days for response
6. **Sign-off** — Real name, title, company, phone, website

### Personalization
Each email references the specific supplier's capabilities, certifications, or notable products found during discovery. Not generic templates.

### Multilingual Support
If a supplier's detected language is not English:
- The ENTIRE email is written in that language (including subject line)
- Culturally appropriate greetings are used (e.g., "尊敬的" for Chinese, "Sayın" for Turkish)
- Units, date formats, and business terminology are adapted
- Buyer identity (name, company) stays in original form

### Email Sending
- Emails are sent via Resend API
- Each email gets a unique tracking ID
- Delivery events (sent, delivered, opened, bounced) are tracked via webhooks
- Bounced emails flag the supplier as "uncontactable"

### Output
`OutreachState` containing:
- `selected_suppliers` — Indices of suppliers being contacted
- `supplier_statuses` — Per-supplier tracking (email status, response status)
- `draft_emails` — The actual email content
- `auto_config` — Settings like auto-send threshold and max concurrent outreach

---

## 10. Post-Pipeline Agents

These agents run after the main pipeline, either automatically or on user action.

### Follow-Up Agent
**Purpose:** Draft follow-up emails for non-responsive suppliers.

**Cadence:**
- Day 3: Gentle reminder — "Just checking if you received our inquiry"
- Day 7: More direct — "We're finalizing our supplier selection this week"
- Day 14: Final notice — "This is our last follow-up, response needed within 3 business days"

After 3 follow-ups with no response, the supplier is marked "non-responsive" and removed from the active pipeline.

**Tone progression:** Friendly → Professional urgency → Direct/firm

### Response Parser Agent
**Purpose:** Extract structured quote data from supplier email responses.

**What it extracts:**
- Unit price + currency
- MOQ
- Lead time
- Payment terms
- Shipping terms (Incoterms)
- Quote validity period
- Sample availability/cost
- Whether they can fulfill the specifications
- Fulfillment notes if they cannot

**Confidence scoring:**
- 90-100: All key fields clearly stated
- 70-89: Most fields present, some inferred
- 50-69: Partial info, several missing/ambiguous
- Below 50: Very incomplete

Fields are only extracted if explicit or clearly implied. The system never guesses.

### Negotiation Agent
**Purpose:** Evaluate supplier quotes and draft intelligent responses.

**Decision framework — four possible actions:**

| Action | When to Use | Email Tone |
|--------|-------------|------------|
| **ACCEPT** | Price within budget, all critical fields present, high verification score | Warm, confirm next steps |
| **CLARIFY** | Missing critical fields, unclear terms, need proforma invoice | Professional, specific asks |
| **COUNTER** | Price 10-30% above budget, MOQ too high, lead time too long | Firm but polite, never reveal competitor details |
| **REJECT** | Price >50% above budget, can't meet fundamentals, risk too high | Respectful decline |

**Rules:**
- Never reveal competitor names or exact prices
- Always include a specific CTA with timeline
- Keep to 3-6 sentences main point + specific asks

### Phone Agent
**Purpose:** Make AI-powered phone calls to suppliers via Retell AI voice platform.

**Call structure:**
1. Introduce self (name, company, product seeking)
2. Ask if they manufacture directly
3. Get pricing for requested quantity
4. Ask about MOQ
5. Ask about lead time and expedite options
6. Ask about customization capabilities
7. Ask about certifications
8. Get email address for formal RFQ

**Rules:** One question at a time, repeat back numbers to confirm, keep under 5 minutes, if busy offer callback.

### Inbox Monitor
**Purpose:** Monitor email inbox for supplier responses, route them to the response parser, and update project state.

**Runs on a schedule** (configurable interval) checking for new emails from contacted suppliers, matching them to projects via sender email address.

### Form Filler
**Purpose:** Auto-fill supplier contact forms on websites when email addresses aren't available. Uses Browserbase (headless browser) to navigate to supplier websites, find contact forms, and fill them with the buyer's information and RFQ details.

---

## 11. The Discovery Sub-System (Multi-Team)

The actual build includes an advanced multi-team discovery system that goes beyond the brief's single discovery agent.

### Architecture
Instead of one monolithic discovery agent, the system deploys 5 specialized search "teams" in parallel, each with a different search strategy and scoring lens:

#### Team 1: Direct Manufacturer Hunt
- **Mission:** Find actual factories, not intermediaries
- **Strategy:** Searches for factory indicators (OEM, manufacturing facility, production capacity)
- **Scoring priority:** Manufacturing evidence (factory photos, production lines, capacity statements)

#### Team 2: Market Intelligence Sweep
- **Mission:** Capture broad market signals
- **Strategy:** Wide-net search across all marketplace platforms
- **Scoring priority:** Pricing norms, MOQ patterns, common lead times

#### Team 3: Regional Deep Dive
- **Mission:** Find suppliers in specific geographic regions using local languages
- **Strategy:** Region-specific searches (Chinese on 1688.com, Turkish on local directories, etc.)
- **Scoring priority:** Regional expertise, local certifications, proximity to ports

#### Team 4: Reputation & Trust
- **Mission:** Surface the most trusted, well-reviewed suppliers
- **Strategy:** Focus on review sites, certification databases, industry awards
- **Scoring priority:** Verification score, review quality, certification validity

#### Team 5: Proximity & Logistics
- **Mission:** Find suppliers optimized for the buyer's shipping needs
- **Strategy:** Geographic proximity to delivery location, port access, shipping infrastructure
- **Scoring priority:** Lead time, shipping cost, logistics fit

### Aggregation
Results from all 5 teams are merged by the aggregator:
1. Deduplication (same priority-based key system as legacy discovery)
2. Cross-reference boosting (suppliers found by multiple teams get score boost)
3. Multi-dimensional scoring (each team contributes its own score dimension)
4. Final ranking combines all dimensions

### Fallback
If multi-team discovery fails, the system falls back to the legacy single-agent discovery system automatically.

---

## 12. Checkpoints & User Steering

### What Checkpoints Are
Checkpoints are pause points between pipeline stages where the user can review progress and adjust parameters. They are optional (controlled by a feature flag).

### The 5 Checkpoint Types

| Checkpoint | Between Stages | What User Can Do |
|------------|---------------|------------------|
| `CONFIRM_REQUIREMENTS` | Parse → Discover | Edit parsed requirements, answer clarifying questions |
| `REVIEW_SUPPLIERS` | Discover → Verify | Review discovered suppliers, remove irrelevant ones |
| `SET_CONFIDENCE_GATE` | Verify → Compare | Set minimum verification score threshold |
| `ADJUST_WEIGHTS` | Compare → Recommend | Change comparison weights (price vs. speed vs. risk) |
| `OUTREACH_PREFERENCES` | Recommend → Outreach | Choose which suppliers to contact, set email preferences |

### Auto-Continue
Each checkpoint has a timeout (default 30 seconds). If the user doesn't interact, the pipeline auto-continues with default settings. This prevents the pipeline from stalling.

### Checkpoint Data Flow
When a user responds to a checkpoint:
1. Their answers are merged into the `buyer_context` via `merge_checkpoint_answers()`
2. The modified context is passed to subsequent stages
3. The pipeline resumes from the next stage

### Re-Run from Stage
Users can also trigger a re-run from any stage forward (e.g., re-run from discovery with modified requirements). The system preserves all state from prior stages and only re-executes the requested stages.

---

## 13. Buyer Context & Personalization

### What Buyer Context Is
A structured profile of the buyer's preferences, constraints, and history that threads through every agent. It personalizes the entire pipeline.

### Components

#### Logistics Profile
- Primary shipping address, preferred ports
- Fulfillment model (direct-to-consumer, warehouse, dropship)
- Import experience level (first-time, occasional, regular)
- Customs broker availability
- Preferred shipping methods and Incoterms

#### Financial Profile
- Budget range, payment methods available
- Deposit capability (percentage willing to pay upfront)
- Currency preferences
- Cost sensitivity (how much price drives decisions)

#### Timeline Context
- Project deadline, urgency level
- Flexibility on timing
- Seasonal requirements

#### Quality Context
- Use case (retail, promotional, industrial)
- Quality tier expectations (economy, standard, premium)
- Required certifications
- Acceptable defect rate

#### Communication Preferences
- Language, timezone
- Preferred communication channel (email, phone, WhatsApp)
- Response time expectations

### How It's Built
1. **Initial build:** At project start, merges user defaults, business profile, and parsed requirements
2. **Checkpoint updates:** User answers at checkpoints are merged in
3. **Post-project learning:** After project completion, preferences are saved to the persistent user sourcing profile

### Metadata Tracking
The system tracks which fields were `explicitly_provided` by the user vs. `inferred` by the AI. This affects confidence in recommendations — explicitly stated preferences have higher weight.

---

## 14. Supplier Memory & Learning

### What It Is
A persistent database of supplier information that grows across projects. Every supplier discovered, verified, or interacted with is stored and can be retrieved in future searches.

### How Memory Search Works
When a new project starts, the system searches its memory using a hybrid approach:

1. **Keyword extraction** — Extracts specific product terms from the product_type and material fields (excluding generic B2B terms like "manufacturer", "supplier")
2. **Anchor term matching** — Requires multiple anchor term matches to avoid false positives
3. **Relevance scoring** — Composite of:
   - Base verification score (45% weight)
   - Is verified flag (bonus)
   - Interaction count (more interactions = more trusted)
   - Anchor term hit count
   - Keyword match count

### How Memory Gets Updated
- **After discovery:** New suppliers are upserted into the database
- **After verification:** Verification outcomes update supplier records
- **After project completion:** User feedback (positive/negative) updates supplier sentiment and relationship data

### User Profile Learning
The system maintains a `UserSourcingProfile` per user that accumulates across projects:
- **Supplier relationships:** Known suppliers with sentiment, communication rating, project count
- **Category experience:** Per-product-type breakdown with preferred regions, typical budgets, lessons learned
- **Behavioral signals:** Total projects, average budget, preferred risk/price sensitivity
- **Import experience level auto-upgrade:** First-time → Occasional (2+ projects) → Regular (5+ projects)

---

## 15. Chat Agent (Interactive Advisor)

### Intent
After the pipeline completes, users can chat with an AI advisor that has full access to all results and can trigger actions.

### What It Can Do

**Answer questions** from the data:
- "Why was Supplier X ranked lower than Supplier Y?"
- "What are the shipping costs from China vs. Turkey?"
- "Which supplier has the best certifications?"

**Trigger re-evaluation (most common):**
When a user shifts priorities ("I care more about speed now"), the chat agent first checks if existing data can be re-scored rather than triggering a full re-search. This is a critical efficiency optimization.

**Available actions the chat agent can trigger:**

| Action | What It Does | When to Use |
|--------|-------------|-------------|
| `rescore` | Re-run comparison + recommendation with adjusted weights | User shifts priorities |
| `adjust_weights` | Same as rescore | Explicit weight changes |
| `research` | Targeted additional search, then re-evaluate combined set | Need more options in specific area |
| `rediscover` | Full new discovery from scratch | Completely different product/region |
| `draft_outreach` | Draft RFQ emails for specific suppliers | User ready to contact |

### Decision Logic: Research vs. Rescore
The chat agent is instructed to:
1. **Re-evaluate first** — If user shifts priorities, check if existing data already covers the need. Re-score without re-searching.
2. **Research only when needed** — New discovery only if: completely different product/region, current results missing a critical dimension, user explicitly asks for more options, or current set is too small.
3. **Both** — Sometimes add suppliers AND re-rank.

### Response Style
- Under 200 words unless detailed analysis requested
- Cites specific supplier names, scores, and data points
- References shipping and landed costs for international suppliers
- Explains what changed in rankings when re-evaluating

---

## 16. Data Contracts Between Stages

Each stage reads and writes specific typed data structures. Here are the key contracts:

### ParsedRequirements (Stage 1 → 2)
```
product_type: string
material: string | null
dimensions: string | null
quantity: integer | null
customization: string | null
delivery_location: string | null
deadline: string | null
certifications_needed: string[]
budget_range: string | null
search_queries: string[] (5+ B2B queries)
regional_searches: RegionalSearchConfig[] (region, queries, language, platforms)
clarifying_questions: ClarifyingQuestion[] (question, field, suggestions, why, impact, default)
sourcing_strategy: string | null
sourcing_preference: string | null
risk_tolerance: string | null
priority_tradeoff: string | null
minimum_supplier_count: integer | null
evidence_strictness: string | null
missing_fields: string[]
```

### DiscoveredSupplier (Stage 2 → 3)
```
name: string
website: string | null
email: string | null
phone: string | null
location: string | null
country: string | null
description: string | null
relevance_score: float (0-100)
source: string (google_places, firecrawl, alibaba, memory, etc.)
capabilities: string[]
certifications: string[]
estimated_moq: string | null
estimated_pricing: string | null
product_page_url: string | null
language_discovered: string | null
intermediary: IntermediaryDetection | null
enrichment: ContactEnrichment | null
filtered_reason: string | null
```

### SupplierVerification (Stage 3 → 4)
```
supplier_name: string
checks: VerificationCheck[] (check_type, status, score, details)
composite_score: float (0-100)
risk_level: string (low/medium/high)
recommendation: string (proceed/caution/reject)
```

### SupplierComparison (Stage 4 → 5)
```
supplier_name: string
supplier_index: integer
overall_score: float (0-100)
estimated_pricing: string
estimated_shipping_cost: string
estimated_landed_cost: string
lead_time: string
moq: string
certifications: string[]
strengths: string[]
weaknesses: string[]
price_score: float (0-5)
quality_score: float (0-5)
shipping_score: float (0-5)
review_score: float (0-5)
lead_time_score: float (0-5)
```

### SupplierRecommendation (Stage 5 → 6)
```
rank: integer
supplier_name: string
supplier_index: integer
overall_score: float (0-100)
confidence: float
reasoning: string
best_for: string
lane: string (best_overall/best_low_risk/best_speed_to_order/alternative)
why_trust: string[]
uncertainty_notes: string[]
verify_before_po: string[]
needs_manual_verification: boolean
manual_verification_reason: string | null
```

### GraphState (Pipeline-Wide Shared State)
```
raw_description: string
current_stage: string (PipelineStage enum)
error: string | null
parsed_requirements: dict | null
discovery_results: dict | null
verification_results: dict | null
comparison_result: dict | null
recommendation_result: dict | null
outreach_result: dict | null
progress_events: list[dict]
user_answers: dict | null
auto_outreach_enabled: boolean
user_id: string | null
buyer_context: dict | null
user_sourcing_profile: dict | null
active_checkpoint: dict | null
checkpoint_responses: dict
checkpoint_auto_continue: boolean
confidence_gate_threshold: float
gated_suppliers: list[dict]
```

---

## 17. All Prompts: Full Text & Intent

### Prompt 1: Requirements Parser
**File:** `app/agents/prompts/requirements_parser.md`
**Role:** "MASTER PROCUREMENT SOURCER AND REQUIREMENTS ANALYST"
**Intent:** Extract structured specs, generate multilingual search strategies, ask smart clarifying questions.

**Key instructions:**
- Treat each request independently (no assumptions from prior requests)
- Separate product TYPE from MATERIAL from GEOGRAPHY
- Generate 5+ B2B-oriented search queries targeting manufacturers, not retail stores
- Identify 2-4 optimal sourcing regions with local-language queries
- Ask 0-4 clarifying questions based on input completeness
- Include sourcing vs. delivery location disambiguation rules
- Include the full JSON output schema

### Prompt 2: Discovery
**File:** `app/agents/prompts/discovery.md`
**Role:** "MASTER PROCUREMENT SOURCER AND SUPPLIER ANALYST"
**Intent:** Score, rank, and enrich suppliers from raw search results.

**Key instructions:**
- Score 0-100 with explicit weights (product match 35%, direct manufacturer 20%, location 15%, certs 10%, reviews 10%, MOQ 10%)
- Detect intermediaries (marketplaces, directories, trading companies) — apply -20 penalty
- Detect retail stores — penalize unless artisan search
- Product type vs. material separation (hoodies FROM Egyptian cotton vs. Egyptian cotton PRODUCTS)
- Only use product page URLs from raw data — never fabricate URLs
- Provide shipping cost estimates based on origin → destination
- Normalize multilingual results to English
- Return ALL suppliers scoring ≥20 (no arbitrary cap)

### Prompt 3: Verification
**File:** `app/agents/prompts/verification.md`
**Role:** "Supplier verification analyst"
**Intent:** Assess legitimacy across 6 dimensions with weighted scoring.

**Dimensions:** Website Quality (20%), Business Registration (25%), Certifications (20%), Reviews (15%), Social Presence (10%), Years in Operation (10%)

**Risk levels:** Low (≥70), Medium (40-70), High (<40)
**Recommendations:** Proceed (≥60), Caution (40-60), Reject (<40)

### Prompt 4: Comparison
**File:** `app/agents/prompts/comparison.md`
**Role:** "Procurement comparison analyst"
**Intent:** Side-by-side analysis with landed cost calculations and narrative trade-offs.

**Scoring weights:** Total cost (30%), Lead time (20%), MOQ fit (15%), Payment terms (10%), Certifications (10%), Verification score (15%)

**Key requirement:** Calculate LANDED cost (unit + shipping + duties), not just unit price. Flag when cheap unit price is offset by expensive shipping.

### Prompt 5: Recommendation
**File:** `app/agents/prompts/recommendation.md`
**Role:** "Senior procurement advisor"
**Intent:** Final ranked recommendations with decision lanes, trust signals, and actionable next steps.

**Structure:** Executive summary → Decision checkpoint → Ranked list with lanes → Elimination rationale → Caveats

**Lane assignment:** best_overall, best_low_risk, best_speed_to_order, alternative

### Prompt 6: Outreach
**File:** `app/agents/prompts/outreach.md`
**Role:** "Professional procurement email writer"
**Intent:** Draft personalized, multilingual RFQ emails.

**Key requirement:** Use REAL buyer info (name, company, phone). Write ENTIRE email in supplier's language if non-English. Include culturally appropriate greetings.

### Prompt 7: Follow-Up
**File:** `app/agents/prompts/followup.md`
**Role:** "Professional procurement follow-up email writer"
**Intent:** Escalating follow-up cadence (Day 3 → Day 7 → Day 14).
Tone: Friendly → Urgent → Direct. Under 150 words per email.

### Prompt 8: Response Parser
**File:** `app/agents/prompts/response_parser.md`
**Role:** "Procurement data extraction specialist"
**Intent:** Extract structured quote data with confidence scoring. Never guess — only extract explicit or clearly implied information.

### Prompt 9: Negotiation
**File:** `app/agents/prompts/negotiation.md`
**Role:** "Procurement negotiation specialist"
**Intent:** Four-action framework (Accept/Clarify/Counter/Reject) based on quote analysis. Never reveal competitor details.

### Prompt 10: Phone Agent
**File:** `app/agents/prompts/phone_agent.md`
**Role:** "Professional procurement specialist making a phone call"
**Intent:** Structured phone call script for AI voice agent. One question at a time. Keep under 5 minutes. Get email for formal RFQ.

### Prompt 11: Chat
**File:** `app/agents/prompts/chat.md`
**Role:** "AI procurement advisor"
**Intent:** Interactive advisor with action-triggering capability. Key principle: re-evaluate existing data before triggering new research.

### Prompt 12: Contact Enrichment
**File:** `app/agents/prompts/contact_enrichment.md`
**Role:** "Contact information extraction specialist"
**Intent:** Extract emails, phones, addresses from website content. Priority: sales@ > info@ > named person > support@ > ignore noreply@.

### Discovery Sub-Prompts (6 files)
These are currently brief stubs (1-2 lines each) indicating team mission. The actual intelligence is in the team agent code, not the prompts:
- Direct Manufacturer: Prioritize factory indicators
- Market Intelligence: Capture broad market signals
- Regional Deep Dive: Use local-language strategies
- Reputation & Trust: Prioritize verified trust signals
- Proximity & Logistics: Prioritize lead-time and shipping-fit
- Aggregator: Merge and deduplicate across teams

---

## 18. Error Handling & Recovery Patterns

### Stage-Level Recovery
Each stage catches all exceptions and writes an error to the shared state. The orchestrator checks for errors after each stage and stops the pipeline if one occurs.

**Pattern:**
```
IF stage fails:
    → Set current_stage = FAILED
    → Set error = descriptive message with traceback
    → Pipeline stops
    → User sees error in UI
```

### Non-Fatal Failures
Some stages treat failures as non-fatal:
- **Comparison failure** → Pipeline continues with empty comparison, recommendations based on discovery + verification only
- **Outreach failure** → Pipeline marks as complete, logs outreach error, user can retry manually

### Auto-Recovery (Recommendation Quality)
If recommendations are weak (fewer than 2 lanes covered, average confidence below 50, or fewer than 3 recommendations):
1. Expand search parameters (add OEM, certified, export, wholesale query variations)
2. Increase minimum supplier count to 8
3. Re-run discover → verify → compare → recommend
4. If recovery produces better results, use them
5. If not, add caveat about low quality

### Verification Pool Backfill
If the top supplier pool has fewer than 25 candidates, borderline suppliers from the filtered list are re-admitted (except those filtered for "wrong_industry"), up to a maximum of 40 total.

### LLM Output Parsing
The system handles LLM response parsing failures with multiple fallback strategies:
1. Try direct JSON parse
2. Try stripping markdown code block wrappers (```json ... ```)
3. Try regex extraction of JSON from response
4. If all fail, return a minimal valid object with "unknown" product type

### Feature Flag Fallbacks
Multi-team discovery has a feature flag. If multi-team discovery fails, the system automatically falls back to legacy single-agent discovery.

---

## 19. Evaluation & Quality Assurance Suite

The project includes an automated evaluation system (`agentic_suite/`) for measuring pipeline quality across multiple scenarios.

### How It Works
1. **Define scenarios** — JSON file with test cases (product descriptions, expected focus areas)
2. **Run scenarios** — CLI tool submits each scenario to the live backend, polls until completion
3. **Auto-answer clarifications** — A ClarificationAgent automatically answers any clarifying questions to keep runs flowing
4. **Critique each run** — A CriticAgent evaluates results against a rubric (success rate, supplier counts, confidence scores, failure modes)
5. **Aggregate across runs** — Statistics on success rate, stage dropoff, failure modes
6. **Generate PRD** — A PRDWriterAgent creates a product requirements document from aggregate findings, prioritizing improvements

### Key Metrics Tracked
- Success/failure rate
- Terminal stage (where failures occur)
- Duration per run
- Discovered/verified/recommended counts
- Confidence scores
- Clarification round trips
- Stage dropoff frequency

### Output
Timestamped directory with run artifacts, critique reports, aggregate statistics, and auto-generated PRD with workstreams and success metrics.

---

## 20. Deviations from the Original Brief

| Area | Brief Planned | Actually Built | Why Different |
|------|--------------|----------------|---------------|
| **Parser model** | Haiku (cheap extraction) | Sonnet (balanced reasoning) | Regional strategy and clarifying questions need stronger reasoning |
| **Discovery architecture** | Single agent with parallel tool calls | 5-team multi-strategy system | More robust, diverse results, different scoring lenses |
| **Intermediary handling** | Brief mentioned intermediary detection | Full resolution system with URL patterns + LLM classification + direct website extraction | Critical for quality — many search results are intermediaries |
| **Agents count** | 9 agents (A-I) | 13+ agents + 5 discovery sub-teams | Added chat agent, phone agent, negotiation agent, inbox monitor, form filler, contact enricher |
| **Outreach** | Part of main pipeline | Optional, can be auto or manual | More flexible, respects user preference |
| **Phone calls** | Not in brief | Full AI voice agent via Retell | Added channel for suppliers without email |
| **Form filling** | Not in brief | Browserbase-powered auto form fill | Added channel for suppliers with only contact forms |
| **Buyer context** | Not in brief | Full persistent personalization system | Cross-project learning is a key differentiator |
| **Checkpoints** | Brief mentioned human-in-the-loop | 5 typed checkpoints with auto-continue | More granular control without blocking |
| **Feedback agent** | Brief had post-order feedback | Replaced with retrospective system + persistent supplier memory | More sophisticated learning loop |
| **Evaluation suite** | Brief mentioned DeepEval | Custom agentic suite with scenario runner + critic + PRD writer | More tailored to procurement domain |
| **Celery/Redis** | Brief planned Celery for task queue | Background scheduler in FastAPI | Simpler deployment, fewer moving parts |
| **LiteLLM** | Brief planned LiteLLM for model routing | Direct Anthropic API calls with config-based model selection | Simpler, fewer dependencies |
| **Semantic caching** | Brief planned Redis + embedding cache | Not implemented in current build | Future optimization opportunity |
| **Import data** | Brief planned ImportGenius/ImportYeti | Not implemented in current build | Cost concern — these are paid APIs |
| **OpenCorporates** | Brief planned for business verification | Not implemented in current build | API integration not completed |
| **Landing page** | Brief planned Framer + Waitlister | Next.js integrated frontend | Single codebase approach |

---

## 21. Outreach Orchestration (Detailed)

The outreach system is significantly more complex than the basic Stage 6 overview suggests. It operates as its own mini-pipeline with multiple steps and fallback channels.

### The Outreach Approval Workflow

```
Recommendation complete
    │
    ▼
Draft emails for top 5 recommended suppliers (auto or manual trigger)
    │
    ▼
User reviews drafts (can edit, skip, reorder)
    │
    ▼
Quick-approval decision per supplier:
    ├─ APPROVE → Queue for sending
    ├─ EDIT → Modify email, then re-approve
    └─ SKIP → Remove from outreach batch
    │
    ▼
Emails sent via Resend API
    │
    ▼
Delivery tracking via webhooks (sent → delivered → opened → bounced)
    │
    ▼
Response monitoring (inbox scan for supplier replies)
    │
    ▼
Quote parsing (extract pricing, MOQ, lead time from response)
    │
    ▼
Negotiation cycle (Accept / Clarify / Counter / Reject)
```

### Fallback Channels

When a supplier has no email address, the system falls back to alternative contact methods in this order:

1. **Email** (primary) — Standard RFQ email via Resend
2. **Contact form filling** (fallback 1) — Uses Browserbase headless browser to navigate to supplier's website, locate the contact form, and auto-fill it with buyer info and RFQ details
3. **Phone call** (fallback 2) — Uses Retell AI voice agent to place an automated call with a structured procurement script
4. **Manual flag** — If all automated channels fail, the supplier is flagged for manual outreach by the user

### Quote Parsing Confidence Tiers

When supplier responses arrive, the response parser assigns confidence:

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 90-100 | All fields clearly stated | Auto-populate quote, mark ready |
| 70-89 | Most fields present, some inferred | Populate with flags, user verify |
| 50-69 | Partial info, gaps exist | Populate known fields, request clarification |
| Below 50 | Very incomplete | Flag for manual review |

### Negotiation Decision Tree

After quotes are parsed, the negotiation agent evaluates each:

```
EVALUATE QUOTE:
├─ Price within budget + all fields present + high verification?
│   └─ YES → ACCEPT (draft confirmation, request proforma invoice)
│
├─ Missing critical fields (no MOQ, vague shipping)?
│   └─ YES → CLARIFY (draft specific questions)
│
├─ Price 10-30% over budget OR MOQ too high?
│   └─ YES → COUNTER (draft counter-offer, never reveal competitor details)
│
└─ Price >50% over OR can't meet fundamentals?
    └─ YES → REJECT (respectful decline)
```

---

## 22. Communication Monitoring

### Purpose
Track all outbound and inbound communications per project, maintaining a durable record of every interaction with each supplier.

### What Gets Tracked

**Per outbound message:**
- Email ID (from Resend)
- Recipient supplier name and index
- Send timestamp
- Subject and body content
- Delivery status events timeline (queued → sent → delivered → opened → bounced)

**Per inbound message:**
- Sender email address matched to supplier
- Receipt timestamp
- Raw body content
- Parsed quote data (if applicable)
- Confidence score of parsing

### Status Event Timeline
Each message accumulates a timeline of events:
```
[2026-02-10 10:00] QUEUED — Email drafted and approved
[2026-02-10 10:01] SENT — Delivered to Resend API
[2026-02-10 10:02] DELIVERED — Resend confirms delivery
[2026-02-11 09:15] OPENED — Recipient opened email (tracking pixel)
[2026-02-12 14:30] RESPONSE_RECEIVED — Inbound email matched
[2026-02-12 14:31] PARSED — Quote extracted with confidence 87%
```

### Webhook Integration
- **Resend webhooks** — Delivery events (sent, delivered, opened, bounced, complained) are received via webhook and matched to the originating project + supplier via email_id reverse lookup
- **Retell webhooks** — Phone call events (started, ended, transcript_ready) are matched via call_id reverse lookup

---

## 23. Dashboard Intelligence

### Purpose
Aggregate project data into actionable dashboard views for the user.

### Attention Items (Priority Alerts)
The dashboard surfaces high-priority items that need user action:

| Alert Type | Trigger | Urgency |
|-----------|---------|---------|
| **Clarifying questions pending** | Parser generated questions, awaiting user answers | High |
| **Outreach approval needed** | Draft emails ready for review | High |
| **Send failures** | Emails bounced or failed delivery | High |
| **Quotes ready for review** | Supplier responses parsed, awaiting user evaluation | Medium |
| **Follow-ups due** | Non-responsive suppliers past follow-up threshold | Medium |

### Project Status Computation
Each project gets a dynamic status note based on its current state:
- "Analyzing your requirements..." (parsing)
- "Searching X sources for suppliers..." (discovering)
- "Found Y suppliers, verifying legitimacy..." (verifying)
- "Comparing Z verified suppliers..." (comparing)
- "Recommendation ready — N suppliers shortlisted" (complete)
- Includes contextual details like clarification count, outreach state, response count

### Activity Timeline
Merges two data sources into a unified chronological feed:
1. **Runtime events** — Progress events from the pipeline (stage changes, milestones)
2. **Database events** — Persisted events (project creation, outreach actions, responses received)

Each event gets a relative time label ("2 minutes ago", "yesterday") for the UI.

### Price Aggregation
Extracts the best available price from either:
- Comparison results (estimated pricing from comparison stage)
- Parsed quotes (actual pricing from supplier responses)
Displays as the "best price" on project cards.

### Visual Consistency
Projects get deterministic visual styling (color variant) based on a hash of the project ID, ensuring consistent appearance across sessions.

---

## 24. Authentication & Lead Capture

### Authentication Flow
- **Sign up** — Email + password registration via Supabase Auth
- **Login** — Email + password, returns JWT access token
- **Google OAuth** — Social login integration
- **Token refresh** — Automatic JWT refresh on expiry
- **User profile** — Name, email, business info, sourcing profile stored per user

### Lead Capture (Pre-Product)
A lightweight endpoint for collecting email addresses from the landing page before users create full accounts:
- **Input:** Email address, sourcing note (what they're looking for), traffic source
- **Deduplication:** If the email already exists, updates the record rather than creating a duplicate
- **Output:** Lead ID + dedup flag
- **Purpose:** Build a waitlist/mailing list of interested users for marketing

### Intake Flow (Landing → Project)
The hero landing page has a conversational input where users describe what they need. When submitted:
1. `POST /intake/start` creates a new project with the description
2. Persists a telemetry event (`hero_intake_started`) with source tracking
3. Returns a redirect URL to the workspace page with the new project ID
4. The workspace page picks up the project and begins the pipeline

---

## 25. Frontend Architecture Overview

### Page Structure
- **Landing page** (`/`) — Hero section with conversational intake input
- **Dashboard** (`/dashboard`) — Project cards, activity feed, attention items
- **Workspace** (`/product`) — Main project workspace with phase tabs

### Workspace Phase Tabs
The workspace presents 6 user-facing phases that map to backend pipeline stages:

| Tab | Maps To | Content |
|-----|---------|---------|
| Brief | Parsing stage | Requirements display, clarifying questions |
| Search | Discovery + Verification | Supplier cards, progress feed, agent narration |
| Compare | Comparison + Recommendation | Comparison table, recommendation verdict |
| Outreach | Outreach stage | Email drafts, approval flow, delivery tracking |
| Samples | Post-outreach | Sample requests, negotiation |
| Order | Post-negotiation | Final order preparation |

### Key UI Components

**LiveProgressFeed / AgentNarrationPanel** — Real-time display of what the AI is doing, showing stage progress, current activity, and narrative text as the pipeline runs.

**SupplierCard** — Card-based display of each supplier with: name, location, relevance/verification scores, certifications, estimated pricing, product page link, contact info.

**WeightSliders** — Interactive sliders for adjusting comparison weights (price, speed, risk, quality) at checkpoints.

**ProactiveAlerts** — Banner alerts for time-sensitive information (e.g., Chinese New Year lead time warnings).

**ErrorRecoveryCard** — Contextual error display with guidance on what went wrong and what to try next.

**Supplier Profile** (drill-down view) — Full supplier detail page with:
- Hero section (name, scores, quick stats)
- Verification check results
- Quote data and parsed responses
- Risk assessment and confidence scores
- Communication log (emails, calls, timeline)
- Company details (contact, website, certifications)
- Portfolio (product images, capabilities)

### State Management
A single `WorkspaceContext` (React context) manages all project state, phase routing, API polling, and checkpoint handling. It continuously polls the backend for status updates until the pipeline completes or fails.

### Animation & Design
- Warm color palette (cream background, teal primary, warm accents) — deliberately NOT typical B2B blue/grey
- Framer Motion animations with signature ease-out-expo curves
- Progressive disclosure: lead with verdict/recommendation, drill down optional

---

## 26. LLM Gateway Details

### Model Configuration
- **Sonnet** (claude-sonnet-4-5-20250929) — `settings.model_balanced` — Used for reasoning-heavy tasks: parsing, discovery scoring, comparison, recommendation, outreach drafting, chat
- **Haiku** (claude-haiku-4-5-20251001) — `settings.model_fast` — Used for extraction tasks: contact enrichment, verification data extraction, follow-up emails

### Cost Tracking
The gateway maintains a running session cost counter:
- Tracks input tokens, output tokens, and cache read/write tokens per call
- Calculates cost using model-specific pricing (Haiku: $1/$5 per MTok, Sonnet: $3/$15 per MTok)
- Logs cumulative session cost for monitoring

### Streaming Support
Full async streaming support for long-running LLM calls, allowing the frontend to show progressive output.

### JSON Truncation Repair
When LLM responses hit the max_tokens limit and produce truncated JSON, a `repair_truncated_json()` utility attempts to close open brackets and braces to produce valid JSON. This prevents pipeline failures from token limit issues.

### Prompt Caching
System prompts are cached by Anthropic's API (90% discount on repeated prompt prefixes). Since all runs of a given agent share the same system prompt, this significantly reduces cost after the first run.

---

*This document was generated from a complete analysis of the Procurement AI codebase as of February 2026. It covers every agent, every prompt, every data contract, and every decision algorithm in the system.*
