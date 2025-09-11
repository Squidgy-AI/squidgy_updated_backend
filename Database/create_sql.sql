-- Individual SQL statements for Squidgy AI Backend
-- Run these statements one at a time if facing issues with batch execution

-- 1. Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  sender TEXT NOT NULL,
  message TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create n8n_logs table
CREATE TABLE IF NOT EXISTS n8n_logs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  message TEXT NOT NULL,
  request_payload JSONB,
  response_payload JSONB,
  status TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create website_data table
CREATE TABLE IF NOT EXISTS website_data (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  session_id TEXT NOT NULL,
  url TEXT NOT NULL,
  screenshot_path TEXT,
  favicon_path TEXT,
  analysis JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create tools_usage table
CREATE TABLE IF NOT EXISTS tools_usage (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  tool_params JSONB,
  tool_result JSONB,
  execution_time FLOAT,
  status TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create client_kb table
CREATE TABLE IF NOT EXISTS client_kb (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  client_id TEXT NOT NULL,
  kb_type TEXT NOT NULL,
  content JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Add unique constraint to website_data
ALTER TABLE website_data
ADD CONSTRAINT IF NOT EXISTS unique_website_session_url 
UNIQUE (session_id, url);

-- 7. Add unique constraint to client_kb
ALTER TABLE client_kb
ADD CONSTRAINT IF NOT EXISTS unique_client_kb_type 
UNIQUE (client_id, kb_type);

-- 8. Create index on chat_history(session_id)
CREATE INDEX IF NOT EXISTS idx_chat_history_session 
ON chat_history(session_id);

-- 9. Create index on chat_history(user_id)
CREATE INDEX IF NOT EXISTS idx_chat_history_user 
ON chat_history(user_id);

-- 10. Create index on n8n_logs(session_id)
CREATE INDEX IF NOT EXISTS idx_n8n_logs_session 
ON n8n_logs(session_id);

-- 11. Create index on tools_usage(session_id)
CREATE INDEX IF NOT EXISTS idx_tools_usage_session 
ON tools_usage(session_id);

-- 12. Create index on client_kb(client_id)
CREATE INDEX IF NOT EXISTS idx_client_kb_client 
ON client_kb(client_id);