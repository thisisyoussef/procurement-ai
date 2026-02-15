"""LangGraph orchestrator — 7-stage automotive procurement pipeline.

Wires all agents into a StateGraph with human-in-the-loop interrupt gates
at every stage transition. Uses PostgresSaver for durable checkpointing.
"""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from automotive.agents import (
    comparison_engine,
    intelligence_report,
    requirements_parser,
    response_ingestion,
    rfq_outreach,
    supplier_discovery,
    supplier_qualification,
)
from automotive.schemas.pipeline_state import (
    ALL_STAGES,
    STAGE_COMPARE,
    STAGE_COMPLETE,
    STAGE_DISCOVER,
    STAGE_QUALIFY,
    STAGE_QUOTE_INGEST,
    STAGE_REPORT,
    STAGE_RFQ,
    ProcurementState,
)

logger = logging.getLogger(__name__)


# ── Node wrappers ──────────────────────────────────────────────────────

async def parse_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 1: Parse natural language into structured requirements."""
    return await requirements_parser.run(state)


async def discover_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 2: Search multiple sources for potential suppliers."""
    return await supplier_discovery.run(state)


async def qualify_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 3: Verify certifications, financial health, capabilities."""
    return await supplier_qualification.run(state)


async def compare_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 4: Build normalized comparison matrix."""
    return await comparison_engine.run(state)


async def report_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 5: Generate per-supplier intelligence reports."""
    return await intelligence_report.run(state)


async def rfq_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 6: Generate RFQ packages for approved suppliers."""
    return await rfq_outreach.run(state)


async def quote_ingest_node(state: ProcurementState) -> dict[str, Any]:
    """Agent 7: Parse incoming supplier quotes."""
    return await response_ingestion.run(state)


async def complete_node(state: ProcurementState) -> dict[str, Any]:
    """Terminal node — marks project as complete."""
    return {
        "current_stage": "complete",
        "messages": [
            {
                "role": "system",
                "content": "Pipeline complete. Final intelligence package ready for buyer review.",
            }
        ],
    }


# ── HITL gate nodes ───────────────────────────────────────────────────
# These nodes use LangGraph's interrupt() to pause the graph and wait
# for human approval. State is checkpointed to PostgreSQL and the graph
# resumes when the human provides input via Command(resume=...).

