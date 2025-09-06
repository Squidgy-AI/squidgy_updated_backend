-- Fix safe_insert_chat_history function to include agent_id parameter
-- This fixes the "null value in column 'agent_id' violates not-null constraint" error

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

COMMENT ON FUNCTION safe_insert_chat_history IS 'Safely insert chat history with automatic duplicate prevention and agent_id support';