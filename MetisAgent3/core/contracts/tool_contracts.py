"""
Tool Contracts - Tool System Data Models

CLAUDE.md COMPLIANT:
- Abstract base classes with clear interfaces
- Immutable configuration objects  
- Strong typing for all tool operations
- Generic capability system
"""

from typing import Any, Dict, List, Optional, Set, Union
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from .base_types import AgentResult, ExecutionContext, ExecutionStatus, Priority, HealthStatus


class ToolType(str, Enum):
    """Tool categorization"""
    INTERNAL = "internal"    # Built-in Python tools within MetisAgent3
    MCP = "mcp"             # Model Context Protocol servers
    PLUGIN = "plugin"       # External dynamic plugins (Python modules, APIs, executables)


class CapabilityType(str, Enum):
    """Capability classification"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ANALYZE = "analyze"
    TRANSFORM = "transform"


class ToolCapability(BaseModel):
    """Individual tool capability definition"""
    name: str
    description: str
    capability_type: CapabilityType
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_permissions: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        frozen = True


class ToolMetadata(BaseModel):
    """Tool metadata and configuration"""
    name: str
    description: str
    version: str
    tool_type: ToolType
    author: Optional[str] = None
    capabilities: List[ToolCapability]
    dependencies: List[str] = Field(default_factory=list)
    configuration_schema: Dict[str, Any] = Field(default_factory=dict)
    tags: Set[str] = Field(default_factory=set)

    class Config:
        frozen = True


class ToolConfiguration(BaseModel):
    """Tool-specific configuration"""
    tool_name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    user_permissions: List[str] = Field(default_factory=list)
    rate_limits: Dict[str, int] = Field(default_factory=dict)

    class Config:
        frozen = True


class ToolExecutionRequest(BaseModel):
    """Request for tool execution"""
    tool_name: str
    capability: str
    input_data: Dict[str, Any]
    context: ExecutionContext
    priority: Priority = Priority.MEDIUM
    timeout_seconds: Optional[int] = None

    class Config:
        frozen = True


class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    request: ToolExecutionRequest
    result: AgentResult[Any]
    execution_time_ms: float
    resource_usage: Optional[Dict[str, Any]] = None

    class Config:
        frozen = True


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        self.metadata = metadata
        self.config = config
        
    @abstractmethod
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        pass
    
    @abstractmethod
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        pass
    
    def get_capabilities(self) -> List[str]:
        """Get list of capability names"""
        return [cap.name for cap in self.metadata.capabilities]
    
    def get_capability_info(self, capability: str) -> Optional[ToolCapability]:
        """Get information about a specific capability"""
        for cap in self.metadata.capabilities:
            if cap.name == capability:
                return cap
        return None


class ToolRegistry(BaseModel):
    """Registry of available tools"""
    tools: Dict[str, ToolMetadata] = Field(default_factory=dict)
    configurations: Dict[str, ToolConfiguration] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    def register_tool(self, metadata: ToolMetadata, config: ToolConfiguration):
        """Register a new tool"""
        self.tools[metadata.name] = metadata
        self.configurations[metadata.name] = config
        self.last_updated = datetime.now()

    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool"""
        return self.tools.get(tool_name)

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfiguration]:
        """Get configuration for a tool"""
        return self.configurations.get(tool_name)

    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[str]:
        """List available tools, optionally filtered by type"""
        if tool_type:
            return [name for name, metadata in self.tools.items() if metadata.tool_type == tool_type]
        return list(self.tools.keys())

    class Config:
        frozen = False