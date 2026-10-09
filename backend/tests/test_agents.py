from app.agents.planner import ResearchPlannerAgent
from app.agents.schemas import (
    AgentStatus,
    ResearchTaskType,
)
from app.agents.state import ResearchState


def test_research_planner_creates_plan() -> None:
    state: ResearchState = {
        "original_question": (
            "How did the company's revenue and operating expenses "
            "change between 2023 and 2025?"
        ),
    }

    result = ResearchPlannerAgent().run(state)

    assert result.status == "planned"

    plan = result.research_plan

    assert plan.normalized_question.startswith("How did")
    assert len(plan.tasks) == 3

    task_types = {task.task_type for task in plan.tasks}

    assert ResearchTaskType.FINANCIAL_ANALYSIS in task_types
    assert ResearchTaskType.DOCUMENT_RESEARCH in task_types
    assert ResearchTaskType.EXTERNAL_RESEARCH in task_types


def test_research_planner_creates_agent_result() -> None:
    state: ResearchState = {
        "original_question": "Analyze revenue growth.",
    }

    result = ResearchPlannerAgent().run(state)

    agent_results = result.agent_results

    assert len(agent_results) == 1
    assert agent_results[0].agent_name == "research_planner"
    assert agent_results[0].status == AgentStatus.COMPLETED


def test_research_planner_rejects_empty_question() -> None:
    state: ResearchState = {
        "original_question": "   ",
    }

    try:
        ResearchPlannerAgent().run(state)
    except ValueError as exc:
        assert str(exc) == "Research question cannot be empty."
    else:
        raise AssertionError("Expected ValueError.")