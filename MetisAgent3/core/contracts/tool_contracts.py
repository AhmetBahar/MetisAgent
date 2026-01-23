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


class RiskLevel(str, Enum):
    """Risk level for tool operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCapability(BaseModel):
    """Individual tool capability definition"""
    name: str
    description: str
    capability_type: CapabilityType
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_permissions: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    is_idempotent: bool = False  # Safe to retry without side effects
    side_effects: List[str] = Field(default_factory=list)  # What this capability modifies

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

    # Enhanced fields for MCP Server Plan v1.2
    risk_level: RiskLevel = RiskLevel.LOW  # Overall tool risk level
    requires_confirmation: bool = False  # Requires user confirmation
    category: Optional[str] = None  # Tool category (scada, workorder, etc.)
    min_compatible_version: Optional[str] = None  # Minimum compatible version
    max_compatible_version: Optional[str] = None  # Maximum compatible version
    deprecated: bool = False  # Is this tool deprecated
    deprecation_message: Optional[str] = None
    computer_mode: Optional[str] = None  # For computer tools: "off", "restricted", "dev"
    application_id: Optional[str] = None  # Application filter: "axis", "rmms", None=all
    usage_patterns: List[str] = Field(default_factory=list)  # Multi-step chaining examples for LLM

    class Config:
        frozen = True

    def is_compatible_with(self, target_version: str) -> bool:
        """Check if tool is compatible with a target version"""
        from packaging import version
        try:
            target = version.parse(target_version)
            if self.min_compatible_version:
                if target < version.parse(self.min_compatible_version):
                    return False
            if self.max_compatible_version:
                if target > version.parse(self.max_compatible_version):
                    return False
            return True
        except Exception:
            return True  # Assume compatible if version parsing fails


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
    """Registry of available tools with versioning and enhanced querying"""
    tools: Dict[str, ToolMetadata] = Field(default_factory=dict)
    configurations: Dict[str, ToolConfiguration] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    registry_version: str = "1.2.0"  # MCP Server Plan v1.2

    def register_tool(self, metadata: ToolMetadata, config: ToolConfiguration):
        """Register a new tool"""
        self.tools[metadata.name] = metadata
        self.configurations[metadata.name] = config
        self.last_updated = datetime.now()

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.configurations.pop(tool_name, None)
            self.last_updated = datetime.now()
            return True
        return False

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

    def list_tools_by_category(self, category: str) -> List[str]:
        """List tools by category"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.category == category
        ]

    def list_tools_by_application(self, application_id: str) -> List[str]:
        """List tools for a specific application (axis, rmms, etc.)"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.application_id is None or metadata.application_id == application_id
        ]

    def filter_tools_for_application(self, application_id: str) -> Dict[str, 'ToolMetadata']:
        """Get all tools filtered by application_id"""
        return {
            name: metadata for name, metadata in self.tools.items()
            if metadata.application_id is None or metadata.application_id == application_id
        }

    def list_tools_by_risk_level(self, risk_level: RiskLevel) -> List[str]:
        """List tools by risk level"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.risk_level == risk_level
        ]

    def get_high_risk_tools(self) -> List[str]:
        """Get list of high/critical risk tools"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]

    def get_deprecated_tools(self) -> List[str]:
        """Get list of deprecated tools"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.deprecated
        ]

    def get_computer_tools(self) -> List[str]:
        """Get list of computer tools (file, browser, code execution)"""
        return [
            name for name, metadata in self.tools.items()
            if metadata.computer_mode is not None
        ]

    def check_version_compatibility(self, tool_name: str, target_version: str) -> bool:
        """Check if tool is compatible with target version"""
        metadata = self.tools.get(tool_name)
        if not metadata:
            return False
        return metadata.is_compatible_with(target_version)

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """Get tool version"""
        metadata = self.tools.get(tool_name)
        return metadata.version if metadata else None

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary statistics"""
        categories = {}
        risk_levels = {}
        tool_types = {}

        for metadata in self.tools.values():
            # Count by category
            cat = metadata.category or "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1

            # Count by risk level
            risk = metadata.risk_level.value
            risk_levels[risk] = risk_levels.get(risk, 0) + 1

            # Count by tool type
            ttype = metadata.tool_type.value
            tool_types[ttype] = tool_types.get(ttype, 0) + 1

        return {
            "registry_version": self.registry_version,
            "total_tools": len(self.tools),
            "last_updated": self.last_updated.isoformat(),
            "categories": categories,
            "risk_levels": risk_levels,
            "tool_types": tool_types,
            "deprecated_count": len(self.get_deprecated_tools()),
            "high_risk_count": len(self.get_high_risk_tools())
        }

    class Config:
        frozen = False