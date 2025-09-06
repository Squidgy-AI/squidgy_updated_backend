-- Optimized Database Schema for Faster Performance and Better Context Management
-- This schema improves on the existing tables for better performance and group chat functionality

-- 1. Enhanced chat_history table with better indexing
DROP INDEX IF EXISTS idx_chat_history_session;
DROP INDEX IF EXISTS idx_chat_history_user;

CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON public.chat_history 
    USING btree (user_id, session_id, timestamp DESC);
    
CREATE INDEX IF NOT EXISTS idx_chat_history_agent ON public.chat_history 
    USING btree (sender, timestamp DESC) WHERE sender != 'User';

-- 2. Optimized client_kb table with better structure
CREATE TABLE IF NOT EXISTS public.client_context (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    client_id text NOT NULL,
    context_type text NOT NULL, -- 'website_info', 'social_media', 'business_info', etc.
    content jsonb NOT NULL,
    embedding vector(384), -- For free sentence-transformers model (384 dimensions)
    source_url text NULL,
    confidence_score float DEFAULT 1.0,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone NULL DEFAULT now(),
    updated_at timestamp with time zone NULL DEFAULT now(),
    CONSTRAINT client_context_pkey PRIMARY KEY (id),
    CONSTRAINT unique_client_context_type UNIQUE (client_id, context_type, source_url)
) TABLESPACE pg_default;

