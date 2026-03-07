-- Updated schema to include highlevel_tokens JSON field
create table if not exists public.squidgy_agent_business_setup (
  firm_id uuid null,
  firm_user_id uuid not null,
  agent_id character varying(255) not null,
  agent_name character varying(255) not null,
  setup_json jsonb null default '{}'::jsonb,
  created_at timestamp with time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp with time zone null default CURRENT_TIMESTAMP,
  is_enabled boolean not null default false,
  session_id uuid null,
  setup_type character varying(50) not null,
  id uuid not null default gen_random_uuid (),
  ghl_location_id text null,
  ghl_user_id text null,
  
  -- NEW FIELD: Store all HighLevel tokens as JSON
  highlevel_tokens jsonb null default '{}'::jsonb,
  
  constraint squidgy_agent_business_setup_pkey primary key (firm_user_id, agent_id, setup_type),
  constraint unique_user_agent_setup_type unique (firm_user_id, agent_id, setup_type),
  constraint chk_setup_type_values check (
    (
      (setup_type)::text = any (
        (
          array[
            'agent_config'::character varying,
            'SolarSetup'::character varying,
            'CalendarSetup'::character varying,
            'NotificationSetup'::character varying,
            'GHLSetup'::character varying,
            'FacebookIntegration'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint valid_setup_types check (
    (
      (setup_type)::text = any (
        array[
          ('agent_config'::character varying)::text,
          ('SolarSetup'::character varying)::text,
          ('CalendarSetup'::character varying)::text,
          ('NotificationSetup'::character varying)::text,
          ('GHLSetup'::character varying)::text,
          ('FacebookIntegration'::character varying)::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

-- Add column to existing table (if table already exists)
ALTER TABLE public.squidgy_agent_business_setup 
ADD COLUMN IF NOT EXISTS highlevel_tokens jsonb DEFAULT '{}'::jsonb;

-- Existing indexes
create index IF not exists idx_public_agent_setup_firm_user on public.squidgy_agent_business_setup using btree (firm_user_id) TABLESPACE pg_default;
create index IF not exists idx_public_agent_setup_agent on public.squidgy_agent_business_setup using btree (agent_id) TABLESPACE pg_default;
create index IF not exists idx_public_agent_setup_json on public.squidgy_agent_business_setup using gin (setup_json) TABLESPACE pg_default;
create index IF not exists idx_public_agent_setup_enabled on public.squidgy_agent_business_setup using btree (firm_user_id, is_enabled) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_session_id on public.squidgy_agent_business_setup using btree (session_id) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_type on public.squidgy_agent_business_setup using btree (setup_type) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_user_type on public.squidgy_agent_business_setup using btree (firm_user_id, setup_type) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_agent_type on public.squidgy_agent_business_setup using btree (agent_id, setup_type) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_user_agent on public.squidgy_agent_business_setup using btree (firm_user_id, agent_id) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_ghl on public.squidgy_agent_business_setup using btree (firm_user_id, agent_id) TABLESPACE pg_default
where ((setup_type)::text = 'GHLSetup'::text);
create index IF not exists idx_agent_setup_facebook on public.squidgy_agent_business_setup using btree (firm_user_id, agent_id) TABLESPACE pg_default
where ((setup_type)::text = 'FacebookIntegration'::text);
create index IF not exists idx_agent_setup_ghl_location on public.squidgy_agent_business_setup using btree (ghl_location_id) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_ghl_user on public.squidgy_agent_business_setup using btree (ghl_user_id) TABLESPACE pg_default;
create index IF not exists idx_agent_setup_ghl_credentials on public.squidgy_agent_business_setup using btree (ghl_location_id, ghl_user_id) TABLESPACE pg_default;

-- NEW INDEX: For querying highlevel_tokens JSON
create index IF not exists idx_agent_setup_highlevel_tokens on public.squidgy_agent_business_setup using gin (highlevel_tokens) TABLESPACE pg_default;

-- NEW INDEX: For querying by PIT token specifically
create index IF not exists idx_agent_setup_pit_token on public.squidgy_agent_business_setup using btree (firm_user_id, agent_id) TABLESPACE pg_default
where (highlevel_tokens->>'private_integration_token' IS NOT NULL);

-- Add comment for the new column
COMMENT ON COLUMN public.squidgy_agent_business_setup.highlevel_tokens IS 'Stores all HighLevel tokens including PIT, access tokens, Firebase tokens, and expiry information';