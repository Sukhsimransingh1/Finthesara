
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError


class LLMOutputError(RuntimeError):
    """Raised when an LLM response cannot be parsed safely."""


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a complete JSON object from an LLM response."""

    text = content.strip()

    if not text:
        raise LLMOutputError("LLM returned an empty response.")

    # Remove a Markdown JSON code fence when present.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.I)
        text = re.sub(r"\s*```\s*$", "", text, count=1)
        text = text.strip()

    # First, try parsing the complete response.
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as original_error:
        # Some models wrap JSON in introductory or trailing text.
        # Locate a JSON object and accept it only if it parses completely.
        decoder = json.JSONDecoder()
        start = text.find("{")

        while start != -1:
            try:
                parsed, _ = decoder.raw_decode(text[start:])
                break
            except json.JSONDecodeError:
                start = text.find("{", start + 1)
        else:
            raise LLMOutputError(
                "LLM response was not valid complete JSON. "
                f"Parser detail: {original_error.msg} "
                f"(line {original_error.lineno}, "
                f"column {original_error.colno}). "
                "The response may be truncated."
            ) from original_error

    if not isinstance(parsed, dict):
        raise LLMOutputError("LLM response must be a JSON object.")

    return parsed


def parse_pydantic[T: BaseModel](
    content: str,
    schema: type[T],
) -> T:
    """Parse an LLM JSON response into a Pydantic model."""

    payload = parse_json_object(content)

    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise LLMOutputError(
            f"LLM response failed schema validation: {exc}"
        ) from exc
