"""LLM gateway for automotive agents — wraps Anthropic Claude API."""

import logging
from typing import Any

import anthropic

from app.core.config import get_settings
from automotive.core.config import MODEL_TIER_BALANCED, MODEL_TIER_CHEAP

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def call_llm(
    *,
    system: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    tools: list[dict] | None = None,
    tool_choice: dict | None = None,
) -> anthropic.types.Message:
    """Call Claude with the given system prompt and messages."""
    client = get_anthropic_client()
    model = model or MODEL_TIER_BALANCED

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    logger.info("Calling %s (tokens=%d)", model, max_tokens)
    response = await client.messages.create(**kwargs)
    logger.info(
        "Response: %d input tokens, %d output tokens",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return response


async def call_llm_structured(
    *,
    system: str,
    messages: list[dict[str, str]],
    output_schema: dict,
    model: str | None = None,
    max_tokens: int = 4096,
) -> dict:
    """Call Claude with structured output via tool use pattern."""
    client = get_anthropic_client()
    model = model or MODEL_TIER_BALANCED

    tool_def = {
        "name": "structured_output",
        "description": "Return the structured output matching the required schema.",
        "input_schema": output_schema,
    }

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0.0,
        system=system,
        messages=messages,
        tools=[tool_def],
        tool_choice={"type": "tool", "name": "structured_output"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "structured_output":
            return block.input

    raise ValueError("LLM did not return structured output")


async def call_haiku(
    *,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    **kwargs,
) -> anthropic.types.Message:
    """Convenience wrapper for cheap Haiku calls."""
    return await call_llm(
        system=system,
        messages=messages,
        model=MODEL_TIER_CHEAP,
        max_tokens=max_tokens,
        **kwargs,
    )


async def call_sonnet(
    *,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 4096,
    **kwargs,
) -> anthropic.types.Message:
    """Convenience wrapper for Sonnet calls."""
    return await call_llm(
        system=system,
        messages=messages,
        model=MODEL_TIER_BALANCED,
        max_tokens=max_tokens,
        **kwargs,
    )
