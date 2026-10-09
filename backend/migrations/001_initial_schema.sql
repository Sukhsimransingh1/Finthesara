-- Phase 1 database foundation for agentic-finance-research.
-- Apply to a fresh Supabase PostgreSQL project before application data migrations.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    display_name text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    name text NOT NULL CHECK (length(trim(name)) > 0),
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.research_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES public.projects (id) ON DELETE CASCADE,
    question text NOT NULL CHECK (length(trim(question)) > 0),
    status text NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'planning', 'researching', 'verifying', 'awaiting_review', 'completed', 'failed'
    )),
    requested_depth text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.research_tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    research_run_id uuid NOT NULL REFERENCES public.research_runs (id) ON DELETE CASCADE,
    objective text NOT NULL CHECK (length(trim(objective)) > 0),
    expected_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
    completion_criteria jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'in_progress', 'completed', 'failed', 'skipped'
    )),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES public.projects (id) ON DELETE CASCADE,
    title text NOT NULL CHECK (length(trim(title)) > 0),
    company text,
    document_type text NOT NULL,
    publication_date date,
    source_url text,
    storage_path text,
    content_hash text,
    status text NOT NULL DEFAULT 'registered' CHECK (status IN (
        'registered', 'processing', 'ready', 'failed', 'archived'
    )),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT documents_project_content_hash_unique UNIQUE (project_id, content_hash)
);

-- vector is deliberately dimensionless here. EMBEDDING_DIMENSION is centralized
-- in application configuration; a future retrieval migration can create a
-- dimension-specific ANN index after the embedding provider is selected.
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    content text NOT NULL CHECK (length(trim(content)) > 0),
    embedding vector,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_chunks_document_chunk_index_unique UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS public.sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES public.projects (id) ON DELETE CASCADE,
    document_id uuid REFERENCES public.documents (id) ON DELETE SET NULL,
    source_type text NOT NULL CHECK (source_type IN ('document', 'web', 'manual', 'structured_data')),
    title text,
    publisher text,
    source_url text,
    retrieved_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.claims (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    research_run_id uuid NOT NULL REFERENCES public.research_runs (id) ON DELETE CASCADE,
    research_task_id uuid REFERENCES public.research_tasks (id) ON DELETE SET NULL,
    claim_text text NOT NULL CHECK (length(trim(claim_text)) > 0),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'supported', 'unsupported', 'contradicted')),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.calculations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    research_run_id uuid NOT NULL REFERENCES public.research_runs (id) ON DELETE CASCADE,
    calculation_type text NOT NULL CHECK (length(trim(calculation_type)) > 0),
    inputs jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    unit text,
    source_reference text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.claim_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.claims (id) ON DELETE CASCADE,
    source_id uuid REFERENCES public.sources (id) ON DELETE SET NULL,
    document_chunk_id uuid REFERENCES public.document_chunks (id) ON DELETE SET NULL,
    calculation_id uuid REFERENCES public.calculations (id) ON DELETE SET NULL,
    relationship text NOT NULL CHECK (relationship IN ('supports', 'contradicts', 'context')),
    excerpt text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT claim_evidence_has_evidence CHECK (
        num_nonnulls(source_id, document_chunk_id, calculation_id) >= 1
    )
);

CREATE TABLE IF NOT EXISTS public.verification_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.claims (id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('pass', 'fail', 'insufficient_evidence', 'contradiction')),
    reason text,
    -- Snapshot of claim_evidence IDs considered at decision time. The relational
    -- claim_evidence table remains the authoritative evidence relationship.
    evidence_ids uuid[] NOT NULL DEFAULT '{}',
    expected_value jsonb,
    actual_value jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.human_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    research_run_id uuid NOT NULL REFERENCES public.research_runs (id) ON DELETE CASCADE,
    reviewer_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    decision text CHECK (decision IN ('approve', 'reject', 'request_research')),
    comment text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.evaluation_datasets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE RESTRICT,
    project_id uuid REFERENCES public.projects (id) ON DELETE SET NULL,
    name text NOT NULL CHECK (length(trim(name)) > 0),
    description text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.evaluation_cases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_dataset_id uuid NOT NULL REFERENCES public.evaluation_datasets (id) ON DELETE CASCADE,
    question text NOT NULL CHECK (length(trim(question)) > 0),
    expected_results jsonb NOT NULL DEFAULT '{}'::jsonb,
    tags text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.evaluation_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_dataset_id uuid NOT NULL REFERENCES public.evaluation_datasets (id) ON DELETE RESTRICT,
    initiated_by uuid NOT NULL REFERENCES public.profiles (id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
    results jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES public.projects (id) ON DELETE CASCADE,
    research_run_id uuid REFERENCES public.research_runs (id) ON DELETE SET NULL,
    claim_id uuid REFERENCES public.claims (id) ON DELETE SET NULL,
    author_id uuid REFERENCES public.profiles (id) ON DELETE SET NULL,
    feedback_type text NOT NULL CHECK (feedback_type IN ('general', 'claim', 'report', 'bug')),
    content text NOT NULL CHECK (length(trim(content)) > 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'profiles', 'projects', 'research_runs', 'research_tasks', 'documents',
        'claims', 'human_reviews', 'evaluation_datasets', 'evaluation_cases'
    ]
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS %I ON public.%I',
            format('set_%s_updated_at', table_name),
            table_name
        );
        EXECUTE format(
            'CREATE TRIGGER %I BEFORE UPDATE ON public.%I '
            'FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()',
            format('set_%s_updated_at', table_name),
            table_name
        );
    END LOOP;
END;
$$;
