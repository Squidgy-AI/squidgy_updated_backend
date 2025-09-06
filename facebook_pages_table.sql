-- Create table for storing Facebook pages data
CREATE TABLE IF NOT EXISTS squidgy_facebook_pages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    firm_user_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    page_name TEXT NOT NULL,
    page_access_token TEXT,
    page_category TEXT,
    instagram_business_account_id TEXT,
    is_instagram_available BOOLEAN DEFAULT FALSE,
    is_connected_to_ghl BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMP WITH TIME ZONE,
    raw_page_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique pages per location
    UNIQUE(location_id, page_id)
);

-- Create index for faster lookups
CREATE INDEX idx_facebook_pages_location ON squidgy_facebook_pages(location_id);
CREATE INDEX idx_facebook_pages_firm_user ON squidgy_facebook_pages(firm_user_id);

-- Add RLS policies if needed
ALTER TABLE squidgy_facebook_pages ENABLE ROW LEVEL SECURITY;