from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from app.agents.llm_planner import LLMResearchPlannerAgent
from app.agents.llm_researcher import LLMResearchAgent
from app.agents.llm_synthesizer import LLMSynthesisAgent
from app.agents.llm_verifier import LLMVerificationAgent
from app.agents.schemas import AgentStatus, ResearchTaskType, VerificationStatus
from app.agents.state import ResearchState
from app.llm.schemas import (
    LLMResponse,
    LLMUsage,
    PlannerLLMOutput,
    PlannerLLMTask,
    ResearchLLMOutput,
    SynthesisLLMOutput,
    VerificationLLMOutput,
)
from app.retrieval.schemas import EvidenceItem, EvidencePackage, RetrievalFilters
from pydantic import BaseModel


class FakeLLM:
    def __init__(self, output: BaseModel) -> None:
        self.output = output

    def invoke_structured[T: BaseModel](
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> tuple[T, LLMResponse]:
        del system_prompt, user_prompt

        if not isinstance(self.output, schema):
            raise TypeError(
                "FakeLLM output does not match the requested schema."
            )

        return (
            self.output,
            LLMResponse(
                content="{}",
                model="test-model",
                usage=LLMUsage(),
            ),
        )

class FakeRetriever:
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
        del query
        del project_id
        del top_k
        del retrieval_k
        del similarity_threshold
        del filters

        evidence = EvidenceItem(
            evidence_id="ev-1",
            chunk_id="chunk-1",
            document_id="doc-1",
            content="Revenue increased by 20 percent.",
            company="Example Corp",
            document_type="annual_report",
            source_url="https://example.com/report",
            rrf_score=0.03,
            retrieval_methods=["vector", "sparse"],
        )

        return EvidencePackage(
            query="test",
            project_id=uuid4(),
            evidence=[evidence],
            evidence_count=1,
        )


def base_state() -> ResearchState:
    return {
        "run_id": "run-1",
        "user_id": "user-1",
        "project_id": str(uuid4()),
        "original_question": "Analyze Example Corp revenue growth.",
        "normalized_question": "Analyze Example Corp revenue growth.",
        "companies": ["Example Corp"],
        "financial_results": [
            {
                "company": "Example Corp",
                "finding": "Revenue increased.",
            }
        ],
        "calculations": [
            {
                "calculation_id": "calc-1",
                "metric": "revenue_growth",
                "value": "0.20",
            }
        ],
        "evidence": [],
        "contradictions": [],
        "retry_count": 0,
        "max_retries": 1,
        "status": "running",
    }


def test_llm_planner_creates_research_plan() -> None:
    llm = FakeLLM(
        PlannerLLMOutput(
            normalized_question="Analyze Example Corp revenue growth.",
            companies=["Example Corp"],
            required_metrics=["revenue"],
            tasks=[
                PlannerLLMTask(
                    task_id="task-1",
                    task_type=ResearchTaskType.FINANCIAL_ANALYSIS.value,
                    description="Analyze revenue growth.",
                    required_tools=["revenue_analysis"],
                    completion_criteria=["Calculate growth."],
                )
            ],
        )
    )

    output = LLMResearchPlannerAgent(llm=llm).run(base_state())

    assert output.companies == ["Example Corp"]
    assert len(output.research_plan.tasks) == 1
    assert (
        output.research_plan.tasks[0].task_type
        == ResearchTaskType.FINANCIAL_ANALYSIS
    )


def test_llm_research_agent_grounds_findings() -> None:
    llm = FakeLLM(
        ResearchLLMOutput(
            findings=["Revenue increased by 20 percent."],
            claims=["Revenue increased by 20 percent."],
            evidence_ids=["ev-1"],
            source_urls=["https://example.com/report"],
        )
    )

    state = base_state()

    output = LLMResearchAgent(
        llm=llm,
        retriever=FakeRetriever(),
    ).run(state)

    evidence = output["evidence"]
    agent_results = output["agent_results"]

    assert isinstance(evidence, list)
    assert isinstance(agent_results, list)
    assert len(evidence) == 1
    assert agent_results[0].status == AgentStatus.COMPLETED


def test_llm_verifier_returns_pass() -> None:
    llm = FakeLLM(
        VerificationLLMOutput(
            status=VerificationStatus.PASS.value,
            verified_claims=["Revenue increased."],
            confidence=0.95,
        )
    )

    output = LLMVerificationAgent(llm=llm).run(base_state())

    assert output.result.status == VerificationStatus.PASS
    assert output.result.confidence == Decimal("0.95")


def test_llm_synthesizer_creates_claims() -> None:
    llm = FakeLLM(
        SynthesisLLMOutput(
            report="Example Corp revenue increased.",
            claims=[],
        )
    )

    output = LLMSynthesisAgent(llm=llm).run(base_state())

    assert output["draft_report"] == "Example Corp revenue increased."
    assert output["status"] == "synthesized"