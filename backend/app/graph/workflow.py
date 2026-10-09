from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.financial_analyst import FinancialAnalystAgent
from app.agents.llm_planner import LLMResearchPlannerAgent
from app.agents.llm_researcher import LLMResearchAgent
from app.agents.llm_synthesizer import LLMSynthesisAgent
from app.agents.llm_verifier import LLMVerificationAgent
from app.agents.planner import ResearchPlannerAgent
from app.agents.researcher import ResearchAgent
from app.agents.verifier import VerificationAgent
from app.graph.nodes import (
    evidence_fusion_node,
    financial_node,
    human_review_node,
    planner_node,
    research_node,
    synthesis_node,
    targeted_research_node,
    verification_node,
)
from app.graph.routing import route_after_verification
from app.graph.state import ResearchState
from app.llm.client import GroqLLMClient
from app.retrieval.hybrid import HybridRetriever
from app.tools.data_source import FinancialDataSource


def build_research_graph(
    *,
    data_source: FinancialDataSource,
    researcher: ResearchAgent | None = None,
    planner: ResearchPlannerAgent | None = None,
    verifier: VerificationAgent | None = None,
) -> Any:
    """
    Build the deterministic research graph used by tests.

    No LLM client is created here.
    """

    financial_agent = FinancialAnalystAgent(
        data_source=data_source,
    )

    planner_agent = planner or ResearchPlannerAgent()

    researcher_agent = (
        researcher
        or ResearchAgent(
            retriever=HybridRetriever(),
        )
    )

    verifier_agent = verifier or VerificationAgent()

    workflow = StateGraph(ResearchState)

    workflow.add_node(
        "planner",
        lambda state: planner_node(
            state,
            agent=planner_agent,
        ),
    )

    workflow.add_node(
        "financial_analysis",
        lambda state: financial_node(
            state,
            agent=financial_agent,
        ),
    )

    workflow.add_node(
        "research",
        lambda state: research_node(
            state,
            agent=researcher_agent,
        ),
    )

    workflow.add_node(
        "evidence_fusion",
        evidence_fusion_node,
    )

    workflow.add_node(
        "verification",
        lambda state: verification_node(
            state,
            agent=verifier_agent,
        ),
    )

    workflow.add_node(
        "targeted_research",
        lambda state: targeted_research_node(
            state,
            agent=researcher_agent,
        ),
    )

    workflow.add_node(
        "synthesis",
        lambda state: synthesis_node(
            state,
            agent=None,
        ),
    )

    workflow.add_node(
        "human_review",
        human_review_node,
    )

    workflow.add_edge(
        START,
        "planner",
    )

    workflow.add_edge(
        "planner",
        "financial_analysis",
    )

    workflow.add_edge(
        "planner",
        "research",
    )

    workflow.add_edge(
        "financial_analysis",
        "evidence_fusion",
    )

    workflow.add_edge(
        "research",
        "evidence_fusion",
    )

    workflow.add_edge(
        "evidence_fusion",
        "verification",
    )

    workflow.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "targeted_research": "targeted_research",
            "synthesis": "synthesis",
        },
    )

    workflow.add_edge(
        "targeted_research",
        "verification",
    )

    workflow.add_edge(
        "synthesis",
        "human_review",
    )

    workflow.add_edge(
        "human_review",
        END,
    )

    return workflow.compile()


def build_production_research_graph(
    *,
    data_source: FinancialDataSource,
    retriever: HybridRetriever | None = None,
) -> Any:
    """
    Build the production LLM-powered research graph.

    Uses:
    - Groq
    - LangGraph
    - Hybrid RAG
    - deterministic financial analysis
    - verification
    - synthesis
    - human review
    """

    llm = GroqLLMClient()

    hybrid_retriever = retriever or HybridRetriever()

    planner_agent = LLMResearchPlannerAgent(
        llm=llm,
    )

    financial_agent = FinancialAnalystAgent(
        data_source=data_source,
    )

    researcher_agent = LLMResearchAgent(
        llm=llm,
        retriever=hybrid_retriever,
    )

    verifier_agent = LLMVerificationAgent(
        llm=llm,
    )

    synthesizer_agent = LLMSynthesisAgent(
        llm=llm,
    )

    workflow = StateGraph(ResearchState)

    workflow.add_node(
        "planner",
        lambda state: planner_node(
            state,
            agent=planner_agent,
        ),
    )

    workflow.add_node(
        "financial_analysis",
        lambda state: financial_node(
            state,
            agent=financial_agent,
        ),
    )

    workflow.add_node(
        "research",
        lambda state: research_node(
            state,
            agent=researcher_agent,
        ),
    )

    workflow.add_node(
        "evidence_fusion",
        evidence_fusion_node,
    )

    workflow.add_node(
        "verification",
        lambda state: verification_node(
            state,
            agent=verifier_agent,
        ),
    )

    workflow.add_node(
        "targeted_research",
        lambda state: targeted_research_node(
            state,
            agent=researcher_agent,
        ),
    )

    workflow.add_node(
        "synthesis",
        lambda state: synthesis_node(
            state,
            agent=synthesizer_agent,
        ),
    )

    workflow.add_node(
        "human_review",
        human_review_node,
    )

    workflow.add_edge(
        START,
        "planner",
    )

    workflow.add_edge(
        "planner",
        "financial_analysis",
    )

    workflow.add_edge(
        "planner",
        "research",
    )

    workflow.add_edge(
        "financial_analysis",
        "evidence_fusion",
    )

    workflow.add_edge(
        "research",
        "evidence_fusion",
    )

    workflow.add_edge(
        "evidence_fusion",
        "verification",
    )

    workflow.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "targeted_research": "targeted_research",
            "synthesis": "synthesis",
        },
    )

    workflow.add_edge(
        "targeted_research",
        "verification",
    )

    workflow.add_edge(
        "synthesis",
        "human_review",
    )

    workflow.add_edge(
        "human_review",
        END,
    )

    return workflow.compile()