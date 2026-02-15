"""Central pipeline state — the TypedDict that flows through all LangGraph nodes."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import add

from automotive.schemas.comparison import ComparisonMatrix
from automotive.schemas.discovery import DiscoveryResult
from automotive.schemas.qualification import QualificationResult
from automotive.schemas.quotes import QuoteIngestionResult
from automotive.schemas.report import IntelligenceReportResult
from automotive.schemas.requirements import ParsedRequirement
from automotive.schemas.rfq import RFQResult


class ProcurementState(TypedDict, total=False):
    """Complete state flowing through the 7-stage automotive procurement pipeline."""

    # Immutable context
    project_id: str
    org_id: str
    created_by: str
    created_at: str

    # Messages (append-only)
    messages: Annotated[list[dict], add]

    # Stage outputs
    raw_request: str
    parsed_requirement: dict  # ParsedRequirement as dict
    discovery_result: dict  # DiscoveryResult as dict
    qualification_result: dict  # QualificationResult as dict
    comparison_matrix: dict  # ComparisonMatrix as dict
    intelligence_reports: dict  # IntelligenceReportResult as dict
    rfq_result: dict  # RFQResult as dict
    quote_ingestion: dict  # QuoteIngestionResult as dict

    # Pipeline control
    current_stage: str
    approvals: dict  # stage → {approved: bool, by: str, at: str, notes: str}
    errors: Annotated[list[dict], add]

    # Human modifications
    human_overrides: dict  # stage → modifications made by human

    # Weight adjustments (for comparison)
    weight_profile: dict  # dimension → weight (floats)

    # Buyer info
    buyer_company: str
    buyer_contact_name: str
    buyer_contact_email: str


# Stage names
STAGE_PARSE = "parse"
STAGE_DISCOVER = "discover"
STAGE_QUALIFY = "qualify"
STAGE_COMPARE = "compare"
STAGE_REPORT = "report"
STAGE_RFQ = "rfq"
STAGE_QUOTE_INGEST = "quote_ingest"
STAGE_COMPLETE = "complete"

ALL_STAGES = [
    STAGE_PARSE,
    STAGE_DISCOVER,
    STAGE_QUALIFY,
    STAGE_COMPARE,
    STAGE_REPORT,
    STAGE_RFQ,
    STAGE_QUOTE_INGEST,
    STAGE_COMPLETE,
]
