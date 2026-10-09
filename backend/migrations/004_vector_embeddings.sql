-- Phase 3: Configure document chunk embeddings.
-- Model: BAAI/bge-base-en-v1.5
-- Dimension: 768

ALTER TABLE public.document_chunks
ALTER COLUMN embedding TYPE vector(768);