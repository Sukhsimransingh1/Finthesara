-- Indexes for current ownership, lifecycle, and provenance access patterns.

CREATE INDEX IF NOT EXISTS projects_owner_id_idx ON public.projects (owner_id);
CREATE INDEX IF NOT EXISTS research_runs_project_status_created_at_idx
    ON public.research_runs (project_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS research_tasks_run_status_idx
    ON public.research_tasks (research_run_id, status);
CREATE INDEX IF NOT EXISTS documents_project_company_type_publication_date_idx
    ON public.documents (project_id, company, document_type, publication_date DESC);
CREATE INDEX IF NOT EXISTS documents_project_status_idx ON public.documents (project_id, status);
CREATE INDEX IF NOT EXISTS documents_metadata_gin_idx ON public.documents USING gin (metadata);
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON public.document_chunks (document_id);
CREATE INDEX IF NOT EXISTS document_chunks_metadata_gin_idx ON public.document_chunks USING gin (metadata);
CREATE INDEX IF NOT EXISTS sources_project_id_idx ON public.sources (project_id);
CREATE INDEX IF NOT EXISTS sources_document_id_idx ON public.sources (document_id);
CREATE INDEX IF NOT EXISTS claims_run_status_idx ON public.claims (research_run_id, status);
CREATE INDEX IF NOT EXISTS claims_task_id_idx ON public.claims (research_task_id);
CREATE INDEX IF NOT EXISTS calculations_run_type_idx ON public.calculations (research_run_id, calculation_type);
CREATE INDEX IF NOT EXISTS claim_evidence_claim_id_idx ON public.claim_evidence (claim_id);
CREATE INDEX IF NOT EXISTS claim_evidence_source_id_idx ON public.claim_evidence (source_id);
CREATE INDEX IF NOT EXISTS claim_evidence_document_chunk_id_idx ON public.claim_evidence (document_chunk_id);
CREATE INDEX IF NOT EXISTS claim_evidence_calculation_id_idx ON public.claim_evidence (calculation_id);
CREATE INDEX IF NOT EXISTS verification_results_claim_status_idx
    ON public.verification_results (claim_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS human_reviews_run_status_idx ON public.human_reviews (research_run_id, status);
CREATE INDEX IF NOT EXISTS evaluation_datasets_owner_id_idx ON public.evaluation_datasets (owner_id);
CREATE INDEX IF NOT EXISTS evaluation_cases_dataset_id_idx ON public.evaluation_cases (evaluation_dataset_id);
CREATE INDEX IF NOT EXISTS evaluation_runs_dataset_status_idx
    ON public.evaluation_runs (evaluation_dataset_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS feedback_project_created_at_idx ON public.feedback (project_id, created_at DESC);
