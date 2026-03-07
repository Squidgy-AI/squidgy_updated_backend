-- ============================================================================
-- MCP (Model Context Protocol) Management Tables
-- ============================================================================

-- MCPs table for managing external and custom MCPs
CREATE TABLE IF NOT EXISTS mcps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    trust_level TEXT NOT NULL CHECK (trust_level IN ('OFFICIAL', 'VERIFIED', 'COMMUNITY', 'INTERNAL')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'scanning', 'approved', 'rejected', 'active', 'failed')),
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security scans table for tracking vulnerability assessments
CREATE TABLE IF NOT EXISTS security_scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mcp_id UUID REFERENCES mcps(id) ON DELETE CASCADE,
    scan_type TEXT NOT NULL DEFAULT 'full',
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    vulnerabilities JSONB DEFAULT '[]',
    scan_details JSONB DEFAULT '{}',
    passed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MCP audit logs for tracking all MCP-related activities
CREATE TABLE IF NOT EXISTS mcp_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mcp_id UUID REFERENCES mcps(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    user_id UUID,
    tool_name TEXT,
    request_params JSONB DEFAULT '{}',
    response_data JSONB DEFAULT '{}',
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extend existing chat_history table to track MCP tool usage
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'chat_history' AND column_name = 'mcp_tool_used') THEN
        ALTER TABLE chat_history ADD COLUMN mcp_tool_used TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'chat_history' AND column_name = 'mcp_context') THEN
        ALTER TABLE chat_history ADD COLUMN mcp_context JSONB;
    END IF;
END $$;

-- Extend existing notifications table for MCP-related notifications
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'notifications' AND column_name = 'mcp_context') THEN
        ALTER TABLE notifications ADD COLUMN mcp_context JSONB;
    END IF;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcps_status ON mcps(status);
CREATE INDEX IF NOT EXISTS idx_mcps_trust_level ON mcps(trust_level);
CREATE INDEX IF NOT EXISTS idx_mcps_created_at ON mcps(created_at);

CREATE INDEX IF NOT EXISTS idx_security_scans_mcp_id ON security_scans(mcp_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_created_at ON security_scans(created_at);

CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_mcp_id ON mcp_audit_logs(mcp_id);
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_timestamp ON mcp_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_tool_name ON mcp_audit_logs(tool_name);

-- Create trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_mcps_updated_at') THEN
        CREATE TRIGGER update_mcps_updated_at 
            BEFORE UPDATE ON mcps 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Insert some default official MCPs (examples)
-- INSERT INTO mcps (url, name, trust_level, status, metadata) 
-- VALUES 
--     ('https://github.com/anthropics/mcp-server-filesystem', 'filesystem-mcp', 'OFFICIAL', 'approved', '{"description": "Official Anthropic filesystem MCP server"}'),
--     ('https://github.com/anthropics/mcp-server-brave-search', 'brave-search-mcp', 'OFFICIAL', 'approved', '{"description": "Official Anthropic Brave search MCP server"}'),
--     ('https://github.com/anthropics/mcp-server-sqlite', 'sqlite-mcp', 'OFFICIAL', 'approved', '{"description": "Official Anthropic SQLite MCP server"}')
-- ON CONFLICT (url) DO NOTHING;

-- Create view for MCP statistics
CREATE OR REPLACE VIEW mcp_stats AS
SELECT 
    trust_level,
    status,
    COUNT(*) as count
FROM mcps 
GROUP BY trust_level, status
ORDER BY trust_level, status;

-- Create view for recent MCP activity
CREATE OR REPLACE VIEW recent_mcp_activity AS
SELECT 
    mal.timestamp,
    mal.action,
    mal.tool_name,
    m.name as mcp_name,
    m.trust_level,
    mal.success,
    mal.execution_time_ms
FROM mcp_audit_logs mal
LEFT JOIN mcps m ON mal.mcp_id = m.id
ORDER BY mal.timestamp DESC
LIMIT 100;

-- Disable RLS (Row Level Security) for MCP tables
ALTER TABLE mcps DISABLE ROW LEVEL SECURITY;
ALTER TABLE security_scans DISABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_audit_logs DISABLE ROW LEVEL SECURITY;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON mcps TO your_app_user;
-- GRANT ALL ON security_scans TO your_app_user;
-- GRANT ALL ON mcp_audit_logs TO your_app_user;