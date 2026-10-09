from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError


class LLMOutputError(RuntimeError):
    """Raised when an LLM response cannot be parsed safely."""


def parse_json_object(content: str) -> dict[str, object]:
    """Parse an LLM response containing a JSON object."""

    text = content.strip()

    if not text:
        raise LLMOutputError("LLM returned an empty response.")

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(
            "LLM response was not valid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMOutputError(
            "LLM response must be a JSON object."
        )

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