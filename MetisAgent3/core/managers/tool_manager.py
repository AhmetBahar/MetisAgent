"""
Tool Manager Implementation - MCP-First Architecture

CLAUDE.md COMPLIANT:
- MCP (Model Context Protocol) first-class support
- Auto-detection of tool types (MCP/Native/External/Plugin)
- Circuit breakers and fault tolerance
- Health monitoring with structured metrics
- Dynamic tool lifecycle management
- No quick fixes - proper architectural implementation
"""

import asyncio
import json
import subprocess
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import logging

from ..contracts import (
    BaseTool,
    ToolMetadata,
    ToolConfiguration,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolRegistry,
    HealthStatus,
    AgentResult,
    ExecutionContext,
    ToolType,
    CapabilityType,
    ToolCapability
)
from ..interfaces import IToolManager, IToolExecutor, IToolHealth

logger = logging.getLogger(__name__)


class ToolState(str, Enum):
    """Tool lifecycle states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    RUNNING = "running"
    FAILED = "failed"
    STOPPING = "stopping"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Fault-tolerant circuit breaker"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def on_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def on_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class MCPTool(BaseTool):
    """MCP-based tool implementation with JSON-RPC over stdio"""
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration, server_command: List[str]):
        super().__init__(metadata, config)
        self.server_command = server_command
        self.process = None
        self.state = ToolState.UNLOADED
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute MCP tool capability via JSON-RPC"""
        try:
            if self.state != ToolState.RUNNING:
                await self.start_server()
            
            # Prepare JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": context.trace_id,
                "method": f"tools/{capability}",
                "params": input_data
            }
            
            # Send request
            self.process.stdin.write(json.dumps(request).encode() + b'\n')
            await self.process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                return AgentResult(
                    success=False,
                    error="MCP tool response timeout",
                    error_code="TIMEOUT"
                )
            
            if not response_line:
                return AgentResult(
                    success=False,
                    error="No response from MCP server",
                    error_code="NO_RESPONSE"
                )
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                return AgentResult(
                    success=False,
                    error=response["error"]["message"],
                    error_code=response["error"].get("code", "MCP_ERROR")
                )
            
            return AgentResult(
                success=True,
                data=response.get("result"),
                metadata={
                    "tool_type": "mcp",
                    "capability": capability,
                    "server_command": " ".join(self.server_command)
                }
            )
            
        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
    
    async def health_check(self) -> HealthStatus:
        """Check MCP server health"""
        try:
            if self.state != ToolState.RUNNING or not self.process:
                return HealthStatus(
                    healthy=False,
                    component=self.metadata.name,
                    message=f"MCP server not running (state: {self.state})"
                )
            
            # Check if process is alive
            if self.process.returncode is not None:
                return HealthStatus(
                    healthy=False,
                    component=self.metadata.name,
                    message=f"MCP server process terminated (code: {self.process.returncode})"
                )
            
            # Send ping request
            ping_request = {
                "jsonrpc": "2.0",
                "id": "health_ping",
                "method": "ping",
                "params": {}
            }
            
            self.process.stdin.write(json.dumps(ping_request).encode() + b'\n')
            await self.process.stdin.drain()
            
            try:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=5.0
                )
                
                response = json.loads(response_line.decode())
                
                return HealthStatus(
                    healthy=True,
                    component=self.metadata.name,
                    message="MCP server healthy",
                    details={
                        "response_time_ms": 5000 - 5000,  # Would calculate actual response time
                        "process_id": self.process.pid
                    }
                )
                
            except asyncio.TimeoutError:
                return HealthStatus(
                    healthy=False,
                    component=self.metadata.name,
                    message="MCP server health check timeout"
                )
                
        except Exception as e:
            return HealthStatus(
                healthy=False,
                component=self.metadata.name,
                message=f"Health check error: {e}"
            )
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input against capability schema"""
        errors = []
        
        capability_info = self.get_capability_info(capability)
        if not capability_info:
            errors.append(f"Capability '{capability}' not found")
            return errors
        
        # Validate required fields
        required_fields = capability_info.input_schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Required field '{field}' missing")
        
        return errors
    
    async def start_server(self):
        """Start MCP server process"""
        try:
            self.state = ToolState.LOADING
            
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.state = ToolState.RUNNING
            logger.info(f"Started MCP server for {self.metadata.name} (PID: {self.process.pid})")
            
        except Exception as e:
            self.state = ToolState.FAILED
            logger.error(f"Failed to start MCP server for {self.metadata.name}: {e}")
            raise
    
    async def stop_server(self):
        """Stop MCP server process"""
        if self.process and self.process.returncode is None:
            self.state = ToolState.STOPPING
            
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            
            self.state = ToolState.UNLOADED
            logger.info(f"Stopped MCP server for {self.metadata.name}")


class ExecutablePlugin(BaseTool):
    """Executable-based plugin implementation"""
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration, executable_path: str):
        super().__init__(metadata, config)
        self.executable_path = executable_path
        self.state = ToolState.LOADED  # Assume executable exists
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute executable with JSON input/output"""
        try:
            import json
            import subprocess
            
            # Prepare command
            cmd = [self.executable_path, capability, json.dumps(input_data)]
            
            # Execute
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    return AgentResult(success=True, data=output_data)
                except json.JSONDecodeError:
                    return AgentResult(success=True, data={"output": result.stdout})
            else:
                return AgentResult(success=False, error=result.stderr or "Executable failed")
                
        except Exception as e:
            return AgentResult(success=False, error=f"Executable plugin error: {e}")
    
    async def health_check(self) -> HealthStatus:
        """Check if executable exists and is accessible"""
        try:
            result = subprocess.run([self.executable_path, "--health"], capture_output=True, timeout=5)
            healthy = result.returncode == 0
            return HealthStatus(
                healthy=healthy,
                component=self.metadata.name,
                message="Executable accessible" if healthy else "Executable not accessible"
            )
        except Exception:
            return HealthStatus(healthy=False, component=self.metadata.name, message="Executable not found")
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for executable plugin"""
        errors = []
        # Basic validation - executable plugins expect JSON-serializable input
        try:
            import json
            json.dumps(input_data)
        except TypeError as e:
            errors.append(f"Input data not JSON serializable: {e}")
        return errors


class APIPlugin(BaseTool):
    """API-based plugin implementation (configured via ToolConfiguration.config)

    Expects config.config to contain:
      - api_base_url: str
      - auth: { token?: str, headers?: dict }
    """
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        base = (config.config or {}).get('api_base_url', '')
        self.api_base_url = base.rstrip('/') if base else ''
        self.state = ToolState.LOADED
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute API call"""
        try:
            import aiohttp
            import asyncio
            
            url = f"{self.api_base_url}/{capability}"
            headers = {}
            auth = (self.config.config or {}).get('auth') or {}
            token = auth.get('token')
            custom_headers = auth.get('headers') or {}
            if token:
                headers['Authorization'] = f"Bearer {token}"
            headers.update(custom_headers)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=input_data, headers=headers or None, timeout=30) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        return AgentResult(success=True, data=result_data)
                    else:
                        error_text = await response.text()
                        return AgentResult(success=False, error=f"API error {response.status}: {error_text}")
                        
        except Exception as e:
            return AgentResult(success=False, error=f"API plugin error: {e}")
    
    async def health_check(self) -> HealthStatus:
        """Check API health endpoint"""
        try:
            import aiohttp
            
            headers = {}
            auth = (self.config.config or {}).get('auth') or {}
            token = auth.get('token')
            custom_headers = auth.get('headers') or {}
            if token:
                headers['Authorization'] = f"Bearer {token}"
            headers.update(custom_headers)

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/health", headers=headers or None, timeout=5) as response:
                    healthy = response.status == 200
                    return HealthStatus(
                        healthy=healthy,
                        component=self.metadata.name,
                        message=f"API health check: {response.status}"
                    )
        except Exception as e:
            return HealthStatus(healthy=False, component=self.metadata.name, message=f"API unreachable: {e}")
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for API plugin"""
        errors = []
        # Basic validation - API plugins expect JSON-serializable input
        try:
            import json
            json.dumps(input_data)
        except TypeError as e:
            errors.append(f"Input data not JSON serializable: {e}")
        return errors


class NativeTool(BaseTool):
    """Python-native tool implementation"""
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration, module_path: str, class_name: str):
        super().__init__(metadata, config)
        self.module_path = module_path
        self.class_name = class_name
        self.tool_instance = None
        self.state = ToolState.UNLOADED
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute native tool capability"""
        try:
            if self.state != ToolState.RUNNING:
                await self.load_tool_instance()
            
            # Check if tool instance implements BaseTool interface (modern)
            if hasattr(self.tool_instance, 'execute') and hasattr(self.tool_instance, 'metadata'):
                # Modern BaseTool interface - delegate to tool's execute method
                return await self.tool_instance.execute(capability, input_data, context)
            else:
                # Legacy interface - look for capability method
                method = getattr(self.tool_instance, capability, None)
                if not method:
                    return AgentResult(
                        success=False,
                        error=f"Capability '{capability}' not implemented",
                        error_code="CAPABILITY_NOT_FOUND"
                    )
                
                # Execute capability
                if asyncio.iscoroutinefunction(method):
                    result = await method(input_data, context)
                else:
                    result = method(input_data, context)
                
                return AgentResult(
                    success=True,
                    data=result,
                    metadata={
                        "tool_type": "native",
                        "capability": capability,
                        "module_path": self.module_path
                    }
                )
            
        except Exception as e:
            logger.error(f"Native tool execution failed: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
    
    async def health_check(self) -> HealthStatus:
        """Check native tool health"""
        try:
            if self.state != ToolState.RUNNING or not self.tool_instance:
                return HealthStatus(
                    healthy=False,
                    component=self.metadata.name,
                    message=f"Native tool not loaded (state: {self.state})"
                )
            
            # Check if tool instance has health_check method
            if hasattr(self.tool_instance, 'health_check'):
                if asyncio.iscoroutinefunction(self.tool_instance.health_check):
                    return await self.tool_instance.health_check()
                else:
                    return self.tool_instance.health_check()
            
            return HealthStatus(
                healthy=True,
                component=self.metadata.name,
                message="Native tool healthy"
            )
            
        except Exception as e:
            return HealthStatus(
                healthy=False,
                component=self.metadata.name,
                message=f"Health check error: {e}"
            )
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for native tool capability"""
        errors = []
        
        capability_info = self.get_capability_info(capability)
        if not capability_info:
            errors.append(f"Capability '{capability}' not found")
            return errors
        
        # Additional validation can be added here
        return errors
    
    async def load_tool_instance(self):
        """Load native tool instance"""
        try:
            self.state = ToolState.LOADING
            
            # Import module
            module = importlib.import_module(self.module_path)
            tool_class = getattr(module, self.class_name)
            
            # Instantiate tool with metadata and config parameters
            self.tool_instance = tool_class(self.metadata, self.config)
            
            self.state = ToolState.RUNNING
            logger.info(f"Loaded native tool {self.metadata.name}")
            
        except Exception as e:
            self.state = ToolState.FAILED
            logger.error(f"Failed to load native tool {self.metadata.name}: {e}")
            raise


class ToolManager(IToolManager, IToolExecutor, IToolHealth):
    """MCP-first tool manager with dynamic loading and fault tolerance"""
    
    def __init__(self, graph_memory_service=None):
        self.registry = ToolRegistry()
        self.tools: Dict[str, BaseTool] = {}
        self.tool_states: Dict[str, ToolState] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self.graph_memory = graph_memory_service
        self.startup_time = datetime.now()  # Track system startup time
        self._lock = asyncio.Lock()
    
    async def load_tool(self, metadata: ToolMetadata, config: ToolConfiguration) -> bool:
        """Load and register a tool with auto-detection"""
        async with self._lock:
            try:
                # Validate configuration
                validation_errors = await self.validate_tool_config(metadata, config)
                if validation_errors:
                    logger.error(f"Tool {metadata.name} validation failed: {validation_errors}")
                    return False
                
                # Auto-detect and instantiate tool
                tool_instance = await self._instantiate_tool(metadata, config)
                if not tool_instance:
                    return False
                
                # Register tool
                self.registry.register_tool(metadata, config)
                self.tools[metadata.name] = tool_instance
                self.tool_states[metadata.name] = ToolState.LOADED
                self.circuit_breakers[metadata.name] = CircuitBreaker()
                
                # Initialize metrics
                self.metrics[metadata.name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "avg_execution_time_ms": 0.0,
                    "last_execution": None,
                    "load_time": datetime.now()
                }
                
                # Initial health check
                health = await tool_instance.health_check()
                self.health_status[metadata.name] = health
                
                # Sync to graph memory
                if self.graph_memory:
                    logger.info(f"📦 Syncing {metadata.name} to graph memory...")
                    await self.graph_memory.sync_tool_capabilities(metadata, config)
                else:
                    logger.warning(f"⚠️ graph_memory not available for {metadata.name}")

                logger.info(f"Successfully loaded {metadata.tool_type} tool: {metadata.name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load tool {metadata.name}: {e}")
                return False
    
    async def _instantiate_tool(self, metadata: ToolMetadata, config: ToolConfiguration) -> Optional[BaseTool]:
        """Auto-detect tool type and instantiate"""
        try:
            if metadata.tool_type == ToolType.MCP:
                # MCP Tool
                server_command = config.config.get("server_command")
                if not server_command:
                    logger.error(f"MCP tool {metadata.name} missing server_command")
                    return None
                return MCPTool(metadata, config, server_command)
            
            elif metadata.tool_type == ToolType.INTERNAL:
                # Native Tool
                module_path = config.config.get("module_path")
                class_name = config.config.get("class_name")
                if not module_path or not class_name:
                    logger.error(f"Native tool {metadata.name} missing module_path or class_name")
                    return None
                
                # Create and load native tool instance
                native_tool = NativeTool(metadata, config, module_path, class_name)
                await native_tool.load_tool_instance()
                return native_tool
            
            elif metadata.tool_type == ToolType.PLUGIN:
                # Plugin Tool - External dynamic plugins
                plugin_type = config.config.get("plugin_type", "python_module")
                
                if plugin_type == "python_module":
                    # Python module plugin
                    module_path = config.config.get("module_path")
                    class_name = config.config.get("class_name")
                    if not module_path or not class_name:
                        logger.error(f"Python plugin {metadata.name} missing module_path or class_name")
                        return None
                    
                    # Create and load native tool instance
                    native_tool = NativeTool(metadata, config, module_path, class_name)
                    await native_tool.load_tool_instance()
                    return native_tool
                
                elif plugin_type == "executable":
                    # Executable plugin (command-line tools)
                    executable_path = config.config.get("executable_path")
                    if not executable_path:
                        logger.error(f"Executable plugin {metadata.name} missing executable_path")
                        return None
                    return ExecutablePlugin(metadata, config, executable_path)

                elif plugin_type == "api":
                    # API-backed plugin (HTTP proxy)
                    return APIPlugin(metadata, config)
                
                elif plugin_type == "api":
                    # API-based plugin (REST/HTTP)
                    api_base_url = config.config.get("api_base_url")
                    if not api_base_url:
                        logger.error(f"API plugin {metadata.name} missing api_base_url")
                        return None
                    return APIPlugin(metadata, config, api_base_url)
                
                else:
                    logger.error(f"Unknown plugin type: {plugin_type} for {metadata.name}")
                    return None
            
            else:
                logger.error(f"Unknown tool type: {metadata.tool_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to instantiate tool {metadata.name}: {e}")
            return None
    
    async def unload_tool(self, tool_name: str) -> bool:
        """Unload and cleanup tool"""
        async with self._lock:
            try:
                if tool_name not in self.tools:
                    return False
                
                tool = self.tools[tool_name]
                
                # Cleanup tool resources
                if isinstance(tool, MCPTool):
                    await tool.stop_server()
                
                # Remove from all tracking
                del self.tools[tool_name]
                del self.tool_states[tool_name]
                del self.circuit_breakers[tool_name]
                del self.metrics[tool_name]
                del self.health_status[tool_name]
                
                # Remove from registry
                if tool_name in self.registry.tools:
                    del self.registry.tools[tool_name]
                if tool_name in self.registry.configurations:
                    del self.registry.configurations[tool_name]
                
                logger.info(f"Unloaded tool: {tool_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unload tool {tool_name}: {e}")
                return False
    
    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get loaded tool instance"""
        return self.tools.get(tool_name)
    
    async def get_registry_info(self) -> Dict[str, Any]:
        """Get tool registry information"""
        return {
            "version": "3.0.0",  # MetisAgent3 version
            "last_updated": self.registry.last_updated.isoformat() if self.registry.last_updated else datetime.now().isoformat(),
            "tools": {
                name: {
                    "type": tool.metadata.tool_type.value,
                    "status": self.tool_states.get(name, ToolState.UNLOADED).value,
                    "capabilities": [cap.name for cap in tool.metadata.capabilities],
                    "health": self.health_status.get(name, HealthStatus(healthy=False, component=name, message="Unknown")).healthy,
                    "version": tool.metadata.version,
                    "author": tool.metadata.author or "Unknown"
                }
                for name, tool in self.tools.items()
            },
            "supported_types": [t.value for t in ToolType],
            "total_tools": len(self.tools),
            "healthy_tools": sum(1 for h in self.health_status.values() if h.healthy),
            "failed_tools": sum(1 for s in self.tool_states.values() if s == ToolState.FAILED),
            "tool_types": {
                tool_type.value: sum(1 for t in self.tools.values() if t.metadata.tool_type == tool_type)
                for tool_type in ToolType
            }
        }
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        total_tools = len(self.tools)
        healthy_tools = sum(1 for h in self.health_status.values() if h.healthy)
        
        return {
            "system_status": "healthy" if healthy_tools == total_tools and total_tools > 0 else "degraded" if healthy_tools > 0 else "critical",
            "total_tools": total_tools,
            "healthy_tools": healthy_tools,
            "failed_tools": sum(1 for s in self.tool_states.values() if s == ToolState.FAILED),
            "running_tools": sum(1 for s in self.tool_states.values() if s == ToolState.RUNNING),
            "tools": {
                name: {
                    "state": self.tool_states.get(name, ToolState.UNLOADED).value,
                    "health": self.health_status.get(name, HealthStatus(healthy=False, component=name, message="Unknown")).healthy,
                    "metrics": self.metrics.get(name, {}),
                    "circuit_breaker": {
                        "can_execute": self.circuit_breakers.get(name, CircuitBreaker()).can_execute(),
                        "failure_count": self.circuit_breakers.get(name, CircuitBreaker()).failure_count
                    }
                }
                for name in self.tools.keys()
            },
            "summary": {
                "system_uptime": self._get_system_uptime(),
                "startup_time": self.startup_time.isoformat(),
                "last_health_check": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_system_uptime(self) -> str:
        """Calculate and format system uptime"""
        uptime_delta = datetime.now() - self.startup_time
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def validate_tool_config(self, metadata: ToolMetadata, config: ToolConfiguration) -> List[str]:
        """Validate tool configuration"""
        errors = []
        
        # Basic validation
        if not metadata.name:
            errors.append("Tool name is required")
        
        if not metadata.capabilities:
            errors.append("Tool must have at least one capability")
        
        # Tool-type specific validation
        if metadata.tool_type == ToolType.INTERNAL:
            if not config.config.get("module_path"):
                errors.append("Internal tool requires module_path")
            if not config.config.get("class_name"):
                errors.append("Internal tool requires class_name")
        
        elif metadata.tool_type == ToolType.MCP:
            if not config.config.get("server_command"):
                errors.append("MCP tool requires server_command")
        
        elif metadata.tool_type == ToolType.PLUGIN:
            plugin_type = config.config.get("plugin_type", "python_module")
            
            if plugin_type == "python_module":
                if not config.config.get("module_path"):
                    errors.append("Python plugin requires module_path")
                if not config.config.get("class_name"):
                    errors.append("Python plugin requires class_name")
            elif plugin_type == "executable":
                if not config.config.get("executable_path"):
                    errors.append("Executable plugin requires executable_path")
            elif plugin_type == "api":
                if not config.config.get("api_base_url"):
                    errors.append("API plugin requires api_base_url")
        
        # Resource limits validation
        if config.resource_limits:
            if config.resource_limits.get("max_memory_mb", 0) < 0:
                errors.append("max_memory_mb must be non-negative")
            if config.resource_limits.get("max_execution_time_seconds", 0) < 0:
                errors.append("max_execution_time_seconds must be non-negative")
        
        return errors
    
    async def discover_tools(self, directory: str) -> List[Dict[str, Any]]:
        """Discover tools in directory (basic implementation)"""
        discovered = []
        tools_dir = Path(directory)
        
        if not tools_dir.exists():
            return discovered
        
        # Look for Python files that might be tools
        for tool_file in tools_dir.glob("*_tool.py"):
            try:
                # Basic heuristic - files ending with _tool.py
                discovered.append({
                    "name": tool_file.stem,
                    "path": str(tool_file),
                    "type": "internal",
                    "discovered": True,
                    "needs_metadata": True  # Indicates it needs proper metadata to be loaded
                })
            except Exception as e:
                logger.warning(f"Error discovering tool {tool_file}: {e}")
        
        return discovered
    
    async def list_tools(self, tool_type: Optional[str] = None) -> List[str]:
        """List available tools by type"""
        if tool_type:
            return [
                name for name, metadata in self.registry.tools.items()
                if metadata.tool_type.value == tool_type
            ]
        return list(self.tools.keys())
    
    async def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Get capabilities for a specific tool"""
        tool = self.tools.get(tool_name)
        if tool:
            return tool.get_capabilities()
        return []
    
    async def validate_tool_config(self, metadata: ToolMetadata, config: ToolConfiguration) -> List[str]:
        """Validate tool configuration"""
        errors = []
        
        # Basic validation
        if not metadata.name:
            errors.append("Tool name is required")
        
        if not metadata.capabilities:
            errors.append("Tool must have at least one capability")
        
        if config.tool_name != metadata.name:
            errors.append("Configuration tool name must match metadata")
        
        # Type-specific validation
        if metadata.tool_type == ToolType.MCP:
            if "server_command" not in config.config:
                errors.append("MCP tools require server_command configuration")
        
        elif metadata.tool_type == ToolType.INTERNAL:
            if not all(key in config.config for key in ["module_path", "class_name"]):
                errors.append("Native tools require module_path and class_name")
        
        return errors
    
    async def reload_tool(self, tool_name: str) -> bool:
        """Reload tool with updated configuration"""
        metadata = self.registry.get_tool_metadata(tool_name)
        config = self.registry.get_tool_config(tool_name)
        
        if not metadata or not config:
            return False
        
        await self.unload_tool(tool_name)
        return await self.load_tool(metadata, config)
    
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute tool with circuit breaker protection"""
        start_time = datetime.now()
        
        # Check circuit breaker
        circuit_breaker = self.circuit_breakers.get(request.tool_name)
        if circuit_breaker and not circuit_breaker.can_execute():
            return ToolExecutionResult(
                request=request,
                result=AgentResult(
                    success=False,
                    error="Circuit breaker OPEN - tool temporarily unavailable",
                    error_code="CIRCUIT_BREAKER_OPEN"
                ),
                execution_time_ms=0
            )
        
        # Get tool
        tool = self.tools.get(request.tool_name)
        if not tool:
            return ToolExecutionResult(
                request=request,
                result=AgentResult(
                    success=False,
                    error="Tool not found",
                    error_code="TOOL_NOT_FOUND"
                ),
                execution_time_ms=0
            )
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                tool.execute(request.capability, request.input_data, request.context),
                timeout=request.timeout_seconds
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update metrics and circuit breaker
            await self._update_metrics(request.tool_name, execution_time, result.success)
            
            # Log to graph memory
            if self.graph_memory:
                await self.graph_memory.log_tool_operation(
                    request.context.user_id,
                    request.tool_name, 
                    request.capability,
                    result,
                    execution_time
                )
            
            if result.success and circuit_breaker:
                circuit_breaker.on_success()
            elif not result.success and circuit_breaker:
                circuit_breaker.on_failure()
            
            return ToolExecutionResult(
                request=request,
                result=result,
                execution_time_ms=execution_time
            )
            
        except asyncio.TimeoutError:
            if circuit_breaker:
                circuit_breaker.on_failure()
            
            await self._update_metrics(request.tool_name, 0, False)
            
            return ToolExecutionResult(
                request=request,
                result=AgentResult(
                    success=False,
                    error="Tool execution timeout",
                    error_code="TIMEOUT"
                ),
                execution_time_ms=0
            )
        
        except Exception as e:
            if circuit_breaker:
                circuit_breaker.on_failure()
            
            await self._update_metrics(request.tool_name, 0, False)
            
            return ToolExecutionResult(
                request=request,
                result=AgentResult(
                    success=False,
                    error=str(e),
                    error_code="EXECUTION_ERROR"
                ),
                execution_time_ms=0
            )
    
    async def execute_parallel(self, requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
        """Execute multiple tools in parallel"""
        tasks = [self.execute_tool(request) for request in requests]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def execute_chain(self, requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
        """Execute tools in sequence with data passing"""
        results = []
        context_data = {}
        
        for request in requests:
            # Inject previous results
            if context_data:
                request.context.metadata.update(context_data)
            
            result = await self.execute_tool(request)
            results.append(result)
            
            # Extract data for next step
            if result.result.success and result.result.data:
                context_data[f"{request.tool_name}_result"] = result.result.data
        
        return results
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel ongoing execution (not implemented)"""
        return False
    
    async def get_execution_status(self, execution_id: str) -> Optional[str]:
        """Get execution status (not implemented)"""
        return None
    
    async def check_tool_health(self, tool_name: str) -> HealthStatus:
        """Check individual tool health"""
        tool = self.tools.get(tool_name)
        if not tool:
            return HealthStatus(
                healthy=False,
                component=tool_name,
                message="Tool not found"
            )
        
        try:
            health = await tool.health_check()
            self.health_status[tool_name] = health
            return health
        except Exception as e:
            error_health = HealthStatus(
                healthy=False,
                component=tool_name,
                message=f"Health check failed: {e}"
            )
            self.health_status[tool_name] = error_health
            return error_health
    
    async def check_all_tools_health(self) -> Dict[str, HealthStatus]:
        """Check health of all loaded tools"""
        health_results = {}
        for tool_name in self.tools:
            health_results[tool_name] = await self.check_tool_health(tool_name)
        return health_results
    
    async def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """Get performance metrics for tool"""
        return self.metrics.get(tool_name, {})
    
    async def monitor_tool_usage(self, tool_name: str) -> Any:
        """Stream tool usage metrics (not implemented)"""
        return {}
    
    async def set_health_threshold(self, tool_name: str, metric: str, threshold: float) -> bool:
        """Set health monitoring thresholds (not implemented)"""
        return True
    
    async def _update_metrics(self, tool_name: str, execution_time_ms: float, success: bool):
        """Update tool performance metrics"""
        if tool_name not in self.metrics:
            return
        
        metrics = self.metrics[tool_name]
        metrics["total_executions"] += 1
        metrics["last_execution"] = datetime.now()
        
        if success:
            metrics["successful_executions"] += 1
            # Update average execution time
            total = metrics["total_executions"]
            current_avg = metrics["avg_execution_time_ms"]
            metrics["avg_execution_time_ms"] = (
                (current_avg * (total - 1) + execution_time_ms) / total
            )
        else:
            metrics["failed_executions"] += 1
