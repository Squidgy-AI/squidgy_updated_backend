-- Add facebook_account_id column to squidgy_agent_business_setup table
-- This stores the Facebook account ID from GHL for use with social-media-posting API

ALTER TABLE squidgy_agent_business_setup 
ADD COLUMN IF NOT EXISTS facebook_account_id TEXT;

-- Add index for better performance when querying by facebook_account_id
CREATE INDEX IF NOT EXISTS idx_agent_business_setup_facebook_account_id 
ON squidgy_agent_business_setup (facebook_account_id) 
WHERE facebook_account_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN squidgy_agent_business_setup.facebook_account_id 
IS 'Facebook account ID from GHL social-media-posting API, used for page attachment operations';