"""Typed state models for the LangGraph agent pipeline.

These Pydantic models define the data contracts between agents.
Each agent reads from and writes to specific fields — this prevents
race conditions in parallel execution.
"""

from __future__ import annotations

import time
from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Agent A: Requirements Parser output ──────────────────────────

class RegionalSearchConfig(BaseModel):
    """Regional search strategy for a specific manufacturing hub."""
    region: str = Field(description="Country or region name, e.g. 'China', 'Turkey'")
    language_code: str = Field(description="ISO language code, e.g. 'zh', 'tr', 'vi'")
    language_name: str = Field(description="Language name, e.g. 'Chinese', 'Turkish'")
    search_queries: list[str] = Field(default_factory=list, description="Queries in target language")
    rationale: str = ""


class ClarifyingQuestion(BaseModel):
    """A clarifying question the AI wants to ask the user before searching."""
    field: str = Field(description="Which requirement field this relates to")
    question: str = Field(description="Human-readable question text")
    importance: str = "recommended"  # "critical", "recommended", "optional"
    suggestions: list[str] = Field(default_factory=list)


class ProgressEvent(BaseModel):
    """A granular progress update for the frontend."""
    stage: str
    substep: str
    detail: str
    progress_pct: float | None = None
    timestamp: float = Field(default_factory=time.time)


class ContactEnrichmentResult(BaseModel):
    """Tracks contact enrichment attempts and results for a supplier."""
    sources_tried: list[str] = Field(default_factory=list)
    sources_succeeded: list[str] = Field(default_factory=list)
    emails_found: list[str] = Field(default_factory=list)
    phones_found: list[str] = Field(default_factory=list)
    best_email: str | None = None
    best_phone: str | None = None
    enrichment_confidence: float = 0.0  # 0-100


class IntermediaryDetection(BaseModel):
    """Result of intermediary/directory detection for a discovered supplier."""
    is_intermediary: bool = False
    intermediary_type: str | None = None  # "directory", "marketplace", "trading_company"
    original_url: str | None = None
    extracted_manufacturer_name: str | None = None
    resolved_direct_url: str | None = None


class AutoOutreachConfig(BaseModel):
    """Configuration for autonomous outreach mode."""
    mode: str = "manual"  # "manual", "semi_auto", "auto"
    auto_send_threshold: float = 80.0
    max_concurrent_outreach: int = 5
    follow_up_schedule: list[int] = Field(default_factory=lambda: [3, 7, 14])


class InboxMonitorConfig(BaseModel):
    """Configuration for response monitoring (groundwork — not yet implemented)."""
    enabled: bool = False
    poll_interval_seconds: int = 300
    inbox_provider: str | None = None  # "gmail", "outlook", "imap"


class EmailDeliveryEvent(BaseModel):
    """A delivery tracking event from Resend webhooks."""
    event_type: str  # "delivered", "bounced", "opened", "clicked", "complained"
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)


class CommunicationStatusEvent(BaseModel):
    """Immutable status change for a communication record."""
    event_type: str
    status: str
    timestamp: float = Field(default_factory=time.time)
    source: str = "system"
    details: dict[str, Any] = Field(default_factory=dict)


class CommunicationMessage(BaseModel):
    """Outbound or inbound communication record."""
    message_key: str
    direction: str  # "outbound" | "inbound"
    channel: str = "email"
    supplier_index: int | None = None
    supplier_name: str | None = None
    to_email: str | None = None
    from_email: str | None = None
    cc_emails: list[str] = Field(default_factory=list)
    subject: str | None = None
    body_preview: str | None = None
    resend_email_id: str | None = None
    inbox_message_id: str | None = None
    matched_sender: str | None = None
    thread_key: str | None = None
    source: str | None = None
    delivery_status: str = "unknown"
    parsed_response: bool = False
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    events: list[CommunicationStatusEvent] = Field(default_factory=list)


class CommunicationMonitorState(BaseModel):
    """End-to-end communications monitor for outreach."""
    owner_email: str | None = None
    last_inbox_check_at: float | None = None
    last_inbox_check_source: str | None = None
    last_inbox_message_count: int = 0
    total_outbound: int = 0
    total_inbound: int = 0
    total_replies: int = 0
    total_failures: int = 0
    messages: list[CommunicationMessage] = Field(default_factory=list)


class PhoneCallConfig(BaseModel):
    """Configuration for AI phone calling via Retell."""
    enabled: bool = False
    voice_id: str = "11labs-Adrian"
    max_call_duration_seconds: int = 300
    questions_to_ask: list[str] = Field(default_factory=list)


