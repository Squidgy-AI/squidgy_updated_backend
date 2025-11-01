# 🚀 MCP (Model Context Protocol) Server

This directory contains the complete MCP server implementation for integrating external tools and APIs.

## 📁 Directory Structure

```
mcp/
├── README.md                    # This file
├── __init__.py                  # Package initialization
├── config.py                    # Configuration management
├── models.py                    # Pydantic data models
├── registry.py                  # Tool discovery and management
├── server.py                    # Main MCP gateway server
├── config_loader.py             # Configuration file processor
├── bridges/                     # Custom tool bridges
│   ├── __init__.py
│   └── ghl_bridge.py           # GoHighLevel integration
└── config/                      # MCP configuration files
    ├── README.md               # Configuration guide
    ├── external_config_official.json      # Official Anthropic MCPs
    └── external_config_github_public.json # Community MCPs
```

## 🎯 Quick Start

### 1. Load MCP Configurations
```bash
# Load all MCPs
python mcp_cli.py load

# Load specific categories
python mcp_cli.py load --config official
python mcp_cli.py load --config community
```

### 2. List Available Tools
```bash
# See all MCPs
python mcp_cli.py list

# See only enabled MCPs
python mcp_cli.py list --enabled-only
```

### 3. Use MCP Tools via API
```bash
# Call any MCP tool
curl -X POST http://localhost:8000/api/v1/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "instagram_post",
    "params": {
      "caption": "Hello from MCP!"
    }
  }'
```

## 🔧 Available Tools

### Official MCPs (Pre-trusted)
- **Filesystem**: `read_file`, `write_file`, `list_directory`
- **Git**: `git_status`, `git_log`, `git_diff`
- **SQLite**: `execute_query`, `create_table`
- **Search**: `web_search` (requires BRAVE_API_KEY)
- **GitHub**: `create_repository` (requires GITHUB_TOKEN)

### Community MCPs (Security Scanned)
- **Instagram**: `instagram_post`, `get_profile_info` ✅ Enabled
- **PDF**: `create_pdf`, `merge_pdfs` ✅ Enabled
- **Weather**: `get_current_weather` (disabled - example URL)
- **Email**: `send_email` (disabled - example URL)
- **Slack**: `send_message` (disabled - example URL)

## 🛡️ Security Features

- **Automatic vulnerability scanning** for community MCPs
- **Approval workflow** for untrusted repositories
- **Sandboxed execution** for community tools
- **Trust level management** (OFFICIAL, COMMUNITY, INTERNAL)
- **Pre-commit validation** hooks

## 📋 Configuration Management

### Add New MCP
```bash
# Add via CLI
python mcp_cli.py add https://github.com/user/repo mcp-name

# Or edit JSON files in config/ directory
```

### Approve Community MCP
```bash
# Validate configuration
python scripts/validate_mcp_configs.py

# Approve after security review
python scripts/validate_mcp_configs.py --approve mcp-name

# Enable in config and reload
python mcp_cli.py enable mcp-name
```

## 🔗 Integration

### n8n Workflows
Use HTTP Request nodes to call MCP tools:
```json
{
  "method": "POST",
  "url": "http://localhost:8000/api/v1/mcp/call",
  "body": {
    "tool": "tool_name",
    "params": { "param1": "value1" }
  }
}
```

### Custom Applications
All MCP tools are available via REST API at `/api/v1/mcp/call`

## 📚 Documentation

- **Main Documentation**: `../MCP_DOCUMENTATION.md` - Complete usage guide
- **Configuration Guide**: `config/README.md` - JSON configuration details
- **Validation Scripts**: `../scripts/validate_mcp_configs.py`
- **CLI Tool**: `../mcp_cli.py`

## 🚨 Important Notes

- **Environment Variables**: Required only at RUNTIME for tool execution
- **Security Scanning**: Happens automatically when loading community MCPs
- **Approval Required**: All enabled community MCPs must be approved
- **Database Integration**: Uses existing Supabase for MCP storage

## 🆘 Troubleshooting

1. **MCP not loading**: Check `python mcp_cli.py list` and validate config
2. **Tool not found**: Ensure MCP is enabled and loaded
3. **Environment errors**: Set required env vars before calling tools
4. **Validation fails**: Run `python scripts/validate_mcp_configs.py`

For complete documentation, see `../MCP_DOCUMENTATION.md`