-- Queries to completely delete sa@squidgy.ai from all Supabase tables
-- Run these in order to clean up the user completely

-- 1. Delete from profiles table (if exists)
DELETE FROM public.profiles 
WHERE email = 'sa@squidgy.ai';

-- 2. Delete from invitations table (if exists as sender or recipient)
DELETE FROM public.invitations 
WHERE sender_id IN (
    SELECT user_id FROM public.profiles WHERE email = 'sa@squidgy.ai'
) OR recipient_email = 'sa@squidgy.ai';

-- 3. Delete from any other custom tables that might reference the user
-- Add more DELETE statements here for your custom tables as needed

-- 4. Delete from auth.users table (REQUIRES SERVICE ROLE KEY)
-- This is the main auth table and requires admin access
-- You'll need to run this with a service role key or through Supabase Dashboard

-- Option A: Using SQL Editor with service role key
DELETE FROM auth.users 
WHERE email = 'sa@squidgy.ai';

-- Option B: Using Supabase Dashboard
-- Go to Authentication → Users → Find sa@squidgy.ai → Delete

-- 5. Verification queries to check if user is completely removed
SELECT 'Checking profiles:' as table_name, count(*) as remaining_records
FROM public.profiles 
WHERE email = 'sa@squidgy.ai'

UNION ALL

SELECT 'Checking invitations:', count(*)
FROM public.invitations 
WHERE recipient_email = 'sa@squidgy.ai'

UNION ALL

SELECT 'Checking auth.users:', count(*)
FROM auth.users 
WHERE email = 'sa@squidgy.ai';

-- Expected result: All counts should be 0