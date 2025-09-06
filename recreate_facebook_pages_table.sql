-- Recreate squidgy_facebook_pages table with proper UUID types and clean structure
-- Drop redundant ghl_location_id and ghl_user_id columns (user_id IS ghl_user_id, location_id IS ghl_location_id)

-- 1. Drop existing table (if exists)
DROP TABLE IF EXISTS public.squidgy_facebook_pages CASCADE;

-- 2. Create new table with UUID types and clean structure
CREATE TABLE public.squidgy_facebook_pages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  firm_user_id uuid NOT NULL,                          -- Changed: TEXT → UUID
  location_id uuid NOT NULL,                           -- Changed: TEXT → UUID (GHL location ID) 
  user_id uuid NOT NULL,                               -- Changed: TEXT → UUID (same as ghl_user_id)
  page_id text NOT NULL,                               -- Keep: Facebook page ID (stays text)
  page_name text NOT NULL,                             -- Keep: Facebook page name
  page_access_token text NULL,                         -- Keep: Facebook page token
  page_category text NULL,                             -- Keep: Facebook page category
  instagram_business_account_id text NULL,             -- Keep: Instagram account ID
  is_instagram_available boolean NULL DEFAULT false,   -- Keep: Instagram availability
  is_connected_to_ghl boolean NULL DEFAULT false,      -- Keep: Connection status
  connected_at timestamp with time zone NULL,          -- Keep: Connection timestamp
  raw_page_data jsonb NULL,                            -- Keep: Full Facebook page data
  created_at timestamp with time zone NULL DEFAULT now(),
  updated_at timestamp with time zone NULL DEFAULT now(),
  
  -- Constraints
  CONSTRAINT squidgy_facebook_pages_pkey PRIMARY KEY (id),
  CONSTRAINT squidgy_facebook_pages_location_page_unique UNIQUE (location_id, page_id),
  CONSTRAINT squidgy_facebook_pages_firm_user_page_unique UNIQUE (firm_user_id, page_id)
) TABLESPACE pg_default;

-- 3. Create indexes for optimal query performance
CREATE INDEX idx_facebook_pages_firm_user 
ON public.squidgy_facebook_pages USING btree (firm_user_id);

CREATE INDEX idx_facebook_pages_location 
ON public.squidgy_facebook_pages USING btree (location_id);

CREATE INDEX idx_facebook_pages_user 
ON public.squidgy_facebook_pages USING btree (user_id);

CREATE INDEX idx_facebook_pages_page_id 
ON public.squidgy_facebook_pages USING btree (page_id);

CREATE INDEX idx_facebook_pages_connected 
ON public.squidgy_facebook_pages USING btree (firm_user_id, is_connected_to_ghl);

CREATE INDEX idx_facebook_pages_location_connected 
ON public.squidgy_facebook_pages USING btree (location_id, is_connected_to_ghl);

-- 4. Add helpful comments
COMMENT ON TABLE public.squidgy_facebook_pages IS 
'Facebook pages storage with UUID types for consistency. location_id = GHL location, user_id = GHL user';

COMMENT ON COLUMN public.squidgy_facebook_pages.firm_user_id IS 
'UUID of the firm user (converted from string format like "80b957fc-de1d-4f28-920c-41e0e2e28e5e")';

COMMENT ON COLUMN public.squidgy_facebook_pages.location_id IS 
'GHL location ID as UUID (was ghl_location_id)';

COMMENT ON COLUMN public.squidgy_facebook_pages.user_id IS 
'GHL user ID as UUID (was ghl_user_id)';

COMMENT ON COLUMN public.squidgy_facebook_pages.page_id IS 
'Facebook page ID (stays as text since Facebook uses string IDs)';

-- 5. Create a view for easier migration queries (optional)
CREATE OR REPLACE VIEW facebook_pages_summary AS
SELECT 
    firm_user_id,
    location_id,
    user_id,
    page_id,
    page_name,
    is_connected_to_ghl,
    connected_at,
    created_at
FROM public.squidgy_facebook_pages
ORDER BY created_at DESC;

-- Success message
SELECT 
    'squidgy_facebook_pages table recreated with UUID types!' as result,
    'Removed: ghl_location_id, ghl_user_id (now location_id and user_id are the GHL IDs)' as changes,
    'All IDs except page_id are now UUID type' as data_types;