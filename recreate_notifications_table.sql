-- Drop and recreate notifications table with proper structure for webhook payload
-- This includes all fields from your webhook payload structure

-- Drop existing table and dependencies
DROP TABLE IF EXISTS public.notifications CASCADE;

-- Drop the trigger functions if they exist
DROP FUNCTION IF EXISTS update_notifications_timestamp() CASCADE;
DROP FUNCTION IF EXISTS generate_conversation_id() CASCADE;

-- Create the trigger function for timestamp updates
CREATE OR REPLACE FUNCTION update_notifications_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger function for automatic conversation_id generation
CREATE OR REPLACE FUNCTION generate_conversation_id()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate conversation_id as: conv_{location_id}_{contact_id}
    -- This ensures all messages between same contact and location share same conversation_id
    NEW.conversation_id := 'conv_' || NEW.ghl_location_id || '_' || NEW.ghl_contact_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the new notifications table with all required fields
CREATE TABLE public.notifications (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  
  -- GHL Integration Fields (Required)
  ghl_location_id VARCHAR(255) NOT NULL,
  ghl_contact_id VARCHAR(255) NOT NULL,
  
  -- Message Content (Required)
  message_content TEXT NOT NULL,
  message_type VARCHAR(50) NULL DEFAULT 'SMS',
  
  -- Contact Information
  sender_name VARCHAR(255) NULL,  -- Maps to contact_name from webhook
  sender_phone VARCHAR(50) NULL,
  sender_email VARCHAR(255) NULL,
  
  -- Webhook Payload Fields
  contact_type VARCHAR(100) NULL,  -- From webhook: contact_type
  message_attachment TEXT NULL,    -- From webhook: user_message_attachment  
  tag VARCHAR(255) NULL,           -- From webhook: tag
  agent_message TEXT NULL,         -- From webhook: agent_message
  
  -- Conversation Tracking
  conversation_id VARCHAR(255) NULL,
  
  -- Status Tracking
  read_status BOOLEAN NULL DEFAULT FALSE,
  responded_status BOOLEAN NULL DEFAULT FALSE,
  
  -- Metadata and Timestamps
  metadata JSONB NULL DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
  
  -- Primary Key
  CONSTRAINT notifications_pkey PRIMARY KEY (id),
  
  -- Unique constraint to prevent duplicate messages
  CONSTRAINT idx_notifications_location_contact UNIQUE (ghl_location_id, ghl_contact_id, created_at)
) TABLESPACE pg_default;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_notifications_ghl_location_id 
ON public.notifications USING btree (ghl_location_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_ghl_contact_id 
ON public.notifications USING btree (ghl_contact_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_read_status 
ON public.notifications USING btree (read_status) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
ON public.notifications USING btree (created_at DESC) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_conversation_id 
ON public.notifications USING btree (conversation_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_location_unread 
ON public.notifications USING btree (ghl_location_id, read_status) TABLESPACE pg_default
WHERE (read_status = FALSE);

-- Create indexes for new webhook fields
CREATE INDEX IF NOT EXISTS idx_notifications_contact_type 
ON public.notifications USING btree (contact_type) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_tag 
ON public.notifications USING btree (tag) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_notifications_message_type 
ON public.notifications USING btree (message_type) TABLESPACE pg_default;

-- Create the trigger for automatic timestamp updates
CREATE TRIGGER trigger_update_notifications_timestamp 
BEFORE UPDATE ON public.notifications 
FOR EACH ROW 
EXECUTE FUNCTION update_notifications_timestamp();

-- Create the trigger for automatic conversation_id generation
CREATE TRIGGER trigger_generate_conversation_id
BEFORE INSERT ON public.notifications
FOR EACH ROW
EXECUTE FUNCTION generate_conversation_id();

-- Add comments for documentation
COMMENT ON TABLE public.notifications IS 'Stores incoming messages from GHL webhooks with complete payload support';
COMMENT ON COLUMN public.notifications.ghl_location_id IS 'GHL Location/Account ID that received the message';
COMMENT ON COLUMN public.notifications.ghl_contact_id IS 'GHL Contact ID who sent the message';
COMMENT ON COLUMN public.notifications.message_content IS 'The actual message content from the customer (user_message from webhook)';
COMMENT ON COLUMN public.notifications.message_type IS 'Platform type: SMS, Facebook, Instagram, WhatsApp, etc. (social_media from webhook)';
COMMENT ON COLUMN public.notifications.sender_name IS 'Contact name (contact_name from webhook)';
COMMENT ON COLUMN public.notifications.contact_type IS 'Type of contact from GHL (Lead, Customer, Prospect, etc.)';
COMMENT ON COLUMN public.notifications.message_attachment IS 'URL or path to user message attachment';
COMMENT ON COLUMN public.notifications.tag IS 'Tag associated with the message/contact';
COMMENT ON COLUMN public.notifications.agent_message IS 'Agent response message if available';
COMMENT ON COLUMN public.notifications.conversation_id IS 'Auto-generated conversation ID: conv_{location_id}_{contact_id}';
COMMENT ON COLUMN public.notifications.read_status IS 'Whether the notification has been read by the user';
COMMENT ON COLUMN public.notifications.responded_status IS 'Whether the user has responded to this message';


CREATE OR REPLACE FUNCTION generate_conversation_id()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate conversation_id as: conv_{location_id}_{contact_id}
    -- This ensures all messages between same contact and location share same conversation_id
    NEW.conversation_id := 'conv_' || NEW.ghl_location_id || '_' || NEW.ghl_contact_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the trigger if it exists
DROP TRIGGER IF EXISTS set_conversation_id_trigger ON public.notifications;

-- Create the trigger that fires before insert
CREATE TRIGGER set_conversation_id_trigger
    BEFORE INSERT ON public.notifications
    FOR EACH ROW
    EXECUTE FUNCTION generate_conversation_id();

-- Insert sample data for testing (optional)
-- INSERT INTO public.notifications (
--     ghl_location_id,
--     ghl_contact_id,
--     message_content,
--     sender_name,
--     message_type,
--     contact_type,
--     tag
-- ) VALUES (
--     'loc_test_123',
--     'contact_sample_456',
--     'Hi! I am interested in your solar panels. Can you provide a quote?',
--     'John Test User',
--     'SMS',
--     'Lead',
--     'solar_lead_hot'
-- );

-- Verify table structure
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'notifications' 
-- ORDER BY ordinal_position;