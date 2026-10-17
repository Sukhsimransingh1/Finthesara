
from __future__ import annotations

import json
from typing import Any

from app.agents.schemas import Claim, SynthesisOutput
from app.agents.state import ResearchState
from app.llm.prompts import SYNTHESIS_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import SynthesisLLMOutput

MAX_SECTION_CHARS = 2500
MAX_EVIDENCE_ITEMS = 4
MAX_EVIDENCE_CHARS = 650


def _plain(value: Any) -> Any:
    """Convert values into JSON-serializable data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _compact_json(value: Any, limit: int = MAX_SECTION_CHARS) -> str:
    serialized = json.dumps(
        _plain(value),
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    if len(serialized) <= limit:
        return serialized
    return serialized[:limit] + "... [truncated]"


def _short_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


class LLMSynthesisAgent:
    """Generate a compact, evidence-grounded final research report."""

    name = "llm_synthesis_agent"

    def __init__(self, *, llm: StructuredLLM) -> None:
        self.llm = llm

    def run(self, state: ResearchState) -> dict[str, object]:
        question = str(
            state.get("normalized_question")
            or state.get("original_question")
            or ""
        ).strip()

        research_output_raw = state.get("research_output")
        research_output: dict[str, Any] = (
            research_output_raw
            if isinstance(research_output_raw, dict)
            else {}
        )

        evidence_context: list[dict[str, Any]] = []
        for item in state.get("evidence", [])[:MAX_EVIDENCE_ITEMS]:
            publication_date = (
                item.publication_date.isoformat()
                if item.publication_date is not None
                else None
            )

            evidence_context.append(
                {
                    "evidence_id": str(item.evidence_id),
                    "company": item.company,
                    "document_type": item.document_type,
                    "publication_date": publication_date,
                    "content": _short_text(
                        item.content,
                        MAX_EVIDENCE_CHARS,
                    ),
                    "source_url": item.source_url,
                }
            )

        research_context = {
            "findings": research_output.get("findings", [])[:6],
            "claims": research_output.get("claims", [])[:6],
            "limitations": research_output.get("limitations", [])[:6],
            "evidence_ids": research_output.get("evidence_ids", [])[:8],
            "source_urls": research_output.get("source_urls", [])[:6],
        }

        financial_results = state.get("financial_results", [])[:3]
        calculations = state.get("calculations", [])[:5]
        financial_evidence = state.get("financial_evidence", [])[:3]
        contradictions = state.get("contradictions", [])[:3]

        verification = state.get("verification_result")
        if verification is not None:
            verification = _plain(verification)

        prompt = f"""
Research question:
{_short_text(question, 800)}

Research findings and limitations:
{_compact_json(research_context, 1800)}

Retrieved evidence:
{_compact_json(evidence_context, 3000)}

Financial analysis:
{_compact_json(financial_results, 1200)}

Calculations:
{_compact_json(calculations, 1500)}

Structured financial source evidence:
{_compact_json(financial_evidence, 1200)}

Verification result:
{_compact_json(verification, 1000)}

Contradictions:
{_compact_json(contradictions, 600)}

Report requirements:
- Answer the research question directly.
- Use only the supplied evidence and calculations.
- Cite evidence IDs beside claims they support.
- Never invent financial values, fiscal years, sources, or URLs.
- Preserve reported units and fiscal-year labels.
- Clearly identify missing data; never treat missing values as zero.
- Distinguish source-reported figures from calculated metrics.
- If evidence is insufficient, explain the limitation concisely.
"""

        parsed, _ = self.llm.invoke_structured(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=SynthesisLLMOutput,
        )

        claims = [
            Claim(
                claim_id=claim.claim_id,
                statement=claim.statement,
                evidence_ids=claim.evidence_ids,
                calculation_ids=claim.calculation_ids,
            )
            for claim in parsed.claims
        ]

        output = SynthesisOutput(
            report=parsed.report,
            claims=claims,
        )

        return {
            "draft_report": output.report,
            "claims": claims,
            "status": "synthesized",
        }
