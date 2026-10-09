from __future__ import annotations

from uuid import UUID

from app.agents.researcher import ResearchAgent
from app.agents.schemas import ResearchPlan, ResearchTask, ResearchTaskType
from app.agents.state import ResearchState
from app.retrieval.schemas import EvidenceItem, EvidencePackage


class FakeHybridRetriever:
    def search(
        self,
        query: str,
        *,
        project_id: UUID,
        top_k: int = 10,
        retrieval_k: int = 20,
        similarity_threshold: float = 0.0,
        filters: object | None = None,
    ) -> EvidencePackage:
        return EvidencePackage(
            query=query,
            project_id=project_id,
            evidence=[
                EvidenceItem(
                    evidence_id="evidence-1",
                    chunk_id="chunk-1",
                    document_id="document-1",
                    content="Example Corp revenue increased.",
                    company="Example Corp",
                    document_type="annual_report",
                    page_number=10,
                    source_url="https://example.com/report",
                    vector_rank=1,
                    sparse_rank=2,
                    vector_score=0.92,
                    sparse_score=0.80,
                    rrf_score=0.03,
                    retrieval_methods=["vector", "sparse"],
                )
            ],
            evidence_count=1,
        )


def make_state() -> ResearchState:
    plan = ResearchPlan(
        normalized_question="How did Example Corp perform?",
        tasks=[
            ResearchTask(
                task_id="research-task",
                task_type=ResearchTaskType.DOCUMENT_RESEARCH,
                description="Find supporting financial evidence.",
            )
        ],
    )

    return {
        "original_question": "How did Example Corp perform?",
        "normalized_question": "How did Example Corp perform?",
        "project_id": "bc8d4f9e-15d5-44f9-a896-c131421d8d4a",
        "research_plan": plan,
    }


def test_research_agent_returns_evidence() -> None:
    agent = ResearchAgent(
        retriever=FakeHybridRetriever(),
    )

    result = agent.run(make_state())

    evidence = result["evidence"]

    assert isinstance(evidence, list)
    assert len(evidence) == 1

    agent_results = result["agent_results"]

    assert isinstance(agent_results, list)
    assert agent_results[0].status.value == "completed"


def test_research_agent_requires_project_id() -> None:
    state = make_state()
    state.pop("project_id")

    agent = ResearchAgent(
        retriever=FakeHybridRetriever(),
    )

    result = agent.run(state)

    assert result["status"] == "research_failed"