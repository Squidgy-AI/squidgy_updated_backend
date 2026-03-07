# 🚀 MCP Server Complete Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Setup & Installation](#setup--installation)
4. [Configuration Management](#configuration-management)
5. [Running the MCP Server](#running-the-mcp-server)
6. [Available Tools & APIs](#available-tools--apis)
7. [Adding New MCPs](#adding-new-mcps)
8. [Security & Approval Workflow](#security--approval-workflow)
9. [n8n Integration Guide](#n8n-integration-guide)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Usage](#advanced-usage)

---

## Introduction

Your MCP (Model Context Protocol) server is a centralized hub that integrates multiple external MCP tools and your existing APIs into a unified interface. It provides:

- **Official MCPs**: Pre-trusted tools from Anthropic (filesystem, git, SQLite, etc.)
- **Community MCPs**: Third-party tools with security scanning (Instagram, PDF, email, etc.)
- **Custom Bridge Tools**: Your existing functionality wrapped as MCP tools
- **Security Layer**: Automatic vulnerability scanning and approval workflow
- **REST API**: Easy integration with n8n, webhooks, and other services

---

## Quick Start

### 1. Start the MCP Server
```bash
# Navigate to your project directory
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated

# Start the FastAPI server
python main.py
```

### 2. Load MCP Configurations
```bash
# Load all MCPs (official + community)
python mcp_cli.py load

# Or load specific categories
python mcp_cli.py load --config official    # Only Anthropic MCPs
python mcp_cli.py load --config community   # Only community MCPs
```

### 3. Check Available Tools
```bash
# List all available tools
curl http://localhost:8000/api/v1/mcp/tools

# Check server health
curl http://localhost:8000/api/v1/mcp/health
```

### 4. Call a Tool
```bash
# Example: Use Instagram MCP (after setting env vars)
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"

curl -X POST http://localhost:8000/api/v1/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "instagram_post",
    "params": {
      "caption": "Hello from MCP! 🚀"
    }
  }'
```

---

## Setup & Installation

### Prerequisites
```bash
# Install required Python packages
pip install fastapi uvicorn supabase python-multipart
pip install bandit safety  # For security scanning
```

### Environment Variables
Create a `.env` file in your project root:
```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_service_key

# Optional: API Keys for specific MCPs
BRAVE_API_KEY=your_brave_search_key
GITHUB_TOKEN=your_github_token
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
WEATHER_API_KEY=your_weather_api_key
SMTP_SERVER=your_smtp_server
EMAIL_PASSWORD=your_email_password
SLACK_BOT_TOKEN=your_slack_token
```

### Database Setup
Your Supabase database should already have the MCP tables. If not:
```sql
-- Run the SQL in Database/mcp_tables.sql
-- This creates tables for: mcps, mcp_security_scans, mcp_audit_logs, mcp_configs
```

---

## Configuration Management

### Configuration Files Location
```
mcp/config/
├── external_config_official.json     # Anthropic MCPs
├── external_config_github_public.json # Community MCPs
└── README.md                          # Configuration guide
```

### View Current MCPs
```bash
# List all MCPs
python mcp_cli.py list

# List only enabled MCPs
python mcp_cli.py list --enabled-only

# List by category
python mcp_cli.py list --category official
python mcp_cli.py list --category community
```

### Enable/Disable MCPs
```bash
# Enable a specific MCP
python mcp_cli.py enable instagram-tools

# Disable a specific MCP  
python mcp_cli.py disable weather-tools

# Check system status
python mcp_cli.py status
```

### Validate Configurations
```bash
# Basic validation
python scripts/validate_mcp_configs.py

# Strict mode (production check)
python scripts/validate_mcp_configs.py --strict

# Approve a community MCP
python scripts/validate_mcp_configs.py --approve mcp-name
```

---

## Running the MCP Server

### Local Development
```bash
# Start with auto-reload
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment

#### Heroku
```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
git add .
git commit -m "Deploy MCP server"
git push heroku main
```

#### DigitalOcean/VPS
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Health Monitoring
```bash
# Check if server is running
curl http://localhost:8000/health

# Check MCP system status
curl http://localhost:8000/api/v1/mcp/health

# View recent activity
curl http://localhost:8000/api/v1/mcp/audit
```

---

## Available Tools & APIs

### Core API Endpoints

#### 1. List Available Tools
```bash
GET /api/v1/mcp/tools
```
**Response:**
```json
{
  "tools": [
    {
      "name": "instagram_post",
      "description": "Create Instagram post",
      "mcp": "instagram-tools",
      "trust_level": "COMMUNITY",
      "parameters": {
        "caption": "string",
        "image_url": "string (optional)"
      }
    }
  ]
}
```

#### 2. Call a Tool
```bash
POST /api/v1/mcp/call
Content-Type: application/json

{
  "tool": "tool_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

#### 3. Health Check
```bash
GET /api/v1/mcp/health
```

#### 4. Load Configurations
```bash
POST /api/v1/mcp/config/load?config_type=all
POST /api/v1/mcp/config/load?config_type=official
POST /api/v1/mcp/config/load?config_type=community
```

### Available MCP Tools

#### Official MCPs (Pre-trusted)
| Tool | Description | Env Variables |
|------|-------------|---------------|
| `read_file` | Read file contents | None |
| `write_file` | Write to file | None |
| `list_directory` | List directory contents | None |
| `execute_query` | Run SQLite query | None |
| `git_log` | View git history | None |
| `git_status` | Check git status | None |
| `web_search` | Brave search (disabled) | `BRAVE_API_KEY` |
| `create_repository` | GitHub operations (disabled) | `GITHUB_TOKEN` |

#### Community MCPs (Security Scanned)
| Tool | Description | Status | Env Variables |
|------|-------------|--------|---------------|
| `instagram_post` | Create Instagram post | ✅ Enabled | `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` |
| `get_profile_info` | Get Instagram profile | ✅ Enabled | `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` |
| `create_pdf` | Generate PDF documents | ✅ Enabled | None |
| `merge_pdfs` | Combine PDF files | ✅ Enabled | None |
| `get_current_weather` | Weather info (example) | ❌ Disabled | `WEATHER_API_KEY` |
| `send_email` | Send emails (example) | ❌ Disabled | `SMTP_SERVER`, `EMAIL_PASSWORD` |
| `send_message` | Slack messaging (example) | ❌ Disabled | `SLACK_BOT_TOKEN` |

#### Custom Bridge Tools
Your existing APIs are available as MCP tools:
- GHL (GoHighLevel) contact management
- Facebook posting functionality
- Any other custom tools in `Tools/` directory

---

## Adding New MCPs

### 1. Add Official MCP
Edit `mcp/config/external_config_official.json`:
```json
{
  "new_official_tool": {
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

### 2. Add Community MCP
Edit `mcp/config/external_config_github_public.json`:
```json
{
  "new_community_tool": {
    "url": "https://github.com/username/mcp-server",
    "name": "community-tools",
    "description": "Community MCP description",
    "enabled": false,
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

### 3. Via CLI
```bash
# Add new MCP via command line
python mcp_cli.py add https://github.com/user/repo new-name --enabled

# Add to specific config
python mcp_cli.py add https://github.com/user/repo new-name --config community
```

---

## Security & Approval Workflow

### Community MCP Security Process

#### 1. Add MCP (Disabled)
```bash
# Add with enabled: false
# System will scan repository automatically
```

#### 2. Security Scanning
The system automatically:
- Clones repository securely
- Runs Bandit (static analysis)
- Runs Safety (dependency scan)
- Calculates risk score (0-100)
- Auto-approves if score ≤ max_risk_score

#### 3. Manual Review (if needed)
```bash
# Review GitHub repository manually
# Check code quality, dependencies, permissions

# If safe, approve:
python scripts/validate_mcp_configs.py --approve mcp-name
```

#### 4. Enable MCP
```bash
# Edit JSON config: set "enabled": true
# Or use CLI:
python mcp_cli.py enable mcp-name
```

#### 5. Load into System
```bash
python mcp_cli.py load --config community
```

### Pre-commit Validation
```bash
# Add to .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mcp-validation
        name: MCP Configuration Validation
        entry: python scripts/validate_mcp_configs.py --strict
        language: system
        files: ^mcp/config/.*\.json$
```

---

## n8n Integration Guide

### Server URL Configuration

**Your MCP Server URLs:**
- **Local Development**: `http://localhost:8000`
- **Production**: `https://your-mcp-server.herokuapp.com` (or your domain)

### Node-Level Configuration

#### 1. HTTP Request Node Setup

**Basic Configuration:**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/v1/mcp/call`
- **Authentication**: None (or add Bearer token if secured)
- **Body Content Type**: JSON

**Headers Tab:**
```
Content-Type: application/json
```

**Body Tab (JSON format):**
```json
{
  "tool": "{{ $json.tool_name }}",
  "params": "{{ $json.tool_params }}"
}
```

**Options Tab:**
- Response Format: JSON
- Timeout: 30000 (30 seconds)

#### 2. Pre-configured Tool Nodes

##### Instagram Post Node
**Node Name**: `Instagram Post`
**HTTP Request Configuration:**
```
Method: POST
URL: http://localhost:8000/api/v1/mcp/call
Headers:
  Content-Type: application/json
Body:
{
  "tool": "instagram_post",
  "params": {
    "caption": "{{ $json.caption || 'Default caption' }}",
    "image_url": "{{ $json.image_url }}"
  }
}
```

##### File Read Node
**Node Name**: `Read File`
**HTTP Request Configuration:**
```
Method: POST
URL: http://localhost:8000/api/v1/mcp/call
Body:
{
  "tool": "read_file",
  "params": {
    "file_path": "{{ $json.file_path }}"
  }
}
```

##### PDF Generator Node
**Node Name**: `Generate PDF`
**HTTP Request Configuration:**
```
Method: POST
URL: http://localhost:8000/api/v1/mcp/call
Body:
{
  "tool": "create_pdf",
  "params": {
    "content": "{{ $json.content }}",
    "title": "{{ $json.title || 'Generated Document' }}",
    "filename": "{{ $json.filename || 'document.pdf' }}"
  }
}
```

##### Git Status Node
**Node Name**: `Git Status`
**HTTP Request Configuration:**
```
Method: POST
URL: http://localhost:8000/api/v1/mcp/call
Body:
{
  "tool": "git_status",
  "params": {
    "repository_path": "{{ $json.repo_path || '.' }}"
  }
}
```

#### 3. Dynamic Tool Selection Node

**Node Name**: `Dynamic MCP Tool`
**HTTP Request Configuration:**
```
Method: POST
URL: http://localhost:8000/api/v1/mcp/call
Body:
{
  "tool": "{{ $json.selected_tool }}",
  "params": {{ $json.tool_parameters }}
}
```

#### 4. Tool Discovery Node

**Node Name**: `List Available Tools`
**HTTP Request Configuration:**
```
Method: GET
URL: http://localhost:8000/api/v1/mcp/tools
Headers:
  Content-Type: application/json
```

#### 5. Health Check Node

**Node Name**: `MCP Health Check`
**HTTP Request Configuration:**
```
Method: GET
URL: http://localhost:8000/api/v1/mcp/health
```

### Step-by-Step n8n Workflow Creation

#### Creating Your First MCP Workflow

**Step 1: Create New Workflow**
1. Open n8n interface
2. Click "New Workflow"
3. Name it "MCP Instagram Automation"

**Step 2: Add Webhook Trigger**
1. Add "Webhook" node
2. Configure:
   ```
   HTTP Method: POST
   Path: mcp-instagram
   Authentication: None
   ```
3. Test URL will be: `http://your-n8n-url/webhook/mcp-instagram`

**Step 3: Add HTTP Request Node for Instagram**
1. Add "HTTP Request" node
2. Connect it to Webhook
3. Configure:
   ```
   Method: POST
   URL: http://localhost:8000/api/v1/mcp/call
   Authentication: None
   
   Headers:
   Content-Type: application/json
   
   Body (JSON):
   {
     "tool": "instagram_post",
     "params": {
       "caption": "{{ $json.caption }}",
       "image_url": "{{ $json.image_url }}"
     }
   }
   
   Options:
   Response Format: JSON
   ```

**Step 4: Add Response Node**
1. Add "Respond to Webhook" node
2. Connect it to HTTP Request
3. Configure:
   ```
   Response Mode: Using 'Respond to Webhook' Node
   Status Code: 200
   
   Body (JSON):
   {
     "success": "{{ $json.success }}",
     "instagram_url": "{{ $json.result.url }}",
     "post_id": "{{ $json.result.post_id }}"
   }
   ```

#### Complete n8n Node Configurations

##### Node 1: Webhook Trigger
**Node Settings:**
```json
{
  "httpMethod": "POST",
  "path": "mcp-tools",
  "authentication": "none",
  "responseMode": "onReceived",
  "options": {}
}
```

##### Node 2: Set Tool Parameters
**Node Name**: `Prepare MCP Call`
**Type**: `Code`
**JavaScript Code:**
```javascript
// Extract and validate input data
const tool = $input.first().json.tool || 'instagram_post';
const params = $input.first().json.params || {};

// Validate required parameters based on tool
if (tool === 'instagram_post' && !params.caption) {
  throw new Error('Caption is required for Instagram posts');
}

return [
  {
    json: {
      tool: tool,
      params: params,
      timestamp: new Date().toISOString()
    }
  }
];
```

##### Node 3: MCP API Call
**Node Name**: `Call MCP Tool`
**Type**: `HTTP Request`
**Configuration:**
```json
{
  "method": "POST",
  "url": "http://localhost:8000/api/v1/mcp/call",
  "authentication": "none",
  "requestOptions": {
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "tool": "={{ $json.tool }}",
      "params": "={{ $json.params }}"
    },
    "timeout": 30000,
    "proxy": "",
    "allowUnauthorizedCerts": false
  },
  "options": {
    "response": {
      "responseFormat": "json"
    }
  }
}
```

##### Node 4: Error Handling
**Node Name**: `Handle Errors`
**Type**: `IF`
**Configuration:**
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{ $json.success }}",
        "operation": "equal",
        "value2": true
      }
    ]
  }
}
```

##### Node 5: Success Response
**Node Name**: `Success Response`
**Type**: `Respond to Webhook`
**Configuration:**
```json
{
  "options": {
    "responseCode": 200,
    "responseHeaders": {
      "Content-Type": "application/json"
    }
  },
  "responseBody": {
    "success": true,
    "message": "Tool executed successfully",
    "tool": "={{ $json.tool }}",
    "result": "={{ $json.result }}",
    "execution_time": "={{ $json.execution_time }}"
  }
}
```

##### Node 6: Error Response
**Node Name**: `Error Response`
**Type**: `Respond to Webhook`
**Configuration:**
```json
{
  "options": {
    "responseCode": 400,
    "responseHeaders": {
      "Content-Type": "application/json"
    }
  },
  "responseBody": {
    "success": false,
    "error": "={{ $json.error || 'Tool execution failed' }}",
    "tool": "={{ $json.tool }}",
    "timestamp": "={{ new Date().toISOString() }}"
  }
}
```

### Ready-to-Import n8n Workflows

#### Workflow 1: Simple Instagram Poster
```json
{
  "name": "MCP Instagram Poster",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "instagram-post"
      },
      "name": "Instagram Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [240, 300],
      "webhookId": "instagram-mcp"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/v1/mcp/call",
        "options": {
          "response": {
            "responseFormat": "json"
          }
        },
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "tool": "instagram_post",
          "params": {
            "caption": "={{ $json.caption }}",
            "image_url": "={{ $json.image_url }}"
          }
        }
      },
      "name": "Call Instagram MCP",
      "type": "n8n-nodes-base.httpRequest",
      "position": [460, 300]
    },
    {
      "parameters": {
        "options": {
          "responseCode": 200
        },
        "responseBody": {
          "success": "={{ $json.success }}",
          "post_url": "={{ $json.result.url }}",
          "message": "Instagram post created successfully"
        }
      },
      "name": "Respond Success",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [680, 300]
    }
  ],
  "connections": {
    "Instagram Webhook": {
      "main": [
        [
          {
            "node": "Call Instagram MCP",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Call Instagram MCP": {
      "main": [
        [
          {
            "node": "Respond Success",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

#### Workflow 2: Multi-Tool MCP Gateway
```json
{
  "name": "MCP Multi-Tool Gateway",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "mcp-gateway"
      },
      "name": "MCP Gateway Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [240, 300]
    },
    {
      "parameters": {
        "jsCode": "// Validate and prepare MCP call\nconst tool = $input.first().json.tool;\nconst params = $input.first().json.params || {};\n\nif (!tool) {\n  throw new Error('Tool parameter is required');\n}\n\n// Add timestamp and validation\nreturn [\n  {\n    json: {\n      tool: tool,\n      params: params,\n      request_id: Date.now(),\n      timestamp: new Date().toISOString()\n    }\n  }\n];"
      },
      "name": "Prepare MCP Call",
      "type": "n8n-nodes-base.code",
      "position": [460, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/v1/mcp/call",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "tool": "={{ $json.tool }}",
          "params": "={{ $json.params }}"
        },
        "options": {
          "response": {
            "responseFormat": "json"
          },
          "timeout": 30000
        }
      },
      "name": "Execute MCP Tool",
      "type": "n8n-nodes-base.httpRequest",
      "position": [680, 300]
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.success }}",
              "value2": true
            }
          ]
        }
      },
      "name": "Check Success",
      "type": "n8n-nodes-base.if",
      "position": [900, 300]
    },
    {
      "parameters": {
        "responseBody": {
          "success": true,
          "tool": "={{ $json.tool }}",
          "result": "={{ $json.result }}",
          "execution_time": "={{ $json.execution_time }}"
        }
      },
      "name": "Success Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [1120, 200]
    },
    {
      "parameters": {
        "options": {
          "responseCode": 400
        },
        "responseBody": {
          "success": false,
          "error": "={{ $json.error || 'Tool execution failed' }}",
          "tool": "={{ $json.tool }}"
        }
      },
      "name": "Error Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [1120, 400]
    }
  ],
  "connections": {
    "MCP Gateway Webhook": {
      "main": [
        [
          {
            "node": "Prepare MCP Call",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Prepare MCP Call": {
      "main": [
        [
          {
            "node": "Execute MCP Tool",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Execute MCP Tool": {
      "main": [
        [
          {
            "node": "Check Success",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check Success": {
      "main": [
        [
          {
            "node": "Success Response",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Error Response",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### Testing Your n8n Workflows

#### Test Instagram Workflow
```bash
# Test with curl
curl -X POST http://your-n8n-url/webhook/instagram-post \
  -H "Content-Type: application/json" \
  -d '{
    "caption": "Test post from n8n workflow",
    "image_url": "https://example.com/test-image.jpg"
  }'
```

#### Test Multi-Tool Gateway
```bash
# Test PDF generation
curl -X POST http://your-n8n-url/webhook/mcp-gateway \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "create_pdf",
    "params": {
      "content": "Hello from n8n!",
      "title": "Test Document"
    }
  }'

# Test file reading
curl -X POST http://your-n8n-url/webhook/mcp-gateway \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "read_file",
    "params": {
      "file_path": "/path/to/your/file.txt"
    }
  }'
```

### n8n Workflow Examples
```json
{
  "nodes": [
    {
      "name": "Trigger",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "instagram-post"
      }
    },
    {
      "name": "Instagram MCP",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://your-server.com/api/v1/mcp/call",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "tool": "instagram_post",
          "params": {
            "caption": "{{ $json.caption }}",
            "image_url": "{{ $json.image_url }}"
          }
        }
      }
    }
  ]
}
```

#### Example 2: File Processing + PDF Generation
```json
{
  "nodes": [
    {
      "name": "Read File",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://your-server.com/api/v1/mcp/call",
        "body": {
          "tool": "read_file",
          "params": {
            "file_path": "/path/to/file.txt"
          }
        }
      }
    },
    {
      "name": "Generate PDF",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://your-server.com/api/v1/mcp/call",
        "body": {
          "tool": "create_pdf",
          "params": {
            "content": "{{ $json.file_content }}",
            "title": "Generated Report"
          }
        }
      }
    }
  ]
}
```

#### Example 3: Weather + Email Notification
```json
{
  "nodes": [
    {
      "name": "Get Weather",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://your-server.com/api/v1/mcp/call",
        "body": {
          "tool": "get_current_weather",
          "params": {
            "location": "New York"
          }
        }
      }
    },
    {
      "name": "Send Email",
      "type": "n8n-nodes-base.httpRequest", 
      "parameters": {
        "url": "http://your-server.com/api/v1/mcp/call",
        "body": {
          "tool": "send_email",
          "params": {
            "to": "user@example.com",
            "subject": "Weather Update",
            "body": "Current weather: {{ $json.weather_data }}"
          }
        }
      }
    }
  ]
}
```

### n8n Best Practices

#### 1. Error Handling
```json
{
  "name": "Error Handler",
  "type": "n8n-nodes-base.if",
  "parameters": {
    "conditions": {
      "boolean": [
        {
          "value1": "{{ $json.success }}",
          "value2": true
        }
      ]
    }
  }
}
```

#### 2. Environment Variables in n8n
```json
{
  "body": {
    "tool": "instagram_post",
    "params": {
      "caption": "{{ $json.caption }}"
    }
  },
  "headers": {
    "X-API-Key": "{{ $credentials.mcp_server.api_key }}"
  }
}
```

#### 3. Dynamic Tool Selection
```json
{
  "body": {
    "tool": "{{ $json.selected_tool }}",
    "params": "{{ $json.tool_parameters }}"
  }
}
```

### Testing n8n Integration

#### 1. Test Tool Availability
```bash
# Check available tools
curl http://your-server.com/api/v1/mcp/tools