class PhoneCallRequest(BaseModel):
    """Request to initiate a phone call to a supplier."""
    supplier_name: str
    supplier_index: int
    phone_number: str
    questions: list[str] = Field(default_factory=list)


class PhoneCallStatus(BaseModel):
    """Tracks the status of an AI phone call."""
    call_id: str
    supplier_name: str
    supplier_index: int
    status: str = "pending"  # "pending", "in_progress", "completed", "failed", "no_answer"
    duration_seconds: float = 0
    transcript: str | None = None
    recording_url: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class ParsedCallResult(BaseModel):
    """Structured data extracted from a phone call transcript."""
    supplier_name: str
    call_id: str
    pricing_info: str | None = None
    moq: str | None = None
    lead_time: str | None = None
    key_findings: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    raw_transcript: str = ""


class PhoneOutreachResult(BaseModel):
    """Collection of phone call results for a project."""
    calls: list[PhoneCallStatus] = Field(default_factory=list)
    parsed_results: list[ParsedCallResult] = Field(default_factory=list)


class ParsedRequirements(BaseModel):
    """Structured product requirements extracted from natural language."""
    product_type: str = Field(description="Primary product category")
    material: str | None = Field(None, description="Material specification")
    dimensions: str | None = Field(None, description="Size/dimensions")
    quantity: int | None = Field(None, description="Order quantity")
    customization: str | None = Field(None, description="Customization details")
    delivery_location: str | None = Field(None, description="Delivery city/state/country")
    deadline: date | None = Field(None, description="Delivery deadline")
    certifications_needed: list[str] = Field(default_factory=list)
    budget_range: str | None = Field(None, description="Budget range e.g. '$2-5 per unit'")
    missing_fields: list[str] = Field(default_factory=list, description="Fields that couldn't be parsed")
    search_queries: list[str] = Field(
        default_factory=list,
        description="Generated search queries for supplier discovery",
    )
    # Regional search + clarifying questions (Phase 2)
    regional_searches: list[RegionalSearchConfig] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    sourcing_strategy: str | None = Field(None, description="LLM's strategic sourcing approach")
    sourcing_preference: str | None = Field(
        None,
        description="Preferred sourcing country/region — e.g. 'Egypt', 'domestic only'. "
                    "Distinct from delivery_location.",
    )


# ── Agent B: Discovery output ────────────────────────────────────

class DiscoveredSupplier(BaseModel):
    """A supplier found during discovery, before verification."""
    supplier_id: str | None = None
    name: str
    website: str | None = None
    product_page_url: str | None = Field(None, description="Direct link to the specific product page, if found")
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    description: str | None = None
    categories: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    source: str = "unknown"  # google, thomasnet, alibaba, etc.
    relevance_score: float = 0.0
    google_rating: float | None = None
    google_review_count: int | None = None
    estimated_shipping_cost: str | None = Field(None, description="Estimated shipping cost to buyer's location")
    raw_data: dict[str, Any] = Field(default_factory=dict)
    # Intermediary detection fields
    is_intermediary: bool = False
    intermediary_detection: IntermediaryDetection | None = None
    original_source_url: str | None = None
    language_discovered: str | None = None
    enrichment: ContactEnrichmentResult | None = None
    filtered_reason: str | None = Field(
        None,
        description="If set, supplier was filtered from main results. "
                    "Reason: 'retail_store', 'wrong_product_type', 'low_relevance'",
    )


class DiscoveryResults(BaseModel):
    """Output from the Supplier Discovery agent."""
    suppliers: list[DiscoveredSupplier] = Field(default_factory=list)
    sources_searched: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)
    total_raw_results: int = 0
    deduplicated_count: int = 0
    # Enhanced discovery metadata
    regional_results: dict[str, int] = Field(default_factory=dict)
    intermediaries_resolved: int = 0
    search_rounds: int = 1
    filtered_suppliers: list[DiscoveredSupplier] = Field(
        default_factory=list,
        description="Suppliers that didn't make the main list, with filter reasons",
    )


# ── Agent C: Verification output ────────────────────────────────

class VerificationCheck(BaseModel):
    """Result of a single verification check."""
    check_type: str  # website, registration, certifications, reviews, social
    status: str  # passed, failed, unavailable
    score: float = 0.0  # 0-100
    details: str = ""
    raw_data: dict[str, Any] = Field(default_factory=dict)


