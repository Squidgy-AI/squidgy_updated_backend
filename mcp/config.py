import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class MCPConfig:
    """MCP system configuration"""
    
    # Environment detection
    environment: str = os.getenv("ENVIRONMENT", "development")
    is_heroku: bool = "DYNO" in os.environ
    is_digitalocean: bool = "DO_APP_NAME" in os.environ
    
    # Supabase (reuse existing config)
    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_KEY")
    
    # MCP specific settings
    max_concurrent_scans: int = int(os.getenv("MCP_MAX_CONCURRENT_SCANS", "5"))
    sandbox_memory_limit: str = os.getenv("MCP_SANDBOX_MEMORY_LIMIT", "512MB")
    sandbox_enabled: bool = not ("DYNO" in os.environ)  # Disable on Heroku
    github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # Security settings
    scan_timeout: int = int(os.getenv("MCP_SCAN_TIMEOUT", "300"))  # 5 minutes
    trust_official_domains: List[str] = field(default_factory=lambda: [
        "github.com/anthropics/*",
        "anthropic.com",
        "modelcontextprotocol.io"
    ])
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def log_level(self) -> str:
        return "INFO" if self.is_production else "DEBUG"

# Global config instance
config = MCPConfig()