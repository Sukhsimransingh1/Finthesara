from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.config import get_settings
from app.llm.parser import parse_pydantic
from app.llm.schemas import LLMResponse, LLMUsage


class GroqLLMClient:
    """Typed wrapper around the Groq chat model."""

    def __init__(
        self,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        api_key = settings.llm_api_key

        if api_key is None:
            raise RuntimeError("LLM_API_KEY is not configured.")

        self.model_name = model or settings.llm_model

        self.llm = ChatGroq(
            model=self.model_name,
            api_key=api_key,
            temperature=temperature,
            max_retries=max_retries,
        )

    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """Send a normal text request to the Groq model."""

        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = self.llm.invoke(messages)

        return LLMResponse(
            content=self._extract_content(response.content),
            model=self.model_name,
            usage=self._extract_usage(response),
            finish_reason=self._extract_finish_reason(response),
        )

    def invoke_structured[T: BaseModel](
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> tuple[T, LLMResponse]:
        """Invoke the LLM and parse the response into a Pydantic model."""

        response = self.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        parsed = parse_pydantic(
            response.content,
            schema,
        )

        return parsed, response

    @staticmethod
    def _extract_content(content: Any) -> str:
        """Normalize LangChain message content into plain text."""

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []

            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue

                if isinstance(item, dict):
                    text_value = item.get("text")

                    if isinstance(text_value, str):
                        parts.append(text_value)

            if parts:
                return "".join(parts)

        return str(content)

    @staticmethod
    def _extract_usage(response: Any) -> LLMUsage:
        """Extract token usage from a LangChain response."""

        usage_metadata = getattr(
            response,
            "usage_metadata",
            None,
        )

        if not isinstance(usage_metadata, dict):
            return LLMUsage()

        prompt_tokens = usage_metadata.get(
            "input_tokens",
            usage_metadata.get("prompt_tokens", 0),
        )

        completion_tokens = usage_metadata.get(
            "output_tokens",
            usage_metadata.get("completion_tokens", 0),
        )

        total_tokens = usage_metadata.get(
            "total_tokens",
            0,
        )

        return LLMUsage(
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
            total_tokens=int(total_tokens or 0),
        )

    @staticmethod
    def _extract_finish_reason(
        response: Any,
    ) -> str | None:
        """Extract the provider finish reason when available."""

        response_metadata = getattr(
            response,
            "response_metadata",
            None,
        )

        if not isinstance(response_metadata, dict):
            return None

        finish_reason = response_metadata.get("finish_reason")

        if finish_reason is None:
            return None

        return str(finish_reason)