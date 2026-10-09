-- Phase 3.7
-- Return document-level metadata through both vector and sparse retrieval.
--
-- Security note:
-- project_id is intentionally REQUIRED.
-- The backend uses the Supabase service-role client, which bypasses RLS,
-- so retrieval must never accidentally run without a project scope.

-- ============================================================
-- VECTOR SEARCH
-- ============================================================

DROP FUNCTION IF EXISTS public.match_document_chunks(
    vector,
    integer,
    double precision,
    uuid
);

CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding vector(768),
    filter_project_id uuid,
    match_count integer DEFAULT 8,
    match_threshold double precision DEFAULT 0.0,
    filter_company text DEFAULT NULL,
    filter_document_type text DEFAULT NULL,
    filter_publication_date_from date DEFAULT NULL,
    filter_publication_date_to date DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    chunk_index integer,
    content text,
    metadata jsonb,
    similarity double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        dc.id,
        dc.document_id,
        dc.chunk_index,
        dc.content,

        COALESCE(dc.metadata, '{}'::jsonb)
        ||
        jsonb_build_object(
            'company', d.company,
            'document_type', d.document_type,
            'publication_date', d.publication_date,
            'source_url', d.source_url
        ) AS metadata,

        1 - (dc.embedding <=> query_embedding) AS similarity

    FROM public.document_chunks AS dc

    JOIN public.documents AS d
        ON d.id = dc.document_id

    WHERE
        dc.embedding IS NOT NULL

        AND d.project_id = filter_project_id

        AND (
            filter_company IS NULL
            OR d.company = filter_company
        )

        AND (
            filter_document_type IS NULL
            OR d.document_type = filter_document_type
        )

        AND (
            filter_publication_date_from IS NULL
            OR d.publication_date >= filter_publication_date_from
        )

        AND (
            filter_publication_date_to IS NULL
            OR d.publication_date <= filter_publication_date_to
        )

        AND (
            1 - (dc.embedding <=> query_embedding)
        ) >= match_threshold

    ORDER BY dc.embedding <=> query_embedding

    LIMIT GREATEST(match_count, 0);
$$;


-- ============================================================
-- SPARSE SEARCH
-- ============================================================

DROP FUNCTION IF EXISTS public.search_document_chunks(
    text,
    integer,
    uuid
);

CREATE OR REPLACE FUNCTION public.search_document_chunks(
    search_query text,
    filter_project_id uuid,
    match_count integer DEFAULT 8,
    filter_company text DEFAULT NULL,
    filter_document_type text DEFAULT NULL,
    filter_publication_date_from date DEFAULT NULL,
    filter_publication_date_to date DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    chunk_index integer,
    content text,
    metadata jsonb,
    rank double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        dc.id,
        dc.document_id,
        dc.chunk_index,
        dc.content,

        COALESCE(dc.metadata, '{}'::jsonb)
        ||
        jsonb_build_object(
            'company', d.company,
            'document_type', d.document_type,
            'publication_date', d.publication_date,
            'source_url', d.source_url
        ) AS metadata,

        ts_rank_cd(
            to_tsvector('english', dc.content),
            websearch_to_tsquery('english', search_query)
        )::double precision AS rank

    FROM public.document_chunks AS dc

    JOIN public.documents AS d
        ON d.id = dc.document_id

    WHERE
        dc.content IS NOT NULL
        AND dc.content <> ''

        AND d.project_id = filter_project_id

        AND websearch_to_tsquery(
            'english',
            search_query
        ) @@ to_tsvector(
            'english',
            dc.content
        )

        AND (
            filter_company IS NULL
            OR d.company = filter_company
        )

        AND (
            filter_document_type IS NULL
            OR d.document_type = filter_document_type
        )

        AND (
            filter_publication_date_from IS NULL
            OR d.publication_date >= filter_publication_date_from
        )

        AND (
            filter_publication_date_to IS NULL
            OR d.publication_date <= filter_publication_date_to
        )

    ORDER BY rank DESC, dc.id

    LIMIT GREATEST(match_count, 0);
$$;