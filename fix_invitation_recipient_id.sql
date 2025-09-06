-- Fix for invitation creation foreign key constraint error
-- The issue: recipient_id must be NULL for new users who don't exist yet

-- Option 1: Make recipient_id nullable (it already is, so this is just documentation)
-- The recipient_id column is already nullable, which is correct

-- Option 2: Ensure the application code sets recipient_id to NULL for new user invitations
-- When creating an invitation for a user who doesn't exist yet:
-- - Set recipient_id = NULL
-- - Set recipient_email = the email address
-- - When the user accepts the invitation and creates their account, update recipient_id

-- Example of correct invitation creation for new users:
/*
INSERT INTO invitations (
    sender_id,
    recipient_id,  -- This should be NULL for new users
    recipient_email,
    sender_company_id,
    group_id,
    status,
    token
) VALUES (
    'sender-user-id',
    NULL,  -- NULL because the recipient doesn't exist yet
    'newuser@example.com',
    'company-id',
    NULL,
    'pending',
    'unique-token-here'
);
*/

-- To check existing invitations with issues:
SELECT 
    i.id,
    i.recipient_id,
    i.recipient_email,
    i.status,
    p.user_id as profile_exists
FROM invitations i
LEFT JOIN profiles p ON i.recipient_id = p.user_id
WHERE i.recipient_id IS NOT NULL 
  AND p.user_id IS NULL;

-- To fix existing invitations that have invalid recipient_ids:
UPDATE invitations 
SET recipient_id = NULL
WHERE recipient_id IS NOT NULL
  AND recipient_id NOT IN (SELECT user_id FROM profiles);

-- Function to safely create invitations
CREATE OR REPLACE FUNCTION create_invitation(
    p_sender_id UUID,
    p_recipient_email TEXT,
    p_sender_company_id UUID,
    p_group_id UUID DEFAULT NULL,
    p_token TEXT DEFAULT gen_random_uuid()::TEXT
) RETURNS UUID AS $$
DECLARE
    v_recipient_id UUID;
    v_invitation_id UUID;
BEGIN
    -- Check if recipient already exists
    SELECT user_id INTO v_recipient_id
    FROM profiles
    WHERE LOWER(email) = LOWER(p_recipient_email);
    
    -- Create the invitation (recipient_id will be NULL if user doesn't exist)
    INSERT INTO invitations (
        sender_id,
        recipient_id,
        recipient_email,
        sender_company_id,
        group_id,
        status,
        token
    ) VALUES (
        p_sender_id,
        v_recipient_id,  -- Will be NULL for new users
        LOWER(p_recipient_email),
        p_sender_company_id,
        p_group_id,
        'pending',
        p_token
    )
    RETURNING id INTO v_invitation_id;
    
    RETURN v_invitation_id;
END;
$$ LANGUAGE plpgsql;

-- Example usage:
-- SELECT create_invitation('sender-uuid', 'newuser@example.com', 'company-uuid');