# Test in n8n HTTP Request node
GET http://your-server.com/api/v1/mcp/tools
```

#### 2. Test Tool Execution
```bash
# Test Instagram posting
curl -X POST http://your-server.com/api/v1/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "instagram_post",
    "params": {
      "caption": "Test from n8n"
    }
  }'
```

#### 3. Monitor Logs
```bash
# Check MCP audit logs
curl http://your-server.com/api/v1/mcp/audit

# Check server logs
tail -f /path/to/server.log
```

---

## Troubleshooting

### Common Issues

#### 1. MCP Server Won't Start
```bash
# Check if port is in use
lsof -i :8000

# Check environment variables
python -c "import os; print(os.getenv('SUPABASE_URL'))"

# Check dependencies
pip install -r requirements.txt
```

#### 2. Tool Not Found
```bash
# List available tools
python mcp_cli.py list

# Check if MCP is loaded
curl http://localhost:8000/api/v1/mcp/tools

# Reload MCPs
python mcp_cli.py load
```

#### 3. Environment Variables Missing
```bash
# For Instagram tools
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"

# Check if variables are set
env | grep INSTAGRAM
```

#### 4. Security Scan Failures
```bash
# Install security tools
pip install bandit safety

# Check scan results
python scripts/validate_mcp_configs.py
```

#### 5. n8n Connection Issues
```bash
# Test connectivity
curl http://your-server.com/api/v1/mcp/health

