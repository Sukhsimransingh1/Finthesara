
from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.config import get_settings
from app.llm.parser import LLMOutputError, parse_pydantic
from app.llm.schemas import LLMResponse, LLMUsage


class GroqLLMClient:
    """Typed wrapper around the Groq chat model."""

    def __init__(
        self,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
        max_structured_retries: int = 2,
        max_tokens: int = 8192,
    ) -> None:
        settings = get_settings()
        api_key = settings.llm_api_key

        if not api_key:
            raise RuntimeError("LLM_API_KEY is not configured.")

        if max_structured_retries < 0:
            raise ValueError(
                "max_structured_retries must be non-negative."
            )

        if max_tokens < 1:
            raise ValueError("max_tokens must be positive.")

        self.model_name = model or settings.llm_model
        self.max_structured_retries = max_structured_retries

        self.llm = ChatGroq(
            model=self.model_name,
            api_key=api_key,
            temperature=temperature,
            max_retries=max_retries,
            max_tokens=max_tokens,
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
        """Invoke the LLM and retry invalid structured responses."""

        last_error: LLMOutputError | None = None

        for attempt in range(self.max_structured_retries + 1):
            correction = ""

            if attempt > 0 and last_error is not None:
                correction = (
                    "\n\nIMPORTANT: Your previous response could not "
                    "be parsed or validated.\n"
                    f"Reason: {last_error}\n"
                    "Return one complete JSON object matching the "
                    "requested schema. Do not use Markdown fences, "
                    "comments, introductory text, or trailing text. "
                    "Ensure every JSON string is properly escaped and "
                    "every object and array is closed. Do not truncate "
                    "the response. Include all required fields and "
                    "do not invent financial facts."
                )

            response = self.invoke(
                system_prompt=(
                    system_prompt
                    + "\n\nFor structured output, return only one "
                    "complete, valid JSON object. Follow the requested "
                    "schema exactly."
                ),
                user_prompt=user_prompt + correction,
            )

            try:
                parsed = parse_pydantic(response.content, schema)
                return parsed, response
            except LLMOutputError as exc:
                last_error = exc

                finish_reason = (response.finish_reason or "").lower()
                if finish_reason in {"length", "max_tokens"}:
                    last_error = LLMOutputError(
                        "The model reached its output limit and may "
                        "have returned truncated JSON. Increase the "
                        "output budget or reduce the requested output."
                    )

        raise LLMOutputError(
            f"Structured output failed after "
            f"{self.max_structured_retries + 1} attempts: "
            f"{last_error or 'Unknown structured-output error.'}"
        ) from last_error

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
                elif isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)

            if parts:
                return "".join(parts)

        return str(content)

    @staticmethod
    def _extract_usage(response: Any) -> LLMUsage:
        """Extract token usage from a LangChain response."""

        usage_metadata = getattr(response, "usage_metadata", None)

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
        total_tokens = usage_metadata.get("total_tokens", 0)

        return LLMUsage(
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
            total_tokens=int(total_tokens or 0),
        )

    @staticmethod
    def _extract_finish_reason(response: Any) -> str | None:
        """Extract the provider finish reason when available."""

        response_metadata = getattr(response, "response_metadata", None)

        if not isinstance(response_metadata, dict):
            return None

        finish_reason = response_metadata.get("finish_reason")

        if finish_reason is None:
            return None

        return str(finish_reason)