class SupplierVerification(BaseModel):
    """Full verification report for one supplier."""
    supplier_name: str
    supplier_index: int  # Index in the discovery results list
    checks: list[VerificationCheck] = Field(default_factory=list)
    composite_score: float = 0.0  # 0-100
    risk_level: str = "unknown"  # low, medium, high
    recommendation: str = "pending"  # proceed, caution, reject
    summary: str = ""
    preferred_contact_method: str = "email"  # "email", "phone", "website_form"
    contact_notes: str | None = None


class VerificationResults(BaseModel):
    """Output from the Supplier Verification agent."""
    verifications: list[SupplierVerification] = Field(default_factory=list)


# ── Agent G: Comparison output ───────────────────────────────────

class SupplierComparison(BaseModel):
    """Side-by-side comparison data for one supplier."""
    supplier_name: str
    supplier_index: int
    verification_score: float = 0.0
    estimated_unit_price: str | None = None
    estimated_shipping_cost: str | None = Field(None, description="Estimated shipping/freight cost to buyer location")
    estimated_landed_cost: str | None = Field(None, description="Total cost including unit price + shipping")
    moq: str | None = None
    lead_time: str | None = None
    certifications: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    overall_score: float = 0.0  # 0-100 weighted composite
    # Sub-category star ratings (0.0-5.0 scale for frontend star display)
    price_score: float = 0.0
    quality_score: float = 0.0
    shipping_score: float = 0.0
    review_score: float = 0.0
    lead_time_score: float = 0.0


class ComparisonResult(BaseModel):
    """Output from the Comparison agent."""
    comparisons: list[SupplierComparison] = Field(default_factory=list)
    analysis_narrative: str = ""
    best_value: str | None = None
    best_quality: str | None = None
    best_speed: str | None = None


# ── Agent H: Recommendation output ──────────────────────────────

class SupplierRecommendation(BaseModel):
    """Final recommendation for one supplier."""
    rank: int
    supplier_name: str
    supplier_index: int
    overall_score: float
    confidence: str  # high, medium, low
    reasoning: str
    best_for: str  # e.g. "best overall", "budget pick", "fastest delivery"


class RecommendationResult(BaseModel):
    """Output from the Recommendation agent."""
    recommendations: list[SupplierRecommendation] = Field(default_factory=list)
    executive_summary: str = ""
    caveats: list[str] = Field(default_factory=list)


# ── Master Pipeline State ────────────────────────────────────────

