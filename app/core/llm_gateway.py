"""LLM gateway — wraps Anthropic SDK with model routing and cost tracking."""

import logging
import time
from collections.abc import AsyncGenerator

import anthropic
import httpx
from anthropic import AsyncAnthropic

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Shared async client — reuse across agents
_client: AsyncAnthropic | None = None

# Simple cost tracking
MODEL_COSTS = {
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
}
_total_input_tokens = 0
_total_output_tokens = 0
_total_cost_usd = 0.0


def get_anthropic_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        logger.info("Initializing Anthropic client")
        _client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=httpx.Timeout(120.0, connect=30.0),
        )
    return _client


async def call_llm(
    messages: list[dict],
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    tools: list[dict] | None = None,
) -> anthropic.types.Message:
    """Unified LLM call with model routing and cost tracking."""
    global _total_input_tokens, _total_output_tokens, _total_cost_usd

    client = get_anthropic_client()
    model = model or settings.model_balanced
    model_short = model.split("-20")[0] if "-20" in model else model

    # Log the call
    prompt_preview = ""
    if messages and messages[-1].get("content"):
        content = messages[-1]["content"]
        if isinstance(content, str):
            prompt_preview = content[:120].replace("\n", " ")
        elif isinstance(content, list):
            prompt_preview = str(content[0])[:120]
    logger.info("LLM call → %s | max_tokens=%d | prompt: %s...", model_short, max_tokens, prompt_preview)

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    start = time.time()
    response = await client.messages.create(**kwargs)
    elapsed = time.time() - start

    # Track tokens and cost
    input_tok = response.usage.input_tokens
    output_tok = response.usage.output_tokens
    _total_input_tokens += input_tok
    _total_output_tokens += output_tok

    costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
    call_cost = (input_tok * costs["input"] + output_tok * costs["output"]) / 1_000_000
    _total_cost_usd += call_cost

    logger.info(
        "LLM done ← %s | %.1fs | %d→%d tokens | $%.4f (session total: $%.4f)",
        model_short, elapsed, input_tok, output_tok, call_cost, _total_cost_usd,
    )

    return response


async def call_llm_structured(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Convenience: single user message in, text out."""
    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        system=system,
        max_tokens=max_tokens,
    )

    # Check for truncation — response cut off at max_tokens
    if response.stop_reason == "max_tokens":
        logger.warning(
            "⚠️ LLM response TRUNCATED (hit max_tokens=%d). "
            "Output may contain incomplete JSON. Consider increasing max_tokens.",
            max_tokens,
        )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    result = "\n".join(text_blocks)
    logger.debug("LLM response text length: %d chars", len(result))
    return result


def repair_truncated_json(text: str) -> str | None:
    """Attempt to repair truncated JSON by closing open brackets/braces.

    Useful when LLM output is cut off mid-JSON by max_tokens.
    Returns repaired JSON string or None if unrecoverable.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Remove trailing comma
    text = text.rstrip().rstrip(",")

    # Walk the string to track state
    stack: list[str] = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in ("{", "["):
            stack.append(char)
        elif char == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif char == "]" and stack and stack[-1] == "[":
            stack.pop()

    # If in unterminated string, close it
    if in_string:
        text += '"'

    # Remove trailing comma after closing string
    text = text.rstrip().rstrip(",")

    # Close any open brackets/braces in reverse order
    for opener in reversed(stack):
        text += "]" if opener == "[" else "}"

    return text


async def call_llm_stream(
    messages: list[dict],
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> AsyncGenerator[str, None]:
    """Stream LLM response token by token via Anthropic streaming API."""
    global _total_input_tokens, _total_output_tokens, _total_cost_usd

    client = get_anthropic_client()
    model = model or settings.model_balanced
    model_short = model.split("-20")[0] if "-20" in model else model

    logger.info("LLM stream → %s | max_tokens=%d", model_short, max_tokens)
    start = time.time()

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system

    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text

        # Track usage after stream completes
        response = await stream.get_final_message()
        elapsed = time.time() - start
        input_tok = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        _total_input_tokens += input_tok
        _total_output_tokens += output_tok

        costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
        call_cost = (input_tok * costs["input"] + output_tok * costs["output"]) / 1_000_000
        _total_cost_usd += call_cost

        logger.info(
            "LLM stream done ← %s | %.1fs | %d→%d tokens | $%.4f (session total: $%.4f)",
            model_short, elapsed, input_tok, output_tok, call_cost, _total_cost_usd,
        )
