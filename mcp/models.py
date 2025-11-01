from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum

class TrustLevel(str, Enum):
    OFFICIAL = "OFFICIAL"
    VERIFIED = "VERIFIED" 
    COMMUNITY = "COMMUNITY"
    INTERNAL = "INTERNAL"

class MCPStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    FAILED = "failed"

class MCPAddRequest(BaseModel):
    url: str
    name: Optional[str] = None
    trust_level: Optional[TrustLevel] = None

class MCPCallRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
    timeout: Optional[int] = 30

class MCPCallResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    tool_info: Optional[Dict[str, Any]] = None

class MCPInfo(BaseModel):
    id: str
    url: str
    name: str
    trust_level: TrustLevel
    status: MCPStatus
    config: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    available_tools: List[str] = []

class SecurityScanResult(BaseModel):
    mcp_id: str
    risk_score: int  # 0-100
    vulnerabilities: List[Dict[str, Any]] = []
    scan_details: Dict[str, Any] = {}
    passed: bool

class ToolInfo(BaseModel):
    name: str
    description: str
    mcp_id: str
    mcp_type: TrustLevel
    tool_schema: Dict[str, Any] = {}
    
class MCPListResponse(BaseModel):
    mcps: List[MCPInfo]
    total: int

class ToolListResponse(BaseModel):
    tools: List[ToolInfo]
    total: int