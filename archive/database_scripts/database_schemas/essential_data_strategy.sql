-- Essential Data Capture Strategy
-- Ensures we capture ONLY what's needed for performance without overloading

-- 1. PERFORMANCE METRICS - Lightweight tracking (only essential metrics)
CREATE TABLE IF NOT EXISTS public.performance_metrics (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    operation_type text NOT NULL, -- 'agent_query', 'embedding_gen', 'context_lookup'
    execution_time_ms integer NOT NULL,
    success boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    -- Minimal details to avoid bloat
    operation_summary jsonb DEFAULT '{}'::jsonb, -- Key metrics only
    CONSTRAINT performance_metrics_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Auto-cleanup old performance data (keep only last 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_performance_data()
RETURNS void AS $$
BEGIN
    DELETE FROM public.performance_metrics 
    WHERE created_at < now() - interval '7 days';
END;
$$ LANGUAGE plpgsql;

-- 2. CLIENT CONTEXT - Efficient storage with smart deduplication
CREATE TABLE IF NOT EXISTS public.client_context_efficient (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    client_id text NOT NULL,
    context_hash text NOT NULL, -- Hash to prevent duplicates
    context_type text NOT NULL,
    essential_data jsonb NOT NULL, -- Only critical business data
    embedding vector(384),
    relevance_score float DEFAULT 1.0,
    last_accessed timestamp with time zone DEFAULT now(),
    access_count integer DEFAULT 1,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT client_context_efficient_pkey PRIMARY KEY (id),
    CONSTRAINT unique_client_context_hash UNIQUE (client_id, context_hash)
) TABLESPACE pg_default;

-- 3. AGENT INTERACTION LOG - Minimal logging for performance insights
CREATE TABLE IF NOT EXISTS public.agent_interactions_log (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    user_id text NOT NULL,
    agent_name text NOT NULL,
    query_type text, -- 'website_info', 'social_media', 'business_query'
    response_time_ms integer,
    context_sources_used text[], -- Which sources were helpful
    confidence_score float,
    user_satisfied boolean, -- Simple success metric
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT agent_interactions_log_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Auto-cleanup old interaction logs (keep only last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_interaction_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM public.agent_interactions_log 
    WHERE created_at < now() - interval '30 days';
END;
$$ LANGUAGE plpgsql;

-- 4. SMART INDEXING - Only what's needed for performance
CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation_time 
    ON public.performance_metrics (operation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_client_context_efficient_client_access 
    ON public.client_context_efficient (client_id, last_accessed DESC, is_active);

CREATE INDEX IF NOT EXISTS idx_agent_interactions_user_time 
    ON public.agent_interactions_log (user_id, created_at DESC);

-- 5. DATA QUALITY FUNCTIONS - Ensure we capture the RIGHT data

-- Function to log essential interaction data
CREATE OR REPLACE FUNCTION log_agent_interaction(
    p_user_id text,
    p_agent_name text,
    p_query_type text,
    p_response_time_ms integer,
    p_context_sources text[],
    p_confidence_score float,
    p_user_satisfied boolean DEFAULT null
)
RETURNS void AS $$
BEGIN
    INSERT INTO public.agent_interactions_log (
        user_id, agent_name, query_type, response_time_ms, 
        context_sources_used, confidence_score, user_satisfied
    ) VALUES (
        p_user_id, p_agent_name, p_query_type, p_response_time_ms,
        p_context_sources, p_confidence_score, p_user_satisfied
    );
END;
$$ LANGUAGE plpgsql;

-- Function to update client context efficiently (prevents duplicates)
CREATE OR REPLACE FUNCTION upsert_client_context_efficient(
    p_client_id text,
    p_context_type text,
    p_essential_data jsonb,
    p_embedding vector(384)
)
RETURNS uuid AS $$
DECLARE
    context_hash_value text;
    existing_id uuid;
    result_id uuid;
BEGIN
    -- Generate hash of essential data to prevent duplicates
    context_hash_value := md5(p_essential_data::text);
    
    -- Check if similar context already exists
    SELECT id INTO existing_id 
    FROM public.client_context_efficient 
    WHERE client_id = p_client_id 
      AND context_hash = context_hash_value;
    
    IF existing_id IS NOT NULL THEN
        -- Update existing record
        UPDATE public.client_context_efficient 
        SET last_accessed = now(), 
            access_count = access_count + 1,
            relevance_score = LEAST(relevance_score + 0.1, 2.0)
        WHERE id = existing_id;
        
        result_id := existing_id;
    ELSE
        -- Insert new record
        INSERT INTO public.client_context_efficient (
            client_id, context_hash, context_type, essential_data, embedding
        ) VALUES (
            p_client_id, context_hash_value, p_context_type, p_essential_data, p_embedding
        ) RETURNING id INTO result_id;
    END IF;
    
    RETURN result_id;
END;
$$ LANGUAGE plpgsql;

-- 6. MONITORING VIEWS - Quick insights without data bloat

-- View for performance insights
CREATE OR REPLACE VIEW v_performance_summary AS
SELECT 
    operation_type,
    COUNT(*) as operation_count,
    AVG(execution_time_ms) as avg_execution_time,
    MIN(execution_time_ms) as min_execution_time,
    MAX(execution_time_ms) as max_execution_time,
    COUNT(*) FILTER (WHERE success = false) as error_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE success = true) / COUNT(*), 2) as success_rate
FROM public.performance_metrics 
WHERE created_at >= now() - interval '24 hours'
GROUP BY operation_type;

-- View for client context efficiency
CREATE OR REPLACE VIEW v_client_context_summary AS
SELECT 
    context_type,
    COUNT(*) as total_contexts,
    AVG(access_count) as avg_access_count,
    COUNT(*) FILTER (WHERE access_count > 1) as reused_contexts,
    AVG(relevance_score) as avg_relevance
FROM public.client_context_efficient 
WHERE is_active = true
GROUP BY context_type;

-- 7. SCHEDULED CLEANUP - Prevent data bloat
-- Run daily cleanup (set up as a cron job or scheduled function)
CREATE OR REPLACE FUNCTION daily_database_cleanup()
RETURNS void AS $$
BEGIN
    -- Clean old performance metrics
    PERFORM cleanup_old_performance_data();
    
    -- Clean old interaction logs
    PERFORM cleanup_old_interaction_logs();
    
    -- Archive inactive client contexts
    UPDATE public.client_context_efficient 
    SET is_active = false 
    WHERE last_accessed < now() - interval '90 days'
      AND access_count = 1;
    
    -- Log cleanup summary
    INSERT INTO public.performance_metrics (operation_type, execution_time_ms, operation_summary)
    VALUES ('daily_cleanup', 0, jsonb_build_object(
        'performance_records_cleaned', (SELECT COUNT(*) FROM performance_metrics WHERE created_at < now() - interval '7 days'),
        'interaction_logs_cleaned', (SELECT COUNT(*) FROM agent_interactions_log WHERE created_at < now() - interval '30 days'),
        'contexts_archived', (SELECT COUNT(*) FROM client_context_efficient WHERE is_active = false AND last_accessed < now() - interval '90 days')
    ));
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for application use
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

COMMENT ON TABLE public.performance_metrics IS 'Lightweight performance tracking - auto-cleanup after 7 days';
COMMENT ON TABLE public.client_context_efficient IS 'Efficient client context storage with deduplication and relevance scoring';
COMMENT ON TABLE public.agent_interactions_log IS 'Essential interaction logging for insights - auto-cleanup after 30 days';
COMMENT ON FUNCTION upsert_client_context_efficient IS 'Smart context storage - prevents duplicates, tracks usage';
COMMENT ON FUNCTION log_agent_interaction IS 'Logs essential interaction data for performance insights';
COMMENT ON FUNCTION daily_database_cleanup IS 'Automated cleanup to prevent data bloat - run daily';