async def gate_after_parse(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer confirms/edits parsed requirements."""
    from langgraph.types import interrupt

    parsed = state.get("parsed_requirement", {})
    decision = interrupt({
        "type": "requirements_confirmation",
        "data": parsed,
        "message": "Review parsed requirements. Confirm or edit before discovery begins.",
    })

    if decision.get("approved"):
        # Apply any human edits
        if decision.get("edits"):
            merged = {**parsed, **decision["edits"]}
            return {"parsed_requirement": merged, "approvals": {**state.get("approvals", {}), "parse": decision}}
        return {"approvals": {**state.get("approvals", {}), "parse": decision}}
    else:
        return {"errors": [{"stage": "parse", "error": "Requirements rejected by buyer", "reason": decision.get("reason", "")}]}


async def gate_after_discover(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer reviews and filters supplier longlist."""
    from langgraph.types import interrupt

    discovery = state.get("discovery_result", {})
    decision = interrupt({
        "type": "longlist_review",
        "data": discovery,
        "message": "Review discovered suppliers. Add/remove before qualification.",
    })

    if decision.get("approved"):
        # Apply supplier removals
        if decision.get("removed_supplier_ids"):
            suppliers = discovery.get("suppliers", [])
            filtered = [s for s in suppliers if s.get("supplier_id") not in decision["removed_supplier_ids"]]
            discovery["suppliers"] = filtered
            discovery["total_found"] = len(filtered)
            return {"discovery_result": discovery, "approvals": {**state.get("approvals", {}), "discover": decision}}
        return {"approvals": {**state.get("approvals", {}), "discover": decision}}
    else:
        return {"errors": [{"stage": "discover", "error": "Longlist rejected by buyer"}]}


async def gate_after_qualify(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer reviews qualification results and overrides."""
    from langgraph.types import interrupt

    qualification = state.get("qualification_result", {})
    decision = interrupt({
        "type": "shortlist_review",
        "data": qualification,
        "message": "Review qualification results. Override status if needed.",
    })

    if decision.get("approved"):
        # Apply status overrides
        if decision.get("status_overrides"):
            suppliers = qualification.get("suppliers", [])
            overrides = decision["status_overrides"]
            for s in suppliers:
                if s.get("supplier_id") in overrides:
                    s["qualification_status"] = overrides[s["supplier_id"]]
            return {"qualification_result": qualification, "approvals": {**state.get("approvals", {}), "qualify": decision}}
        return {"approvals": {**state.get("approvals", {}), "qualify": decision}}
    else:
        return {"errors": [{"stage": "qualify", "error": "Shortlist rejected by buyer"}]}


async def gate_after_compare(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer reviews comparison matrix, adjusts weights."""
    from langgraph.types import interrupt

    comparison = state.get("comparison_matrix", {})
    decision = interrupt({
        "type": "ranking_review",
        "data": comparison,
        "message": "Review comparison matrix. Adjust weights if needed.",
    })

    if decision.get("approved"):
        if decision.get("weight_adjustments"):
            return {
                "weight_profile": decision["weight_adjustments"],
                "approvals": {**state.get("approvals", {}), "compare": decision},
            }
        return {"approvals": {**state.get("approvals", {}), "compare": decision}}
    else:
        return {"errors": [{"stage": "compare", "error": "Comparison rejected by buyer"}]}


async def gate_after_report(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer reviews intelligence reports."""
    from langgraph.types import interrupt

    reports = state.get("intelligence_reports", {})
    decision = interrupt({
        "type": "report_review",
        "data": reports,
        "message": "Review intelligence reports before RFQ generation.",
    })

    if decision.get("approved"):
        return {"approvals": {**state.get("approvals", {}), "report": decision}}
    else:
        return {"errors": [{"stage": "report", "error": "Reports need revision"}]}


async def gate_before_send(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: CRITICAL — Buyer must explicitly approve RFQ sending."""
    from langgraph.types import interrupt

    rfq = state.get("rfq_result", {})
    decision = interrupt({
        "type": "rfq_send_approval",
        "data": rfq,
        "message": "REVIEW CAREFULLY: Approve RFQ emails before they are sent to suppliers.",
    })

    if decision.get("approved"):
        return {"approvals": {**state.get("approvals", {}), "rfq_send": decision}}
    else:
        return {"errors": [{"stage": "rfq", "error": "RFQ send not approved"}]}


async def gate_after_quotes(state: ProcurementState) -> dict[str, Any]:
    """HITL gate: Buyer reviews parsed quotes."""
    from langgraph.types import interrupt

    quotes = state.get("quote_ingestion", {})
    decision = interrupt({
        "type": "quote_review",
        "data": quotes,
        "message": "Review parsed quotes. Correct any extraction errors.",
    })

    if decision.get("approved"):
        if decision.get("corrections"):
            # Apply manual corrections to quotes
            parsed_quotes = quotes.get("quotes", [])
            for correction in decision["corrections"]:
                sid = correction.get("supplier_id")
                for q in parsed_quotes:
                    if q.get("supplier_id") == sid:
                        q.update(correction.get("updates", {}))
            quotes["quotes"] = parsed_quotes
            return {"quote_ingestion": quotes, "approvals": {**state.get("approvals", {}), "quotes": decision}}
        return {"approvals": {**state.get("approvals", {}), "quotes": decision}}
    else:
        return {"errors": [{"stage": "quote_ingest", "error": "Quotes need re-review"}]}


# ── Routing logic ─────────────────────────────────────────────────────

def _should_expand_search(state: ProcurementState) -> str:
    """Check if discovery returned too few results."""
    discovery = state.get("discovery_result", {})
    total = discovery.get("total_found", 0)
    if total < 3:
        logger.info("Only %d suppliers found, expanding search", total)
        return "expand_search"
    return "proceed"


# ── Graph construction ────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build the complete 7-stage procurement pipeline graph."""
    graph = StateGraph(ProcurementState)

    # Agent nodes
    graph.add_node("parse", parse_node)
    graph.add_node("gate_parse", gate_after_parse)
    graph.add_node("discover", discover_node)
    graph.add_node("gate_discover", gate_after_discover)
    graph.add_node("qualify", qualify_node)
    graph.add_node("gate_qualify", gate_after_qualify)
    graph.add_node("compare", compare_node)
    graph.add_node("gate_compare", gate_after_compare)
    graph.add_node("report", report_node)
    graph.add_node("gate_report", gate_after_report)
    graph.add_node("rfq", rfq_node)
    graph.add_node("gate_rfq_send", gate_before_send)
    graph.add_node("quote_ingest", quote_ingest_node)
    graph.add_node("gate_quotes", gate_after_quotes)
    graph.add_node("complete", complete_node)

    # Linear pipeline with HITL gates at each transition
    graph.set_entry_point("parse")
    graph.add_edge("parse", "gate_parse")
    graph.add_edge("gate_parse", "discover")

    # After discovery, check if we need to expand
    graph.add_conditional_edges(
        "discover",
        _should_expand_search,
        {"expand_search": "discover", "proceed": "gate_discover"},
    )
    graph.add_edge("gate_discover", "qualify")
    graph.add_edge("qualify", "gate_qualify")
    graph.add_edge("gate_qualify", "compare")
    graph.add_edge("compare", "gate_compare")
    graph.add_edge("gate_compare", "report")
    graph.add_edge("report", "gate_report")
    graph.add_edge("gate_report", "rfq")
    graph.add_edge("rfq", "gate_rfq_send")
    graph.add_edge("gate_rfq_send", "quote_ingest")
    graph.add_edge("quote_ingest", "gate_quotes")
    graph.add_edge("gate_quotes", "complete")
    graph.add_edge("complete", END)

    return graph


def compile_graph(checkpointer=None):
    """Compile the graph with optional checkpointer for persistence."""
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)
