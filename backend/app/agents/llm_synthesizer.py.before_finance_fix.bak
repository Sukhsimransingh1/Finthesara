from __future__ import annotations

import json

from app.agents.schemas import Claim, SynthesisOutput
from app.agents.state import ResearchState
from app.llm.prompts import SYNTHESIS_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import SynthesisLLMOutput


class LLMSynthesisAgent:
    """Generate the final auditable research report."""

    name = "llm_synthesis_agent"

    def __init__(self, *, llm: StructuredLLM) -> None:
        self.llm = llm

    def run(self, state: ResearchState) -> dict[str, object]:
        prompt = f"""
Research question:
{state["normalized_question"]}

Financial analysis:
{json.dumps(
    state.get("financial_results", []),
    default=str,
    indent=2,
)}

Calculations:
{json.dumps(
    state.get("calculations", []),
    default=str,
    indent=2,
)}

Retrieved evidence:
{json.dumps(
    [
        {
            "evidence_id": item.evidence_id,
            "content": item.content,
            "company": item.company,
            "document_type": item.document_type,
            "publication_date": (
                item.publication_date.isoformat()
                if item.publication_date
                else None
            ),
            "source_url": item.source_url,
        }
        for item in state.get("evidence", [])
    ],
    default=str,
    indent=2,
)}

Verification:
{json.dumps(
    state.get("verification_result"),
    default=str,
    indent=2,
)}

Contradictions:
{json.dumps(
    state.get("contradictions", []),
    indent=2,
)}

Generate the final research report.
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