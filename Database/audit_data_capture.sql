-- Database Audit: Check what we're capturing and optimize data storage
-- This ensures we capture essential details without overloading

-- 1. Check current table structures and record counts
SELECT 
    schemaname,
    tablename,
    n_tup_ins as "Records Inserted",
    n_tup_upd as "Records Updated", 
    n_tup_del as "Records Deleted"
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_tup_ins DESC;

-- 2. Check table sizes to ensure we're not overloading
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as "Table Size",
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;

-- 3. Verify our new optimized tables exist
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name IN ('client_context', 'agent_knowledge_cache', 'performance_metrics', 'group_conversations')
ORDER BY table_name, ordinal_position;

-- 4. Check if we have proper indexes for performance
SELECT 
    t.tablename,
    i.indexname,
    array_to_string(array_agg(a.attname), ', ') as column_names
FROM pg_indexes i
JOIN pg_class c ON c.relname = i.indexname
JOIN pg_attribute a ON a.attrelid = c.oid
JOIN pg_tables t ON t.tablename = i.tablename
WHERE t.schemaname = 'public'
  AND i.tablename IN ('client_context', 'agent_knowledge_cache', 'agent_documents', 'chat_history')
GROUP BY t.tablename, i.indexname
ORDER BY t.tablename, i.indexname;

-- 5. Sample recent data to verify we're capturing the right information
-- Check agent_documents (should have 384-dimension embeddings)
SELECT 
    agent_name,
    length(content) as content_length,
    array_length(embedding, 1) as embedding_dimensions,
    created_at
FROM agent_documents 
ORDER BY created_at DESC 
LIMIT 3;

-- Check performance_metrics if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'performance_metrics') THEN
        RAISE NOTICE 'Performance metrics table exists - checking recent entries...';
        PERFORM * FROM performance_metrics LIMIT 1;
    ELSE
        RAISE NOTICE 'Performance metrics table does not exist yet';
    END IF;
END $$;

-- 6. Check for data quality issues
-- Verify embeddings are not null and have correct dimensions
SELECT 
    'agent_documents' as table_name,
    COUNT(*) as total_records,
    COUNT(embedding) as records_with_embeddings,
    AVG(array_length(embedding, 1)) as avg_embedding_dimensions
FROM agent_documents
UNION ALL
SELECT 
    'website_data' as table_name,
    COUNT(*) as total_records,
    COUNT(embedding) as records_with_embeddings,
    AVG(array_length(embedding, 1)) as avg_embedding_dimensions
FROM website_data
WHERE EXISTS (SELECT 1 FROM information_schema.columns 
              WHERE table_name = 'website_data' AND column_name = 'embedding');

-- 7. Storage optimization recommendations
SELECT 
    'Storage Recommendations' as category,
    CASE 
        WHEN pg_total_relation_size('public.chat_history') > 50 * 1024 * 1024 THEN 
            'Consider archiving old chat_history records older than 30 days'
        WHEN (SELECT COUNT(*) FROM agent_documents WHERE embedding IS NULL) > 0 THEN
            'Some agent_documents missing embeddings - regenerate'
        ELSE 'Storage is optimized'
    END as recommendation;