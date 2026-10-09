-- Phase 3.3: Vector similarity search for financial research.
--
-- Uses pgvector cosine distance.
-- The embedding model is:
-- BAAI/bge-base-en-v1.5
-- Dimension: 768

CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
ON public.document_chunks
USING hnsw (embedding vector_cosine_ops);


CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding vector(768),
    match_count integer DEFAULT 8,
    match_threshold double precision DEFAULT 0.0,
    filter_project_id uuid DEFAULT NULL
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
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks AS dc
    JOIN public.documents AS d
        ON d.id = dc.document_id
    WHERE dc.embedding IS NOT NULL
      AND (
          filter_project_id IS NULL
          OR d.project_id = filter_project_id
      )
      AND (
          1 - (dc.embedding <=> query_embedding)
      ) >= match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT GREATEST(match_count, 0);
$$;