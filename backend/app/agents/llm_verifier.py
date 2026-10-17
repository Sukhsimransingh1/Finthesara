
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    VerificationAgentOutput,
    VerificationResult,
    VerificationStatus,
)
from app.agents.state import ResearchState
from app.llm.prompts import VERIFICATION_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import VerificationLLMOutput

# Conservative limits for Groq's 8,000 TPM service tier.
MAX_EVIDENCE_ITEMS = 2
MAX_FINANCIAL_ITEMS = 4
MAX_CALCULATIONS = 3
MAX_CONTRADICTIONS = 3
MAX_TEXT_CHARS = 400
MAX_PROMPT_CHARS = 3000



def _get_field(item: Any, key: str, default: Any = None) -> Any:
    """Read a field from a dictionary or an object."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _compact(value: Any, depth: int = 0) -> Any:
    """Reduce nested research state to a bounded JSON-safe representation."""
    if depth >= 5:
        return "[nested content omitted]"

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, str):
        if len(value) > MAX_TEXT_CHARS:
            return value[:MAX_TEXT_CHARS] + "... [truncated]"
        return value

    if hasattr(value, "model_dump"):
        return _compact(value.model_dump(mode="json"), depth + 1)

    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _compact(vars(value), depth + 1)

    if isinstance(value, dict):
        dict_result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 15:
                dict_result["_note"] = "Additional fields omitted."
                break
            dict_result[str(key)] = _compact(item, depth + 1)
        return dict_result

    if isinstance(value, (list, tuple)):
        list_result = [
            _compact(item, depth + 1)
            for item in value[:MAX_FINANCIAL_ITEMS]
        ]
        if len(value) > MAX_FINANCIAL_ITEMS:
            list_result.append("[additional items omitted]")
        return list_result

    return str(value)[:MAX_TEXT_CHARS]


def _json_section(value: Any) -> str:
    """Serialize compact values for the verification prompt."""
    return json.dumps(
        _compact(value),
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _evidence_for_verification(
    state: ResearchState,
) -> list[dict[str, Any]]:
    """Select a small set of traceable evidence items."""
    evidence = state.get("evidence", [])
    selected: list[dict[str, Any]] = []

    for item in evidence[:MAX_EVIDENCE_ITEMS]:
        selected.append(
            {
                "evidence_id": _get_field(item, "evidence_id"),
                "content": str(_get_field(item, "content", ""))[
                    :MAX_TEXT_CHARS
                ],
                "company": _get_field(item, "company"),
                "document_type": _get_field(item, "document_type"),
                "source_url": _get_field(item, "source_url"),
            }
        )

    return selected


def _financial_facts_for_verification(
    state: ResearchState,
) -> list[dict[str, Any]]:
    """Keep important financial values and source identifiers."""
    results = state.get("financial_results", [])
    selected: list[dict[str, Any]] = []

    for item in results[:MAX_FINANCIAL_ITEMS]:
        selected.append(
            {
                key: item[key]
                for key in (
                    "company",
                    "ticker",
                    "metric",
                    "value",
                    "unit",
                    "period",
                    "start_date",
                    "end_date",
                    "source_id",
                    "source_url",
                )
                if key in item
            }
            or _compact(item)
        )

    return selected


class LLMVerificationAgent:
    """Audit financial research claims using bounded LLM context."""

    name = "llm_verification_agent"

    def __init__(self, *, llm: StructuredLLM) -> None:
        self.llm = llm

    def run(self, state: ResearchState) -> VerificationAgentOutput:
        question = str(
            state.get("normalized_question")
            or state.get("original_question")
            or ""
        )

        financial_results = _financial_facts_for_verification(state)
        financial_evidence = state.get("financial_evidence", [])
        calculations = state.get("calculations", [])
        claims = state.get("claims", [])
        contradictions = state.get("contradictions", [])

        sections = [
            "Research question:\n" + question[:2000],
            "Financial results:\n" + _json_section(financial_results),
            "Calculations:\n"
            + _json_section(calculations[:MAX_CALCULATIONS]),
            "Retrieved document evidence:\n"
            + _json_section(_evidence_for_verification(state)),
            "Structured financial source evidence:\n"
            + _json_section(financial_evidence[:MAX_FINANCIAL_ITEMS]),
            "Research claims:\n"
            + _json_section(claims[:MAX_FINANCIAL_ITEMS]),
            "Existing contradictions:\n"
            + _json_section(contradictions[:MAX_CONTRADICTIONS]),
            (
                "Verification rules:\n"
                "- Check financial values against supplied source facts.\n"
                "- Treat a fact as source-backed only when traceable source "
                "metadata is supplied.\n"
                "- Do not claim a URL was independently opened unless a tool "
                "actually opened it.\n"
                "- Do not mark a fact unsupported solely because no uploaded "
                "document chunks were retrieved if SEC source facts exist.\n"
                "- Check arithmetic only when the required inputs are available.\n"
                "- Distinguish reported facts from interpretation.\n"
                "- Return concise findings without repeating the source payload."
            ),
        ]

        prompt = "\n\n".join(sections)

        if len(prompt) > MAX_PROMPT_CHARS:
            prompt = prompt[:MAX_PROMPT_CHARS] + (
                "\n\nAdditional context omitted due to prompt size."
            )

        parsed, _ = self.llm.invoke_structured(
            system_prompt=VERIFICATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=VerificationLLMOutput,
        )

        try:
            status = VerificationStatus(parsed.status)
        except ValueError as exc:
            raise ValueError(
                "LLM returned unsupported verification status: "
                f"{parsed.status}"
            ) from exc

        result = VerificationResult(
            status=status,
            verified_claims=parsed.verified_claims,
            failed_claims=parsed.failed_claims,
            unsupported_claims=parsed.unsupported_claims,
            contradictions=parsed.contradictions,
            issues=parsed.issues,
            confidence=Decimal(str(parsed.confidence)),
        )

        agent_status = (
            AgentStatus.COMPLETED
            if status == VerificationStatus.PASS
            else AgentStatus.FAILED
        )

        agent_result = AgentResult(
            agent_name=self.name,
            status=agent_status,
            summary=f"LLM verification completed with status {status.value}.",
            data={
                "confidence": parsed.confidence,
                "failed_claim_count": len(parsed.failed_claims),
                "unsupported_claim_count": len(parsed.unsupported_claims),
            },
        )

        return VerificationAgentOutput(
            result=result,
            agent_result=agent_result,
        )
