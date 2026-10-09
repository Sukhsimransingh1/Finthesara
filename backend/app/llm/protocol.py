from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.llm.schemas import LLMResponse


class StructuredLLM(Protocol):
    """Minimal interface required by LLM-powered agents."""

    def invoke_structured[T: BaseModel](
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> tuple[T, LLMResponse]:
        ...