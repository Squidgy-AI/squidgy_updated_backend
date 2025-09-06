-- Adjust Supabase Auth Rate Limits
-- Note: These settings are typically managed through the Supabase Dashboard
-- Authentication → Rate Limits section

-- If you have direct database access, you can check current rate limit settings:
-- Rate limits are usually configured in the auth.config table or through environment variables

-- Common rate limit adjustments for development:
-- 1. Email signups per hour: 50 (default is often 3-5)
-- 2. Password reset requests per hour: 20 (default is often 3-5)
-- 3. Email confirmation requests: 20 (default is often 3-5)
-- 4. SMS/OTP requests per hour: 10

-- To temporarily disable rate limiting for testing (NOT RECOMMENDED FOR PRODUCTION):
-- You would need to modify the auth server configuration, which is not accessible via SQL

-- Alternative: Create a development-specific user for testing
-- This avoids hitting rate limits during development

-- For production, implement these best practices:
-- 1. Add CAPTCHA to forms (reduces bot attempts)
-- 2. Implement client-side rate limiting (prevent rapid clicks)
-- 3. Add request throttling in your backend
-- 4. Use separate test accounts for automated testing

-- Check if a specific email is rate limited:
SELECT 
    email,
    last_sign_in_at,
    created_at,
    confirmation_sent_at
FROM auth.users
WHERE email = 'your-test-email@example.com'
ORDER BY created_at DESC
LIMIT 5;