# Check CORS settings in main.py
# Add your n8n domain to allowed origins
```

### Debugging

#### Enable Debug Logging
```python
# In main.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check Database Connection
```bash
# Test Supabase connection
python -c "
from main import create_supabase_client
client = create_supabase_client()
print(client.table('mcps').select('*').execute())
"
```

#### Validate JSON Configuration
```bash
# Check JSON syntax
python -m json.tool mcp/config/external_config_official.json
python -m json.tool mcp/config/external_config_github_public.json
```

---

## Advanced Usage

### Custom MCP Development

#### 1. Create Custom MCP Bridge
```python
# In mcp/bridges/custom_bridge.py
from mcp import App

app = App("custom-tools")

@app.tool("custom_function")
async def custom_function(param1: str, param2: int):
    """Custom tool description"""
    # Your custom logic here
    return {"result": "success", "data": f"{param1}_{param2}"}
```

#### 2. Environment-Specific Configs
```json
{
  "mcps": {
    "development_only": {
      "enabled": true,
      "url": "https://github.com/dev/mcp",
      "environment": "development"
    }
  }
}
```

#### 3. Custom Security Rules
```python
# In mcp/security/custom_rules.py
def custom_security_check(mcp_config):
    # Add custom security validation
    if "dangerous_keyword" in mcp_config.get("description", ""):
        return False, "Contains dangerous keyword"
    return True, "Passed custom check"
```

