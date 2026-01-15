"""
MCP Core - Base classes and utilities for MCP tools
"""

import json
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

class MCPToolResult:
    """Standardized result format for MCP tools"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, metadata: Dict = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }

class MCPTool(ABC):
    """Base class for all MCP tools"""
    
    def __init__(self, name: str, description: str, version: str = "1.0.0", 
                 llm_description: str = None, use_cases: List[str] = None, 
                 keywords: List[str] = None):
        self.name = name
        self.description = description
        self.version = version
        # LLM-friendly descriptions for tool discovery
        self.llm_description = llm_description or description
        self.use_cases = use_cases or []
        self.keywords = keywords or []
        self.capabilities = []
        self.actions = {}
        self.is_enabled = True
        
    def register_action(self, action_name: str, handler, required_params: List[str] = None, optional_params: List[str] = None):
        """Register an action with the tool"""
        self.actions[action_name] = {
            'handler': handler,
            'required_params': required_params or [],
            'optional_params': optional_params or []
        }
        
    def add_capability(self, capability: str):
        """Add a capability to the tool"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def execute_action(self, action_name: str, **kwargs) -> MCPToolResult:
        """Execute a specific action"""
        try:
            if action_name not in self.actions:
                return MCPToolResult(
                    success=False, 
                    error=f"Action '{action_name}' not found in tool '{self.name}'"
                )
            
            action = self.actions[action_name]
            
            # Validate required parameters
            missing_params = []
            for param in action['required_params']:
                if param not in kwargs:
                    missing_params.append(param)
            
            if missing_params:
                return MCPToolResult(
                    success=False,
                    error=f"Missing required parameters: {', '.join(missing_params)}"
                )
            
            # Execute the handler
            result = action['handler'](**kwargs)
            
            if isinstance(result, MCPToolResult):
                return result
            else:
                return MCPToolResult(success=True, data=result)
                
        except Exception as e:
            logger.error(f"Error executing action '{action_name}' in tool '{self.name}': {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def get_info(self) -> Dict:
        """Get tool information"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'capabilities': self.capabilities,
            'actions': {
                action_name: {
                    'required_params': action_info['required_params'],
                    'optional_params': action_info['optional_params']
                }
                for action_name, action_info in self.actions.items()
            },
            'is_enabled': self.is_enabled
        }
    
    def health_check(self) -> MCPToolResult:
        """Check if the tool is healthy and ready to use"""
        try:
            # Default health check - can be overridden by subclasses
            return MCPToolResult(success=True, data={'status': 'healthy'})
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

class MCPToolRegistry:
    """Registry for managing MCP tools"""
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.tool_configs = {}
        
    def register_tool(self, tool: MCPTool) -> bool:
        """Register a tool in the registry"""
        try:
            self.tools[tool.name] = tool
            self.tool_configs[tool.name] = tool.get_info()
            logger.info(f"Tool '{tool.name}' registered successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool '{tool.name}': {str(e)}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the registry"""
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                del self.tool_configs[tool_name]
                logger.info(f"Tool '{tool_name}' unregistered successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister tool '{tool_name}': {str(e)}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[Dict]:
        """List all registered tools"""
        return [tool.get_info() for tool in self.tools.values()]
    
    def execute_tool_action(self, tool_name: str, action_name: str, **kwargs) -> MCPToolResult:
        """Execute an action on a specific tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            return MCPToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found"
            )
        
        if not tool.is_enabled:
            return MCPToolResult(
                success=False,
                error=f"Tool '{tool_name}' is disabled"
            )
        
        # Filter out potential conflicting parameters from kwargs
        filtered_kwargs = kwargs.copy()
        # Always remove these to avoid conflicts
        filtered_kwargs.pop('tool_name', None)
        filtered_kwargs.pop('action_name', None)
        filtered_kwargs.pop('tool', None)  # Alternative naming
        filtered_kwargs.pop('action', None)  # Alternative naming
        
        # Parameter compatibility mapping for visual tools
        if tool_name in ['visual_creator', 'simple_visual_creator']:
            # Map common LLM parameter variations to expected parameters
            if 'description' in filtered_kwargs and 'prompt' not in filtered_kwargs:
                filtered_kwargs['prompt'] = filtered_kwargs.pop('description')
            elif 'theme' in filtered_kwargs and 'prompt' not in filtered_kwargs:
                filtered_kwargs['prompt'] = filtered_kwargs.pop('theme')
            elif 'subject' in filtered_kwargs and 'prompt' not in filtered_kwargs:
                filtered_kwargs['prompt'] = filtered_kwargs.pop('subject')
            elif 'text' in filtered_kwargs and 'prompt' not in filtered_kwargs:
                filtered_kwargs['prompt'] = filtered_kwargs.pop('text')
        
        return tool.execute_action(action_name, **filtered_kwargs)
    
    def health_check_all(self) -> Dict[str, MCPToolResult]:
        """Run health check on all tools"""
        results = {}
        for tool_name, tool in self.tools.items():
            results[tool_name] = tool.health_check()
        return results

# Global registry instance
registry = MCPToolRegistry()

# Register internal todo tool
def _register_internal_tools():
    """Register internal tools that don't follow standard MCP pattern"""
    try:
        from tools.internal.todo_manager import get_todo_tool
        
        # Register todo tool as internal tool
        registry.tools['todo_tool'] = get_todo_tool()
        registry.tool_configs['todo_tool'] = {
            'name': 'todo_tool',
            'description': 'Internal todo list management with workflow integration',
            'actions': ['todo_create', 'todo_update_status', 'todo_get_all', 'todo_clear'],
            'version': '1.0.0',
            'type': 'internal'
        }
        
        logger.info("Internal todo tool registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register internal tools: {e}")

# Auto-register internal tools
_register_internal_tools()