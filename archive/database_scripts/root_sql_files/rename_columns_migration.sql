-- Migration: Rename mixed-case and space-containing columns to lowercase_underscore format
-- Run this on Supabase to fix column naming convention

-- Rename "PIT_Token" to pit_token
ALTER TABLE public.ghl_subaccounts
RENAME COLUMN "PIT_Token" TO pit_token;

-- Rename "Firebase Token" to firebase_token
ALTER TABLE public.ghl_subaccounts
RENAME COLUMN "Firebase Token" TO firebase_token;

-- Rename "firebase token time" to firebase_token_time
ALTER TABLE public.ghl_subaccounts
RENAME COLUMN "firebase token time" TO firebase_token_time;

-- Verify the changes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ghl_subaccounts'
  AND column_name IN ('pit_token', 'firebase_token', 'firebase_token_time')
ORDER BY column_name;
