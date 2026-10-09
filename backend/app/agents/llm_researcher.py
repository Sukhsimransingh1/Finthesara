from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    ResearchAgentOutput,
)
from app.agents.state import ResearchState
from app.llm.prompts import RESEARCH_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import ResearchLLMOutput
from app.retrieval.schemas import EvidencePackage, RetrievalFilters


class HybridRetrieverProtocol(Protocol):
    def search(
        self,
        query: str,
        *,
        project_id: UUID,
        top_k: int = 10,
        retrieval_k: int = 20,
        similarity_threshold: float = 0.0,
        filters: RetrievalFilters | None = None,
    ) -> EvidencePackage:
        ...


class LLMResearchAgent:
    """Retrieve evidence and reason over it with an LLM."""

    name = "llm_research_agent"

    def __init__(
        self,
        *,
        llm: StructuredLLM,
        retriever: HybridRetrieverProtocol,
    ) -> None:
        self.llm = llm
        self.retriever = retriever

    def run(self, state: ResearchState) -> dict[str, object]:
        project_id = state.get("project_id")

        if not project_id:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary="Research requires a project ID.",
                        errors=["project_id is missing."],
                    )
                ],
            }

        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary="Research requires a valid project ID.",
                        errors=["project_id is not a valid UUID."],
                    )
                ],
            }

        evidence_package = self.retriever.search(
            state["normalized_question"],
            project_id=project_uuid,
            top_k=10,
            retrieval_k=20,
        )

        evidence_context = json.dumps(
            [
                {
                    "evidence_id": item.evidence_id,
                    "company": item.company,
                    "document_type": item.document_type,
                    "publication_date": (
                        item.publication_date.isoformat()
                        if item.publication_date
                        else None
                    ),
                    "content": item.content,
                    "source_url": item.source_url,
                }
                for item in evidence_package.evidence
            ],
            indent=2,
        )

        financial_context = json.dumps(
            state.get("financial_results", []),
            default=str,
            indent=2,
        )

        prompt = f"""
Research question:
{state["normalized_question"]}

Retrieved evidence:
{evidence_context}

Deterministic financial analysis:
{financial_context}

Reason only over the supplied material and produce grounded research findings.
"""

        parsed, _ = self.llm.invoke_structured(
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=ResearchLLMOutput,
        )

        evidence_ids = [
            evidence.evidence_id
            for evidence in evidence_package.evidence
        ]

        agent_result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary="Completed evidence-grounded LLM research.",
            data={
                "finding_count": len(parsed.findings),
                "claim_count": len(parsed.claims),
                "evidence_count": len(evidence_ids),
            },
            evidence_ids=evidence_ids,
        )

        output = ResearchAgentOutput(
            findings=parsed.findings,
            evidence_ids=evidence_ids,
            source_urls=parsed.source_urls,
            contradictions=parsed.contradictions,
        )

        return {
            "evidence": evidence_package.evidence,
            "contradictions": parsed.contradictions,
            "agent_results": [agent_result],
            "research_output": output.model_dump(),
        }