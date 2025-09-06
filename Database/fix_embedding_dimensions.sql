-- Fix embedding dimensions for free sentence-transformers model
-- This updates the existing agent_documents table to use 384 dimensions instead of 1536

-- 1. First, check if we need to update the embedding column
-- Drop the old index if it exists
DROP INDEX IF EXISTS agent_documents_embedding_idx;

-- Update the embedding column to use 384 dimensions (sentence-transformers)
ALTER TABLE public.agent_documents 
ALTER COLUMN embedding TYPE vector(384);

-- Recreate the index with the new dimensions
CREATE INDEX agent_documents_embedding_idx ON public.agent_documents 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Also update any other tables that might have old embedding dimensions
-- Update website_data table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'website_data' 
               AND column_name = 'embedding') THEN
        ALTER TABLE public.website_data 
        ALTER COLUMN embedding TYPE vector(384);
        
        -- Recreate index
        DROP INDEX IF EXISTS website_data_embedding_idx;
        CREATE INDEX website_data_embedding_idx ON public.website_data 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
            WHERE embedding IS NOT NULL;
    END IF;
END $$;

-- First drop existing functions to avoid conflicts
DROP FUNCTION IF EXISTS match_agents_by_similarity(vector, double precision, integer);
DROP FUNCTION IF EXISTS match_agents_by_similarity(vector, float, int);
DROP FUNCTION IF EXISTS match_agent_documents(vector, double precision, integer, text);
DROP FUNCTION IF EXISTS match_agent_documents(vector, float, int, text);

-- Update any RPC functions that expect 1536 dimensions
-- Create match_agents_by_similarity function with correct return type
CREATE OR REPLACE FUNCTION match_agents_by_similarity(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    agent_name text,
    content text,
    metadata jsonb,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.id,
        ad.agent_name,
        ad.content,
        ad.metadata,
        1 - (ad.embedding <=> query_embedding) as similarity
    FROM public.agent_documents ad
    WHERE ad.embedding IS NOT NULL
        AND 1 - (ad.embedding <=> query_embedding) >= match_threshold
    ORDER BY ad.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Create match_agent_documents function with correct return type
CREATE OR REPLACE FUNCTION match_agent_documents(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_agent text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    agent_name text,
    content text,
    metadata jsonb,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.id,
        ad.agent_name,
        ad.content,
        ad.metadata,
        1 - (ad.embedding <=> query_embedding) as similarity
    FROM public.agent_documents ad
    WHERE ad.embedding IS NOT NULL
        AND (filter_agent IS NULL OR ad.agent_name = filter_agent)
        AND 1 - (ad.embedding <=> query_embedding) >= match_threshold
    ORDER BY ad.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Clear any existing embeddings so they get regenerated with correct dimensions
UPDATE public.agent_documents SET embedding = NULL;

COMMENT ON FUNCTION match_agents_by_similarity IS 'Updated for 384-dimension sentence-transformers embeddings';
COMMENT ON FUNCTION match_agent_documents IS 'Updated for 384-dimension sentence-transformers embeddings';