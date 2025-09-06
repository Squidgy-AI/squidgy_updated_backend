-- Fix database constraints to allow PersonalAssistant (agent_config)
-- Run this in your Supabase SQL editor

-- Drop the restrictive constraint that only allowed progressive setup types
ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS valid_setup_types;

-- Add new constraint that allows agent_config for PersonalAssistant + progressive setup types
ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT valid_setup_types 
CHECK (setup_type IN ('agent_config', 'SolarSetup', 'CalendarSetup', 'NotificationSetup'));

-- Allow setup_type to be NULL temporarily for insert operations
ALTER TABLE public.squidgy_agent_business_setup 
ALTER COLUMN setup_type DROP NOT NULL;

-- Update any existing records that might be NULL
UPDATE public.squidgy_agent_business_setup 
SET setup_type = 'agent_config' 
WHERE setup_type IS NULL;

-- Make setup_type NOT NULL again
ALTER TABLE public.squidgy_agent_business_setup 
ALTER COLUMN setup_type SET NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN public.squidgy_agent_business_setup.setup_type IS 'Setup type: agent_config (PersonalAssistant), SolarSetup, CalendarSetup, NotificationSetup';