"""LangGraph orchestrator — wires all agents into a directed pipeline.

Pipeline: parse → discover → verify → compare → recommend

Each node reads from and writes to the shared PipelineState.
The graph supports human-in-the-loop interrupts at critical junctures.
"""

from __future__ import annotations

import traceback
import logging
from typing import Any, TypedDict

from app.agents.comparison_agent import compare_suppliers
from app.agents.recommendation_agent import generate_recommendation
from app.agents.requirements_parser import parse_requirements
from app.agents.supplier_discovery import discover_suppliers
from app.agents.supplier_verifier import verify_suppliers
from app.schemas.agent_state import (
    AutoOutreachConfig,
    ComparisonResult,
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    PipelineStage,
    RecommendationResult,
    SupplierOutreachStatus,
    VerificationResults,
)

logger = logging.getLogger(__name__)

# ── State as TypedDict for LangGraph compatibility ───────────────

class GraphState(TypedDict, total=False):
    """State passed between graph nodes."""
    raw_description: str
    current_stage: str
    error: str | None

    # Agent outputs
    parsed_requirements: dict | None
    discovery_results: dict | None
    verification_results: dict | None
    comparison_result: dict | None
    recommendation_result: dict | None
    outreach_result: dict | None

    # Progress & clarifying questions
    progress_events: list[dict]
    user_answers: dict | None

    # Auto-outreach flag — when True, pipeline auto-drafts and queues RFQ emails
    auto_outreach_enabled: bool


# ── Graph Nodes ──────────────────────────────────────────────────

