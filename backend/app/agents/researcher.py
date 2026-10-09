from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    ResearchAgentOutput,
    ResearchTaskType,
)
from app.agents.state import ResearchState
from app.retrieval.schemas import EvidencePackage, RetrievalFilters


class HybridRetrieverProtocol(Protocol):
    """Interface required by the research agent."""

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


class ResearchAgent:
    """Retrieve traceable financial evidence using hybrid RAG."""

    name = "research_agent"

    def __init__(
        self,
        *,
        retriever: HybridRetrieverProtocol,
    ) -> None:
        self.retriever = retriever

    def run(self, state: ResearchState) -> dict[str, object]:
        plan = state.get("research_plan")

        if plan is None:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary="Research could not start without a research plan.",
                        errors=["research_plan is missing from research state."],
                    )
                ],
                "status": "research_failed",
            }

        research_tasks = [
            task
            for task in plan.tasks
            if task.task_type
            in {
                ResearchTaskType.DOCUMENT_RESEARCH,
                ResearchTaskType.EXTERNAL_RESEARCH,
            }
        ]

        if not research_tasks:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.COMPLETED,
                        summary="No research retrieval task was required.",
                    )
                ],
                "status": "research_skipped",
            }

        project_id = state.get("project_id")

        if not project_id:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary="Research could not start without a project ID.",
                        errors=["project_id is missing from research state."],
                    )
                ],
                "status": "research_failed",
            }

        try:
            project_uuid = UUID(str(project_id))
        except ValueError:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary=(
                            "Research could not start because "
                            "project_id is invalid."
                        ),
                        errors=["project_id is not a valid UUID."],
                    )
                ],
                "status": "research_failed",
            }

        try:
            response = self.retriever.search(
                state["normalized_question"],
                project_id=project_uuid,
                top_k=10,
                retrieval_k=20,
            )
        except Exception as exc:
            return {
                "evidence": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary="Hybrid retrieval failed.",
                        errors=[str(exc)],
                    )
                ],
                "status": "research_failed",
            }

        evidence = response.evidence

        source_urls = [
            item.source_url
            for item in evidence
            if item.source_url is not None
        ]

        output = ResearchAgentOutput(
            findings=[
                (
                    "Hybrid retrieval returned "
                    f"{len(evidence)} evidence item(s)."
                )
            ],
            evidence_ids=[
                item.evidence_id
                for item in evidence
            ],
            source_urls=source_urls,
        )

        agent_result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary="Completed hybrid financial document retrieval.",
            data={
                "evidence_count": len(evidence),
                "retrieval_methods": sorted(
                    {
                        method
                        for item in evidence
                        for method in item.retrieval_methods
                    }
                ),
            },
            evidence_ids=output.evidence_ids,
        )

        return {
            "evidence": evidence,
            "agent_results": [agent_result],
            "status": "research_completed",
        }