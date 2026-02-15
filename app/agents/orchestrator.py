"""LangGraph orchestrator — adaptive procurement pipeline with checkpoint steering.

Default pipeline:
parse -> discover -> verify -> compare -> recommend -> (optional outreach)

When checkpoints are enabled:
parse -> checkpoint_1 -> discover -> checkpoint_2 -> verify -> checkpoint_3 ->
compare -> checkpoint_4 -> recommend -> checkpoint_5 -> (optional outreach)
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Any, TypedDict

from app.agents.comparison_agent import compare_suppliers
from app.agents.recommendation_agent import generate_recommendation
from app.agents.requirements_parser import parse_requirements
from app.agents.supplier_discovery import discover_suppliers as legacy_discover_suppliers
from app.agents.supplier_verifier import verify_suppliers
from app.core.config import get_settings
from app.core.progress import emit_progress
from app.schemas.agent_state import (
    AutoOutreachConfig,
    CheckpointType,
    ComparisonResult,
    DiscoveryResults,
    OutreachState,
    ParsedRequirements,
    PipelineStage,
    RecommendationResult,
    SupplierOutreachStatus,
    VerificationResults,
)
from app.schemas.buyer_context import BuyerContext
from app.schemas.user_profile import UserSourcingProfile
from app.services.buyer_context_builder import build_initial_buyer_context

logger = logging.getLogger(__name__)
settings = get_settings()


class GraphState(TypedDict, total=False):
    """State passed between graph nodes."""

    raw_description: str
    current_stage: str
    error: str | None

    parsed_requirements: dict | None
    discovery_results: dict | None
    verification_results: dict | None
    comparison_result: dict | None
    recommendation_result: dict | None
    outreach_result: dict | None

    progress_events: list[dict]
    user_answers: dict | None

    auto_outreach_enabled: bool
    user_id: str | None

    buyer_context: dict | None
    user_sourcing_profile: dict | None

    active_checkpoint: dict | None
    checkpoint_responses: dict[str, dict]
    checkpoint_auto_continue: bool
    confidence_gate_threshold: float
    gated_suppliers: list[dict]


@dataclass(frozen=True)
class _NodeCheckpoint:
    name: str
    checkpoint_type: CheckpointType


_CHECKPOINTS = {
    "checkpoint_1": _NodeCheckpoint("checkpoint_1", CheckpointType.CONFIRM_REQUIREMENTS),
    "checkpoint_2": _NodeCheckpoint("checkpoint_2", CheckpointType.REVIEW_SUPPLIERS),
    "checkpoint_3": _NodeCheckpoint("checkpoint_3", CheckpointType.SET_CONFIDENCE_GATE),
    "checkpoint_4": _NodeCheckpoint("checkpoint_4", CheckpointType.ADJUST_WEIGHTS),
    "checkpoint_5": _NodeCheckpoint("checkpoint_5", CheckpointType.OUTREACH_PREFERENCES),
}


def _load_buyer_context(state: GraphState) -> BuyerContext | None:
    raw = state.get("buyer_context")
    if not raw:
        return BuyerContext() if settings.enable_buyer_context else None
    try:
        return BuyerContext(**raw)
    except Exception:
        logger.warning("Invalid buyer_context in graph state; resetting")
        return BuyerContext() if settings.enable_buyer_context else None


def _load_user_profile(state: GraphState) -> UserSourcingProfile | None:
    raw = state.get("user_sourcing_profile")
    if not raw:
        return None
    try:
        return UserSourcingProfile(**raw)
    except Exception:
        logger.warning("Invalid user_sourcing_profile in graph state; ignoring")
        return None


async def _discover_with_strategy(
    requirements: ParsedRequirements,
    buyer_context: BuyerContext | None,
    user_profile: UserSourcingProfile | None,
) -> DiscoveryResults:
    if settings.enable_multi_team_discovery:
        try:
            from app.agents.discovery import discover_suppliers as multi_discover_suppliers

            return await multi_discover_suppliers(
                requirements,
                buyer_context=buyer_context,
                user_profile=user_profile,
            )
        except Exception:
            logger.warning("Multi-team discovery failed; falling back to legacy discovery", exc_info=True)

    return await legacy_discover_suppliers(
        requirements,
        buyer_context=buyer_context,
        user_profile=user_profile,
    )


def _expand_search_parameters(requirements: ParsedRequirements) -> ParsedRequirements:
    expanded = requirements.model_copy(deep=True)
    base_queries = list(expanded.search_queries or [])
    product = expanded.product_type or "supplier"
    expansions = [
        f"{product} OEM manufacturer",
        f"{product} certified supplier",
        f"{product} export factory",
        f"{product} wholesale producer",
    ]
    expanded.search_queries = list(dict.fromkeys(base_queries + expansions))
    expanded.minimum_supplier_count = max(expanded.minimum_supplier_count or 0, 8)
    return expanded


async def _attempt_recovery_recommendation(
    state: GraphState,
    requirements: ParsedRequirements,
    buyer_context: BuyerContext | None,
    user_profile: UserSourcingProfile | None,
) -> tuple[GraphState, RecommendationResult | None]:
    """Auto re-discovery pass used when recommendation quality is weak."""
    try:
        expanded = _expand_search_parameters(requirements)
        rediscovery = await _discover_with_strategy(expanded, buyer_context, user_profile)

        top_suppliers = sorted(
            rediscovery.suppliers,
            key=lambda s: s.relevance_score,
            reverse=True,
        )[:20]
        reverify = await verify_suppliers(
            top_suppliers,
            requirements=expanded,
            buyer_context=buyer_context,
        )

        gate = float(state.get("confidence_gate_threshold") or 30)
        score_map = {v.supplier_name: v for v in reverify.verifications}
        filtered = [
            supplier
            for supplier in rediscovery.suppliers
            if (score_map.get(supplier.name) and score_map[supplier.name].composite_score >= gate)
        ]
        recompare = await compare_suppliers(
            expanded,
            filtered or rediscovery.suppliers[:10],
            reverify,
            buyer_context=buyer_context,
            user_profile=user_profile,
        )
        rerecommend = await generate_recommendation(
            expanded,
            recompare,
            reverify,
            buyer_context=buyer_context,
            user_profile=user_profile,
        )

        next_state: GraphState = {
            **state,
            "parsed_requirements": expanded.model_dump(mode="json"),
            "discovery_results": rediscovery.model_dump(mode="json"),
            "verification_results": reverify.model_dump(mode="json"),
            "comparison_result": recompare.model_dump(mode="json"),
        }
        return next_state, rerecommend
    except Exception:
        logger.warning("Expanded re-discovery recommendation pass failed", exc_info=True)
        return state, None


async def parse_node(state: GraphState) -> GraphState:
    """Node A: Parse requirements from raw description."""
    logger.info("═══ STAGE 1/5: PARSING REQUIREMENTS ═══")
    try:
        buyer_context = _load_buyer_context(state)
        user_profile = _load_user_profile(state)

        result = await parse_requirements(
            state["raw_description"],
            buyer_context=buyer_context,
            user_profile=user_profile,
        )

        if settings.enable_buyer_context and state.get("user_id"):
            if not state.get("buyer_context"):
                try:
                    buyer_context = await build_initial_buyer_context(state["user_id"], result)
                except Exception:
                    logger.warning("Failed to build initial buyer context", exc_info=True)
                    buyer_context = buyer_context or BuyerContext()

        logger.info("═══ PARSING COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.DISCOVERING.value,
            "parsed_requirements": result.model_dump(mode="json"),
            "buyer_context": buyer_context.model_dump(mode="json") if buyer_context else state.get("buyer_context"),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
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
        buyer_context = _load_buyer_context(state)
        user_profile = _load_user_profile(state)

        result = await _discover_with_strategy(requirements, buyer_context, user_profile)

        logger.info("═══ DISCOVERY COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.VERIFYING.value,
            "discovery_results": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
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
        requirements = ParsedRequirements(**state["parsed_requirements"])
        discovery = DiscoveryResults(**state["discovery_results"])
        buyer_context = _load_buyer_context(state)

        top_suppliers = sorted(
            discovery.suppliers, key=lambda s: s.relevance_score, reverse=True
        )[:20]
        result = await verify_suppliers(
            top_suppliers,
            requirements=requirements,
            buyer_context=buyer_context,
        )

        if not result.verifications:
            logger.error("All supplier verifications failed — no results to proceed with")
            return {
                **state,
                "current_stage": PipelineStage.FAILED.value,
                "error": (
                    "Supplier verification failed: all supplier checks returned errors. "
                    "Try restarting supplier search or restart from the brief."
                ),
            }

        try:
            enriched_map = {(s.name, s.website or ""): s for s in top_suppliers}
            for i, supplier in enumerate(discovery.suppliers):
                key = (supplier.name, supplier.website or "")
                enriched = enriched_map.get(key)
                if enriched:
                    if enriched.email and not supplier.email:
                        discovery.suppliers[i].email = enriched.email
                    if enriched.phone and not supplier.phone:
                        discovery.suppliers[i].phone = enriched.phone
                    if enriched.enrichment:
                        discovery.suppliers[i].enrichment = enriched.enrichment
        except Exception as e:  # noqa: BLE001
            logger.warning("Contact merge failed (non-fatal): %s", e)

        logger.info(
            "═══ VERIFICATION COMPLETE (%d/%d suppliers verified) ═══",
            len(result.verifications),
            len(top_suppliers),
        )
        return {
            **state,
            "current_stage": PipelineStage.COMPARING.value,
            "discovery_results": discovery.model_dump(mode="json"),
            "verification_results": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Stage failed: %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.FAILED.value,
            "error": f"Supplier verification failed: {str(e)}\n{traceback.format_exc()}",
        }


async def compare_node(state: GraphState) -> GraphState:
    """Node D: Compare verified suppliers side by side."""
    logger.info("═══ STAGE 4/5: COMPARING SUPPLIERS ═══")
    try:
        requirements = ParsedRequirements(**state["parsed_requirements"])
        discovery = DiscoveryResults(**state["discovery_results"])
        verifications = VerificationResults(**state["verification_results"])
        buyer_context = _load_buyer_context(state)
        user_profile = _load_user_profile(state)

        gate = float(state.get("confidence_gate_threshold") or 30)
        verification_map = {v.supplier_name: v for v in verifications.verifications}

        verified_suppliers = []
        gated_suppliers: list[dict[str, Any]] = []
        for supplier in discovery.suppliers:
            verification = verification_map.get(supplier.name)
            if not verification:
                continue
            if verification.composite_score >= gate:
                verified_suppliers.append(supplier)
            else:
                gated_suppliers.append(
                    {
                        "name": supplier.name,
                        "score": verification.composite_score,
                        "reason": "below_confidence_gate",
                    }
                )

        if not verified_suppliers:
            verified_suppliers = discovery.suppliers[:10]

        result = await compare_suppliers(
            requirements,
            verified_suppliers,
            verifications,
            buyer_context=buyer_context,
            user_profile=user_profile,
        )
        logger.info("═══ COMPARISON COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.RECOMMENDING.value,
            "comparison_result": result.model_dump(mode="json"),
            "gated_suppliers": gated_suppliers,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Comparison stage failed (non-fatal): %s", str(e))
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
    """Node E: Generate final recommendations."""
    logger.info("═══ STAGE 5/5: GENERATING RECOMMENDATIONS ═══")
    try:
        requirements = ParsedRequirements(**state["parsed_requirements"])
        comparison = ComparisonResult(**state["comparison_result"])
        verifications = VerificationResults(**state["verification_results"])
        buyer_context = _load_buyer_context(state)
        user_profile = _load_user_profile(state)

        result = await generate_recommendation(
            requirements,
            comparison,
            verifications,
            buyer_context=buyer_context,
            user_profile=user_profile,
        )

        lanes_covered = {
            rec.lane
            for rec in result.recommendations
            if rec.lane in {"best_overall", "best_low_risk", "best_speed_to_order"}
        }
        avg_conf = (
            sum(rec.overall_score for rec in result.recommendations) / len(result.recommendations)
            if result.recommendations
            else 0.0
        )

        if settings.enable_multi_team_discovery and (
            len(lanes_covered) < 2
            or avg_conf < 50
            or len(result.recommendations) < 3
        ):
            logger.info("Low recommendation quality detected — triggering expanded search loop")
            next_state, recovered = await _attempt_recovery_recommendation(
                state,
                requirements,
                buyer_context,
                user_profile,
            )
            if recovered and len(recovered.recommendations) >= len(result.recommendations):
                result = recovered
                state = next_state
                result.caveats.append("Expanded search was automatically applied to improve lane coverage.")
            else:
                result.caveats.append(
                    "Recommendation quality was low. Consider restarting with expanded search terms."
                )

        logger.info("═══ RECOMMENDATIONS COMPLETE ═══")
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "recommendation_result": result.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
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

        rec_indices = {r.supplier_index for r in recommendations.recommendations}
        selected = []
        selected_indices = []
        for rec in recommendations.recommendations[:5]:
            idx = rec.supplier_index
            if idx in rec_indices and idx < len(discovery.suppliers):
                supplier = discovery.suppliers[idx]
                if supplier.email:
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

        business_profile = None
        owner_user_id = state.get("user_id")
        if owner_user_id:
            try:
                from app.api.v1.outreach import _fetch_business_profile

                business_profile = await _fetch_business_profile(owner_user_id)
            except Exception:
                logger.warning("Could not fetch business profile for outreach", exc_info=True)

        result = await draft_outreach_emails(
            selected,
            requirements,
            recommendations,
            business_profile=business_profile,
            buyer_context=_load_buyer_context(state),
            user_profile=_load_user_profile(state),
        )

        for draft in result.drafts:
            draft.status = "auto_queued"

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

        logger.info("═══ OUTREACH COMPLETE: %d emails auto-queued ═══", len(result.drafts))
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "outreach_result": outreach.model_dump(mode="json"),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Outreach stage failed (non-fatal): %s", str(e))
        return {
            **state,
            "current_stage": PipelineStage.COMPLETE.value,
            "outreach_result": {"error": str(e)},
            "error": None,
        }


async def checkpoint_node(state: GraphState, checkpoint_type: CheckpointType) -> GraphState:
    """Emit checkpoint event and optionally pause for steering input."""
    if not settings.enable_checkpoints:
        return {**state, "active_checkpoint": None}

    try:
        from app.agents.checkpoints import apply_checkpoint_steering, build_checkpoint_event

        checkpoint = build_checkpoint_event(checkpoint_type, state)
        emit_progress("checkpoint", checkpoint_type.value, checkpoint.summary)

        if state.get("checkpoint_auto_continue"):
            return {**state, "active_checkpoint": None}

        raw_response = (state.get("checkpoint_responses") or {}).get(checkpoint_type.value)
        if raw_response:
            updated = apply_checkpoint_steering(state, raw_response, checkpoint_type)
            updated["active_checkpoint"] = None
            return updated

        return {
            **state,
            "current_stage": PipelineStage.STEERING.value,
            "active_checkpoint": checkpoint.model_dump(mode="json"),
        }
    except Exception:
        logger.warning("Checkpoint handling failed for %s", checkpoint_type.value, exc_info=True)
        return state


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
        PipelineStage.STEERING.value: "end",
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


def _mk_checkpoint_node(checkpoint: _NodeCheckpoint):
    async def _inner(state: GraphState) -> GraphState:
        return await checkpoint_node(state, checkpoint.checkpoint_type)

    _inner.__name__ = f"{checkpoint.name}_node"
    return _inner


def build_pipeline_graph():
    """Build and compile the LangGraph procurement pipeline."""
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(GraphState)

        graph.add_node("parse", parse_node)
        graph.add_node("discover", discover_node)
        graph.add_node("verify", verify_node)
        graph.add_node("compare", compare_node)
        graph.add_node("recommend", recommend_node)
        graph.add_node("outreach", outreach_node)

        if settings.enable_checkpoints:
            graph.add_node("checkpoint_1", _mk_checkpoint_node(_CHECKPOINTS["checkpoint_1"]))
            graph.add_node("checkpoint_2", _mk_checkpoint_node(_CHECKPOINTS["checkpoint_2"]))
            graph.add_node("checkpoint_3", _mk_checkpoint_node(_CHECKPOINTS["checkpoint_3"]))
            graph.add_node("checkpoint_4", _mk_checkpoint_node(_CHECKPOINTS["checkpoint_4"]))
            graph.add_node("checkpoint_5", _mk_checkpoint_node(_CHECKPOINTS["checkpoint_5"]))

        graph.set_entry_point("parse")

        if settings.enable_checkpoints:
            graph.add_edge("parse", "checkpoint_1")
            graph.add_conditional_edges("checkpoint_1", should_continue, {"discover": "discover", "end": END})

            graph.add_edge("discover", "checkpoint_2")
            graph.add_conditional_edges("checkpoint_2", should_continue, {"verify": "verify", "end": END})

            graph.add_edge("verify", "checkpoint_3")
            graph.add_conditional_edges("checkpoint_3", should_continue, {"compare": "compare", "end": END})

            graph.add_edge("compare", "checkpoint_4")
            graph.add_conditional_edges("checkpoint_4", should_continue, {"recommend": "recommend", "end": END})

            graph.add_edge("recommend", "checkpoint_5")
            graph.add_conditional_edges("checkpoint_5", should_continue_after_recommend, {"outreach": "outreach", "end": END})
        else:
            graph.add_conditional_edges("parse", should_continue, {"discover": "discover", "end": END})
            graph.add_conditional_edges("discover", should_continue, {"verify": "verify", "end": END})
            graph.add_conditional_edges("verify", should_continue, {"compare": "compare", "end": END})
            graph.add_conditional_edges("compare", should_continue, {"recommend": "recommend", "end": END})
            graph.add_conditional_edges("recommend", should_continue_after_recommend, {"outreach": "outreach", "end": END})

        graph.add_edge("outreach", END)
        return graph.compile()
    except ImportError:
        return None


async def run_pipeline_sequential(
    raw_description: str,
    auto_outreach: bool = False,
) -> GraphState:
    """Fallback: run pipeline sequentially without LangGraph."""
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
        "checkpoint_auto_continue": True,
    }

    steps: list[Any] = [parse_node]
    if settings.enable_checkpoints:
        steps.extend(
            [
                lambda s: checkpoint_node(s, CheckpointType.CONFIRM_REQUIREMENTS),
                discover_node,
                lambda s: checkpoint_node(s, CheckpointType.REVIEW_SUPPLIERS),
                verify_node,
                lambda s: checkpoint_node(s, CheckpointType.SET_CONFIDENCE_GATE),
                compare_node,
                lambda s: checkpoint_node(s, CheckpointType.ADJUST_WEIGHTS),
                recommend_node,
                lambda s: checkpoint_node(s, CheckpointType.OUTREACH_PREFERENCES),
            ]
        )
    else:
        steps.extend([discover_node, verify_node, compare_node, recommend_node])

    for step in steps:
        state = await step(state)
        if state.get("error"):
            break

    if not state.get("error") and auto_outreach:
        state = await outreach_node(state)

    return state


async def rerun_from_stage(
    project_state: dict,
    from_stage: str,
    modified_state: dict | None = None,
) -> GraphState:
    """Re-run the pipeline from a specific stage forward."""
    logger.info("Re-running pipeline from stage: %s", from_stage)

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
        "buyer_context": project_state.get("buyer_context"),
        "user_sourcing_profile": project_state.get("user_sourcing_profile"),
        "checkpoint_auto_continue": True,
    }

    if modified_state:
        state.update(modified_state)

    stage_order = ["discover", "verify", "compare", "recommend"]
    node_map = {
        "discover": discover_node,
        "verify": verify_node,
        "compare": compare_node,
        "recommend": recommend_node,
    }

    stage_aliases = {
        "discovering": "discover",
        "verifying": "verify",
        "comparing": "compare",
        "recommending": "recommend",
    }
    from_stage_key = stage_aliases.get(from_stage, from_stage)
    if from_stage_key not in stage_order:
        from_stage_key = "discover"

    start_idx = stage_order.index(from_stage_key)
    for stage_name in stage_order[start_idx:]:
        state = await node_map[stage_name](state)
        if state.get("error"):
            logger.error("Re-run stopped at %s: %s", stage_name, str(state.get("error", ""))[:200])
            break

    return state


async def run_pipeline(
    raw_description: str,
    auto_outreach: bool = False,
) -> GraphState:
    """Run the full procurement pipeline."""
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
        "checkpoint_auto_continue": True,
    }

    if graph is not None:
        logger.info("Using LangGraph orchestrator")
        try:
            result = await graph.ainvoke(initial_state)
            return result
        except Exception:
            logger.info("Falling back to sequential pipeline", exc_info=True)

    return await run_pipeline_sequential(raw_description, auto_outreach=auto_outreach)
