
from __future__ import annotations

import json
import re
from typing import Any, Protocol
from uuid import UUID

from app.agents.schemas import AgentResult, AgentStatus, ResearchAgentOutput
from app.agents.state import ResearchState
from app.llm.prompts import RESEARCH_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import ResearchLLMOutput
from app.retrieval.schemas import EvidencePackage, RetrievalFilters

MAX_EVIDENCE_ITEMS = 4
MAX_EVIDENCE_CHARS = 750
MAX_FINANCIAL_CONTEXT_CHARS = 1800
MAX_QUESTION_CHARS = 1000


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


def _normalize_company(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _get_companies(state: ResearchState) -> list[str]:
    companies = state.get("companies", [])

    if not companies:
        plan = state.get("research_plan")
        if plan is not None:
            companies = getattr(plan, "companies", []) or []

    return [
        company.strip()
        for company in companies
        if isinstance(company, str) and company.strip()
    ]


def _evidence_matches_company(item: Any, companies: list[str]) -> bool:
    if not companies:
        return True

    if isinstance(item, dict):
        company = item.get("company")
        content = item.get("content", "")
    else:
        company = getattr(item, "company", None)
        content = getattr(item, "content", "")

    if isinstance(company, str) and company.strip():
        normalized_source = _normalize_company(company)
        return any(
            normalized_source == _normalize_company(target)
            for target in companies
        )

    normalized_content = _normalize_company(str(content))
    return any(
        _normalize_company(target) in normalized_content
        for target in companies
    )


def _short_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _compact_json(value: Any, max_chars: int) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    serialized = json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(serialized) <= max_chars:
        return serialized
    return serialized[:max_chars] + "... [truncated]"


def _evidence_item_context(item: Any) -> dict[str, Any]:
    def get_value(key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    publication_date = get_value("publication_date")
    if hasattr(publication_date, "isoformat"):
        publication_date = publication_date.isoformat()

    return {
        "evidence_id": str(get_value("evidence_id", "")),
        "company": get_value("company"),
        "document_type": get_value("document_type"),
        "publication_date": publication_date,
        "content": _short_text(
            get_value("content", ""),
            MAX_EVIDENCE_CHARS,
        ),
        "source_url": get_value("source_url"),
    }


class LLMResearchAgent:
    """Retrieve relevant evidence and reason over a bounded context."""

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
            return self._failure("project_id is missing.")

        try:
            project_uuid = UUID(str(project_id))
        except (ValueError, TypeError, AttributeError):
            return self._failure("project_id is not a valid UUID.")

        question = str(
            state.get("normalized_question")
            or state.get("original_question")
            or ""
        ).strip()

        if not question:
            return self._failure("The research question is empty.")

        question = _short_text(question, MAX_QUESTION_CHARS)

        evidence_package = self.retriever.search(
            question,
            project_id=project_uuid,
            top_k=8,
            retrieval_k=12,
        )

        companies = _get_companies(state)
        retrieved_evidence = list(evidence_package.evidence)
        relevant_evidence = [
            item
            for item in retrieved_evidence
            if _evidence_matches_company(item, companies)
        ]
        rejected_count = len(retrieved_evidence) - len(relevant_evidence)

        if not relevant_evidence:
            target = ", ".join(companies) or "the requested subject"
            summary = (
                f"No relevant evidence for {target} was found in "
                "the retrieved project documents."
            )
            result = AgentResult(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                summary=summary,
                data={
                    "finding_count": 0,
                    "claim_count": 0,
                    "evidence_count": 0,
                    "retrieved_count": len(retrieved_evidence),
                    "rejected_irrelevant_count": rejected_count,
                },
                evidence_ids=[],
            )
            return {
                "evidence": [],
                "contradictions": [],
                "agent_results": [result],
                "research_output": {
                    "findings": [],
                    "claims": [],
                    "evidence_ids": [],
                    "source_urls": [],
                    "contradictions": [],
                    "limitations": [summary],
                },
                "status": "no_relevant_evidence",
            }

        # Keep the most relevant retrieved items, but bound the LLM context.
        selected_evidence = relevant_evidence[:MAX_EVIDENCE_ITEMS]
        evidence_context = [
            _evidence_item_context(item)
            for item in selected_evidence
        ]

        allowed_ids = {
            str(item.evidence_id)
            for item in selected_evidence
        }
        allowed_urls = {
            str(item.source_url)
            for item in selected_evidence
            if item.source_url
        }

        financial_context = _compact_json(
            state.get("financial_results", [])[:3],
            MAX_FINANCIAL_CONTEXT_CHARS,
        )

        prompt = f"""
Research question:
{question}

Requested companies:
{_compact_json(companies, 500)}

Retrieved company-filtered evidence:
{_compact_json(evidence_context, 4200)}

Deterministic financial analysis:
{financial_context}

Rules:
- Use only supplied evidence and financial results.
- Do not transfer facts between companies.
- Support factual claims with supplied evidence IDs.
- Return only supplied evidence IDs and source URLs.
- Do not invent values, fiscal years, sources, or URLs.
- Preserve reported units and fiscal-year labels.
- State missing information in limitations.
- Do not treat missing data as zero.
"""

        parsed, _ = self.llm.invoke_structured(
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=ResearchLLMOutput,
        )

        accepted_ids = [
            evidence_id
            for evidence_id in parsed.evidence_ids
            if evidence_id in allowed_ids
        ]
        accepted_urls = [
            url for url in parsed.source_urls if url in allowed_urls
        ]

        limitations = list(parsed.limitations)
        if rejected_count:
            limitations.append(
                f"Excluded {rejected_count} retrieved evidence item(s) "
                "because their company attribution did not match."
            )
        if len(relevant_evidence) > len(selected_evidence):
            limitations.append(
                f"Only {len(selected_evidence)} of "
                f"{len(relevant_evidence)} relevant retrieved evidence "
                "items were included in this LLM call to control context size."
            )

        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary="Completed bounded, company-filtered research.",
            data={
                "finding_count": len(parsed.findings),
                "claim_count": len(parsed.claims),
                "evidence_count": len(selected_evidence),
                "retrieved_count": len(retrieved_evidence),
                "rejected_irrelevant_count": rejected_count,
            },
            evidence_ids=accepted_ids,
        )

        output = ResearchAgentOutput(
            findings=parsed.findings,
            evidence_ids=accepted_ids,
            source_urls=accepted_urls,
            contradictions=parsed.contradictions,
        ).model_dump()

        output["claims"] = parsed.claims
        output["limitations"] = limitations

        return {
            "evidence": selected_evidence,
            "contradictions": parsed.contradictions,
            "agent_results": [result],
            "research_output": output,
            "status": "research_completed",
        }

    def _failure(self, message: str) -> dict[str, object]:
        return {
            "evidence": [],
            "agent_results": [
                AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.FAILED,
                    summary=message,
                    errors=[message],
                )
            ],
            "status": "research_failed",
        }
