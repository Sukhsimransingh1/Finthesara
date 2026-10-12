from __future__ import annotations

import json
from decimal import Decimal

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


class LLMVerificationAgent:
    """Audit financial research claims using an LLM."""

    name = "llm_verification_agent"

    def __init__(self, *, llm: StructuredLLM) -> None:
        self.llm = llm

    def run(self, state: ResearchState) -> VerificationAgentOutput:
        prompt = f"""
Research question:
{state["normalized_question"]}

Financial results:
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

Retrieved document evidence:
{json.dumps(
    [
        {
            "evidence_id": item.evidence_id,
            "content": item.content,
            "company": item.company,
            "document_type": item.document_type,
            "source_url": item.source_url,
        }
        for item in state.get("evidence", [])
    ],
    default=str,
    indent=2,
)}

Structured financial source evidence (SEC XBRL facts):
{json.dumps(
    state.get("financial_evidence", []),
    default=str,
    indent=2,
)}

Verification rules:
- Treat a structured SEC fact as source-backed only when it includes a source_id,
  source_url, metric, value, and reporting-period dates.
- Check whether the financial result agrees with its structured source fact.
- Do not claim you independently fetched or opened a source URL unless a tool did so.
- If source-backed facts are present, do not mark them unsupported merely because
  no uploaded-document/RAG chunks were retrieved.
- Do not claim an arithmetic calculation is verified unless its inputs are present
  and the formula is checked.
- Distinguish source-backed reported facts from interpretation.

Existing contradictions:
{json.dumps(
    state.get("contradictions", []),
    indent=2,
)}

Audit the research.
"""

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
            summary=(
                "LLM verification completed with status "
                f"{status.value}."
            ),
            data={
                "confidence": parsed.confidence,
                "failed_claim_count": len(parsed.failed_claims),
                "unsupported_claim_count": len(
                    parsed.unsupported_claims
                ),
            },
        )

        return VerificationAgentOutput(
            result=result,
            agent_result=agent_result,
        )