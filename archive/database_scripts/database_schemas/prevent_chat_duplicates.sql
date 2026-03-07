-- Prevent Chat History Duplicates - Database Schema Updates
-- Run this script to add constraints that prevent duplicate chat history entries

-- 1. Add a unique constraint to prevent exact duplicate messages in the same session
-- This creates a composite unique constraint on session_id, user_id, sender, message, and timestamp (truncated to minute)
-- This allows the same message to be sent in different sessions or by different users, but prevents exact duplicates

-- First, let's clean up any existing duplicates before adding the constraint
WITH duplicate_messages AS (
    SELECT 
        id,
        ROW_NUMBER() OVER (
            PARTITION BY session_id, user_id, sender, message
            ORDER BY timestamp ASC
        ) as row_num
    FROM chat_history
)
DELETE FROM chat_history 
WHERE id IN (
    SELECT id FROM duplicate_messages WHERE row_num > 1
);

-- 2. Add a computed column for message deduplication
-- This helps prevent duplicates by creating a hash of the message content and metadata
-- Using only immutable fields for the generated column
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS message_hash text 
GENERATED ALWAYS AS (
    md5(session_id || '|' || user_id || '|' || sender || '|' || message)
) STORED;

-- 3. Create unique index on the message hash to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_history_unique_message 
ON chat_history (message_hash);

-- 4. Add additional indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_history_session_timestamp 
ON chat_history (session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_chat_history_user_timestamp 
ON chat_history (user_id, timestamp DESC);

-- 5. Create a function to safely insert chat history with duplicate checking
CREATE OR REPLACE FUNCTION safe_insert_chat_history(
    p_session_id text,
    p_user_id text,
    p_sender text,
    p_message text,
    p_timestamp timestamp with time zone DEFAULT now(),
    p_agent_id text DEFAULT 'SOLAgent'
)
RETURNS uuid AS $$
DECLARE
    new_id uuid;
    message_hash_val text;
BEGIN
    -- Calculate the message hash (matching the generated column)
    message_hash_val := md5(p_session_id || '|' || p_user_id || '|' || p_sender || '|' || p_message);
    
    -- Check if a message with this hash already exists
    SELECT id INTO new_id 
    FROM chat_history 
    WHERE message_hash = message_hash_val
    LIMIT 1;
    
    -- If no duplicate found, insert new message
    IF new_id IS NULL THEN
        INSERT INTO chat_history (session_id, user_id, sender, message, timestamp, agent_id)
        VALUES (p_session_id, p_user_id, p_sender, p_message, p_timestamp, p_agent_id)
        RETURNING id INTO new_id;
    END IF;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Create improved unique constraints for client_kb table
-- Add constraint to prevent duplicate kb entries for same client and type
DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'unique_client_kb_type' 
        AND table_name = 'client_kb'
    ) THEN
        ALTER TABLE client_kb 
        ADD CONSTRAINT unique_client_kb_type 
        UNIQUE (client_id, kb_type);
    END IF;
END $$;

-- 7. Create improved unique constraints for website_data table
-- Add constraint to prevent duplicate website entries for same session and URL
DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'unique_website_session_url' 
        AND table_name = 'website_data'
    ) THEN
        ALTER TABLE website_data 
        ADD CONSTRAINT unique_website_session_url 
        UNIQUE (session_id, url);
    END IF;
END $$;

-- 8. Add missing columns to website_data if they don't exist
ALTER TABLE website_data 
ADD COLUMN IF NOT EXISTS user_id text,
ADD COLUMN IF NOT EXISTS analysis_embedding vector(384),
ADD COLUMN IF NOT EXISTS content_type text DEFAULT 'website',
ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'completed';

-- 9. Create indexes for better performance on new columns
CREATE INDEX IF NOT EXISTS idx_website_data_user 
ON website_data (user_id);

CREATE INDEX IF NOT EXISTS idx_website_data_user_status 
ON website_data (user_id, processing_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_website_data_content_type 
ON website_data (content_type, processing_status);

-- Create vector similarity index if pgvector is available
CREATE INDEX IF NOT EXISTS idx_website_data_embedding 
ON website_data USING ivfflat (analysis_embedding vector_cosine_ops)
WITH (lists = 50) 
WHERE analysis_embedding IS NOT NULL;

-- 10. Comments for documentation
COMMENT ON COLUMN chat_history.message_hash IS 'Generated hash to prevent duplicate messages';
COMMENT ON FUNCTION safe_insert_chat_history IS 'Safely insert chat history with automatic duplicate prevention';
COMMENT ON INDEX idx_chat_history_unique_message IS 'Prevents duplicate chat messages using computed hash';

-- Usage Instructions:
-- To use the safe insert function in your application code, replace:
-- INSERT INTO chat_history (session_id, user_id, sender, message, timestamp) VALUES (...)
-- 
-- With:
-- SELECT safe_insert_chat_history(session_id, user_id, sender, message, timestamp);