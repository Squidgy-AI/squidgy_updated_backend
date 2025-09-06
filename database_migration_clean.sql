-- Clean migration for squidgy_agent_business_setup table
-- Only supports progressive setup types (no agent_config waste)
-- Run this in your Supabase SQL editor

-- Step 1: Add new columns to existing table
ALTER TABLE public.squidgy_agent_business_setup 
ADD COLUMN IF NOT EXISTS session_id UUID NULL,
ADD COLUMN IF NOT EXISTS setup_type VARCHAR(50) NULL;

-- Step 2: Since you don't want agent_config, we'll only allow progressive setup types
-- Clean up existing records - remove any that don't fit progressive setup
-- Since you don't want agent_config, we'll remove all existing records
-- They will be recreated when users complete progressive setup
DELETE FROM public.squidgy_agent_business_setup;

-- Step 3: Make setup_type NOT NULL and add constraint
ALTER TABLE public.squidgy_agent_business_setup 
ALTER COLUMN setup_type SET NOT NULL;

-- Add check constraint to only allow valid progressive setup types
ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT valid_setup_types 
CHECK (setup_type IN ('SolarSetup', 'CalendarSetup', 'NotificationSetup'));

-- Step 4: Update primary key structure for multiple setup types per user
-- Drop existing primary key
ALTER TABLE public.squidgy_agent_business_setup DROP CONSTRAINT IF EXISTS squidgy_agent_business_setup_pkey;

-- Add new id column as primary key
ALTER TABLE public.squidgy_agent_business_setup 
ADD COLUMN IF NOT EXISTS id UUID DEFAULT gen_random_uuid();

-- Create new primary key on id
ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT squidgy_agent_business_setup_pkey PRIMARY KEY (id);

-- Step 5: Create unique constraint for one setup type per user per agent
ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT unique_user_agent_setup_type UNIQUE (firm_user_id, agent_id, setup_type);

-- Step 6: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agent_setup_session_id ON public.squidgy_agent_business_setup(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_setup_type ON public.squidgy_agent_business_setup(setup_type);
CREATE INDEX IF NOT EXISTS idx_agent_setup_user_type ON public.squidgy_agent_business_setup(firm_user_id, setup_type);
CREATE INDEX IF NOT EXISTS idx_agent_setup_agent_type ON public.squidgy_agent_business_setup(agent_id, setup_type);

-- Step 7: Add comments for documentation
COMMENT ON COLUMN public.squidgy_agent_business_setup.setup_type IS 'Progressive setup type: SolarSetup, CalendarSetup, NotificationSetup';
COMMENT ON COLUMN public.squidgy_agent_business_setup.session_id IS 'Chat session ID where the setup was completed';
COMMENT ON TABLE public.squidgy_agent_business_setup IS 'User-specific progressive setup configurations for agents';