async def parse_node(state: GraphState) -> GraphState:
    """Node A: Parse requirements from raw description."""
    logger.info("═══ STAGE 1/5: PARSING REQUIREMENTS ═══")
    try:
        result = await parse_requirements(state["raw_description"])
        logger.info("═══ PARSING COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.DISCOVERING.value,
            "parsed_requirements": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:
        logger.error("Stage failed: %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.FAILED.value,
            "error": f"Requirements parsing failed: {str(e)}\n{traceback.format_exc()}",
        }


async def discover_node(state: GraphState) -> GraphState:
    """Node B: Discover suppliers from multiple sources."""
    logger.info("═══ STAGE 2/5: DISCOVERING SUPPLIERS ═══")
    try:
        requirements = ParsedRequirements(**state["parsed_requirements"])
        result = await discover_suppliers(requirements)
        logger.info("═══ DISCOVERY COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.VERIFYING.value,
            "discovery_results": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:
        logger.error("Stage failed: %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.FAILED.value,
            "error": f"Supplier discovery failed: {str(e)}\n{traceback.format_exc()}",
        }


async def verify_node(state: GraphState) -> GraphState:
    """Node C: Verify discovered suppliers."""
    logger.info("═══ STAGE 3/5: VERIFYING SUPPLIERS ═══")
    try:
        discovery = DiscoveryResults(**state["discovery_results"])
        # Verify top 20 suppliers by relevance
        top_suppliers = sorted(
            discovery.suppliers, key=lambda s: s.relevance_score, reverse=True
        )[:20]
        result = await verify_suppliers(top_suppliers)
        logger.info("═══ VERIFICATION COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.COMPARING.value,
            "verification_results": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:
        logger.error("Stage failed: %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.FAILED.value,
            "error": f"Supplier verification failed: {str(e)}\n{traceback.format_exc()}",
        }


async def compare_node(state: GraphState) -> GraphState:
    """Node G: Compare verified suppliers side by side."""
    logger.info("═══ STAGE 4/5: COMPARING SUPPLIERS ═══")
    try:
        requirements = ParsedRequirements(**state["parsed_requirements"])
        discovery = DiscoveryResults(**state["discovery_results"])
        verifications = VerificationResults(**state["verification_results"])
        # Only compare suppliers that were actually verified
        verified_names = {v.supplier_name for v in verifications.verifications}
        verified_suppliers = [s for s in discovery.suppliers if s.name in verified_names]
        result = await compare_suppliers(requirements, verified_suppliers, verifications)
        logger.info("═══ COMPARISON COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.RECOMMENDING.value,
            "comparison_result": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:
        logger.error("Comparison stage failed (non-fatal): %s", str(e))
        # Non-fatal: generate an empty comparison so recommendation can still run
        from app.schemas.agent_state import ComparisonResult
        empty = ComparisonResult(
            comparisons=[],
            analysis_narrative="Comparison could not be generated. Recommendations are based on discovery and verification data only.",
        )
        return {
            **state,
            "current_stage": PipelineStage.RECOMMENDING.value,
            "comparison_result": empty.model_dump(mode="json"),
            "error": None,
        }


async def recommend_node(state: GraphState) -> GraphState:
    """Node H: Generate final recommendations."""
    logger.info("═══ STAGE 5/5: GENERATING RECOMMENDATIONS ═══")
    try:
        requirements = ParsedRequirements(**state["parsed_requirements"])
        comparison = ComparisonResult(**state["comparison_result"])
        verifications = VerificationResults(**state["verification_results"])
        result = await generate_recommendation(requirements, comparison, verifications)
        logger.info("═══ RECOMMENDATIONS COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "recommendation_result": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:
        logger.error("Stage failed: %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.FAILED.value,
            "error": f"Recommendation failed: {str(e)}\n{traceback.format_exc()}",
        }


async def outreach_node(state: GraphState) -> GraphState:
    """Node F: Auto-draft and queue outreach emails for top recommended suppliers."""
    logger.info("═══ STAGE 6/6: AUTONOMOUS OUTREACH ═══")
    try:
        from app.agents.outreach_agent import draft_outreach_emails

        requirements = ParsedRequirements(**state["parsed_requirements"])
        discovery = DiscoveryResults(**state["discovery_results"])
        recommendations = RecommendationResult(**state["recommendation_result"])
        verifications = VerificationResults(**state["verification_results"])

        # Select top recommended suppliers that have email addresses
        rec_indices = {r.supplier_index for r in recommendations.recommendations}
        selected = []
        selected_indices = []
        for rec in recommendations.recommendations[:5]:  # Top 5
            idx = rec.supplier_index
            if idx < len(discovery.suppliers):
                supplier = discovery.suppliers[idx]
                if supplier.email:  # Only suppliers with known emails
                    selected.append(supplier)
                    selected_indices.append(idx)

        if not selected:
            logger.warning("No recommended suppliers have email addresses — skipping outreach")
            return {
                **state,
                "current_stage": PipelineStage.COMPLETE.value,
                "outreach_result": {"skipped": True, "reason": "no_emails"},
                "error": None,
            }

        # Draft emails
        result = await draft_outreach_emails(selected, requirements, recommendations)

        # Mark all drafts as auto_queued (the scheduler will send them)
        for draft in result.drafts:
            draft.status = "auto_queued"

        # Build outreach state
        supplier_statuses = [
            SupplierOutreachStatus(
                supplier_name=s.name,
                supplier_index=idx,
            )
            for idx, s in zip(selected_indices, selected)
        ]

        outreach = OutreachState(
            selected_suppliers=selected_indices,
            supplier_statuses=supplier_statuses,
            draft_emails=result.drafts,
            auto_config=AutoOutreachConfig(
                mode="auto",
                auto_send_threshold=60.0,
                max_concurrent_outreach=5,
            ),
        )

        logger.info(
            "═══ OUTREACH COMPLETE: %d emails auto-queued ═══",
            len(result.drafts),
        )
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "outreach_result": outreach.model_dump(mode="json"),
            "error": None,
        }

    except Exception as e:
        logger.error("Outreach stage failed (non-fatal): %s", str(e))
        # Non-fatal: pipeline is still complete even if outreach drafting fails
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "outreach_result": {"error": str(e)},
            "error": None,
        }


# ── Conditional Edges ────────────────────────────────────────────

def should_continue(state: GraphState) -> str:
    """Route based on current stage — stop on failure."""
    if state.get("error"):
        return "end"
    stage = state.get("current_stage", "")
    stage_to_next = {
        PipelineStage.DISCOVERING.value: "discover",
        PipelineStage.VERIFYING.value: "verify",
        PipelineStage.COMPARING.value: "compare",
        PipelineStage.RECOMMENDING.value: "recommend",
        PipelineStage.OUTREACHING.value: "outreach",
        PipelineStage.COMPLETE.value: "end",
        PipelineStage.FAILED.value: "end",
    }
    return stage_to_next.get(stage, "end")


def should_continue_after_recommend(state: GraphState) -> str:
    """After recommend: route to outreach if auto_outreach_enabled, else end."""
    if state.get("error"):
        return "end"
    if state.get("auto_outreach_enabled"):
        return "outreach"
    return "end"


# ── Build the Graph ──────────────────────────────────────────────

def build_pipeline_graph():
    """
    Build and compile the LangGraph procurement pipeline.

    Returns a compiled graph that can be invoked with:
        result = await graph.ainvoke({"raw_description": "...", "current_stage": "parsing"})
    """
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(GraphState)

        # Add nodes
        graph.add_node("parse", parse_node)
        graph.add_node("discover", discover_node)
        graph.add_node("verify", verify_node)
        graph.add_node("compare", compare_node)
        graph.add_node("recommend", recommend_node)
        graph.add_node("outreach", outreach_node)

        # Set entry point
        graph.set_entry_point("parse")

        # Add conditional edges
        graph.add_conditional_edges("parse", should_continue, {
            "discover": "discover",
            "end": END,
        })
        graph.add_conditional_edges("discover", should_continue, {
            "verify": "verify",
            "end": END,
        })
        graph.add_conditional_edges("verify", should_continue, {
            "compare": "compare",
            "end": END,
        })
        graph.add_conditional_edges("compare", should_continue, {
            "recommend": "recommend",
            "end": END,
        })
        # After recommend: conditionally route to outreach or end
        graph.add_conditional_edges("recommend", should_continue_after_recommend, {
            "outreach": "outreach",
            "end": END,
        })
        graph.add_edge("outreach", END)

        return graph.compile()

    except ImportError:
        # Fallback: run pipeline sequentially without LangGraph
        return None


async def run_pipeline_sequential(
    raw_description: str,
    auto_outreach: bool = False,
) -> GraphState:
    """
    Fallback: run the pipeline sequentially without LangGraph.
    Used when LangGraph is not installed or for simpler deployments.
    """
    logger.info("Running pipeline in sequential mode (LangGraph not available)")
    state: GraphState = {
        "raw_description": raw_description,
        "current_stage": PipelineStage.PARSING.value,
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "outreach_result": None,
        "progress_events": [],
        "user_answers": None,
        "auto_outreach_enabled": auto_outreach,
    }

    steps = [parse_node, discover_node, verify_node, compare_node, recommend_node]

    for step in steps:
        state = await step(state)
        if state.get("error"):
            break

    # Run outreach if enabled and pipeline succeeded
    if not state.get("error") and auto_outreach:
        state = await outreach_node(state)

    return state


async def rerun_from_stage(
    project_state: dict,
    from_stage: str,
    modified_state: dict | None = None,
) -> GraphState:
    """Re-run the pipeline from a specific stage forward.

    Used by the chat agent to refresh results after parameter changes
    (e.g., adjusted scoring weights, new search queries).

    Args:
        project_state: The full project dict from in-memory store.
        from_stage: Stage to start from — "discover", "verify", "compare", "recommend".
        modified_state: Optional overrides to inject into the state before re-running.

    Returns:
        Updated GraphState with new results from the re-run stages.
    """
    logger.info("Re-running pipeline from stage: %s", from_stage)

    # Reconstruct GraphState from existing project data
    state: GraphState = {
        "raw_description": project_state.get("product_description", ""),
        "current_stage": from_stage,
        "error": None,
        "parsed_requirements": project_state.get("parsed_requirements"),
        "discovery_results": project_state.get("discovery_results"),
        "verification_results": project_state.get("verification_results"),
        "comparison_result": project_state.get("comparison_result"),
        "recommendation_result": project_state.get("recommendation_result"),
        "progress_events": project_state.get("progress_events", []),
        "user_answers": project_state.get("user_answers"),
    }

    # Apply any overrides
    if modified_state:
        state.update(modified_state)

    # Determine which stages to run
    stage_order = ["discover", "verify", "compare", "recommend"]
    node_map = {
        "discover": discover_node,
        "verify": verify_node,
        "compare": compare_node,
        "recommend": recommend_node,
    }

    start_idx = stage_order.index(from_stage) if from_stage in stage_order else 0
    stages_to_run = stage_order[start_idx:]

    for stage_name in stages_to_run:
        step_fn = node_map[stage_name]
        logger.info("Re-running stage: %s", stage_name)
        state = await step_fn(state)
        if state.get("error"):
            logger.error("Re-run stopped at %s: %s", stage_name, state["error"][:200])
            break

    return state


async def run_pipeline(
    raw_description: str,
    auto_outreach: bool = False,
) -> GraphState:
    """
    Run the full procurement pipeline.

    Tries LangGraph first, falls back to sequential execution.

    Args:
        raw_description: Natural-language product/supplier requirements.
        auto_outreach: If True, auto-draft and queue outreach emails after recommendations.
    """
    logger.info("Pipeline started for: '%s' (auto_outreach=%s)", raw_description[:80], auto_outreach)
    graph = build_pipeline_graph()

    initial_state: GraphState = {
        "raw_description": raw_description,
        "current_stage": PipelineStage.PARSING.value,
        "error": None,
        "parsed_requirements": None,
        "discovery_results": None,
        "verification_results": None,
        "comparison_result": None,
        "recommendation_result": None,
        "outreach_result": None,
        "progress_events": [],
        "user_answers": None,
        "auto_outreach_enabled": auto_outreach,
    }

    if graph is not None:
        logger.info("Using LangGraph orchestrator")
        try:
            result = await graph.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.info("Falling back to sequential pipeline")

    return await run_pipeline_sequential(raw_description, auto_outreach=auto_outreach)
