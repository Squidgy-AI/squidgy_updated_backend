# 📋 MCP Configuration Files Guide

This directory contains **self-documenting JSON configuration files** for managing external MCPs (Model Context Protocol servers).

## 📁 Configuration Files

### `external_config_official.json`
- **Purpose**: Pre-vetted, trusted MCP servers from Anthropic
- **Trust Level**: `OFFICIAL`
- **Security**: No scanning required (trusted)
- **Permissions**: Full system access
- **Examples**: Filesystem, SQLite, Git, GitHub tools

### `external_config_github_public.json`
- **Purpose**: Community-contributed MCP servers
- **Trust Level**: `COMMUNITY` 
- **Security**: Full security scanning required
- **Permissions**: Sandboxed execution only
- **Examples**: Instagram, Weather, Email tools

## 🚀 Quick Start

### **1. View Available MCPs**
```bash
# List all MCPs
python mcp_cli.py list

# List only enabled MCPs
python mcp_cli.py list --enabled-only

# List by category
python mcp_cli.py list --category official
python mcp_cli.py list --category community
```

### **2. Add New MCP**

#### **Official MCP (trusted source)**
```json
// Add to external_config_official.json
{
  "new_official_mcp": {
    "url": "https://github.com/anthropics/mcp-server-example",
    "name": "example-tools",
    "description": "Example official MCP",
    "enabled": true,
    "auto_approve": true,
    "security_scan": false,
    "sandbox": false,
    "tags": ["example"],
    "capabilities": ["example_tool"]
  }
}
```

#### **Community MCP (requires approval)**
```json
// Add to external_config_github_public.json
{
  "new_community_mcp": {
    "url": "https://github.com/username/mcp-server",
    "name": "community-tools",
    "description": "Community MCP description",
    "enabled": false,  // Start disabled
    "auto_approve": false,
    "security_scan": true,
    "sandbox": true,
    "max_risk_score": 30,
    "tags": ["community"],
    "capabilities": ["community_tool"],
    "env_required": ["API_KEY"]
  }
}
```

### **3. Validation & Approval Workflow**

```bash
# 1. Validate configuration
python scripts/validate_mcp_configs.py

# 2. For community MCPs - approve after security review
python scripts/validate_mcp_configs.py --approve community-tools

# 3. Enable the MCP (set "enabled": true in JSON)

# 4. Strict validation (production-ready check)
python scripts/validate_mcp_configs.py --strict

# 5. Load MCPs into system
python mcp_cli.py load --config community
```

### **4. Using MCPs**

```bash
# Load all configurations
python mcp_cli.py load

# Check available tools
curl http://localhost:8000/api/v1/mcp/tools

# Call a tool
curl -X POST http://localhost:8000/api/v1/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "instagram_post",
    "params": {
      "caption": "Hello from MCP!"
    }
  }'
```

## 📋 Field Reference

### **Required Fields (All MCPs)**
- `url`: GitHub repository URL
- `name`: Unique identifier for CLI/API usage
- `description`: Human-readable description
- `enabled`: `true` to load, `false` to skip

### **Security Fields (Community MCPs)**
- `auto_approve`: Must be `false` for community
- `security_scan`: Must be `true` for community
- `sandbox`: Must be `true` for community
- `max_risk_score`: Integer 0-100 (risk tolerance)

### **Optional Fields**
- `tags`: Array of keywords for categorization
- `capabilities`: Array of tool names the MCP provides
- `env_required`: Environment variables needed at runtime

### **Auto-Generated Fields (After Approval)**
- `_approval_date`: ISO timestamp when approved
- `_approved_by`: Username who approved
- `_approval_note`: Approval note/reason

## 🔒 Security Workflow

### **Official MCPs**
1. ✅ Add to `external_config_official.json`
2. ✅ Set `enabled: true`
3. ✅ Load: `python mcp_cli.py load --config official`
4. ✅ Ready to use immediately

### **Community MCPs**
1. ⚠️ Add to `external_config_github_public.json` with `enabled: false`
2. ⚠️ Validate: `python scripts/validate_mcp_configs.py`
3. 🔍 **Manual security review** of GitHub repository
4. ✅ Approve: `python scripts/validate_mcp_configs.py --approve mcp-name`
5. ✅ Enable: Set `enabled: true` in JSON
6. ✅ Load: `python mcp_cli.py load --config community`

