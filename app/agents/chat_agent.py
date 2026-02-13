"""Chat agent — conversational AI advisor with access to full project state.

Unlike pipeline agents, this is streaming and action-aware. It can trigger
re-scoring, re-discovery, outreach drafting, and preference adjustments.
"""

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.llm_gateway import call_llm_stream
from app.schemas.agent_state import ChatAction

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "chat.md").read_text()


def _build_context_summary(project_state: dict) -> str:
    """Build a compact context string from the project state.

    Strips raw_data and other bulky fields to fit within ~4K tokens.
    """
    parts: list[str] = []

    # Requirements
    reqs = project_state.get("parsed_requirements")
    if reqs:
        parts.append("## Parsed Requirements")
        for key in [
            "product_type", "material", "dimensions", "quantity",
            "customization", "delivery_location", "deadline",
            "certifications_needed", "budget_range",
        ]:
            val = reqs.get(key)
            if val:
                parts.append(f"- {key}: {val}")

    # Discovered suppliers (compact)
    disc = project_state.get("discovery_results")
    if disc:
        suppliers = disc.get("suppliers", [])
        parts.append(f"\n## Discovered Suppliers ({len(suppliers)} found)")
        for i, s in enumerate(suppliers[:50]):
            line = f"{i}. **{s['name']}**"
            if s.get("city"):
                line += f" — {s['city']}"
            if s.get("country"):
                line += f", {s['country']}"
            if s.get("google_rating"):
                line += f" | Rating: {s['google_rating']}"
            if s.get("relevance_score"):
                line += f" | Relevance: {s['relevance_score']:.0f}"
            if s.get("estimated_shipping_cost"):
                line += f" | Shipping: {s['estimated_shipping_cost']}"
            if s.get("is_intermediary"):
                line += " | [INTERMEDIARY]"
            parts.append(line)
        if len(suppliers) > 50:
            parts.append(f"... and {len(suppliers) - 50} more suppliers")

    # Verifications (compact)
    verif = project_state.get("verification_results")
    if verif:
        parts.append("\n## Verification Results")
        for v in verif.get("verifications", []):
            parts.append(
                f"- {v['supplier_name']}: score={v['composite_score']:.0f}, "
                f"risk={v['risk_level']}, rec={v['recommendation']}"
            )

    # Comparison
    comp = project_state.get("comparison_result")
    if comp:
        parts.append("\n## Comparison")
        for c in comp.get("comparisons", []):
            line = (
                f"- {c['supplier_name']}: overall={c['overall_score']:.0f}, "
                f"price={c.get('estimated_unit_price', 'N/A')}, "
                f"MOQ={c.get('moq', 'N/A')}, lead={c.get('lead_time', 'N/A')}"
            )
            if c.get("estimated_shipping_cost"):
                line += f", shipping={c['estimated_shipping_cost']}"
            if c.get("estimated_landed_cost"):
                line += f", landed={c['estimated_landed_cost']}"
            parts.append(line)
        if comp.get("analysis_narrative"):
            parts.append(f"\nAnalysis: {comp['analysis_narrative'][:1000]}")
        if comp.get("best_value"):
            parts.append(f"Best value: {comp['best_value']}")
        if comp.get("best_quality"):
            parts.append(f"Best quality: {comp['best_quality']}")
        if comp.get("best_speed"):
            parts.append(f"Best speed: {comp['best_speed']}")

    # Recommendations
    rec = project_state.get("recommendation_result")
    if rec:
        parts.append("\n## Recommendations")
        if rec.get("executive_summary"):
            parts.append(rec["executive_summary"])
        for r in rec.get("recommendations", []):
            parts.append(
                f"#{r['rank']} {r['supplier_name']} — score={r['overall_score']:.0f}, "
                f"confidence={r['confidence']}, best_for={r['best_for']}\n"
                f"   {r['reasoning']}"
            )

    return "\n".join(parts)


def _build_messages(
    user_message: str,
    conversation_history: list[dict],
    context_summary: str,
) -> list[dict]:
    """Build the messages list for the LLM call."""
    messages: list[dict] = []

    # First message includes the context
    if conversation_history:
        # Inject context as the first user message if this is a continuation
        messages.append({
            "role": "user",
            "content": f"Here is the current project analysis:\n\n{context_summary}\n\n---\n\n{conversation_history[0]['content']}",
        })
        # Add the rest of the history
        for msg in conversation_history[1:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        # Add the new user message
        messages.append({"role": "user", "content": user_message})
    else:
        # First message in the conversation
        messages.append({
            "role": "user",
            "content": f"Here is the current project analysis:\n\n{context_summary}\n\n---\n\n{user_message}",
        })

    return messages


def parse_action_from_response(full_text: str) -> tuple[str, ChatAction | None]:
    """Extract an ACTION block from the response text if present.

    Returns (clean_text, action_or_none).
    """
    action_start = full_text.find("<ACTION>")
    if action_start == -1:
        return full_text.strip(), None

    action_end = full_text.find("</ACTION>")
    if action_end == -1:
        return full_text.strip(), None

    clean_text = (full_text[:action_start] + full_text[action_end + 9:]).strip()
    action_json = full_text[action_start + 8:action_end].strip()

    try:
        data = json.loads(action_json)
        action = ChatAction(
            action_type=data.get("action_type", "none"),
            parameters=data.get("parameters", {}),
        )
        logger.info("Parsed chat action: %s", action.action_type)
        return clean_text, action
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to parse action JSON: %s", e)
        return clean_text, None


async def chat_with_context(
    user_message: str,
    conversation_history: list[dict],
    project_state: dict,
) -> AsyncGenerator[str, None]:
    """Stream a chat response with full project context.

    Yields text chunks as they arrive from the LLM.
    The caller is responsible for collecting the full text and calling
    parse_action_from_response() afterward.
    """
    context_summary = _build_context_summary(project_state)
    messages = _build_messages(user_message, conversation_history, context_summary)

    logger.info("Chat agent streaming response for: %s", user_message[:80])

    async for chunk in call_llm_stream(
        messages=messages,
        system=SYSTEM_PROMPT,
        model=settings.model_balanced,
        max_tokens=3000,
        temperature=0.3,
    ):
        yield chunk
