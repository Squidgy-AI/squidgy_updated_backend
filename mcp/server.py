from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from supabase import Client
from .models import (
    MCPCallRequest, MCPCallResponse, MCPAddRequest, 
    MCPListResponse, ToolListResponse, MCPInfo, TrustLevel
)
from .registry import ToolRegistry, SimpleMCPServer
from .config import config
from .config_loader import MCPConfigLoader
import logging
import uuid

logger = logging.getLogger(__name__)

class MCPGateway:
    """Main MCP Gateway that handles all tool calls and MCP management"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.registry = ToolRegistry(supabase_client)
        self.config_loader = MCPConfigLoader(supabase_client, self)
        self.router = APIRouter()
        self._setup_routes()
        
    async def initialize(self):
        """Initialize the MCP system"""
        await self.registry.initialize()
        # Load MCPs from configuration files
        await self.config_loader.load_all_configs()
        
    def _setup_routes(self):
        """Setup FastAPI routes for MCP endpoints"""
        
        @self.router.post("/call", response_model=MCPCallResponse)
        async def call_tool(request: MCPCallRequest):
            """Universal tool calling endpoint"""
            try:
                result = await self.registry.call_tool(request.tool, request.params)
                
                tool_info = self.registry.get_tool(request.tool)
                return MCPCallResponse(
                    success=True,
                    result=result,
                    tool_info={
                        "name": tool_info.name,
                        "mcp_id": tool_info.mcp_id,
                        "trust_level": tool_info.mcp_type.value
                    } if tool_info else None
                )
                
            except Exception as e:
                logger.error(f"Tool call failed for '{request.tool}': {e}")
                return MCPCallResponse(
                    success=False,
                    error=str(e)
                )
        
        @self.router.get("/tools", response_model=ToolListResponse)
        async def list_tools():
            """List all available tools"""
            tools = self.registry.list_tools()
            return ToolListResponse(
                tools=tools,
                total=len(tools)
            )
        
        @self.router.get("/mcps", response_model=MCPListResponse)
        async def list_mcps():
            """List all loaded MCPs"""
            mcps = self.registry.list_mcps()
            return MCPListResponse(
                mcps=mcps,
                total=len(mcps)
            )
        
        @self.router.post("/add")
        async def add_mcp(request: MCPAddRequest):
            """Add a new external MCP"""
            try:
                # Determine trust level based on URL
                trust_level = self._classify_trust_level(request.url)
                
                # Create MCP entry in database
                mcp_data = {
                    "id": str(uuid.uuid4()),
                    "url": request.url,
                    "name": request.name or self._extract_name_from_url(request.url),
                    "trust_level": trust_level.value,
                    "status": "pending" if trust_level == TrustLevel.COMMUNITY else "approved",
                    "config": {},
                    "metadata": {}
                }
                
                result = self.supabase.table('mcps').insert(mcp_data).execute()
                
                return {
                    "success": True,
                    "mcp_id": mcp_data["id"],
                    "status": mcp_data["status"],
                    "message": "MCP added successfully" if trust_level != TrustLevel.COMMUNITY 
                              else "MCP queued for security scanning"
                }
                
            except Exception as e:
                logger.error(f"Failed to add MCP: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/remove/{mcp_id}")
        async def remove_mcp(mcp_id: str):
            """Remove an MCP"""
            try:
                result = self.supabase.table('mcps').delete().eq('id', mcp_id).execute()
                
                # Reload registry to remove tools
                await self.registry.initialize()
                
                return {"success": True, "message": "MCP removed successfully"}
                
            except Exception as e:
                logger.error(f"Failed to remove MCP: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "mcps_loaded": len(self.registry.mcps),
                "tools_available": len(self.registry.tools),
                "config": {
                    "environment": config.environment,
                    "sandbox_enabled": config.sandbox_enabled
                }
            }
        
        @self.router.get("/config/list")
        async def list_config_mcps():
            """List MCPs available in configuration files"""
            return self.config_loader.list_available_mcps()
        
        @self.router.post("/config/load")
        async def load_config_mcps(config_type: str = "all"):
            """Load MCPs from configuration files"""
            try:
                if config_type == "all":
                    await self.config_loader.load_all_configs()
                elif config_type == "official":
                    await self.config_loader.load_config_file("external_config_official.json")
                elif config_type == "community":
                    await self.config_loader.load_config_file("external_config_github_public.json")
                else:
                    raise HTTPException(status_code=400, detail="Invalid config_type")
                
                # Reload registry
                await self.registry.initialize()
                
                return {
                    "success": True,
                    "message": f"Loaded {config_type} MCPs from configuration",
                    "mcps_loaded": len(self.registry.mcps),
                    "tools_available": len(self.registry.tools)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/config/enable/{mcp_name}")
        async def enable_config_mcp(mcp_name: str):
            """Enable a specific MCP from configuration"""
            try:
                success = await self.config_loader.enable_mcp(mcp_name)
                if success:
                    await self.registry.initialize()
                    return {"success": True, "message": f"Enabled MCP: {mcp_name}"}
                else:
                    raise HTTPException(status_code=404, detail=f"MCP not found: {mcp_name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/config/disable/{mcp_name}")
        async def disable_config_mcp(mcp_name: str):
            """Disable a specific MCP from configuration"""
            try:
                success = await self.config_loader.disable_mcp(mcp_name)
                if success:
                    await self.registry.initialize()
                    return {"success": True, "message": f"Disabled MCP: {mcp_name}"}
                else:
                    raise HTTPException(status_code=404, detail=f"MCP not found: {mcp_name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def _classify_trust_level(self, url: str) -> TrustLevel:
        """Classify trust level based on URL"""
        for domain in config.trust_official_domains:
            if domain.replace("*", "") in url:
                return TrustLevel.OFFICIAL
        
        if "github.com" in url:
            return TrustLevel.COMMUNITY
        
        return TrustLevel.VERIFIED
    
    def _extract_name_from_url(self, url: str) -> str:
        """Extract MCP name from URL"""
        if "github.com" in url:
            parts = url.split("/")
            if len(parts) >= 2:
                return parts[-1].replace(".git", "")
        
        return "unknown-mcp"


# Export the SimpleMCPServer for use in bridges
Server = SimpleMCPServer