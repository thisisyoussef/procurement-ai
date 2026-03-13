# Procurement AI Agent Strategy V2 — Implementation Plan

> **Goal:** Transform Procurement AI from a linear search-and-rank pipeline into an adaptive, context-aware procurement partner that learns across projects and guides users through decisions.
>
> **Audience:** Engineering team implementing these changes.
>
> **Estimated scope:** 6 phases, ~8-12 weeks of focused development.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: Buyer Context & User Model](#2-phase-1-buyer-context--user-model)
3. [Phase 2: Multi-Strategy Discovery Teams](#3-phase-2-multi-strategy-discovery-teams)
4. [Phase 3: Pipeline Checkpoints & Steering](#4-phase-3-pipeline-checkpoints--steering)
5. [Phase 4: Agent Intelligence Upgrades](#5-phase-4-agent-intelligence-upgrades)
6. [Phase 5: Feedback Loops & Learning](#6-phase-5-feedback-loops--learning)
7. [Phase 6: Post-Pipeline Guidance & Proactive Intelligence](#7-phase-6-post-pipeline-guidance--proactive-intelligence)
8. [Cross-Cutting: Prompt & UX Rewrites](#8-cross-cutting-prompt--ux-rewrites)
9. [Migration & Backward Compatibility](#9-migration--backward-compatibility)
10. [Dependency Order & Parallelization](#10-dependency-order--parallelization)

---

## 1. Executive Summary

This plan covers four major strategic shifts:

**A. From anonymous pipeline to personalized partner.** Build a persistent `BuyerContext` and `UserSourcingProfile` that accumulate across projects. Every agent receives this context. The system gets smarter with every interaction.

**B. From single-source search to multi-strategy teams.** Replace the monolithic discovery agent with 2-5 specialized search teams that approach the problem from different angles, then aggregate intelligently.

**C. From fire-and-forget pipeline to steered workflow.** Add lightweight checkpoints between every pipeline stage where the user can review, adjust, and redirect — or skip to let the system proceed with defaults.

**D. From data presentation to decision guidance.** Rewrite agent outputs to produce narrative judgment rather than raw scores. The system should tell the user what it would do and why, not just show numbers.

---

## 2. Phase 1: Buyer Context & User Model

**Why first:** Every other improvement depends on having rich user context available. This is the foundation.

### 2.1 New Schema: `BuyerContext`

Create `app/schemas/buyer_context.py`:

```python
class LogisticsProfile(BaseModel):
    """Shipping and import logistics for the buyer."""
    shipping_address: str | None = None           # Full address
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_country: str | None = None
    shipping_zip: str | None = None
    port_of_entry: str | None = None              # e.g., "Port of Los Angeles"
    has_freight_forwarder: bool | None = None
    has_customs_broker: bool | None = None
    fulfillment_type: str | None = None           # "own_warehouse", "3pl", "dropship"
    fulfillment_provider: str | None = None       # e.g., "ShipBob Dallas"
    import_experience: str | None = None          # "first_time", "occasional", "regular"
    preferred_incoterms: str | None = None        # "FOB", "DDP", "CIF", etc.

class FinancialProfile(BaseModel):
    """Budget and payment capabilities."""
    budget_hard_cap: float | None = None          # Absolute max spend
    budget_currency: str = "USD"
    payment_methods: list[str] = []               # ["wire", "credit_card", "lc", "trade_assurance"]
    can_pay_deposit: bool | None = None           # Can afford 30-50% upfront?
    max_deposit_amount: float | None = None
    payment_terms_preference: str | None = None   # "net_30", "50_50", "lc"

class TimelineContext(BaseModel):
    """Deadline and urgency context."""
    hard_deadline: date | None = None
    deadline_reason: str | None = None            # "product_launch", "seasonal", "restock", "flexible"
    buffer_weeks: int | None = None               # Acceptable buffer beyond deadline
    urgency_level: str | None = None              # "critical", "important", "flexible"

class QualityContext(BaseModel):
    """Quality standards and requirements."""
    use_case: str | None = None                   # "retail", "events_merch", "corporate_gifts", "personal"
    quality_tier: str | None = None               # "premium", "standard", "budget"
    needs_samples_first: bool | None = None
    inspection_requirements: str | None = None    # "none", "self_inspect", "third_party_qc"
    defect_tolerance: str | None = None           # "zero_tolerance", "standard_aql", "relaxed"
    industry_standards: list[str] = []            # ["BSCI", "OEKO-TEX", "organic_certified"]

class CommunicationPreferences(BaseModel):
    """How the buyer prefers to interact with suppliers."""
    preferred_language: str = "en"
    needs_english_speaking_contact: bool | None = None
    preferred_channel: str | None = None          # "email", "whatsapp", "phone", "platform_chat"
    timezone: str | None = None
    response_expectation: str | None = None       # "same_day", "within_3_days", "flexible"

class BuyerContext(BaseModel):
    """
    Complete buyer context threaded through every agent.
    Built up progressively through checkpoints — NOT a form filled upfront.
    """
    logistics: LogisticsProfile = Field(default_factory=LogisticsProfile)
    financial: FinancialProfile = Field(default_factory=FinancialProfile)
    timeline: TimelineContext = Field(default_factory=TimelineContext)
    quality: QualityContext = Field(default_factory=QualityContext)
    communication: CommunicationPreferences = Field(default_factory=CommunicationPreferences)

    # Contextual metadata
    is_first_import: bool | None = None
    sourced_this_category_before: bool | None = None
    previous_supplier_names: list[str] = []       # Known good/bad suppliers
    category_experience_level: str | None = None  # "novice", "experienced", "expert"

    # Confidence tracking — which fields were explicitly provided vs inferred
    explicitly_provided_fields: list[str] = []
    inferred_fields: list[str] = []
```

### 2.2 New Schema: `UserSourcingProfile`

This is the persistent, cross-project profile that learns over time. Create `app/schemas/user_profile.py`:

```python
class SupplierRelationship(BaseModel):
    """A known supplier relationship from past projects."""
    supplier_id: str
    supplier_name: str
    sentiment: str              # "positive", "neutral", "negative"
    notes: str | None = None
    last_interaction_date: date | None = None
    projects_together: int = 0
    quoted_prices: list[str] = []   # Historical prices for reference
    communication_rating: str | None = None  # "excellent", "good", "poor", "unresponsive"

class CategoryExperience(BaseModel):
    """Buyer's experience in a product category."""
    category: str                   # "apparel", "packaging", "electronics", etc.
    projects_completed: int = 0
    preferred_regions: list[str] = []
    typical_budget_range: str | None = None
    typical_quantity_range: str | None = None
    known_good_suppliers: list[str] = []
    known_bad_suppliers: list[str] = []
    lessons_learned: list[str] = [] # e.g., "Turkish suppliers are slow to respond"

class UserSourcingProfile(BaseModel):
    """
    Persistent profile that accumulates across all projects.
    Stored in the users table as a JSONB column.
    """
    # Defaults inferred from history
    default_shipping_address: str | None = None
    default_port_of_entry: str | None = None
    default_payment_methods: list[str] = []
    default_incoterms: str | None = None
    default_quality_tier: str | None = None
    import_experience_level: str = "unknown"      # Upgraded automatically

    # Learned preferences
    preferred_sourcing_regions: list[str] = []
    avoided_regions: list[str] = []
    preferred_communication_language: str = "en"
    needs_english_contacts: bool = True
    price_sensitivity: str = "moderate"           # "high", "moderate", "low"
    risk_tolerance: str = "moderate"              # "conservative", "moderate", "aggressive"

    # Relationship history
    supplier_relationships: list[SupplierRelationship] = []
    category_experience: list[CategoryExperience] = []

    # Behavioral signals (auto-updated)
    total_projects: int = 0
    total_suppliers_contacted: int = 0
    average_project_budget: float | None = None
    most_common_categories: list[str] = []
    last_project_date: date | None = None
```

### 2.3 Database Changes

**Migration `0007_buyer_context_user_profile.py`:**

```python
# Add to users table
op.add_column('users', sa.Column('sourcing_profile', JSONB, nullable=True))
op.add_column('users', sa.Column('default_buyer_context', JSONB, nullable=True))

# Add to runtime_projects table
op.add_column('runtime_projects', sa.Column('buyer_context', JSONB, nullable=True))
```

### 2.4 Threading Buyer Context Through the Pipeline

**Changes to `app/agents/orchestrator.py`:**

Add `buyer_context` to `GraphState`:

```python
class GraphState(TypedDict, total=False):
    # ... existing fields ...
    buyer_context: dict | None          # BuyerContext serialized
    user_sourcing_profile: dict | None  # UserSourcingProfile serialized
```

Every agent node receives `buyer_context` and `user_sourcing_profile` from the state. Update each node to pass these to the agent functions.

**Changes to each agent function signature:**

```python
# Before:
async def parse_requirements(raw_description: str) -> ParsedRequirements:

# After:
async def parse_requirements(
    raw_description: str,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> ParsedRequirements:
```

Apply this pattern to: `discover_suppliers`, `verify_suppliers`, `compare_suppliers`, `generate_recommendation`, `draft_outreach_emails`.

### 2.5 Progressive Context Gathering

The buyer context is NOT gathered via a form. It's built up through the checkpoint system (Phase 3). However, we pre-populate what we can from:

1. **User's business profile** (already exists): shipping address, company name, phone.
2. **User sourcing profile** (new): defaults from past projects.
3. **Parsed requirements**: delivery location, deadline, budget.

Create `app/services/buyer_context_builder.py`:

```python
async def build_initial_buyer_context(
    user_id: str,
    parsed_requirements: ParsedRequirements,
) -> BuyerContext:
    """
    Build the initial BuyerContext by combining:
    1. User's stored sourcing profile defaults
    2. Business profile data
    3. Whatever was parsed from the current request
    """
    # Load user profile and business profile from DB
    # Merge into BuyerContext
    # Mark which fields are inferred vs explicit
    ...

async def merge_checkpoint_answers(
    context: BuyerContext,
    checkpoint_answers: dict,
) -> BuyerContext:
    """Merge user answers from a checkpoint into the buyer context."""
    ...

async def update_user_profile_from_project(
    user_id: str,
    project_state: dict,
    buyer_context: BuyerContext,
):
    """After project completion, update the persistent user profile."""
    ...
```

### 2.6 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| CREATE | `app/schemas/buyer_context.py` | `BuyerContext`, `LogisticsProfile`, etc. |
| CREATE | `app/schemas/user_profile.py` | `UserSourcingProfile`, `SupplierRelationship`, `CategoryExperience` |
| CREATE | `app/services/buyer_context_builder.py` | Context assembly and progressive enrichment |
| CREATE | `alembic/versions/0007_buyer_context.py` | Migration for new columns |
| MODIFY | `app/schemas/agent_state.py` | Add `buyer_context` to `PipelineState` |
| MODIFY | `app/agents/orchestrator.py` | Add `buyer_context` and `user_sourcing_profile` to `GraphState` |
| MODIFY | `app/models/user.py` | Add `sourcing_profile` and `default_buyer_context` JSONB columns |
| MODIFY | `app/agents/requirements_parser.py` | Accept and use `BuyerContext` |
| MODIFY | `app/agents/supplier_discovery.py` | Accept and use `BuyerContext` |
| MODIFY | `app/agents/supplier_verifier.py` | Accept and use `BuyerContext` |
| MODIFY | `app/agents/comparison_agent.py` | Accept and use `BuyerContext` |
| MODIFY | `app/agents/recommendation_agent.py` | Accept and use `BuyerContext` |
| MODIFY | `app/agents/outreach_agent.py` | Accept and use `BuyerContext` |
| MODIFY | All agent prompts in `app/agents/prompts/` | Add buyer context section to each prompt |

---

## 3. Phase 2: Multi-Strategy Discovery Teams

**Why:** The current discovery agent treats all sources interchangeably. Specialized teams with different mandates produce richer, more diverse results.

### 3.1 Architecture

Replace the monolithic `discover_suppliers()` function with a fan-out/aggregate pattern:

```
ParsedRequirements + BuyerContext
         │
    ┌────┼─────────────────────────────┐
    │    │    STRATEGY SELECTION        │
    │    │    (picks 2-5 teams based    │
    │    │     on requirements)         │
    └────┼─────────────────────────────┘
         │
    ┌────┴────┬──────────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼          ▼
 Team 1    Team 2     Team 3    Team 4     Team 5
 Direct    Market     Regional  Reputation Proximity
 Mfg Hunt Intelligence Deep Dive & Trust   & Logistics
    │         │          │          │          │
    └────┬────┴──────────┴──────────┴──────────┘
         │
    ┌────▼─────────────────────────────┐
    │         AGGREGATION LAYER         │
    │  Cross-reference, enrich, score   │
    │  Produce multi-dimensional ranks  │
    │  Detect coverage gaps             │
    │  Synthesize market intelligence   │
    └──────────────────────────────────┘
         │
         ▼
    DiscoveryResults (enriched)
```

### 3.2 Strategy Selector

Create `app/agents/discovery/strategy_selector.py`:

```python
class DiscoveryTeam(str, Enum):
    DIRECT_MANUFACTURER = "direct_manufacturer"
    MARKET_INTELLIGENCE = "market_intelligence"
    REGIONAL_DEEP_DIVE = "regional_deep_dive"
    REPUTATION_TRUST = "reputation_trust"
    PROXIMITY_LOGISTICS = "proximity_logistics"

class TeamConfig(BaseModel):
    team: DiscoveryTeam
    priority: int                       # 1 = highest
    search_queries: list[str]           # Team-specific queries
    sources: list[str]                  # Which tools to use
    max_results: int = 20
    scoring_lens: str                   # What this team optimizes for

async def select_strategies(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    user_profile: UserSourcingProfile | None = None,
) -> list[TeamConfig]:
    """
    Select 2-5 discovery teams based on requirements and buyer context.

    Rules:
    - Team 1 (Direct Manufacturer) ALWAYS runs.
    - Team 2 (Market Intelligence) ALWAYS runs.
    - Team 3 (Regional Deep Dive) runs when regional_searches exist
      in ParsedRequirements AND buyer has import experience.
    - Team 4 (Reputation & Trust) runs when:
      - risk_tolerance is "low" or "conservative"
      - OR it's a technical/regulated product (auto, medical, food)
      - OR buyer is first-time importer
    - Team 5 (Proximity & Logistics) runs when:
      - priority_tradeoff is "fastest_delivery"
      - OR buyer has a hard deadline within 6 weeks
      - OR buyer explicitly prefers domestic/nearshore
      - OR shipping cost is a top concern (heavy/bulky products)
    """
```

### 3.3 Team Implementations

Refactor `app/agents/supplier_discovery.py` into a package:

```
app/agents/discovery/
├── __init__.py
├── strategy_selector.py
├── team_direct_manufacturer.py
├── team_market_intelligence.py
├── team_regional_deep_dive.py
├── team_reputation_trust.py
├── team_proximity_logistics.py
├── aggregator.py
└── prompts/
    ├── direct_manufacturer.md
    ├── market_intelligence.md
    ├── regional_deep_dive.md
    ├── reputation_trust.md
    ├── proximity_logistics.md
    └── aggregator.md
```

**Team 1: Direct Manufacturer Hunt** (`team_direct_manufacturer.py`)

```python
async def run_direct_manufacturer_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    """
    Mandate: Find the actual factories that make this product.

    Sources:
    - Google Places with type filter "manufacturer"
    - ThomasNet, Kompass, MFG.com searches
    - Firecrawl with queries like "{product} factory {region}"

    Scoring lens: Manufacturing confidence
    - Factory address present? +20
    - Production photos/equipment mentioned? +15
    - OEM/ODM language on site? +15
    - Capacity numbers mentioned? +10
    - NOT a trading company? +20
    - Intermediary resolver passes? +20

    Aggressively runs intermediary_resolver on every result.
    Discards anything that doesn't pass.
    """
```

**Team 2: Market Intelligence Sweep** (`team_market_intelligence.py`)

```python
async def run_market_intelligence_sweep(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    """
    Mandate: Map the competitive landscape for this product.

    Sources:
    - Alibaba, GlobalSources, IndiaMART, 1688
    - Trade show exhibitor directories
    - Industry association member lists

    Does NOT filter intermediaries — intentionally includes them
    to capture pricing ranges, MOQ norms, and market positioning.

    Produces MarketIntelligence alongside suppliers:
    - price_range_low / price_range_high (across all results)
    - typical_moq_range
    - dominant_regions (which countries have most suppliers)
    - common_certifications (what certifications are standard)
    - market_maturity (many suppliers = mature market = price competition)
    """
```

**Team 3: Regional Deep Dive** (`team_regional_deep_dive.py`)

```python
async def run_regional_deep_dive(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    regions: list[RegionalSearchConfig],
) -> TeamResult:
    """
    Mandate: Go deep in the top 2-3 sourcing regions using local-language queries.

    Sources per region:
    - Local search engines (Baidu for China, Yandex for Russia)
    - Local business directories
    - Regional marketplace variants (1688 for China, n11.com for Turkey)
    - Firecrawl with localized queries from regional_searches

    Scoring lens: Regional depth
    - Found via local-language source? +25
    - No English website (hidden gem)? +15
    - Located in known manufacturing cluster? +20
    - Has local business registration? +15
    - Export experience mentioned? +10
    - Competitive pricing vs. Team 2 market intelligence? +15
    """
```

**Team 4: Reputation & Trust Signal** (`team_reputation_trust.py`)

```python
async def run_reputation_trust_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
    user_profile: UserSourcingProfile | None = None,
) -> TeamResult:
    """
    Mandate: Find suppliers with the strongest trust signals.

    Sources:
    - Certification body directories (ISO, BSCI, IATF registrars)
    - Google Places filtered by 4.0+ rating, 50+ reviews
    - Firecrawl: "{product} supplier certified ISO reviews"
    - User's own supplier relationship history (from UserSourcingProfile)
    - Supplier memory DB sorted by verification_score and interaction_count

    Scoring lens: Trust level
    - ISO/relevant certification verified? +25
    - Google rating ≥ 4.0 with 100+ reviews? +20
    - Previously used by this user (positive)? +20
    - Previously used by other Procurement AI users (positive)? +10
    - Featured in industry publications? +10
    - Years in operation > 5? +10
    - Export track record? +5
    """
```

**Team 5: Proximity & Logistics** (`team_proximity_logistics.py`)

```python
async def run_proximity_logistics_search(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> TeamResult:
    """
    Mandate: Find suppliers optimized for logistics efficiency.

    Activated when: shipping cost or lead time is high priority,
    or buyer has a hard deadline.

    Sources:
    - Google Places near buyer's delivery location (expanding radius)
    - Domestic manufacturer directories
    - Near-shore manufacturers (Mexico for US, Eastern Europe for EU)
    - Port-proximate manufacturers (near major shipping lanes)

    Scoring lens: Logistics fit
    - Same country as delivery? +30
    - Near-shore (e.g., Mexico for US buyer)? +20
    - Near major port with direct shipping lane? +15
    - Estimated lead time within deadline? +20
    - Estimated shipping cost below market average? +15

    Produces logistics-specific data:
    - estimated_transit_days (not just lead time)
    - shipping_lane (e.g., "Shenzhen → LA, ~14 days ocean")
    - port_proximity_km
    """
```

### 3.4 Aggregation Layer

Create `app/agents/discovery/aggregator.py`:

```python
class TeamResult(BaseModel):
    """Output from a single discovery team."""
    team: DiscoveryTeam
    suppliers: list[DiscoveredSupplier]
    market_intelligence: MarketIntelligence | None = None  # Only from Team 2
    coverage_notes: str = ""
    confidence: float = 0.0  # How confident this team is in its results

class MarketIntelligence(BaseModel):
    """Market context from Team 2 for use by comparison/recommendation."""
    price_range_low: str | None = None
    price_range_high: str | None = None
    typical_moq_range: str | None = None
    dominant_regions: list[str] = []
    common_certifications: list[str] = []
    market_maturity: str = "unknown"  # "emerging", "growing", "mature", "saturated"

class AggregatedDiscoveryResults(BaseModel):
    """Enhanced DiscoveryResults with multi-team data."""
    suppliers: list[DiscoveredSupplier]      # Final merged, deduplicated list
    market_intelligence: MarketIntelligence | None = None
    team_reports: list[TeamResult]            # Raw team outputs for transparency
    cross_reference_boost: dict[str, float]   # supplier_name → boost from multi-team appearance
    coverage_gaps: list[str]                  # e.g., "No domestic suppliers found"
    # Existing DiscoveryResults fields
    sources_searched: list[str] = []
    total_raw_results: int = 0
    deduplicated_count: int = 0

async def aggregate_team_results(
    team_results: list[TeamResult],
    requirements: ParsedRequirements,
    buyer_context: BuyerContext,
) -> AggregatedDiscoveryResults:
    """
    Merge results from all teams into a single ranked list.

    Steps:
    1. DEDUPLICATE: Match suppliers across teams by domain, email, name.
       Merge records — keep the richest data from each team.

    2. CROSS-REFERENCE BOOST: Suppliers found by multiple teams get a
       confidence boost. A factory found by Team 1 (direct mfg) AND
       Team 4 (reputation) is much more trustworthy than one found
       by only one team.
       - 2 teams: +15% boost
       - 3 teams: +25% boost
       - 4+ teams: +35% boost

    3. MULTI-DIMENSIONAL SCORING: Instead of a single relevance_score,
       produce a score vector per supplier:
       - manufacturing_confidence (from Team 1)
       - market_position (from Team 2)
       - regional_depth (from Team 3)
       - trust_level (from Team 4)
       - logistics_fit (from Team 5)
       The final relevance_score is a weighted combination based on
       buyer_context.priority_tradeoff.

    4. COVERAGE GAP DETECTION: Check if all decision lanes have
       candidates. Flag gaps like:
       - "No certified suppliers found for this product category"
       - "No domestic/nearshore options available"
       - "All suppliers have long lead times vs. your deadline"

    5. MARKET INTELLIGENCE SYNTHESIS: Package Team 2's pricing ranges,
       MOQ norms, and regional distribution as a MarketIntelligence
       object for downstream agents.

    6. HAIKU PRE-FILTER: Before Sonnet scoring, run a Haiku binary
       relevance filter on each supplier: "Does this supplier
       plausibly make {product_type}? Yes/No." Discard No's.
       This cuts Sonnet scoring tokens by 40-60%.

    7. SONNET FINAL RANKING: Pass surviving candidates to Sonnet
       for nuanced scoring with the full buyer context and
       market intelligence.
    """
```

### 3.5 Updated Discovery Entry Point

The new `discover_suppliers()` becomes a coordinator:

```python
async def discover_suppliers(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext | None = None,
    user_profile: UserSourcingProfile | None = None,
) -> AggregatedDiscoveryResults:
    # 1. Select strategies
    teams = await select_strategies(requirements, buyer_context, user_profile)

    # 2. Run teams in parallel
    team_results = await asyncio.gather(*[
        run_team(team_config, requirements, buyer_context, user_profile)
        for team_config in teams
    ])

    # 3. Aggregate
    return await aggregate_team_results(team_results, requirements, buyer_context)
```

### 3.6 New Fields on `DiscoveredSupplier`

Add to `app/schemas/agent_state.py`:

```python
class DiscoveredSupplier(BaseModel):
    # ... existing fields ...

    # NEW: Multi-dimensional scores from team aggregation
    discovery_teams: list[str] = []          # Which teams found this supplier
    manufacturing_confidence: float = 0.0    # 0-100, from Team 1
    market_position: float = 0.0             # 0-100, from Team 2
    regional_depth_score: float = 0.0        # 0-100, from Team 3
    trust_level: float = 0.0                 # 0-100, from Team 4
    logistics_fit: float = 0.0               # 0-100, from Team 5
    cross_reference_count: int = 0           # How many teams found this
```

### 3.7 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| CREATE | `app/agents/discovery/__init__.py` | Package init |
| CREATE | `app/agents/discovery/strategy_selector.py` | Team selection logic |
| CREATE | `app/agents/discovery/team_direct_manufacturer.py` | Team 1 |
| CREATE | `app/agents/discovery/team_market_intelligence.py` | Team 2 |
| CREATE | `app/agents/discovery/team_regional_deep_dive.py` | Team 3 |
| CREATE | `app/agents/discovery/team_reputation_trust.py` | Team 4 |
| CREATE | `app/agents/discovery/team_proximity_logistics.py` | Team 5 |
| CREATE | `app/agents/discovery/aggregator.py` | Cross-team aggregation |
| CREATE | `app/agents/discovery/prompts/` | Per-team prompt templates (5 files) |
| CREATE | `app/agents/discovery/prompts/aggregator.md` | Aggregation scoring prompt |
| MODIFY | `app/schemas/agent_state.py` | Add multi-dim scores to `DiscoveredSupplier`, add `MarketIntelligence` |
| MODIFY | `app/agents/orchestrator.py` | Update `discover_node` to use new entry point |
| RETIRE | `app/agents/supplier_discovery.py` | Replace with `app/agents/discovery/` package (keep as fallback initially) |

---

## 4. Phase 3: Pipeline Checkpoints & Steering

**Why:** Users currently have no agency between "start" and "results." Checkpoints let them steer without blocking the pipeline.

### 4.1 Checkpoint Architecture

A checkpoint is NOT a hard stop. It's a "draft-and-confirm" pattern:

```
Agent completes → Emit CHECKPOINT event → Start countdown timer (30s default)
                                              │
                                   ┌──────────┴──────────┐
                                   │                      │
                              User engages           Timer expires
                              (via API/frontend)     │
                                   │                 ▼
                              Pipeline PAUSES    Pipeline CONTINUES
                              at "steering"      with defaults
                              status
                                   │
                              User provides input
                              (adjust, redirect, approve)
                                   │
                              Pipeline RESUMES
                              with user input
```

### 4.2 New Schema: `CheckpointEvent`

Add to `app/schemas/agent_state.py`:

```python
class CheckpointType(str, Enum):
    CONFIRM_REQUIREMENTS = "confirm_requirements"    # After parse
    REVIEW_SUPPLIERS = "review_suppliers"             # After discovery
    SET_CONFIDENCE_GATE = "set_confidence_gate"       # After verification
    ADJUST_WEIGHTS = "adjust_weights"                 # After comparison
    OUTREACH_PREFERENCES = "outreach_preferences"     # Before outreach

class ContextQuestion(BaseModel):
    """A contextual question asked at a specific checkpoint."""
    field: str                  # Which BuyerContext field this populates
    question: str               # Human-readable question
    context: str                # Why this is being asked NOW
    options: list[str] = []     # Suggested answers (if applicable)
    default: str | None = None  # Default if user doesn't answer

class CheckpointEvent(BaseModel):
    """Emitted when a pipeline stage completes and offers steering."""
    checkpoint_type: CheckpointType
    summary: str                            # What just happened
    next_stage_preview: str                 # What's about to happen
    context_questions: list[ContextQuestion] # Questions that would improve next stage
    adjustable_parameters: dict[str, Any]   # What the user can change
    auto_continue_seconds: int = 30         # Countdown before auto-continuing
    requires_explicit_approval: bool = False # If True, don't auto-continue
    timestamp: float = Field(default_factory=time.time)

class CheckpointResponse(BaseModel):
    """User's response to a checkpoint."""
    checkpoint_type: CheckpointType
    answers: dict[str, Any] = {}            # Answers to context questions
    parameter_overrides: dict[str, Any] = {} # Adjusted parameters
    action: str = "continue"                # "continue", "redirect", "pause", "restart_stage"
    redirect_instructions: str | None = None # Free text for "redirect"
```

### 4.3 Add `PipelineStage.STEERING` State

In `app/schemas/agent_state.py`:

```python
class PipelineStage(str, Enum):
    # ... existing ...
    STEERING = "steering"       # NEW: at a checkpoint, awaiting optional user input
```

### 4.4 Checkpoint Definitions

Each checkpoint gathers specific context and offers specific steering:

**Checkpoint 1: After Parsing → Before Discovery**

```python
# Summary: "Here's what I understood from your request."
# Shows: parsed product type, quantity, material, delivery location, regions to search
# Context questions:
#   - "Do you have a customs broker?" → buyer_context.logistics.has_customs_broker
#   - "Have you imported before?" → buyer_context.is_first_import
#   - "Should I search in these regions: [China, Turkey, Portugal]?" → adjustable
# Adjustable: product_type, regions, search_queries, certifications
# Auto-continue: 30s (parsing output is usually fine)
```

**Checkpoint 2: After Discovery → Before Verification**

```python
# Summary: "Found 23 suppliers across 4 regions. Here's the breakdown."
# Shows: supplier list grouped by team/region, counts per source
# Context questions:
#   - "What quality tier are you targeting?" → buyer_context.quality.quality_tier
#   - "Do you need samples before committing?" → buyer_context.quality.needs_samples_first
# Adjustable:
#   - Pin/remove specific suppliers
#   - Request "search again with different terms"
#   - Adjust minimum supplier count
# Auto-continue: 45s (users often want to scan the list)
```

**Checkpoint 3: After Verification → Before Comparison**

```python
# Summary: "Verified 18 suppliers: 7 low risk, 8 medium, 3 high risk."
# Shows: risk breakdown, high-risk supplier names
# Context questions:
#   - "What's your budget cap for the total order?" → buyer_context.financial.budget_hard_cap
#   - "Which payment methods can you use?" → buyer_context.financial.payment_methods
# Adjustable:
#   - Confidence gate threshold (include/exclude high-risk suppliers)
#   - Manual override: "include this supplier despite high risk"
# Auto-continue: 30s
```

**Checkpoint 4: After Comparison → Before Recommendation**

```python
# Summary: "Compared 15 suppliers on price, quality, shipping, and lead time."
# Shows: comparison highlights, price range, best value/quality/speed
# Context questions:
#   - "Your deadline is June 15 — should I weight lead time higher?" → timeline context
# Adjustable:
#   - Scoring weights (cost, quality, speed, risk)
#   - decision_preferences already exists — surface it here
# Auto-continue: 30s
```

**Checkpoint 5: After Recommendation → Before Outreach**

```python
# Summary: "Top 5 recommendations across 3 decision lanes."
# Shows: recommended suppliers with reasoning
# Context questions:
#   - "Should I request samples in the first email?" → outreach preference
#   - "Want to mention your deadline?" → outreach content
#   - "Preferred payment terms to mention?" → buyer_context.financial
# Adjustable:
#   - Which suppliers to contact
#   - Email tone / specific talking points
# requires_explicit_approval: True (outreach is a real action)
```

### 4.5 Orchestrator Changes

Modify `app/agents/orchestrator.py` to insert checkpoint nodes between each agent:

```python
async def checkpoint_node(state: GraphState, checkpoint_type: CheckpointType) -> GraphState:
    """
    Generic checkpoint node. Emits a checkpoint event and checks if
    the user has provided steering input.
    """
    # Build checkpoint event based on checkpoint_type and current state
    checkpoint = build_checkpoint_event(checkpoint_type, state)

    # Emit checkpoint event (stored in progress_events for frontend to see)
    emit_progress(stage="checkpoint", substep=checkpoint_type.value, ...)

    # Check if user has pre-submitted answers for this checkpoint
    # (via the API before the pipeline reached this point)
    user_steering = state.get("checkpoint_responses", {}).get(checkpoint_type.value)

    if user_steering:
        # Apply steering
        state = apply_checkpoint_steering(state, user_steering, checkpoint_type)
    else:
        # Set status to "steering" — frontend will show checkpoint UI
        # Pipeline pauses here until user responds or timeout
        state["current_stage"] = PipelineStage.STEERING.value
        state["active_checkpoint"] = checkpoint.model_dump(mode="json")

    return state
```

The graph becomes:

```
parse → checkpoint_1 → discover → checkpoint_2 → verify → checkpoint_3 →
compare → checkpoint_4 → recommend → checkpoint_5 → outreach
```

### 4.6 New API Endpoint

Add to `app/api/v1/projects.py`:

```python
@router.post("/projects/{project_id}/checkpoint")
async def respond_to_checkpoint(
    project_id: str,
    response: CheckpointResponse,
):
    """Submit user's response to an active checkpoint."""
    # Validate checkpoint_type matches the active checkpoint
    # Merge answers into buyer_context
    # Apply parameter overrides
    # Resume pipeline
```

### 4.7 Frontend Changes

New component: `CheckpointBanner` — a non-blocking UI element that appears at each checkpoint:

- Shows summary of what just happened
- Displays context questions as inline cards (not a modal)
- Shows adjustable parameters with sliders/toggles
- Countdown timer: "Continuing automatically in 25s..."
- "Continue" button to proceed immediately
- "Let me adjust" button to pause the countdown

### 4.8 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| MODIFY | `app/schemas/agent_state.py` | Add `CheckpointEvent`, `CheckpointResponse`, `PipelineStage.STEERING` |
| MODIFY | `app/agents/orchestrator.py` | Add checkpoint nodes between agent nodes |
| CREATE | `app/agents/checkpoints.py` | Checkpoint builder functions per checkpoint type |
| MODIFY | `app/api/v1/projects.py` | Add `/checkpoint` endpoint |
| CREATE | `frontend/src/components/workspace/CheckpointBanner.tsx` | Checkpoint UI |
| MODIFY | `frontend/src/contexts/WorkspaceContext.tsx` | Handle `steering` status |
| MODIFY | `frontend/src/hooks/usePipelinePolling.ts` | Don't stop polling on `steering` |
| MODIFY | `frontend/src/types/pipeline.ts` | Add checkpoint types |

---

## 5. Phase 4: Agent Intelligence Upgrades

These are self-contained improvements to individual agents that make each one smarter.

### 5.1 Switch to Tool-Use for Structured Output

**Problem:** Every agent parses free-form JSON from LLM responses, with truncation recovery and regex fallbacks.

**Fix:** Use Anthropic's tool-use API to enforce output schemas.

**Changes to `app/core/llm_gateway.py`:**

```python
async def call_llm_with_tools(
    prompt: str,
    tools: list[dict],              # Tool schemas defining expected output
    system_prompt: str = "",
    model: str = "sonnet",
    max_tokens: int = 8192,
    temperature: float = 0.2,
) -> dict:
    """
    Call Claude with tool-use. Returns the structured tool_use response.
    Eliminates JSON parsing errors entirely.
    """
    response = await client.messages.create(
        model=resolve_model(model),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice={"type": "any"},  # Force tool use
    )
    # Extract tool_use block
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("No tool_use block in response")
```

**Apply to each agent:** Define the output schema as a tool and call `call_llm_with_tools` instead of `call_llm` + JSON parsing. This eliminates all JSON recovery code in: `requirements_parser.py`, `supplier_discovery.py` (scoring call), `comparison_agent.py`, `recommendation_agent.py`, `outreach_agent.py`, `negotiation_agent.py`, `response_parser.py`.

### 5.2 Two-Stage Scoring in Discovery

**Problem:** All raw results go to a single expensive Sonnet call for scoring.

**Fix:** Add a Haiku pre-filter before Sonnet ranking.

In the aggregator:

```python
async def haiku_relevance_filter(
    suppliers: list[DiscoveredSupplier],
    requirements: ParsedRequirements,
) -> list[DiscoveredSupplier]:
    """
    Fast binary filter: Does this supplier plausibly make {product_type}?
    Uses Haiku for cost efficiency. Parallelized in batches of 10.
    """
    # Batch suppliers into groups of 10
    # For each batch, ask Haiku: "For each supplier, respond YES or NO:
    #   does this supplier make {product_type}?"
    # Return only YES suppliers
```

### 5.3 Confidence Gate Between Verification and Comparison

**Problem:** High-risk suppliers with composite scores of 15 still get full comparison analysis.

**Fix:** Add a configurable threshold (adjustable at Checkpoint 3):

In `app/agents/orchestrator.py`, in `compare_node`:

```python
# Before passing to compare_suppliers, filter by confidence gate
gate = state.get("confidence_gate_threshold", 30)  # Default 30, adjustable
verified_suppliers = [
    s for s, v in zip(suppliers, verifications)
    if v.composite_score >= gate
]
# Store filtered-out suppliers in state for transparency
state["gated_suppliers"] = [
    {"name": s.name, "score": v.composite_score, "reason": "below_confidence_gate"}
    for s, v in zip(suppliers, verifications)
    if v.composite_score < gate
]
```

### 5.4 Adaptive Contact Enrichment

**Problem:** The 5-tier waterfall always runs all tiers sequentially regardless of what's already known.

**Fix:** Make enrichment adaptive:

```python
async def enrich_contact_adaptive(
    supplier: DiscoveredSupplier,
    priority: str = "normal",  # "high" for top recommendations, "low" for bottom
) -> ContactEnrichmentResult:
    """
    Adaptive enrichment based on what we already know and supplier priority.

    Skip waterfall entirely if:
    - Google Places already provided email AND phone

    Low priority (bottom 50% of suppliers):
    - Only Tier 1 (website scrape) + Tier 5 (pattern generation)

    Normal priority:
    - Tiers 1, 3, 5 (scrape, Google search, patterns)

    High priority (top 5 recommendations):
    - Full waterfall: Tiers 1-5
    """
```

### 5.5 Auto Re-Discovery on Low Recommendation Quality

**Problem:** If recommendations have low confidence or missing lane coverage, the user is just told in `caveats`.

**Fix:** Detect and auto-expand:

In `recommend_node`:

```python
result = await generate_recommendation(...)

# Check coverage quality
lanes_covered = set(r.lane for r in result.recommendations if r.lane)
min_confidence = min((r.confidence for r in result.recommendations), default=0)
avg_confidence = ...

if (
    len(lanes_covered) < 2
    or avg_confidence < 50
    or len(result.recommendations) < 3
):
    # Trigger re-discovery with expanded parameters
    logger.info("Low recommendation quality — triggering expanded search")
    expanded_requirements = expand_search_parameters(requirements)
    additional_results = await discover_suppliers(expanded_requirements, buyer_context)
    # Merge with existing results, re-verify, re-compare, re-recommend
```

### 5.6 Parallelize Verification Checks Within Each Supplier

**Problem:** Website quality, reviews, registration checks run sequentially per supplier.

**Fix:** In `app/agents/supplier_verifier.py`, use `asyncio.gather` for independent checks:

```python
async def verify_single_supplier(supplier, requirements, buyer_context):
    website_check, reviews_check, registration_check, image_extraction = await asyncio.gather(
        check_website_quality(supplier),
        check_google_reviews(supplier),
        check_business_registration(supplier),
        extract_images(supplier),  # Best-effort, already non-blocking
        return_exceptions=True,
    )
    # Combine results...
```

### 5.7 Files to Modify

| Action | File | Description |
|--------|------|-------------|
| MODIFY | `app/core/llm_gateway.py` | Add `call_llm_with_tools()` method |
| MODIFY | `app/agents/requirements_parser.py` | Switch to tool-use |
| MODIFY | `app/agents/comparison_agent.py` | Switch to tool-use, add confidence gate |
| MODIFY | `app/agents/recommendation_agent.py` | Switch to tool-use, add re-discovery trigger |
| MODIFY | `app/agents/outreach_agent.py` | Switch to tool-use |
| MODIFY | `app/agents/negotiation_agent.py` | Switch to tool-use |
| MODIFY | `app/agents/response_parser.py` | Switch to tool-use |
| MODIFY | `app/agents/supplier_verifier.py` | Parallelize checks, adaptive enrichment |
| MODIFY | `app/agents/tools/contact_enricher.py` | Add adaptive priority logic |
| MODIFY | `app/agents/orchestrator.py` | Add confidence gate, re-discovery trigger |

---

## 6. Phase 5: Feedback Loops & Learning

**Why:** The system currently treats every project as isolated. This phase makes it compound intelligence over time.

### 6.1 Downstream Feedback Bus

Create `app/services/feedback_bus.py`:

```python
class FeedbackSignal(BaseModel):
    """A correction or learning signal from a downstream agent."""
    source_agent: str           # Which agent emitted this
    target: str                 # What it affects: "supplier", "discovery", "user_profile"
    signal_type: str            # "off_category", "bounce", "great_quote", "unresponsive", etc.
    supplier_id: str | None = None
    supplier_name: str | None = None
    data: dict[str, Any] = {}
    timestamp: float = Field(default_factory=time.time)

async def emit_feedback(signal: FeedbackSignal):
    """
    Process a feedback signal and update the relevant stores.

    Signal types and actions:
    - "off_category" (from comparison): Mark supplier as irrelevant for this
      product type in supplier memory. Reduces future relevance scores.
    - "bounce" (from email delivery): Mark supplier email as invalid.
      Lower trust_level in supplier memory.
    - "great_quote" (from negotiation): Boost supplier trust and record
      pricing data for future market intelligence.
    - "unresponsive" (from follow-up): Record in supplier relationship
      history. Deprioritize for future outreach.
    - "quality_confirmed" (from user retrospective): Strong positive signal.
      Boost supplier across all dimensions.
    - "quality_failed" (from user retrospective): Strong negative signal.
      Flag supplier and record in user's avoided list.
    """
```

### 6.2 Activate Pgvector Semantic Search

**Current state:** `Supplier.embedding` column exists but is unused.

**Implementation:**

```python
# In supplier_repository.py, add:

async def generate_supplier_embedding(supplier: Supplier) -> list[float]:
    """Generate embedding from supplier description + categories + certifications."""
    text = f"{supplier.name} {supplier.description or ''} {' '.join(supplier.categories or [])} {' '.join(supplier.certifications or [])}"
    # Use a lightweight embedding model (e.g., Voyage AI, or Anthropic's embedding endpoint)
    return await embed_text(text)

async def search_supplier_memory_semantic(
    session: AsyncSession,
    requirements: ParsedRequirements,
    limit: int = 20,
) -> list[tuple[Supplier, float]]:
    """Semantic search using pgvector cosine similarity."""
    query_embedding = await generate_supplier_embedding_from_requirements(requirements)
    # Hybrid: combine vector similarity with existing keyword + interaction scoring
    ...
```

### 6.3 User Profile Auto-Update

After each project reaches "complete" status (or the user places an order), auto-update the sourcing profile:

```python
# In app/services/buyer_context_builder.py:

async def update_user_profile_from_project(
    user_id: str,
    project_state: dict,
    buyer_context: BuyerContext,
    user_feedback: dict | None = None,  # From retrospective
):
    """
    Learn from a completed project. Update UserSourcingProfile with:
    - New category experience
    - Supplier relationship updates
    - Default preference refinements
    - Import experience level upgrade
    """
    profile = await load_user_profile(user_id)

    # Update category experience
    category = project_state["parsed_requirements"]["product_type"]
    cat_exp = find_or_create_category_experience(profile, category)
    cat_exp.projects_completed += 1
    # ... update preferred_regions, typical_budget_range, etc.

    # Update supplier relationships
    for supplier_status in project_state.get("outreach_state", {}).get("supplier_statuses", []):
        if supplier_status.get("response_received"):
            update_supplier_relationship(profile, supplier_status, sentiment="neutral")

    # Upgrade import experience level
    profile.total_projects += 1
    if profile.total_projects >= 5:
        profile.import_experience_level = "regular"
    elif profile.total_projects >= 2:
        profile.import_experience_level = "occasional"

    await save_user_profile(user_id, profile)
```

### 6.4 Post-Project Retrospective

Add a simple retrospective prompt after the user places an order:

New API endpoint `POST /api/v1/projects/{id}/retrospective`:

```python
class RetrospectiveRequest(BaseModel):
    supplier_chosen: str | None = None          # Which supplier they went with
    overall_satisfaction: int | None = None      # 1-5
    communication_rating: int | None = None      # 1-5
    pricing_accuracy: str | None = None          # "as_expected", "higher", "lower"
    quality_notes: str | None = None
    would_use_again: bool | None = None
    what_went_wrong: str | None = None           # Free text
    what_went_well: str | None = None            # Free text
```

This feeds into the feedback bus and user profile update.

### 6.5 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| CREATE | `app/services/feedback_bus.py` | Feedback signal processing |
| CREATE | `app/services/embedding_service.py` | Text embedding generation |
| MODIFY | `app/repositories/supplier_repository.py` | Add semantic search, embedding generation |
| MODIFY | `app/services/buyer_context_builder.py` | Add profile auto-update logic |
| MODIFY | `app/api/v1/projects.py` | Add `/retrospective` endpoint |
| CREATE | `app/schemas/retrospective.py` | Retrospective request/response schemas |
| MODIFY | `app/agents/comparison_agent.py` | Emit "off_category" feedback signals |
| MODIFY | `app/agents/outreach_agent.py` | Emit "bounce"/"unresponsive" signals |
| MODIFY | `app/agents/negotiation_agent.py` | Emit "great_quote" signals |
| MODIFY | `app/core/scheduler.py` | Add profile update job after project completion |
| MODIFY | `frontend/src/components/workspace/phases/OrderPhase.tsx` | Add retrospective UI |

---

## 7. Phase 6: Post-Pipeline Guidance & Proactive Intelligence

### 7.1 Narrative Results Instead of Data Tables

**Problem:** Results are presented as scored tables. Users want guidance.

**Fix:** Add a `narrative_briefing` field to each agent's output that the frontend shows ABOVE the data.

For the recommendation agent, change the prompt to produce:

```python
class RecommendationResult(BaseModel):
    # ... existing ...
    narrative_briefing: str = ""  # NEW: 3-5 paragraph advisor-style briefing

# The narrative_briefing should read like:
# "For your 500 heavyweight hoodies with embroidery, I'd go with
#  Guangzhou TextilePro. They're not the cheapest — Dongguan Apparel
#  is about $2/unit less — but TextilePro has BSCI certification..."
```

Apply to comparison (`analysis_narrative` already exists — make it longer and more opinionated) and discovery (add a `discovery_briefing`).

### 7.2 Contextualized Quote Handling

When a quote comes in, the chat agent should proactively contextualize it:

In `app/core/scheduler.py`, in the inbox monitor loop, after parsing a quote:

```python
# After response_parser extracts quote data:
contextualization = await chat_agent.generate_quote_context(
    quote=parsed_quote,
    other_quotes=all_quotes_so_far,
    market_intelligence=project.market_intelligence,
    buyer_context=project.buyer_context,
)
# Store as a proactive message in the chat history
# Frontend shows it as: "💬 Procurement AI: TextilePro quoted $17.50/unit..."
```

### 7.3 Proactive Intelligence (Background Jobs)

Add new scheduler jobs:

```python
# In app/core/scheduler.py:

async def proactive_intelligence_loop():
    """
    Periodic background intelligence for active users.
    Runs every 24 hours.
    """
    for user in active_users:
        profile = await load_user_profile(user.id)

        # Check for seasonal alerts
        alerts = check_seasonal_alerts(profile)
        # e.g., "Chinese New Year in 6 weeks — place orders now"

        # Check for supplier updates (if we have relationships)
        for relationship in profile.supplier_relationships:
            # Re-check supplier website for pricing/certification changes
            ...

        # Store alerts for dashboard display
        for alert in alerts:
            await create_proactive_alert(user.id, alert)
```

New dashboard component: `ProactiveAlerts` — shows time-sensitive intelligence.

### 7.4 Guided Post-Outreach Flow

Improve the chat agent to actively shepherd the procurement process:

Update `app/agents/prompts/chat.md` to include:

```markdown
## Post-Outreach Behavior

When the user has active outreach, proactively update them:

- When a quote arrives: "TextilePro quoted $17.50/unit for 500 pieces. This is
  in line with my estimate and 15% below the next cheapest. Recommend accepting
  but request samples first."

- When a supplier doesn't respond: "Dongguan Apparel hasn't responded in 5 days.
  Common for smaller manufacturers. I've sent a follow-up. If no response by
  Friday, focus on your other 2 quotes."

- When multiple quotes are in: "You have 3 of 5 quotes. Here's how they compare.
  Istanbul is fastest but most expensive. TextilePro is best value. Want to wait
  for the remaining 2 or move forward?"

- When it's time to decide: "All 5 quotes are in. Based on your priorities
  (quality > speed > cost), I'd recommend TextilePro. Here's a comparison
  table and my reasoning."
```

### 7.5 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| MODIFY | `app/agents/prompts/recommendation.md` | Add narrative briefing instructions |
| MODIFY | `app/agents/prompts/comparison.md` | More opinionated analysis narrative |
| MODIFY | `app/agents/prompts/chat.md` | Add post-outreach guidance behavior |
| MODIFY | `app/agents/chat_agent.py` | Add `generate_quote_context()` method |
| MODIFY | `app/core/scheduler.py` | Add proactive intelligence loop |
| CREATE | `app/services/proactive_intelligence.py` | Seasonal alerts, supplier monitoring |
| CREATE | `app/schemas/proactive.py` | Alert schemas |
| MODIFY | `app/api/v1/dashboard.py` | Add proactive alerts to dashboard summary |
| CREATE | `frontend/src/components/workspace/ProactiveAlerts.tsx` | Alert display |
| MODIFY | `frontend/src/components/workspace/phases/OutreachPhase.tsx` | Contextualized quote display |

---

## 8. Cross-Cutting: Prompt & UX Rewrites

### 8.1 Prompt Rewrites

Every agent prompt needs updating to:

1. **Accept and use BuyerContext.** Add a `## Buyer Context` section to each prompt that includes the relevant subset of buyer context. Don't dump everything — each agent gets what it needs.

2. **Produce narrative alongside data.** Add instructions for generating human-readable summaries that express judgment, not just scores.

3. **Reference UserSourcingProfile.** When past projects exist, reference them: "This buyer has sourced apparel before from China with good results."

4. **Use tool-use schemas.** Replace "respond with valid JSON" instructions with tool definitions.

**Priority order for prompt rewrites:**
1. `requirements_parser.md` (asks contextual questions)
2. `discovery.md` → per-team prompts (5 new prompts)
3. `comparison.md` (uses buyer context for cost estimates)
4. `recommendation.md` (narrative briefing)
5. `outreach.md` (buyer context in emails)
6. `chat.md` (post-outreach guidance)
7. All remaining prompts

### 8.2 Frontend Presentation Shift

**Supplier cards** should show user-centric information:
- "Estimated landed cost to Dallas: $17.50/unit" (not "unit price: $14")
- "Communication: English sales team, responds in 24hrs" (not "preferred contact: email")
- "Risk: Medium — verified site, 4.2★, but no certification" (not "composite: 63")

**Results page** should lead with narrative, then data:
- Top: 3-5 paragraph narrative briefing from recommendation agent
- Middle: recommended supplier cards with advisor-style summaries
- Bottom: full comparison table for users who want detail

### 8.3 First Interaction as Conversation

Replace the current "type and submit" entry point with a conversational flow:

```
User types: "500 heavyweight hoodies with embroidery"

Agent responds: "Got it — custom embroidered hoodies, 500 units.
A couple things that'll help me find the right suppliers:

1. Are these for retail or events/merch? (Affects quality requirements)
2. Roughly what's your target per-unit cost — $15 range or $30 range?

I can start searching now with defaults, or wait for your answers."

[Start searching now] [Let me answer first]
```

This replaces the current clarifying question questionnaire with a conversational exchange. Implementation: modify `parse_node` to emit the conversational response as the first checkpoint, rather than the current `clarifying_questions` array.

---

## 9. Migration & Backward Compatibility

### 9.1 Schema Migration Strategy

All new schemas use `Field(default_factory=...)` with empty defaults. Existing projects without `buyer_context` or new fields will work with empty/None values.

The `PipelineState` gains `buyer_context` as an optional field — existing serialized states deserialize without breaking.

### 9.2 Feature Flags

Use a simple feature flag system to roll out incrementally:

```python
# In app/core/config.py:
class Settings(BaseSettings):
    # ... existing ...
    ENABLE_MULTI_TEAM_DISCOVERY: bool = False
    ENABLE_CHECKPOINTS: bool = False
    ENABLE_TOOL_USE_OUTPUT: bool = False
    ENABLE_BUYER_CONTEXT: bool = False
    ENABLE_PROACTIVE_INTELLIGENCE: bool = False
```

Each phase can be toggled independently. The orchestrator checks flags before using new code paths and falls back to existing behavior when disabled.

### 9.3 Fallback Paths

- Multi-team discovery falls back to existing `supplier_discovery.py` when `ENABLE_MULTI_TEAM_DISCOVERY=False`.
- Checkpoints are skipped (auto-continue with 0s timeout) when `ENABLE_CHECKPOINTS=False`.
- Tool-use falls back to existing JSON parsing when `ENABLE_TOOL_USE_OUTPUT=False`.
- Buyer context defaults to empty `BuyerContext()` when not provided.

---

## 10. Dependency Order & Parallelization

### Phase Dependencies

```
Phase 1 (Buyer Context)     ← Foundation, no dependencies
Phase 2 (Discovery Teams)   ← Depends on Phase 1 (needs BuyerContext)
Phase 3 (Checkpoints)       ← Depends on Phase 1 (gathers context at checkpoints)
Phase 4 (Agent Upgrades)    ← Independent (can parallel with Phase 2/3)
Phase 5 (Feedback Loops)    ← Depends on Phase 1 (writes to UserProfile)
Phase 6 (Post-Pipeline)     ← Depends on Phase 1, 5
```

### Recommended Execution Order

```
Week 1-2:   Phase 1 (Buyer Context schemas + DB migration + threading)
            Phase 4.1 (Tool-use in LLM Gateway — independent)

Week 3-4:   Phase 2 (Multi-team discovery — parallel tracks)
            Phase 4.2-4.6 (Other agent upgrades — parallel)

Week 5-6:   Phase 3 (Checkpoints + frontend)
            Phase 5.1-5.2 (Feedback bus + pgvector)

Week 7-8:   Phase 5.3-5.4 (Profile auto-update + retrospective)
            Phase 6.1-6.2 (Narrative results + quote contextualization)

Week 9-10:  Phase 6.3-6.4 (Proactive intelligence + guided post-outreach)
            Phase 8 (Prompt rewrites — rolling)

Week 11-12: Integration testing, feature flag rollout, frontend polish
```

### Parallelization Opportunities

Two engineers can work simultaneously:

- **Engineer A (Backend/Agent):** Phase 1 schemas → Phase 2 discovery teams → Phase 4 agent upgrades → Phase 5 feedback loops
- **Engineer B (Frontend/API):** Phase 1 API changes → Phase 3 checkpoints → Phase 6 UX → Phase 8 frontend rewrites

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Supplier relevance (% off-category in top 10) | ~15% | < 5% |
| Discovery diversity (unique regions in results) | 2-3 | 4-5 |
| User engagement (% of checkpoints interacted with) | N/A | > 40% |
| Repeat project efficiency (time to results, project 3+) | Same as project 1 | 50% faster |
| Quote response rate | ~20% | ~35% |
| User satisfaction (retrospective rating) | N/A | 4.0+ / 5.0 |
| LLM cost per project | Baseline | -30% (via Haiku pre-filter + tool-use) |

---

*This plan is designed to be implemented incrementally with feature flags. Each phase delivers standalone value. The system remains fully functional throughout the rollout — no big-bang migration required.*
