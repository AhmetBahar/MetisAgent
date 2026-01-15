"""
System Tools Configuration - Blueprint Compliant Tool Registry

CLAUDE.md COMPLIANT:
- Core system tools auto-discovery
- Tool metadata and configuration definitions
- Blueprint-first tool loading
"""

from typing import Dict, List, Tuple
from ..contracts.tool_contracts import ToolMetadata, ToolConfiguration, ToolType, ToolCapability, CapabilityType


def get_internal_tools() -> List[Tuple[ToolMetadata, ToolConfiguration]]:
    """Get internal tools that should be auto-loaded for ALL users"""
    
    tools = []
    
    # LLM Tool - Core internal tool for all users
    llm_tool_metadata = ToolMetadata(
        name="llm_tool",
        description="Multi-provider LLM chat interface with conversation management",
        version="3.0.0", 
        tool_type=ToolType.INTERNAL,
        capabilities=[
            ToolCapability(
                name="chat", 
                description="Chat with LLM providers", 
                capability_type=CapabilityType.ANALYZE,
                input_schema={"type": "object", "properties": {"message": {"type": "string"}, "provider": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"response": {"type": "string"}}}
            ),
            ToolCapability(
                name="generate_response", 
                description="Generate text responses", 
                capability_type=CapabilityType.TRANSFORM,
                input_schema={"type": "object", "properties": {"prompt": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"response": {"type": "string"}}}
            ),
            ToolCapability(
                name="get_providers", 
                description="List available LLM providers", 
                capability_type=CapabilityType.READ,
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object", "properties": {"providers": {"type": "array"}}}
            )
        ],
        author="MetisAgent3"
    )
    llm_tool_config = ToolConfiguration(
        tool_name="llm_tool",
        enabled=True,
        config={
            "module_path": "core.tools.llm_tool",
            "class_name": "LLMTool"
        }
    )
    tools.append((llm_tool_metadata, llm_tool_config))
    
    return tools


def get_plugin_tools() -> List[Tuple[ToolMetadata, ToolConfiguration]]:
    """Get plugin tools that should be loaded based on settings"""
    
    tools = []
    
    # Google Tool Plugin - Auto-load at startup
    google_tool_metadata = ToolMetadata(
        name="google_tool",
        description="Complete Google Workspace integration",
        version="1.0.0",
        tool_type=ToolType.PLUGIN,
        capabilities=[],
        author="MetisAgent3"
    )
    google_tool_config = ToolConfiguration(
        tool_name="google_tool",
        enabled=True,
        config={
            "plugin_type": "python_module",
            "module_path": "plugins.google_tool.google_tool",
            "class_name": "GoogleTool",
            "client_id": "placeholder",
            "client_secret": "placeholder",
            "redirect_uri": "http://localhost:5001/oauth2/google/callback",
            "scopes": []
        }
    )
    tools.append((google_tool_metadata, google_tool_config))
    
    # Command Executor Plugin - Load based on user settings
    command_executor_metadata = ToolMetadata(
        name="command_executor",
        description="Platform-independent command execution tool",
        version="3.0.0",
        tool_type=ToolType.PLUGIN,
        capabilities=[
            ToolCapability(
                name="execute_command", 
                description="Execute system commands", 
                capability_type=CapabilityType.EXECUTE,
                input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"output": {"type": "string"}, "exit_code": {"type": "integer"}}},
                examples=[
                    {"input": {"command": "uname -a"}},
                    {"input": {"command": "ip addr show"}}
                ]
            ),
            ToolCapability(
                name="measure_ping",
                description="Measure average ping to a target host (ms)",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Hostname or IP (default: google.com)"},
                        "count": {"type": "integer", "description": "Number of pings (default: 10)"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "average_ms": {"type": "number"},
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                        "return_code": {"type": "integer"}
                    }
                },
                examples=[
                    {"input": {"target": "google.com", "count": 5}},
                    {"input": {"target": "1.1.1.1", "count": 10}}
                ]
            ),
            ToolCapability(
                name="resolve_dns",
                description="Resolve DNS records (A/AAAA/CNAME) with timing and server info",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "type": {"type": "string", "enum": ["A", "AAAA", "CNAME"]},
                        "timeout": {"type": "integer"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "records": {"type": "array", "items": {"type": "string"}},
                        "server": {"type": "string"},
                        "query_ms": {"type": "number"}
                    }
                },
                examples=[
                    {"input": {"target": "google.com", "type": "A"}},
                    {"input": {"target": "ipv6.google.com", "type": "AAAA"}}
                ]
            ),
            ToolCapability(
                name="http_check",
                description="Perform an HTTP(S) request and report status and timings",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string"},
                        "headers": {"type": "object"},
                        "body": {"type": "string"},
                        "timeout": {"type": "number"},
                        "insecure": {"type": "boolean"}
                    },
                    "required": ["url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer"},
                        "time_total_ms": {"type": "number"},
                        "time_connect_ms": {"type": "number"},
                        "time_starttransfer_ms": {"type": "number"},
                        "remote_ip": {"type": "string"}
                    }
                },
                examples=[
                    {"input": {"url": "https://www.google.com"}},
                    {"input": {"url": "https://example.com/health", "method": "GET", "timeout": 5}}
                ]
            ),
            ToolCapability(
                name="port_check",
                description="Check TCP port reachability and measure connect latency",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "timeout": {"type": "number"}
                    },
                    "required": ["host", "port"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "reachable": {"type": "boolean"},
                        "connect_ms": {"type": "number"}
                    }
                },
                examples=[
                    {"input": {"host": "8.8.8.8", "port": 53, "timeout": 2}},
                    {"input": {"host": "www.google.com", "port": 443}}
                ]
            )
        ],
        author="MetisAgent3"
    )
    command_executor_config = ToolConfiguration(
        tool_name="command_executor",
        enabled=True,  # Default enabled, but respects user settings
        config={
            "plugin_type": "python_module",
            "module_path": "tools.command_executor_tool", 
            "class_name": "CommandExecutorTool"
        }
    )
    tools.append((command_executor_metadata, command_executor_config))
    
    return tools


# Backward compatibility
def get_system_tools() -> List[Tuple[ToolMetadata, ToolConfiguration]]:
    """Backward compatibility - returns internal tools"""
    return get_internal_tools()


def get_plugin_discovery_paths() -> List[str]:
    """Get paths where additional plugins should be discovered"""
    return [
        "tools/",           # External tools directory
        "plugins/",         # Plugin directory  
        "core/tools/",      # Core tools directory
    ]


def get_mcp_tools() -> List[Tuple[ToolMetadata, ToolConfiguration]]:
    """Get MCP tools that should be auto-discovered"""
    # Future: Auto-discover MCP servers from config
    return []