-- Indexes for client_context
CREATE INDEX IF NOT EXISTS idx_client_context_client ON public.client_context 
    USING btree (client_id, is_active, updated_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_client_context_type ON public.client_context 
    USING btree (context_type, is_active);

-- Vector similarity index for client context
CREATE INDEX IF NOT EXISTS idx_client_context_embedding ON public.client_context 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 3. Enhanced conversation_context for group chats and agent collaboration
DROP TABLE IF EXISTS public.conversation_context;

CREATE TABLE public.conversation_context (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    session_id text NOT NULL,
    user_id text NOT NULL,
    context_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    active_agents text[] DEFAULT '{}', -- Array of active agent names
    conversation_type text DEFAULT 'single_agent', -- 'single_agent', 'group_chat', 'agent_collaboration'
    last_agent text NULL, -- Last agent that responded
    agent_context jsonb DEFAULT '{}'::jsonb, -- Agent-specific context data
    user_preferences jsonb DEFAULT '{}'::jsonb, -- User preferences and settings
    conversation_flow jsonb DEFAULT '{}'::jsonb, -- Flow state for complex conversations
    is_active boolean DEFAULT true,
    created_at timestamp with time zone NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT conversation_context_pkey PRIMARY KEY (id),
    CONSTRAINT conversation_context_session_key UNIQUE (session_id, user_id)
) TABLESPACE pg_default;

-- Indexes for conversation_context
CREATE INDEX IF NOT EXISTS idx_conversation_context_user ON public.conversation_context 
    USING btree (user_id, is_active, updated_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_conversation_context_session ON public.conversation_context 
    USING btree (session_id, is_active);

-- GIN index for agent array queries
CREATE INDEX IF NOT EXISTS idx_conversation_context_agents ON public.conversation_context 
    USING gin (active_agents);

-- 4. Agent knowledge base with optimized structure
CREATE TABLE IF NOT EXISTS public.agent_knowledge_cache (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    agent_name text NOT NULL,
    knowledge_type text NOT NULL, -- 'core_knowledge', 'learned_context', 'user_specific'
    content_hash text NOT NULL, -- Hash of content for quick lookups
    content text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    embedding vector(384), -- Free sentence-transformers embedding
    relevance_score float DEFAULT 1.0,
    usage_count integer DEFAULT 0,
    last_used timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone NULL DEFAULT now(),
    updated_at timestamp with time zone NULL DEFAULT now(),
    CONSTRAINT agent_knowledge_cache_pkey PRIMARY KEY (id),
    CONSTRAINT unique_agent_content_hash UNIQUE (agent_name, content_hash)
) TABLESPACE pg_default;

-- Indexes for agent_knowledge_cache
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent ON public.agent_knowledge_cache 
    USING btree (agent_name, is_active, relevance_score DESC);
    
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_type ON public.agent_knowledge_cache 
    USING btree (knowledge_type, is_active);
    
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_usage ON public.agent_knowledge_cache 
    USING btree (usage_count DESC, last_used DESC);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_embedding ON public.agent_knowledge_cache 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 5. Fast agent matching cache table
CREATE TABLE IF NOT EXISTS public.agent_match_cache (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    query_hash text NOT NULL, -- Hash of the user query
    query_text text NOT NULL,
    matched_agents text[] NOT NULL, -- Array of matched agent names in order
    match_scores float[] DEFAULT '{}', -- Corresponding match scores
    threshold_used float NOT NULL,
    embedding vector(384), -- Query embedding for similarity searches
    created_at timestamp with time zone NULL DEFAULT now(),
    expires_at timestamp with time zone NULL DEFAULT (now() + interval '1 hour'),
    CONSTRAINT agent_match_cache_pkey PRIMARY KEY (id),
    CONSTRAINT unique_query_hash_threshold UNIQUE (query_hash, threshold_used)
) TABLESPACE pg_default;

-- Indexes for agent_match_cache
CREATE INDEX IF NOT EXISTS idx_agent_match_cache_query ON public.agent_match_cache 
    USING btree (query_hash, expires_at);
    
CREATE INDEX IF NOT EXISTS idx_agent_match_cache_expires ON public.agent_match_cache 
    USING btree (expires_at);

-- Auto-cleanup expired entries
CREATE OR REPLACE FUNCTION cleanup_expired_agent_matches()
RETURNS void AS $$
BEGIN
    DELETE FROM public.agent_match_cache WHERE expires_at < now();
END;
$$ LANGUAGE plpgsql;

-- 6. Group chat and agent collaboration tables
CREATE TABLE IF NOT EXISTS public.group_conversations (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    group_id text NOT NULL,
    session_id text NOT NULL,
    participants jsonb NOT NULL, -- Array of user_ids and agent_names
    conversation_type text DEFAULT 'group_chat', -- 'group_chat', 'agent_collaboration'
    group_context jsonb DEFAULT '{}'::jsonb,
    current_speaker text NULL, -- Current active speaker
    speaker_queue text[] DEFAULT '{}', -- Queue of next speakers
    group_state text DEFAULT 'active', -- 'active', 'paused', 'completed'
    created_at timestamp with time zone NULL DEFAULT now(),
    updated_at timestamp with time zone NULL DEFAULT now(),
    CONSTRAINT group_conversations_pkey PRIMARY KEY (id),
    CONSTRAINT unique_group_session UNIQUE (group_id, session_id)
) TABLESPACE pg_default;

-- Indexes for group_conversations
CREATE INDEX IF NOT EXISTS idx_group_conversations_group ON public.group_conversations 
    USING btree (group_id, group_state, updated_at DESC);

-- GIN index for participants queries
CREATE INDEX IF NOT EXISTS idx_group_conversations_participants ON public.group_conversations 
    USING gin (participants);

-- 7. Message routing and agent coordination
CREATE TABLE IF NOT EXISTS public.message_routing (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    session_id text NOT NULL,
    user_id text NOT NULL,
    message_id uuid NOT NULL, -- Reference to chat_history
    source_agent text NULL,
    target_agents text[] NOT NULL,
    routing_strategy text DEFAULT 'sequential', -- 'sequential', 'parallel', 'conditional'
    routing_context jsonb DEFAULT '{}'::jsonb,
    status text DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at timestamp with time zone NULL DEFAULT now(),
    completed_at timestamp with time zone NULL,
    CONSTRAINT message_routing_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Indexes for message_routing
CREATE INDEX IF NOT EXISTS idx_message_routing_session ON public.message_routing 
    USING btree (session_id, status, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_message_routing_status ON public.message_routing 
    USING btree (status, created_at);

-- 8. Performance monitoring table
CREATE TABLE IF NOT EXISTS public.performance_metrics (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    operation_type text NOT NULL, -- 'agent_match', 'embedding_generation', 'chat_response'
    operation_details jsonb DEFAULT '{}'::jsonb,
    execution_time_ms integer NOT NULL,
    success boolean DEFAULT true,
    error_message text NULL,
    created_at timestamp with time zone NULL DEFAULT now(),
    CONSTRAINT performance_metrics_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Indexes for performance monitoring
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON public.performance_metrics 
    USING btree (operation_type, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_performance_metrics_time ON public.performance_metrics 
    USING btree (execution_time_ms DESC, created_at DESC);

-- 9. Optimized website_data with better indexing
ALTER TABLE public.website_data 
ADD COLUMN IF NOT EXISTS analysis_embedding vector(384),
ADD COLUMN IF NOT EXISTS content_type text DEFAULT 'website',
ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'completed';

-- Better indexes for website_data
CREATE INDEX IF NOT EXISTS idx_website_data_user_status ON public.website_data 
    USING btree (user_id, processing_status, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_website_data_content_type ON public.website_data 
    USING btree (content_type, processing_status);

-- Vector similarity for website analysis
CREATE INDEX IF NOT EXISTS idx_website_data_embedding ON public.website_data 
    USING ivfflat (analysis_embedding vector_cosine_ops) WITH (lists = 50)
    WHERE analysis_embedding IS NOT NULL;

-- 10. Triggers for automatic updates

-- Update timestamps automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
DROP TRIGGER IF EXISTS update_client_context_updated_at ON public.client_context;
CREATE TRIGGER update_client_context_updated_at 
    BEFORE UPDATE ON public.client_context 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversation_context_updated_at ON public.conversation_context;
CREATE TRIGGER update_conversation_context_updated_at 
    BEFORE UPDATE ON public.conversation_context 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_knowledge_cache_updated_at ON public.agent_knowledge_cache;
CREATE TRIGGER update_agent_knowledge_cache_updated_at 
    BEFORE UPDATE ON public.agent_knowledge_cache 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 11. Useful functions for fast queries

-- Get client context with similarity search
CREATE OR REPLACE FUNCTION get_client_context_similarity(
    client_id_param text,
    query_embedding vector(384),
    similarity_threshold float DEFAULT 0.7,
    limit_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    context_type text,
    content jsonb,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.id,
        cc.context_type,
        cc.content,
        1 - (cc.embedding <=> query_embedding) as similarity
    FROM public.client_context cc
    WHERE cc.client_id = client_id_param 
        AND cc.is_active = true
        AND 1 - (cc.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY cc.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get agent knowledge with usage tracking
CREATE OR REPLACE FUNCTION get_agent_knowledge_smart(
    agent_name_param text,
    query_embedding vector(384),
    similarity_threshold float DEFAULT 0.7,
    limit_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float,
    relevance_score float
) AS $$
BEGIN
    -- Update usage statistics
    UPDATE public.agent_knowledge_cache 
    SET usage_count = usage_count + 1, last_used = now()
    WHERE agent_name = agent_name_param 
        AND is_active = true
        AND 1 - (embedding <=> query_embedding) >= similarity_threshold;
    
    -- Return results
    RETURN QUERY
    SELECT 
        akc.id,
        akc.content,
        akc.metadata,
        1 - (akc.embedding <=> query_embedding) as similarity,
        akc.relevance_score
    FROM public.agent_knowledge_cache akc
    WHERE akc.agent_name = agent_name_param 
        AND akc.is_active = true
        AND 1 - (akc.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY 
        (1 - (akc.embedding <=> query_embedding)) * akc.relevance_score DESC,
        akc.usage_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE public.client_context IS 'Optimized client context storage with vector embeddings for fast similarity search';
COMMENT ON TABLE public.conversation_context IS 'Enhanced conversation context supporting group chats and agent collaboration';
COMMENT ON TABLE public.agent_knowledge_cache IS 'Optimized agent knowledge base with usage tracking and smart caching';
COMMENT ON TABLE public.agent_match_cache IS 'Fast cache for agent matching results to reduce computation overhead';
COMMENT ON TABLE public.group_conversations IS 'Support for group chats between users and multiple agents';
COMMENT ON TABLE public.message_routing IS 'Intelligent message routing for complex conversation flows';
COMMENT ON TABLE public.performance_metrics IS 'Performance monitoring for optimization insights';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;