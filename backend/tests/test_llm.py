from __future__ import annotations

from app.llm.parser import LLMOutputError, parse_json_object, parse_pydantic
from pydantic import BaseModel, Field


class ExampleSchema(BaseModel):
    answer: str = Field(min_length=1)
    confidence: float


def test_parse_json_object() -> None:
    result = parse_json_object(
        '{"answer": "valid", "confidence": 0.9}'
    )

    assert result["answer"] == "valid"


def test_parse_json_markdown_fence() -> None:
    result = parse_json_object(
        '```json\n{"answer": "valid", "confidence": 0.9}\n```'
    )

    assert result["answer"] == "valid"


def test_parse_pydantic() -> None:
    result = parse_pydantic(
        '{"answer": "valid", "confidence": 0.9}',
        ExampleSchema,
    )

    assert result.answer == "valid"
    assert result.confidence == 0.9


def test_invalid_json_raises() -> None:
    try:
        parse_json_object("not json")
    except LLMOutputError:
        return

    raise AssertionError("Expected LLMOutputError")


def test_invalid_schema_raises() -> None:
    try:
        parse_pydantic(
            '{"answer": "", "confidence": 0.9}',
            ExampleSchema,
        )
    except LLMOutputError:
        return

    raise AssertionError("Expected LLMOutputError")