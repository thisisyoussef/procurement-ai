"""LangChain model bootstrap and structured invocation utilities."""

from __future__ import annotations

from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from .config import SuiteSettings

try:
    from langchain_anthropic import ChatAnthropic
except Exception:  # noqa: BLE001
    ChatAnthropic = None  # type: ignore[assignment]


T = TypeVar("T", bound=BaseModel)


def build_chat_model(settings: SuiteSettings) -> BaseChatModel | None:
    """Build the configured chat model, or return None when disabled/unavailable."""
    if not settings.llm_enabled:
        return None
    if not settings.anthropic_api_key:
        return None
    if ChatAnthropic is None:
        return None

    return ChatAnthropic(
        model=settings.llm_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.1,
        max_tokens=4096,
    )


async def invoke_structured(
    llm: BaseChatModel | None,
    *,
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
) -> T | None:
    """Run a structured LangChain prompt; return None on failure."""
    if llm is None:
        return None

    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            (
                "human",
                "{user_prompt}\n\nReturn valid JSON only.\n{format_instructions}",
            ),
        ]
    )
    chain = prompt | llm | parser

    try:
        return await chain.ainvoke(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception:  # noqa: BLE001
        return None

