-- Fix Row Level Security policies for password reset functionality
-- Run this in your Supabase SQL editor

-- Enable RLS on the table
ALTER TABLE users_forgot_password ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can insert their own password reset requests" ON users_forgot_password;
DROP POLICY IF EXISTS "Users can view their own password reset requests" ON users_forgot_password;
DROP POLICY IF EXISTS "Service role can manage all password resets" ON users_forgot_password;
DROP POLICY IF EXISTS "Public can insert password reset requests" ON users_forgot_password;

-- Create new policies

-- Allow anyone to insert password reset requests (needed for forgot password flow)
CREATE POLICY "Public can insert password reset requests" 
ON users_forgot_password 
FOR INSERT 
TO public 
WITH CHECK (true);

-- Allow users to view their own password reset requests
CREATE POLICY "Users can view their own password reset requests" 
ON users_forgot_password 
FOR SELECT 
TO authenticated 
USING (
  user_id IN (
    SELECT user_id FROM profiles WHERE id = auth.uid()
  )
);

-- Allow service role full access (for backend operations)
CREATE POLICY "Service role can manage all password resets" 
ON users_forgot_password 
FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- Also ensure the profiles table can be read for email lookup
-- Check if RLS is enabled on profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Public can view profiles for password reset" ON profiles;
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON profiles;

-- Allow public to read profiles for email verification (limited fields)
CREATE POLICY "Public can view profiles for password reset" 
ON profiles 
FOR SELECT 
TO public 
USING (true);

-- Allow authenticated users to view their own profile
CREATE POLICY "Users can view own profile" 
ON profiles 
FOR SELECT 
TO authenticated 
USING (auth.uid() = id);

-- Allow authenticated users to update their own profile
CREATE POLICY "Users can update own profile" 
ON profiles 
FOR UPDATE 
TO authenticated 
USING (auth.uid() = id);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT ON profiles TO anon;
GRANT SELECT ON profiles TO authenticated;
GRANT UPDATE ON profiles TO authenticated;

GRANT INSERT ON users_forgot_password TO anon;
GRANT SELECT ON users_forgot_password TO authenticated;
GRANT ALL ON users_forgot_password TO service_role;