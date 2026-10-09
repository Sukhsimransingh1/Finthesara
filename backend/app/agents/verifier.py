from __future__ import annotations

from decimal import Decimal

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    VerificationAgentOutput,
    VerificationResult,
    VerificationStatus,
)
from app.agents.state import ResearchState


class VerificationAgent:
    """
    Verify that research outputs are supported by evidence and
    that the workflow has enough information to produce a report.
    """

    name = "verification_agent"

    def run(self, state: ResearchState) -> VerificationAgentOutput:
        evidence = state.get("evidence", [])
        calculations = state.get("calculations", [])
        financial_results = state.get("financial_results", [])

        issues: list[str] = []
        unsupported_claims: list[str] = []
        contradictions = state.get("contradictions", [])

        if not evidence:
            issues.append(
                "No supporting evidence was retrieved."
            )

        if not financial_results:
            issues.append(
                "No financial analysis result was produced."
            )

        verified_claims: list[str] = []

        if financial_results:
            verified_claims.append(
                "Financial analysis produced structured results."
            )

        if evidence:
            verified_claims.append(
                "Research produced traceable evidence."
            )

        if not evidence:
            unsupported_claims.append(
                "Research findings cannot be supported without evidence."
            )

        if contradictions:
            status = VerificationStatus.CONTRADICTION
        elif issues:
            status = VerificationStatus.INSUFFICIENT_EVIDENCE
        else:
            status = VerificationStatus.PASS

        if status == VerificationStatus.PASS:
            confidence = Decimal("0.90")
        elif status == VerificationStatus.CONTRADICTION:
            confidence = Decimal("0.40")
        else:
            confidence = Decimal("0.25")

        result = VerificationResult(
            status=status,
            verified_claims=verified_claims,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            issues=issues,
            confidence=confidence,
        )

        agent_result = AgentResult(
            agent_name=self.name,
            status=(
                AgentStatus.COMPLETED
                if status == VerificationStatus.PASS
                else AgentStatus.FAILED
            ),
            summary=f"Verification status: {status.value}.",
            data={
                "calculation_count": len(calculations),
                "evidence_count": len(evidence),
                "status": status.value,
            },
            errors=issues,
        )

        return VerificationAgentOutput(
            result=result,
            agent_result=agent_result,
        )