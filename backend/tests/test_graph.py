from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.agents.researcher import ResearchAgent
from app.agents.schemas import (
    ResearchPlan,
    ResearchTaskType,
)
from app.agents.state import ResearchState
from app.graph.workflow import build_research_graph
from app.retrieval.schemas import EvidenceItem, EvidencePackage
from app.tools.schemas import (
    FinancialDataQuery,
    FinancialDataResult,
    FinancialMetric,
)


class FakeFinancialDataSource:
    """Deterministic financial data source for graph tests."""

    def query(
        self,
        request: FinancialDataQuery,
    ) -> FinancialDataResult:
        values = [
            FinancialMetric(
                company=request.company,
                metric=request.metric,
                period=period,
                value=(
                    Decimal("1000000")
                    if period.label == "2024"
                    else Decimal("1250000")
                ),
                currency="USD",
                unit="absolute",
                source_id=f"source-{period.label}",
                source_url=f"https://example.com/{period.label}",
            )
            for period in request.periods
        ]

        return FinancialDataResult(
            company=request.company,
            metric=request.metric,
            values=values,
            source_count=len(values),
        )


class FakeHybridRetriever:
    """Deterministic hybrid retriever for graph tests."""

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
                    content=(
                        "Example Corp reported revenue growth "
                        "during the reporting period."
                    ),
                    company="Example Corp",
                    document_type="annual_report",
                    publication_date=date(2025, 12, 31),
                    page_number=10,
                    source_url="https://example.com/report",
                    vector_rank=1,
                    sparse_rank=1,
                    vector_score=0.95,
                    sparse_score=0.90,
                    rrf_score=0.032,
                    retrieval_methods=["vector", "sparse"],
                )
            ],
            evidence_count=1,
            retrieval_config={
                "fusion": "weighted_rrf",
                "rrf_k": 60,
                "vector_weight": 1.0,
                "sparse_weight": 1.0,
            },
        )


def make_initial_state() -> ResearchState:
    """Create the initial state supplied to the LangGraph workflow."""

    return {
        "run_id": "test-run-001",
        "user_id": "test-user-001",
        "project_id": "bc8d4f9e-15d5-44f9-a896-c131421d8d4a",
        "original_question": (
            "How did Example Corp revenue change between 2024 and 2025?"
        ),
        "companies": ["Example Corp"],
        "time_range_start": "2024-01-01",
        "time_range_end": "2025-12-31",
        "retry_count": 0,
        "max_retries": 1,
        "status": "started",
    }


def test_research_graph_builds() -> None:
    """The complete LangGraph workflow should compile successfully."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    assert graph is not None
    assert hasattr(graph, "invoke")


def test_research_graph_runs_end_to_end() -> None:
    """The graph should execute planner, parallel agents, verification and synthesis."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    state = make_initial_state()

    result = graph.invoke(state)

    assert result["status"] == "awaiting_human_review"

    assert result["normalized_question"] == (
        "How did Example Corp revenue change between 2024 and 2025?"
    )

    assert "research_plan" in result

    research_plan = result["research_plan"]

    assert isinstance(research_plan, ResearchPlan)
    assert len(research_plan.tasks) == 3

    task_types = {
        task.task_type
        for task in research_plan.tasks
    }

    assert ResearchTaskType.FINANCIAL_ANALYSIS in task_types
    assert ResearchTaskType.DOCUMENT_RESEARCH in task_types
    assert ResearchTaskType.EXTERNAL_RESEARCH in task_types


def test_research_graph_produces_financial_results() -> None:
    """The financial analyst branch should populate financial results."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    financial_results = result.get("financial_results", [])

    assert isinstance(financial_results, list)
    assert len(financial_results) == 1

    financial_result = financial_results[0]

    assert financial_result["company"] == "Example Corp"

    findings = financial_result["findings"]

    assert isinstance(findings, list)
    assert len(findings) > 0


def test_research_graph_produces_evidence() -> None:
    """The research branch should produce traceable evidence."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    evidence = result.get("evidence", [])

    assert isinstance(evidence, list)
    assert len(evidence) == 1

    evidence_item = evidence[0]

    assert evidence_item.evidence_id == "evidence-1"
    assert evidence_item.chunk_id == "chunk-1"
    assert evidence_item.company == "Example Corp"
    assert "vector" in evidence_item.retrieval_methods
    assert "sparse" in evidence_item.retrieval_methods


def test_research_graph_runs_verification() -> None:
    """The verification agent should run after evidence fusion."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    verification_result = result.get("verification_result")

    assert verification_result is not None
    assert verification_result.status.value == "pass"
    assert verification_result.confidence >= Decimal("0.0")
    assert verification_result.confidence <= Decimal("1.0")


def test_research_graph_generates_draft_report() -> None:
    """Synthesis should generate an auditable draft report."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    draft_report = result.get("draft_report")

    assert isinstance(draft_report, str)
    assert len(draft_report) > 0

    assert "# Financial Research Report" in draft_report
    assert "## Research Question" in draft_report
    assert "## Financial Analysis" in draft_report
    assert "## Evidence" in draft_report
    assert "## Verification" in draft_report


def test_research_graph_requires_human_review() -> None:
    """The final workflow state should explicitly require human review."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    assert result["human_review_required"] is True

    human_review = result.get("human_review")

    assert human_review is not None
    assert human_review.required is True
    assert human_review.decision is None


def test_research_graph_tracks_agent_results() -> None:
    """Parallel agent execution should preserve all agent results."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    agent_results = result.get("agent_results", [])

    assert isinstance(agent_results, list)

    agent_names = {
        agent_result.agent_name
        for agent_result in agent_results
    }

    assert "research_planner" in agent_names
    assert "financial_analyst" in agent_names
    assert "research_agent" in agent_names
    assert "verification_agent" in agent_names


def test_research_graph_preserves_calculations() -> None:
    """Financial calculations should survive the graph state transitions."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    calculations = result.get("calculations", [])

    assert isinstance(calculations, list)
    assert len(calculations) > 0


def test_research_graph_preserves_claims() -> None:
    """Synthesis should create traceable report claims."""

    graph = build_research_graph(
        data_source=FakeFinancialDataSource(),
        researcher=ResearchAgent(
            retriever=FakeHybridRetriever(),
        ),
    )

    result = graph.invoke(make_initial_state())

    claims = result.get("claims", [])

    assert isinstance(claims, list)
    assert len(claims) > 0

    claim = claims[0]

    assert claim.claim_id == "report-verification-status"
    assert "verification status" in claim.statement.lower()