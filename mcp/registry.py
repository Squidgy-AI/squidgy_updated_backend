import os
import importlib.util
import asyncio
from typing import Dict, List, Optional, Any
from supabase import Client
from .models import MCPInfo, ToolInfo, TrustLevel, MCPStatus
from .config import config
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Central registry for all MCP tools (internal, custom, external)"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.tools: Dict[str, ToolInfo] = {}
        self.mcps: Dict[str, MCPInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the registry by loading all available tools"""
        logger.info("Initializing MCP Tool Registry...")
        
        # Load internal tools (bridges to existing Tools/)
        await self.load_internal_tools()
        
        # Load custom tools  
        await self.load_custom_tools()
        
        # Load external MCPs from database
        await self.load_external_mcps()
        
        logger.info(f"Registry initialized with {len(self.tools)} tools from {len(self.mcps)} MCPs")
    
    async def load_internal_tools(self):
        """Load bridge tools that wrap existing Tools/ functionality"""
        bridges_dir = os.path.join(os.path.dirname(__file__), "bridges")
        if not os.path.exists(bridges_dir):
            return
            
        for filename in os.listdir(bridges_dir):
            if filename.endswith("_bridge.py"):
                await self._load_bridge_file(filename, bridges_dir)
    
    async def load_custom_tools(self):
        """Load custom MCP tools"""
        custom_dir = os.path.join(os.path.dirname(__file__), "custom")
        if not os.path.exists(custom_dir):
            return
            
        for filename in os.listdir(custom_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                await self._load_custom_file(filename, custom_dir)
    
    async def load_external_mcps(self):
        """Load approved external MCPs from Supabase"""
        try:
            result = self.supabase.table('mcps')\
                .select('*')\
                .eq('status', MCPStatus.ACTIVE.value)\
                .execute()
                
            for mcp_data in result.data:
                await self._load_external_mcp(mcp_data)
                
        except Exception as e:
            logger.error(f"Failed to load external MCPs: {e}")
    
    async def _load_bridge_file(self, filename: str, bridges_dir: str):
        """Load a bridge file and register its tools"""
        try:
            file_path = os.path.join(bridges_dir, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract MCP info and tools from module
            if hasattr(module, 'app'):
                mcp_name = filename.replace('_bridge.py', '')
                mcp_info = MCPInfo(
                    id=f"internal_{mcp_name}",
                    url="internal",
                    name=mcp_name,
                    trust_level=TrustLevel.INTERNAL,
                    status=MCPStatus.ACTIVE,
                    available_tools=self._extract_tools_from_module(module)
                )
                
                self.mcps[mcp_info.id] = mcp_info
                self.loaded_modules[mcp_info.id] = module
                self._register_tools_from_module(module, mcp_info)
                
                logger.info(f"Loaded internal bridge: {mcp_name} with {len(mcp_info.available_tools)} tools")
                
        except Exception as e:
            logger.error(f"Failed to load bridge {filename}: {e}")
    
    async def _load_custom_file(self, filename: str, custom_dir: str):
        """Load a custom MCP file and register its tools"""
        try:
            file_path = os.path.join(custom_dir, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'app'):
                mcp_name = filename.replace('.py', '')
                mcp_info = MCPInfo(
                    id=f"custom_{mcp_name}",
                    url="custom",
                    name=mcp_name,
                    trust_level=TrustLevel.INTERNAL,
                    status=MCPStatus.ACTIVE,
                    available_tools=self._extract_tools_from_module(module)
                )
                
                self.mcps[mcp_info.id] = mcp_info
                self.loaded_modules[mcp_info.id] = module
                self._register_tools_from_module(module, mcp_info)
                
                logger.info(f"Loaded custom MCP: {mcp_name} with {len(mcp_info.available_tools)} tools")
                
        except Exception as e:
            logger.error(f"Failed to load custom MCP {filename}: {e}")
    
    async def _load_external_mcp(self, mcp_data: Dict):
        """Load an external MCP (placeholder for now)"""
        # TODO: Implement external MCP loading with sandboxing
        logger.info(f"External MCP loading not yet implemented: {mcp_data['name']}")
        pass
    
    def _extract_tools_from_module(self, module) -> List[str]:
        """Extract tool names from an MCP module"""
        tools = []
        if hasattr(module, 'app') and hasattr(module.app, '_tools'):
            tools = list(module.app._tools.keys())
        return tools
    
    def _register_tools_from_module(self, module, mcp_info: MCPInfo):
        """Register tools from a module into the registry"""
        if hasattr(module, 'app') and hasattr(module.app, '_tools'):
            for tool_name, tool_func in module.app._tools.items():
                tool_info = ToolInfo(
                    name=tool_name,
                    description=getattr(tool_func, '__doc__', ''),
                    mcp_id=mcp_info.id,
                    mcp_type=mcp_info.trust_level,
                    tool_schema=getattr(tool_func, '_schema', {})
                )
                self.tools[tool_name] = tool_info
    
    def get_tool(self, tool_name: str) -> Optional[ToolInfo]:
        """Get information about a specific tool"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[ToolInfo]:
        """List all available tools"""
        return list(self.tools.values())
    
    def list_mcps(self) -> List[MCPInfo]:
        """List all loaded MCPs"""
        return list(self.mcps.values())
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call a tool by name"""
        tool_info = self.get_tool(tool_name)
        if not tool_info:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        mcp_info = self.mcps.get(tool_info.mcp_id)
        if not mcp_info:
            raise ValueError(f"MCP '{tool_info.mcp_id}' not found")
        
        # Get the actual tool function from loaded modules
        if mcp_info.id in self.loaded_modules:
            module = self.loaded_modules[mcp_info.id]
            if hasattr(module, 'app') and hasattr(module.app, '_tools'):
                tool_func = module.app._tools.get(tool_name)
                if tool_func:
                    return await tool_func(**params)
        
        raise ValueError(f"Tool function '{tool_name}' not executable")


# Simple MCP Server implementation
class SimpleMCPServer:
    """Simplified MCP server for internal tools"""
    
    def __init__(self, name: str):
        self.name = name
        self._tools = {}
    
    def tool(self, name: str):
        """Decorator to register a tool"""
        def decorator(func):
            self._tools[name] = func
            func._schema = self._extract_schema(func)
            return func
        return decorator
    
    def _extract_schema(self, func) -> Dict[str, Any]:
        """Extract parameter schema from function annotations"""
        import inspect
        sig = inspect.signature(func)
        schema = {}
        
        for param_name, param in sig.parameters.items():
            param_info = {"type": "string"}  # Default type
            
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list:
                    param_info["type"] = "array"
            
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
                param_info["required"] = False
            else:
                param_info["required"] = True
                
            schema[param_name] = param_info
        
        return schema