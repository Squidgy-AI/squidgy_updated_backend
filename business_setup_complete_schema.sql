-- Complete Business Setup Database Schema
-- This handles the full business information → location → user → automation flow

-- 1. Business Information Table (from the form screenshot)
CREATE TABLE IF NOT EXISTS public.squidgy_business_information (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_user_id UUID NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    
    -- Business Information (from form)
    business_name VARCHAR(255) NOT NULL,
    business_address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'United States',
    postal_code VARCHAR(20) NOT NULL,
    business_logo_url TEXT NULL,
    
    -- HighLevel Integration Details
    snapshot_id VARCHAR(255) NULL, -- The snapshot ID to use for location creation
    ghl_location_id VARCHAR(255) NULL, -- Created location ID
    ghl_user_email VARCHAR(255) NULL, -- Generated user email
    ghl_user_password VARCHAR(255) NULL, -- Generated user password
    ghl_user_id VARCHAR(255) NULL, -- Created user ID
    
    -- Automation Status
    setup_status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, location_created, user_created, automation_running, completed, failed
    automation_started_at TIMESTAMP WITH TIME ZONE NULL,
    automation_completed_at TIMESTAMP WITH TIME ZONE NULL,
    automation_error TEXT NULL,
    
    -- Integration Results
    pit_token TEXT NULL, -- Private Integration Token
    access_token_expires_at TIMESTAMP WITH TIME ZONE NULL,
    firebase_token_available BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_enabled BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT unique_firm_agent_business UNIQUE (firm_user_id, agent_id),
    CONSTRAINT chk_setup_status CHECK (setup_status IN ('pending', 'location_created', 'user_created', 'automation_running', 'completed', 'failed'))
);

-- 2. Indexes for Business Information
CREATE INDEX IF NOT EXISTS idx_business_firm_user ON public.squidgy_business_information (firm_user_id);
CREATE INDEX IF NOT EXISTS idx_business_agent ON public.squidgy_business_information (agent_id);
CREATE INDEX IF NOT EXISTS idx_business_status ON public.squidgy_business_information (setup_status);
CREATE INDEX IF NOT EXISTS idx_business_ghl_location ON public.squidgy_business_information (ghl_location_id);
CREATE INDEX IF NOT EXISTS idx_business_automation_status ON public.squidgy_business_information (firm_user_id, agent_id, setup_status);
CREATE INDEX IF NOT EXISTS idx_business_pending ON public.squidgy_business_information (setup_status, created_at) WHERE setup_status = 'pending';

-- 3. Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_business_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_business_updated_at
    BEFORE UPDATE ON public.squidgy_business_information
    FOR EACH ROW
    EXECUTE FUNCTION update_business_updated_at();

-- 4. Add new setup_type to existing table for consistency
ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS chk_setup_type_values;

ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS valid_setup_types;

ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT chk_setup_type_values CHECK (
    setup_type::text = ANY (ARRAY[
        'agent_config'::character varying,
        'SolarSetup'::character varying,
        'CalendarSetup'::character varying,
        'NotificationSetup'::character varying,
        'GHLSetup'::character varying,
        'FacebookIntegration'::character varying,
        'BusinessSetup'::character varying  -- NEW: For business information workflow
    ]::text[])
);

-- 5. Comments for documentation
COMMENT ON TABLE public.squidgy_business_information IS 'Stores business information and tracks the complete setup workflow from form submission to automation completion';
COMMENT ON COLUMN public.squidgy_business_information.setup_status IS 'Tracks workflow: pending → location_created → user_created → automation_running → completed/failed';
COMMENT ON COLUMN public.squidgy_business_information.snapshot_id IS 'HighLevel snapshot ID used to create the location';
COMMENT ON COLUMN public.squidgy_business_information.ghl_location_id IS 'Generated HighLevel location ID';
COMMENT ON COLUMN public.squidgy_business_information.ghl_user_email IS 'Generated email for HighLevel user (format: businessname+locationid@domain.com)';
COMMENT ON COLUMN public.squidgy_business_information.ghl_user_password IS 'Generated secure password for HighLevel user';

-- 6. View for easy querying of complete business setup status
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
    abs.highlevel_tokens->>'private_integration_token' as stored_pit_token,
    abs.highlevel_tokens->>'access_token' as stored_access_token,
    (abs.highlevel_tokens->>'tokens'->>'firebase_token') IS NOT NULL as has_firebase_token
FROM public.squidgy_business_information bi
LEFT JOIN public.squidgy_agent_business_setup abs 
    ON bi.firm_user_id = abs.firm_user_id 
    AND bi.agent_id = abs.agent_id 
    AND abs.setup_type = 'GHLSetup';

-- 7. Sample query for monitoring automation progress
-- SELECT * FROM business_setup_status WHERE setup_status IN ('automation_running', 'pending') ORDER BY created_at DESC;