## ⚠️ Important Notes

### **Environment Variables**
- Environment variables in `env_required` are **RUNTIME requirements**
- They are **NOT needed** for loading or scanning MCPs
- Only required when actually **calling the tools**

```bash
# Example: Instagram MCP
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"

# Then call Instagram tools
curl -X POST http://localhost:8000/api/v1/mcp/call \
  -d '{"tool": "instagram_post", "params": {"caption": "Test"}}'
```

### **URL Requirements**
- Must be GitHub or GitLab repositories
- Community MCPs: Any public repository
- Official MCPs: Preferably `github.com/anthropics/*`

### **Approval Tracking**
- All enabled community MCPs must have approval metadata
- Approval metadata is automatically added by validation script
- Strict mode validation enforces approval requirements

## 🛠️ Management Commands

### **Validation**
```bash
# Basic validation
python scripts/validate_mcp_configs.py

# Strict mode (production check)
python scripts/validate_mcp_configs.py --strict

# Approve MCP
python scripts/validate_mcp_configs.py --approve mcp-name
```

### **CLI Management**
```bash
# List MCPs
python mcp_cli.py list [--category official|community] [--enabled-only]

# Load configurations
python mcp_cli.py load [--config official|community|all]

# Enable/disable MCPs
python mcp_cli.py enable mcp-name
python mcp_cli.py disable mcp-name

# Add new MCP via CLI
python mcp_cli.py add https://github.com/user/repo mcp-name [--enabled]
```

### **API Management**
```bash
# List available tools
curl http://localhost:8000/api/v1/mcp/tools

# Health check
curl http://localhost:8000/api/v1/mcp/health

# Load configurations via API
curl -X POST http://localhost:8000/api/v1/mcp/config/load?config_type=community
```

## 🚨 Troubleshooting

### **Validation Errors**
```bash
# Issue: Missing required fields
# Solution: Check JSON structure against field reference

# Issue: Invalid JSON syntax
# Solution: Use JSON validator or python -m json.tool filename.json

# Issue: Trust level mismatch
# Solution: Ensure community MCPs have proper security fields
```

### **Approval Issues**
```bash
# Issue: Strict mode fails for enabled MCP
# Solution: python scripts/validate_mcp_configs.py --approve mcp-name

# Issue: Can't find MCP to approve
# Solution: Check MCP name matches exactly in JSON file
```

### **Runtime Issues**
```bash
# Issue: Tools fail with missing environment variables
# Solution: Export required environment variables before calling tools

# Issue: MCP not loading
# Solution: Check security scan results and approval status
```

## 🎯 Best Practices

1. **Start Disabled**: Always add community MCPs with `enabled: false`
2. **Review Security**: Manually review GitHub repositories before approval
3. **Use Validation**: Always validate before committing changes
4. **Track Changes**: Use git to track configuration changes
5. **Monitor Usage**: Check audit logs for MCP tool usage
6. **Environment Separation**: Use different configs for dev/staging/prod

## 📖 Example Workflows

### **Adding Instagram MCP (Already Done)**
```bash
# 1. Instagram MCP is already configured and approved
python mcp_cli.py list --category community

# 2. Set environment variables
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"

# 3. Load community MCPs
python mcp_cli.py load --config community

# 4. Test Instagram tools
curl -X POST http://localhost:8000/api/v1/mcp/call \
  -d '{"tool": "instagram_post", "params": {"caption": "Hello World!"}}'
```

### **Adding New Weather MCP**
```bash
# 1. Edit external_config_github_public.json
# Replace example URL with real weather MCP repository

# 2. Validate configuration
python scripts/validate_mcp_configs.py

# 3. Review GitHub repository for security
# Manual step: Check code, dependencies, permissions

# 4. Approve after review
python scripts/validate_mcp_configs.py --approve weather-tools

# 5. Enable in JSON file
# Set "enabled": true

# 6. Load into system
python mcp_cli.py load --config community
```

The configuration files are **self-documenting** with embedded comments and examples! 📚