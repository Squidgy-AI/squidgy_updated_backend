-- Fix the search function return type mismatch
-- The function expects uuid but is getting bigint

-- Drop and recreate the match_agents_by_similarity function with correct column order
DROP FUNCTION IF EXISTS match_agents_by_similarity(vector, float, int);

CREATE OR REPLACE FUNCTION match_agents_by_similarity(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    agent_name text,
    content text,
    metadata jsonb,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
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

COMMENT ON FUNCTION match_agents_by_similarity IS 'Fixed return type for agent similarity search';