-- Database Optimization: Indexes and Performance Improvements
-- Execute these SQL commands in your Supabase database

-- 1. Add indexes for frequently queried fields
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_documents_agent_name 
ON agent_documents(agent_name);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_documents_created_at 
ON agent_documents(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_context_client_id 
ON client_context(client_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_context_context_type 
ON client_context(context_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_kb_client_id_kb_type 
ON client_kb(client_id, kb_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_history_session_id 
ON chat_history(session_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_history_timestamp 
ON chat_history(timestamp DESC);

-- 2. Add composite indexes for multi-column queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_documents_agent_embedding 
ON agent_documents(agent_name, embedding);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_context_client_type_active 
ON client_context(client_id, context_type, is_active);

-- 3. Add partial indexes for better performance on filtered queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_context_active 
ON client_context(client_id, context_type) 
WHERE is_active = true;

-- 4. Optimize vector similarity search with proper indexing
-- Enable the vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index for faster vector similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_documents_embedding_hnsw 
ON agent_documents USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- 5. Create stored procedures for better performance
CREATE OR REPLACE FUNCTION optimized_agent_match(
    p_agent_name TEXT,
    p_query_embedding vector,
    p_threshold FLOAT DEFAULT 0.2,
    p_limit INT DEFAULT 5
)
RETURNS TABLE(content TEXT, similarity FLOAT)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.content,
        1 - (ad.embedding <=> p_query_embedding) as similarity
    FROM agent_documents ad
    WHERE ad.agent_name = p_agent_name
        AND 1 - (ad.embedding <=> p_query_embedding) > p_threshold
    ORDER BY ad.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$;

-- 6. Create optimized client context retrieval function
CREATE OR REPLACE FUNCTION get_client_context_optimized(
    p_client_id TEXT,
    p_context_types TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 10
)
RETURNS TABLE(
    context_type TEXT,
    content JSONB,
    confidence_score FLOAT,
    created_at TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.context_type,
        cc.content,
        cc.confidence_score,
        cc.created_at
    FROM client_context cc
    WHERE cc.client_id = p_client_id
        AND cc.is_active = true
        AND (p_context_types IS NULL OR cc.context_type = ANY(p_context_types))
    ORDER BY cc.confidence_score DESC, cc.created_at DESC
    LIMIT p_limit;
END;
$$;

-- 7. Create materialized view for frequently accessed agent statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_stats AS
SELECT 
    agent_name,
    COUNT(*) as document_count,
    AVG(CASE WHEN metadata->>'confidence' IS NOT NULL 
        THEN (metadata->>'confidence')::FLOAT 
        ELSE 1.0 END) as avg_confidence,
    MAX(created_at) as last_updated
FROM agent_documents
GROUP BY agent_name;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_stats_agent_name 
ON agent_stats(agent_name);

-- 8. Set up automatic refresh for materialized view
-- Note: This needs to be set up as a scheduled job in your environment
-- Example cron job to refresh every hour:
-- 0 * * * * psql -d your_db -c "REFRESH MATERIALIZED VIEW CONCURRENTLY agent_stats;"

-- 9. Optimize table statistics for better query planning
ANALYZE agent_documents;
ANALYZE client_context;
ANALYZE client_kb;
ANALYZE chat_history;

-- 10. Add database-level optimizations
-- Enable parallel query execution
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;

-- Optimize for better join performance
SET work_mem = '256MB';
SET effective_cache_size = '4GB';

-- 11. Create partition tables for large datasets (if needed)
-- Example for chat_history partitioning by date
-- This should be done carefully and only if you have large amounts of data

-- CREATE TABLE chat_history_2025_01 PARTITION OF chat_history
-- FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 12. Add constraints for data integrity
ALTER TABLE client_context 
ADD CONSTRAINT check_confidence_score 
CHECK (confidence_score >= 0 AND confidence_score <= 1);

ALTER TABLE agent_documents 
ADD CONSTRAINT check_agent_name_not_empty 
CHECK (LENGTH(agent_name) > 0);

-- 13. Create monitoring view for performance tracking
CREATE OR REPLACE VIEW performance_monitoring AS
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    most_common_vals,
    most_common_freqs
FROM pg_stats 
WHERE schemaname = 'public' 
    AND tablename IN ('agent_documents', 'client_context', 'chat_history', 'client_kb');

-- 14. Add comment documentation
COMMENT ON INDEX idx_agent_documents_embedding_hnsw IS 
'HNSW index for fast vector similarity search on agent documents';

COMMENT ON FUNCTION optimized_agent_match IS 
'Optimized function for agent matching using vector similarity with configurable threshold';

COMMENT ON MATERIALIZED VIEW agent_stats IS 
'Cached statistics for agents to improve dashboard performance';