-- UPDATE EXISTING DATABASE FOR BUSINESS SETUP WORKFLOW
-- Run this SQL to add business setup functionality to your existing tables

-- 1. Add the highlevel_tokens column to existing table (if not exists)
ALTER TABLE public.squidgy_agent_business_setup 
ADD COLUMN IF NOT EXISTS highlevel_tokens jsonb DEFAULT '{}'::jsonb;

-- 2. Update the setup_type constraints to include BusinessSetup
ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS chk_setup_type_values;

ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS valid_setup_types;

ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT chk_setup_type_values CHECK (
    (setup_type)::text = ANY (
        ARRAY[
            'agent_config'::character varying,
            'SolarSetup'::character varying,
            'CalendarSetup'::character varying,
            'NotificationSetup'::character varying,
            'GHLSetup'::character varying,
            'FacebookIntegration'::character varying,
            'BusinessSetup'::character varying  -- NEW: For business workflow
        ]::text[]
    )
);

-- 3. Create the new business information table
CREATE TABLE IF NOT EXISTS public.squidgy_business_information (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_user_id UUID NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    
    -- Business Information (from the form)
    business_name VARCHAR(255) NOT NULL,
    business_address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'United States',
    postal_code VARCHAR(20) NOT NULL,
    business_logo_url TEXT NULL,
    
    -- HighLevel Integration Details
    snapshot_id VARCHAR(255) NULL,
    ghl_location_id VARCHAR(255) NULL,
    ghl_user_email VARCHAR(255) NULL,
    ghl_user_password VARCHAR(255) NULL,
    ghl_user_id VARCHAR(255) NULL,
    
    -- Automation Status Tracking
    setup_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    automation_started_at TIMESTAMP WITH TIME ZONE NULL,
    automation_completed_at TIMESTAMP WITH TIME ZONE NULL,
    automation_error TEXT NULL,
    
    -- Integration Results
    pit_token TEXT NULL,
    access_token_expires_at TIMESTAMP WITH TIME ZONE NULL,
    firebase_token_available BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_enabled BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT unique_firm_agent_business UNIQUE (firm_user_id, agent_id),
    CONSTRAINT chk_business_setup_status CHECK (
        setup_status IN ('pending', 'location_created', 'user_created', 'automation_running', 'completed', 'failed')
    )
);

-- 4. Create indexes for the new table
CREATE INDEX IF NOT EXISTS idx_business_firm_user ON public.squidgy_business_information (firm_user_id);
CREATE INDEX IF NOT EXISTS idx_business_agent ON public.squidgy_business_information (agent_id);
CREATE INDEX IF NOT EXISTS idx_business_status ON public.squidgy_business_information (setup_status);
CREATE INDEX IF NOT EXISTS idx_business_ghl_location ON public.squidgy_business_information (ghl_location_id);
CREATE INDEX IF NOT EXISTS idx_business_automation_status ON public.squidgy_business_information (firm_user_id, agent_id, setup_status);
CREATE INDEX IF NOT EXISTS idx_business_pending ON public.squidgy_business_information (setup_status, created_at) WHERE setup_status = 'pending';

-- 5. Add new indexes for the highlevel_tokens column
CREATE INDEX IF NOT EXISTS idx_agent_setup_highlevel_tokens ON public.squidgy_agent_business_setup USING gin (highlevel_tokens);
CREATE INDEX IF NOT EXISTS idx_agent_setup_pit_token ON public.squidgy_agent_business_setup (firm_user_id, agent_id) 
WHERE (highlevel_tokens->>'private_integration_token' IS NOT NULL);

-- 6. Create an updated trigger for the updated_at column
CREATE OR REPLACE FUNCTION update_business_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists, then create new one
DROP TRIGGER IF EXISTS trigger_business_updated_at ON public.squidgy_business_information;
CREATE TRIGGER trigger_business_updated_at
    BEFORE UPDATE ON public.squidgy_business_information
    FOR EACH ROW
    EXECUTE FUNCTION update_business_updated_at();

-- 7. Create a monitoring view that combines both tables
CREATE OR REPLACE VIEW public.business_setup_status AS
SELECT 
    bi.id,
    bi.firm_user_id,
    bi.agent_id,
    bi.business_name,
    bi.setup_status,
    bi.ghl_location_id,
    bi.ghl_user_email,
    bi.pit_token IS NOT NULL as has_pit_token,
    bi.automation_started_at,
    bi.automation_completed_at,
    bi.created_at,
    -- Get tokens from the existing setup table
    abs.highlevel_tokens->>'private_integration_token' as stored_pit_token,
    abs.highlevel_tokens->>'access_token' as stored_access_token,
    (abs.highlevel_tokens->>'firebase_token') IS NOT NULL as has_firebase_token,
    abs.highlevel_tokens as all_tokens
FROM public.squidgy_business_information bi
LEFT JOIN public.squidgy_agent_business_setup abs 
    ON bi.firm_user_id = abs.firm_user_id 
    AND bi.agent_id = abs.agent_id 
    AND abs.setup_type = 'GHLSetup';

-- 8. Add helpful comments
COMMENT ON TABLE public.squidgy_business_information IS 'Business setup workflow tracking - from form submission to automation completion';
COMMENT ON COLUMN public.squidgy_business_information.setup_status IS 'Workflow status: pending → user_created → automation_running → completed/failed';
COMMENT ON COLUMN public.squidgy_business_information.snapshot_id IS 'HighLevel snapshot ID used to create the location';
COMMENT ON COLUMN public.squidgy_business_information.ghl_location_id IS 'Generated HighLevel location ID from snapshot';
COMMENT ON COLUMN public.squidgy_business_information.ghl_user_email IS 'Generated email: businessname+locationid@domain.com';
COMMENT ON COLUMN public.squidgy_agent_business_setup.highlevel_tokens IS 'Complete HighLevel tokens JSON: PIT, access, Firebase, expiry info';

-- 9. Verify setup with a test query
-- SELECT 'Database setup completed successfully!' as status;

-- 10. Show what tables are ready
-- SELECT table_name, table_type 
-- FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN ('squidgy_business_information', 'squidgy_agent_business_setup')
-- ORDER BY table_name;

-- SETUP COMPLETE!
-- You can now run: python3 business_setup_complete_api.py