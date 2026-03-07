-- Insert PersonalAssistant for ALL users
-- Run this in your Supabase SQL editor

-- First, let's see what users exist (uncomment to check):
-- SELECT DISTINCT firm_user_id FROM public.squidgy_agent_business_setup;

-- Insert PersonalAssistant for your specific user
INSERT INTO public.squidgy_agent_business_setup (
    firm_user_id,
    agent_id,
    agent_name,
    setup_type,
    setup_json,
    is_enabled,
    created_at,
    updated_at
) VALUES (
    '80b957fc-de1d-4f28-920c-41e0e2e28e5e',  -- Your user ID
    'PersonalAssistant',
    'Personal Assistant Bot',
    'agent_config',
    '{"description": "Your general-purpose AI assistant", "capabilities": ["general_chat", "help", "information"]}',
    true,
    NOW(),
    NOW()
) ON CONFLICT (firm_user_id, agent_id, setup_type) DO UPDATE SET
    agent_name = EXCLUDED.agent_name,
    is_enabled = EXCLUDED.is_enabled,
    updated_at = NOW();

-- If you want to add PersonalAssistant for ALL existing users who have any setup:
/*
INSERT INTO public.squidgy_agent_business_setup (
    firm_user_id,
    agent_id,
    agent_name,
    setup_type,
    setup_json,
    is_enabled,
    created_at,
    updated_at
)
SELECT DISTINCT 
    firm_user_id,
    'PersonalAssistant',
    'Personal Assistant Bot',
    'agent_config',
    '{"description": "Your general-purpose AI assistant", "capabilities": ["general_chat", "help", "information"]}',
    true,
    NOW(),
    NOW()
FROM public.squidgy_agent_business_setup
WHERE firm_user_id NOT IN (
    SELECT firm_user_id 
    FROM public.squidgy_agent_business_setup 
    WHERE agent_id = 'PersonalAssistant' AND setup_type = 'agent_config'
);
*/