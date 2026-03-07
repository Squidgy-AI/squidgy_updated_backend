-- QUICK DATABASE SETUP FOR BUSINESS WORKFLOW
-- Run this SQL directly in your database to set up the business setup tables

-- 1. Create the main business information table
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
    snapshot_id VARCHAR(255) NULL,
    ghl_location_id VARCHAR(255) NULL,
    ghl_user_email VARCHAR(255) NULL,
    ghl_user_password VARCHAR(255) NULL,
    ghl_user_id VARCHAR(255) NULL,
    
    -- Automation Status
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
    CONSTRAINT chk_setup_status CHECK (setup_status IN ('pending', 'location_created', 'user_created', 'automation_running', 'completed', 'failed'))
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_business_firm_user ON public.squidgy_business_information (firm_user_id);
CREATE INDEX IF NOT EXISTS idx_business_agent ON public.squidgy_business_information (agent_id);
CREATE INDEX IF NOT EXISTS idx_business_status ON public.squidgy_business_information (setup_status);
CREATE INDEX IF NOT EXISTS idx_business_ghl_location ON public.squidgy_business_information (ghl_location_id);

-- 3. Add the new setup_type to existing table
ALTER TABLE public.squidgy_agent_business_setup 
DROP CONSTRAINT IF EXISTS chk_setup_type_values;

ALTER TABLE public.squidgy_agent_business_setup 
ADD CONSTRAINT chk_setup_type_values CHECK (
    setup_type::text = ANY (ARRAY[
        'agent_config'::character varying,
        'SolarSetup'::character varying,
        'CalendarSetup'::character varying,
        'NotificationSetup'::character varying,
        'GHLSetup'::character varying,
        'FacebookIntegration'::character varying,
        'BusinessSetup'::character varying
    ]::text[])
);

-- 4. Create a view for easy monitoring
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
    abs.highlevel_tokens->>'private_integration_token' as stored_pit_token
FROM public.squidgy_business_information bi
LEFT JOIN public.squidgy_agent_business_setup abs 
    ON bi.firm_user_id = abs.firm_user_id 
    AND bi.agent_id = abs.agent_id 
    AND abs.setup_type = 'GHLSetup';

-- 5. Add comments
COMMENT ON TABLE public.squidgy_business_information IS 'Business setup workflow tracking table';
COMMENT ON COLUMN public.squidgy_business_information.setup_status IS 'Workflow status: pending → user_created → automation_running → completed/failed';

-- Done! Your database is ready for the business setup workflow.