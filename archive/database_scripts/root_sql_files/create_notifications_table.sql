-- Create Notifications Table for GHL Messages
-- This table stores notifications from GHL when messages are received

CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- GHL Integration Fields
    ghl_location_id VARCHAR(255) NOT NULL,
    ghl_contact_id VARCHAR(255) NOT NULL,
    
    -- Message Content
    message_content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'SMS', -- SMS, Facebook, Instagram, WhatsApp, etc.
    
    -- Sender Information
    sender_name VARCHAR(255),
    sender_phone VARCHAR(50),
    sender_email VARCHAR(255),
    
    -- Conversation Tracking
    conversation_id VARCHAR(255),
    
    -- Status Tracking
    read_status BOOLEAN DEFAULT FALSE,
    responded_status BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT idx_notifications_location_contact UNIQUE (ghl_location_id, ghl_contact_id, created_at)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_notifications_ghl_location_id ON public.notifications(ghl_location_id);
CREATE INDEX IF NOT EXISTS idx_notifications_ghl_contact_id ON public.notifications(ghl_contact_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read_status ON public.notifications(read_status);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON public.notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_conversation_id ON public.notifications(conversation_id);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_notifications_location_unread 
ON public.notifications(ghl_location_id, read_status) 
WHERE read_status = FALSE;

-- Add trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notifications_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_notifications_timestamp
    BEFORE UPDATE ON public.notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_notifications_timestamp();

-- Add comment for documentation
COMMENT ON TABLE public.notifications IS 'Stores incoming messages from GHL webhooks for notification system';
COMMENT ON COLUMN public.notifications.ghl_location_id IS 'GHL Location/Account ID that received the message';
COMMENT ON COLUMN public.notifications.ghl_contact_id IS 'GHL Contact ID who sent the message';
COMMENT ON COLUMN public.notifications.message_content IS 'The actual message content from the customer';
COMMENT ON COLUMN public.notifications.message_type IS 'Platform type: SMS, Facebook, Instagram, WhatsApp, etc.';
COMMENT ON COLUMN public.notifications.read_status IS 'Whether the notification has been read by the user';
COMMENT ON COLUMN public.notifications.responded_status IS 'Whether the user has responded to this message';

-- Example data for testing (commented out)
-- INSERT INTO public.notifications (
--     ghl_location_id,
--     ghl_contact_id,
--     message_content,
--     sender_name,
--     sender_phone,
--     message_type
-- ) VALUES (
--     'loc_ABC123',
--     'contact_XYZ789',
--     'Hi, I am interested in your solar panels offer',
--     'John Doe',
--     '+1234567890',
--     'SMS'
-- );