### Performance Optimization

#### 1. Connection Pooling
```python
# Configure in main.py
app.state.db_pool = create_connection_pool()
```

#### 2. Caching
```python
# Add Redis caching for tool results
from redis import Redis
app.state.cache = Redis(host='localhost', port=6379)
```

#### 3. Async Processing
```python
# Use background tasks for heavy operations
from fastapi import BackgroundTasks

@app.post("/api/v1/mcp/call-async")
async def call_tool_async(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_tool_call)
```

### Monitoring & Analytics

#### 1. Add Metrics Endpoint
```python
@app.get("/metrics")
async def get_metrics():
    return {
        "tools_called": get_tool_call_count(),
        "active_mcps": get_active_mcp_count(),
        "uptime": get_server_uptime()
    }
```

#### 2. Integration with Monitoring Services
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram

tool_calls = Counter('mcp_tool_calls_total', 'Total tool calls')
response_time = Histogram('mcp_response_time_seconds', 'Response time')
```

---

## API Reference

### Complete REST API Documentation

#### Authentication
```bash
# Optional: Add API key to headers
Authorization: Bearer your-api-key
```

#### Endpoints

##### GET /api/v1/mcp/tools
List all available tools
**Response:**
```json
{
  "tools": [
    {
      "name": "tool_name",
      "description": "Tool description", 
      "mcp": "mcp_name",
      "trust_level": "OFFICIAL|COMMUNITY",
      "parameters": {},
      "enabled": true
    }
  ],
  "count": 15
}
```

##### POST /api/v1/mcp/call
Execute a tool
**Request:**
```json
{
  "tool": "instagram_post",
  "params": {
    "caption": "Hello World",
    "image_url": "https://example.com/image.jpg"
  }
}
```
**Response:**
```json
{
  "success": true,
  "result": {
    "post_id": "12345",
    "url": "https://instagram.com/p/12345"
  },
  "execution_time": 1.23,
  "tool": "instagram_post",
  "mcp": "instagram-tools"
}
```

##### GET /api/v1/mcp/health
System health check
**Response:**
```json
{
  "status": "healthy",
  "mcps_loaded": 5,
  "tools_available": 15,
  "database_connected": true,
  "uptime": "2h 30m"
}
```

##### POST /api/v1/mcp/config/load
Load MCP configurations
**Query Parameters:**
- `config_type`: `all|official|community`

**Response:**
```json
{
  "success": true,
  "loaded_mcps": 5,
  "message": "Configurations loaded successfully"
}
```

##### GET /api/v1/mcp/audit
View recent activity
**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-11-01T10:30:00Z",
      "action": "tool_call",
      "tool_name": "instagram_post",
      "user": "system",
      "success": true
    }
  ]
}
```

---

This documentation provides everything you need to use your MCP server effectively, from basic setup to advanced n8n integration. The system is production-ready and includes comprehensive security, monitoring, and management features.

For questions or issues, refer to the troubleshooting section or check the configuration files in `mcp/config/` for additional guidance.