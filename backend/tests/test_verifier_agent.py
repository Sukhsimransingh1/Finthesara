from app.agents.schemas import VerificationStatus
from app.agents.state import ResearchState
from app.agents.verifier import VerificationAgent
from app.retrieval.schemas import EvidenceItem


def make_state() -> ResearchState:
    return {
        "normalized_question": "How did Example Corp perform?",
        "financial_results": [
            {
                "company": "Example Corp",
                "findings": ["Revenue increased."],
            }
        ],
        "evidence": [
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
                sparse_rank=1,
                vector_score=0.9,
                sparse_score=0.8,
                rrf_score=0.03,
                retrieval_methods=["vector", "sparse"],
            )
        ],
        "calculations": [],
        "contradictions": [],
    }


def test_verifier_passes_with_financial_results_and_evidence() -> None:
    result = VerificationAgent().run(make_state())

    assert result.result.status == VerificationStatus.PASS
    assert result.result.confidence > 0