-- GHL Registration Database Monitoring Queries
-- Use these to monitor the database during testing

-- 1. Check recent GHL subaccount records
SELECT 
  id,
  firm_user_id,
  subaccount_name,
  creation_status,
  automation_status,
  ghl_location_id,
  soma_ghl_user_id,
  creation_error,
  automation_error,
  created_at,
  updated_at
FROM ghl_subaccounts 
ORDER BY created_at DESC 
LIMIT 10;

-- 2. Check recent Facebook integration records
SELECT 
  id,
  firm_user_id,
  ghl_subaccount_id,
  automation_status,
  automation_step,
  CASE WHEN pit_token IS NOT NULL THEN 'Yes' ELSE 'No' END as has_pit_token,
  CASE WHEN access_token IS NOT NULL THEN 'Yes' ELSE 'No' END as has_access_token,
  CASE WHEN firebase_token IS NOT NULL THEN 'Yes' ELSE 'No' END as has_firebase_token,
  automation_error,
  retry_count,
  created_at,
  updated_at
FROM facebook_integrations 
ORDER BY created_at DESC 
LIMIT 10;

-- 3. Join query to see complete picture
SELECT 
  g.id as ghl_id,
  g.subaccount_name,
  g.creation_status,
  g.automation_status as ghl_automation,
  g.ghl_location_id,
  f.id as facebook_id,
  f.automation_status as facebook_automation,
  f.automation_step,
  CASE WHEN f.pit_token IS NOT NULL THEN 'Yes' ELSE 'No' END as has_pit_token,
  g.created_at
FROM ghl_subaccounts g
LEFT JOIN facebook_integrations f ON f.ghl_subaccount_id = g.id
ORDER BY g.created_at DESC 
LIMIT 5;

-- 4. Count records by status
SELECT 
  creation_status,
  automation_status,
  COUNT(*) as count
FROM ghl_subaccounts 
GROUP BY creation_status, automation_status
ORDER BY creation_status, automation_status;

-- 5. Check for errors
SELECT 
  id,
  subaccount_name,
  creation_status,
  creation_error,
  automation_error,
  created_at
FROM ghl_subaccounts 
WHERE creation_error IS NOT NULL OR automation_error IS NOT NULL
ORDER BY created_at DESC;

-- 6. Test user lookup (replace email)
SELECT user_id, company_id, email, full_name 
FROM profiles 
WHERE email = 'verify@test.com';

-- 7. Clean up test data (use carefully!)
-- DELETE FROM facebook_integrations WHERE facebook_email LIKE '%test%';
-- DELETE FROM ghl_subaccounts WHERE subaccount_name LIKE '%Test%';