class PipelineStage(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    CLARIFYING = "clarifying"
    DISCOVERING = "discovering"
    VERIFYING = "verifying"
    COMPARING = "comparing"
    RECOMMENDING = "recommending"
    OUTREACHING = "outreaching"
    COMPLETE = "complete"
    FAILED = "failed"


class PipelineState(BaseModel):
    """
    The canonical state object passed through the LangGraph pipeline.
    Each agent reads and writes specific fields.
    """
    # Identifiers
    project_id: UUID | None = None
    user_id: UUID | None = None

    # Input
    raw_description: str = ""

    # Stage tracking
    current_stage: PipelineStage = PipelineStage.IDLE
    error: str | None = None

    # Agent outputs — each agent writes to exactly one of these
    parsed_requirements: ParsedRequirements | None = None
    discovery_results: DiscoveryResults | None = None
    verification_results: VerificationResults | None = None
    comparison_result: ComparisonResult | None = None
    recommendation_result: RecommendationResult | None = None


# ── Chat models ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single message in the project chat."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatAction(BaseModel):
    """An action the chat agent decided to trigger."""
    action_type: str  # rescore, rediscover, draft_outreach, adjust_weights, none
    parameters: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response from the chat agent."""
    message: str
    action: ChatAction | None = None


# ── Agent D: Outreach output ──────────────────────────────────

class DraftEmail(BaseModel):
    """A draft RFQ email for one supplier."""
    supplier_name: str
    supplier_index: int
    recipient_email: str | None = None
    subject: str
    body: str
    status: str = "draft"  # draft, approved, sent, failed


class OutreachResult(BaseModel):
    """Output from the Outreach Agent."""
    drafts: list[DraftEmail] = Field(default_factory=list)
    summary: str = ""


# ── Agent E: Follow-up output ─────────────────────────────────

class FollowUpEmail(BaseModel):
    """A follow-up email for a non-responsive supplier."""
    supplier_name: str
    supplier_index: int
    recipient_email: str | None = None
    subject: str
    body: str
    follow_up_number: int  # 1, 2, 3 (day 3, 7, 14)
    status: str = "draft"  # draft, approved, sent


class FollowUpResult(BaseModel):
    """Output from the Follow-up Agent."""
    follow_ups: list[FollowUpEmail] = Field(default_factory=list)
    summary: str = ""


# ── Agent F: Response Parser output ───────────────────────────

class ParsedQuote(BaseModel):
    """Structured quote data extracted from a supplier's email response."""
    supplier_name: str
    supplier_index: int
    unit_price: str | None = None
    currency: str = "USD"
    moq: str | None = None
    lead_time: str | None = None
    payment_terms: str | None = None
    shipping_terms: str | None = None
    validity_period: str | None = None
    notes: str | None = None
    can_fulfill: bool | None = None
    fulfillment_note: str | None = None
    confidence_score: float = 0.0  # 0-100
    raw_text: str = ""


class QuoteParseResult(BaseModel):
    """Output from the Response Parser Agent."""
    quotes: list[ParsedQuote] = Field(default_factory=list)
    parsing_notes: str = ""


# ── Negotiation output ────────────────────────────────────────

class NegotiationResponse(BaseModel):
    """AI-generated negotiation response to a supplier's quote."""
    supplier_name: str
    supplier_index: int
    action: str  # "accept", "clarify", "counter", "reject"
    reasoning: str = ""
    draft_email: DraftEmail | None = None
    confidence: float = 0.0  # 0-100


class NegotiationResult(BaseModel):
    """Output from the Negotiation Agent."""
    responses: list[NegotiationResponse] = Field(default_factory=list)
    summary: str = ""


# ── Outreach tracking state ───────────────────────────────────

class SupplierOutreachStatus(BaseModel):
    """Tracks outreach state for one supplier."""
    supplier_name: str
    supplier_index: int
    email_sent: bool = False
    sent_at: float | None = None
    email_id: str | None = None  # Resend email ID for tracking
    email_ids: list[str] = Field(default_factory=list)  # Historical Resend IDs for this supplier
    delivery_status: str = "unknown"  # "unknown", "sent", "delivered", "bounced", "opened", "clicked"
    send_error: str | None = None
    delivery_events: list[EmailDeliveryEvent] = Field(default_factory=list)
    response_received: bool = False
    response_text: str | None = None
    parsed_quote: ParsedQuote | None = None
    follow_ups_sent: int = 0
    last_follow_up_at: float | None = None
    excluded: bool = False
    exclusion_reason: str | None = None
    # Phone outreach
    phone_call_id: str | None = None
    phone_status: str | None = None  # "pending", "in_progress", "completed", "failed", "no_answer"
    phone_transcript: str | None = None


class OutreachPlanStep(BaseModel):
    """A concrete outreach step for a supplier."""
    stage: str
    objective: str
    owner: str = "system"
    due_in_hours: int = 0


class SupplierOutreachPlan(BaseModel):
    """Execution plan that drives a supplier from intent to quoted offer."""
    supplier_name: str
    supplier_index: int
    channel: str = "email"
    friction_risks: list[str] = Field(default_factory=list)
    steps: list[OutreachPlanStep] = Field(default_factory=list)


class OutreachEvent(BaseModel):
    """Immutable event log entry for outreach lifecycle analytics."""
    event_type: str
    supplier_index: int | None = None
    supplier_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class OutreachState(BaseModel):
    """Full outreach tracking state for a project."""
    selected_suppliers: list[int] = Field(default_factory=list)
    supplier_statuses: list[SupplierOutreachStatus] = Field(default_factory=list)
    excluded_suppliers: list[int] = Field(default_factory=list)
    draft_emails: list[DraftEmail] = Field(default_factory=list)
    follow_up_emails: list[FollowUpEmail] = Field(default_factory=list)
    parsed_quotes: list[ParsedQuote] = Field(default_factory=list)
    auto_config: AutoOutreachConfig | None = None
    # Phone calling
    phone_calls: list[PhoneCallStatus] = Field(default_factory=list)
    parsed_call_results: list[ParsedCallResult] = Field(default_factory=list)
    phone_config: PhoneCallConfig | None = None
    supplier_plans: list[SupplierOutreachPlan] = Field(default_factory=list)
    events: list[OutreachEvent] = Field(default_factory=list)
    quick_approval_decision: str | None = None  # "approved" | "declined"
    communication_monitor: CommunicationMonitorState = Field(default_factory=CommunicationMonitorState)
