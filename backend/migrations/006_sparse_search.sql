-- Phase 3.4: PostgreSQL sparse/full-text retrieval

CREATE INDEX IF NOT EXISTS document_chunks_content_fts_idx
ON public.document_chunks
USING gin (
    to_tsvector('english', content)
);


CREATE OR REPLACE FUNCTION public.search_document_chunks(
    search_query text,
    match_count integer DEFAULT 8,
    filter_project_id uuid DEFAULT NULL
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
        dc.metadata,
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
        AND websearch_to_tsquery('english', search_query) @@
            to_tsvector('english', dc.content)
        AND (
            filter_project_id IS NULL
            OR d.project_id = filter_project_id
        )
    ORDER BY rank DESC, dc.id
    LIMIT GREATEST(match_count, 0);
$$;