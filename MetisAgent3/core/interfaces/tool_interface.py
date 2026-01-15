"""
Tool System Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract interfaces
- No implementation logic
- Strong typing contracts
- Extensible plugin system
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime

from ..contracts import (
    BaseTool,
    ToolMetadata,
    ToolConfiguration,
    ToolExecutionRequest,
    ToolExecutionResult,
    HealthStatus,
    AgentResult,
    ExecutionContext
)


class IToolManager(ABC):
    """Abstract interface for tool management"""
    
    @abstractmethod
    async def load_tool(self, metadata: ToolMetadata, config: ToolConfiguration) -> bool:
        """Load and register a tool"""
        pass
    
    @abstractmethod
    async def unload_tool(self, tool_name: str) -> bool:
        """Unload and deregister a tool"""
        pass
    
    @abstractmethod
    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a loaded tool instance"""
        pass
    
    @abstractmethod
    async def list_tools(self, tool_type: Optional[str] = None) -> List[str]:
        """List available tools"""
        pass
    
    @abstractmethod
    async def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Get capabilities for a specific tool"""
        pass
    
    @abstractmethod
    async def validate_tool_config(self, metadata: ToolMetadata, config: ToolConfiguration) -> List[str]:
        """Validate tool configuration"""
        pass
    
    @abstractmethod
    async def reload_tool(self, tool_name: str) -> bool:
        """Reload a tool with updated configuration"""
        pass


class IToolExecutor(ABC):
    """Abstract interface for tool execution"""
    
    @abstractmethod
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a tool capability"""
        pass
    
    @abstractmethod
    async def execute_parallel(self, requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
        """Execute multiple tools in parallel"""
        pass
    
    @abstractmethod
    async def execute_chain(self, requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
        """Execute tools in sequence with data passing"""
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an ongoing tool execution"""
        pass
    
    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> Optional[str]:
        """Get status of a tool execution"""
        pass


class IToolHealth(ABC):
    """Abstract interface for tool health monitoring"""
    
    @abstractmethod
    async def check_tool_health(self, tool_name: str) -> HealthStatus:
        """Check health of a specific tool"""
        pass
    
    @abstractmethod
    async def check_all_tools_health(self) -> Dict[str, HealthStatus]:
        """Check health of all loaded tools"""
        pass
    
    @abstractmethod
    async def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """Get performance metrics for a tool"""
        pass
    
    @abstractmethod
    async def monitor_tool_usage(self, tool_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream tool usage metrics"""
        pass
    
    @abstractmethod
    async def set_health_threshold(self, tool_name: str, metric: str, threshold: float) -> bool:
        """Set health monitoring thresholds"""
        pass


class IToolDiscovery(ABC):
    """Abstract interface for tool discovery"""
    
    @abstractmethod
    async def discover_tools(self, search_paths: List[str]) -> List[ToolMetadata]:
        """Discover tools in specified paths"""
        pass
    
    @abstractmethod
    async def scan_for_updates(self) -> List[str]:
        """Scan for tool updates"""
        pass
    
    @abstractmethod
    async def validate_tool_signature(self, tool_path: str) -> bool:
        """Validate tool security signature"""
        pass
    
    @abstractmethod
    async def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a tool"""
        pass


class IToolSecurity(ABC):
    """Abstract interface for tool security"""
    
    @abstractmethod
    async def validate_permissions(self, user_id: str, tool_name: str, capability: str) -> bool:
        """Validate user permissions for tool capability"""
        pass
    
    @abstractmethod
    async def audit_tool_execution(self, request: ToolExecutionRequest, result: ToolExecutionResult) -> None:
        """Audit tool execution for security"""
        pass
    
    @abstractmethod
    async def sandbox_tool_execution(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute tool in sandboxed environment"""
        pass
    
    @abstractmethod
    async def check_tool_safety(self, tool_name: str) -> Dict[str, Any]:
        """Perform safety checks on tool"""
        pass


class IToolCache(ABC):
    """Abstract interface for tool result caching"""
    
    @abstractmethod
    async def cache_result(self, request: ToolExecutionRequest, result: ToolExecutionResult) -> None:
        """Cache tool execution result"""
        pass
    
    @abstractmethod
    async def get_cached_result(self, request: ToolExecutionRequest) -> Optional[ToolExecutionResult]:
        """Get cached result for request"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, tool_name: str, pattern: Optional[str] = None) -> int:
        """Invalidate cached results"""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass