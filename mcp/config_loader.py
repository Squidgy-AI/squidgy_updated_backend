import json
import os
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from supabase import Client
from .models import TrustLevel, MCPStatus
from .security.scanner import SecurityScanner
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server import MCPGateway
import logging

logger = logging.getLogger(__name__)

class MCPConfigLoader:
    """Load and manage MCPs from JSON configuration files"""
    
    def __init__(self, supabase_client: Client, mcp_gateway: Optional['MCPGateway'] = None):
        self.supabase = supabase_client
        self.gateway = mcp_gateway
        self.scanner = SecurityScanner()
        self.config_dir = Path(__file__).parent / "config"
        
    async def load_all_configs(self):
        """Load all MCP configurations"""
        logger.info("Loading all MCP configurations...")
        
        # Load official MCPs
        await self.load_config_file("external_config_official.json")
        
        # Load community MCPs  
        await self.load_config_file("external_config_github_public.json")
        
        logger.info("All MCP configurations loaded")
    
    async def load_config_file(self, filename: str):
        """Load MCPs from a specific config file"""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loading config: {config['name']}")
            
            for mcp_key, mcp_config in config["mcps"].items():
                if mcp_config.get("enabled", False):
                    await self.load_mcp_from_config(mcp_config, config["trust_level"])
                else:
                    logger.info(f"Skipping disabled MCP: {mcp_config['name']}")
                    
        except Exception as e:
            logger.error(f"Failed to load config file {filename}: {e}")
    
    async def load_mcp_from_config(self, mcp_config: Dict[str, Any], trust_level: str):
        """Load a single MCP from configuration"""
        try:
            # Check if MCP already exists
            existing = self.supabase.table('mcps')\
                .select('*')\
                .eq('url', mcp_config['url'])\
                .execute()
            
            if existing.data:
                logger.info(f"MCP already exists: {mcp_config['name']}")
                return existing.data[0]
            
            # Check environment requirements (only warn, don't block loading)
            env_check = self._check_env_requirements(mcp_config)
            if not env_check:
                logger.warning(f"Environment requirements not met for {mcp_config['name']} - tools may fail at runtime")
                # Still continue loading for security scanning
            
            # Create MCP entry
            mcp_data = {
                'url': mcp_config['url'],
                'name': mcp_config['name'],
                'trust_level': trust_level,
                'status': 'approved' if mcp_config.get('auto_approve', False) else 'pending',
                'config': {
                    'description': mcp_config.get('description', ''),
                    'tags': mcp_config.get('tags', []),
                    'capabilities': mcp_config.get('capabilities', []),
                    'sandbox': mcp_config.get('sandbox', True),
                    'max_risk_score': mcp_config.get('max_risk_score', 50)
                },
                'metadata': {
                    'source': 'config_file',
                    'auto_loaded': True,
                    'env_required': mcp_config.get('env_required', []),
                    'env_available': env_check
                }
            }
            
            # Insert into database
            result = self.supabase.table('mcps').insert(mcp_data).execute()
            mcp_id = result.data[0]['id']
            
            logger.info(f"Added MCP to database: {mcp_config['name']}")
            
            # Perform security scan if required
            if mcp_config.get('security_scan', False):
                await self._perform_security_scan(mcp_id, mcp_config)
            
            # If approved, trigger loading in gateway
            if self.gateway and mcp_data['status'] == 'approved':
                # Reload registry to pick up new MCP
                await self.gateway.registry.initialize()
            
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Failed to load MCP {mcp_config['name']}: {e}")
            return None
    
    async def _perform_security_scan(self, mcp_id: str, mcp_config: Dict[str, Any]):
        """Perform security scan for community MCPs"""
        try:
            logger.info(f"Starting security scan for {mcp_config['name']}")
            
            # Run security scan
            scan_result = await self.scanner.scan_repository(
                mcp_config['url'], 
                mcp_id
            )
            
            # Save scan results
            scan_data = {
                'mcp_id': mcp_id,
                'scan_type': 'full',
                'risk_score': scan_result.risk_score,
                'vulnerabilities': scan_result.vulnerabilities,
                'scan_details': scan_result.scan_details,
                'passed': scan_result.passed
            }
            
            self.supabase.table('security_scans').insert(scan_data).execute()
            
            # Update MCP status based on scan results
            max_risk_score = mcp_config.get('max_risk_score', 50)
            new_status = 'approved' if (scan_result.passed and scan_result.risk_score <= max_risk_score) else 'rejected'
            
            self.supabase.table('mcps')\
                .update({'status': new_status})\
                .eq('id', mcp_id)\
                .execute()
            
            logger.info(f"Security scan completed for {mcp_config['name']}: {new_status} (risk: {scan_result.risk_score})")
            
        except Exception as e:
            logger.error(f"Security scan failed for {mcp_config['name']}: {e}")
            # Mark as failed
            self.supabase.table('mcps')\
                .update({'status': 'failed'})\
                .eq('id', mcp_id)\
                .execute()
    
    def _check_env_requirements(self, mcp_config: Dict[str, Any]) -> bool:
        """Check if required environment variables are present"""
        required_vars = mcp_config.get('env_required', [])
        
        if not required_vars:
            return True
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables for {mcp_config['name']}: {missing_vars}")
            return False
        
        return True
    
    async def enable_mcp(self, mcp_name: str, config_file: str = None):
        """Enable a specific MCP from config"""
        config_files = ["external_config_official.json", "external_config_github_public.json"] if not config_file else [config_file]
        
        for filename in config_files:
            config_path = self.config_dir / filename
            if not config_path.exists():
                continue
                
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for mcp_key, mcp_config in config["mcps"].items():
                if mcp_config['name'] == mcp_name:
                    mcp_config['enabled'] = True
                    
                    # Save updated config
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # Load the MCP
                    await self.load_mcp_from_config(mcp_config, config["trust_level"])
                    return True
        
        logger.error(f"MCP not found in configs: {mcp_name}")
        return False
    
    async def disable_mcp(self, mcp_name: str, config_file: str = None):
        """Disable a specific MCP from config"""
        config_files = ["external_config_official.json", "external_config_github_public.json"] if not config_file else [config_file]
        
        for filename in config_files:
            config_path = self.config_dir / filename
            if not config_path.exists():
                continue
                
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for mcp_key, mcp_config in config["mcps"].items():
                if mcp_config['name'] == mcp_name:
                    mcp_config['enabled'] = False
                    
                    # Save updated config
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # Remove from database
                    self.supabase.table('mcps')\
                        .delete()\
                        .eq('name', mcp_name)\
                        .execute()
                    
                    logger.info(f"Disabled MCP: {mcp_name}")
                    return True
        
        logger.error(f"MCP not found in configs: {mcp_name}")
        return False
    
    def list_available_mcps(self, config_file: str = None) -> Dict[str, List[Dict]]:
        """List all MCPs available in config files"""
        result = {"official": [], "community": []}
        
        config_files = {
            "external_config_official.json": "official",
            "external_config_github_public.json": "community"
        }
        
        if config_file:
            config_files = {config_file: "unknown"}
        
        for filename, category in config_files.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                continue
                
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                for mcp_key, mcp_config in config["mcps"].items():
                    mcp_info = {
                        "key": mcp_key,
                        "name": mcp_config["name"],
                        "description": mcp_config.get("description", ""),
                        "enabled": mcp_config.get("enabled", False),
                        "url": mcp_config["url"],
                        "tags": mcp_config.get("tags", []),
                        "capabilities": mcp_config.get("capabilities", []),
                        "env_required": mcp_config.get("env_required", [])
                    }
                    
                    if category in result:
                        result[category].append(mcp_info)
                    else:
                        result["community"].append(mcp_info)
                        
            except Exception as e:
                logger.error(f"Failed to read config {filename}: {e}")
        
        return result