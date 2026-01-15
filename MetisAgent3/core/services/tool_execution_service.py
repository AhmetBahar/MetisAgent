#!/usr/bin/env python3
"""
Tool Execution Service - Generic Tool Capability Execution

CLAUDE.md COMPLIANT:
- Single endpoint for all tool executions
- Consistent error handling and logging
- Clean separation between bridge and business logic
- Centralized authentication and authorization
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..contracts.base_types import ExecutionContext
from ..managers.tool_manager import ToolManager
from ..managers.user_manager import UserManager

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionRequest:
    """Request for tool capability execution"""
    tool_name: str
    capability: str
    action: str
    parameters: Dict[str, Any]
    user_id: str
    context: Optional[ExecutionContext] = None


@dataclass  
class ToolExecutionResponse:
    """Response from tool capability execution"""
    success: bool
    tool_name: str
    capability: str
    action: str
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "capability": self.capability,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp
        }


class ToolExecutionService:
    """Generic service for executing tool capabilities"""
    
    def __init__(self, tool_manager: ToolManager, user_manager: UserManager = None):
        self.tool_manager = tool_manager
        self.user_manager = user_manager
        logger.info("🔧 Tool Execution Service initialized")
    
    async def execute_tool_capability(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        """
        Execute a tool capability with consistent error handling and logging
        
        Args:
            request: Tool execution request
            
        Returns:
            ToolExecutionResponse with execution result
        """
        start_time = time.time()
        
        try:
            # 1. Validate request
            validation_error = self._validate_request(request)
            if validation_error:
                return self._error_response(
                    request, validation_error, 
                    execution_time=int((time.time() - start_time) * 1000)
                )
            
            # 2. Get tool instance
            tool_instance = self.tool_manager.tools.get(request.tool_name)
            if not tool_instance:
                return self._error_response(
                    request, f"Tool '{request.tool_name}' not found or not loaded",
                    execution_time=int((time.time() - start_time) * 1000)
                )
            
            # 3. Create execution context
            if not request.context:
                request.context = ExecutionContext(
                    user_id=request.user_id,
                    session_id=f"tool_exec_{int(time.time())}",
                    conversation_id=f"tool_exec_{request.tool_name}_{int(time.time())}"
                )
            
            # 4. Prepare input data
            input_data = {
                'capability': request.capability,
                'action': request.action,
                'user_id': request.user_id,
                **request.parameters
            }
            
            # 5. Execute tool capability
            logger.info(f"🔄 Executing {request.tool_name}.{request.capability}.{request.action} for user {request.user_id}")
            
            result = await tool_instance.execute(request.capability, input_data, request.context)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # 6. Handle result - support both dict and AgentResult formats
            if isinstance(result, dict):
                success = result.get('success', False)
                data = result if success else {}
                error = result.get('error') if not success else None
            elif hasattr(result, 'success') and hasattr(result, 'data'):  # AgentResult object
                success = result.success
                data = result.data or {}
                error = result.error if hasattr(result, 'error') else None
            else:
                logger.error(f"❌ Tool returned invalid response format: {type(result)}")
                return self._error_response(
                    request, f"Tool returned invalid response format: {type(result)}",
                    execution_time=execution_time
                )
            
            if success:
                logger.info(f"✅ Tool execution successful: {request.tool_name}.{request.capability}.{request.action} ({execution_time}ms)")
            else:
                logger.warning(f"⚠️ Tool execution failed: {request.tool_name}.{request.capability}.{request.action} - {error}")
            
            return ToolExecutionResponse(
                success=success,
                tool_name=request.tool_name,
                capability=request.capability,
                action=request.action,
                data=data,
                error=error,
                execution_time_ms=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"💥 Tool execution exception: {request.tool_name}.{request.capability}.{request.action} - {e}")
            return self._error_response(
                request, f"Tool execution failed: {str(e)}",
                execution_time=execution_time
            )
    
    def _validate_request(self, request: ToolExecutionRequest) -> Optional[str]:
        """
        Validate tool execution request
        
        Returns:
            Error message if validation fails, None if valid
        """
        if not request.tool_name:
            return "Tool name is required"
        
        if not request.capability:
            return "Tool capability is required"
            
        if not request.action:
            return "Tool action is required"
            
        if not request.user_id:
            return "User ID is required"
            
        if not isinstance(request.parameters, dict):
            return "Parameters must be a dictionary"
        
        return None
    
    def _error_response(self, request: ToolExecutionRequest, error_message: str, execution_time: int = 0) -> ToolExecutionResponse:
        """Create standardized error response"""
        return ToolExecutionResponse(
            success=False,
            tool_name=request.tool_name,
            capability=request.capability,
            action=request.action,
            data={},
            error=error_message,
            execution_time_ms=execution_time,
            timestamp=datetime.now().isoformat()
        )
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available tools and their capabilities"""
        available_tools = {}
        
        for tool_name, tool_instance in self.tool_manager.tools.items():
            try:
                # Try to get tool metadata
                if hasattr(tool_instance, 'get_metadata'):
                    metadata = tool_instance.get_metadata()
                    available_tools[tool_name] = {
                        "name": metadata.name if hasattr(metadata, 'name') else tool_name,
                        "description": metadata.description if hasattr(metadata, 'description') else "No description",
                        "capabilities": [cap.name for cap in metadata.capabilities] if hasattr(metadata, 'capabilities') else [],
                        "status": "available"
                    }
                else:
                    available_tools[tool_name] = {
                        "name": tool_name,
                        "description": "Tool loaded without metadata",
                        "capabilities": [],
                        "status": "available"
                    }
            except Exception as e:
                available_tools[tool_name] = {
                    "name": tool_name,
                    "description": f"Error loading tool info: {e}",
                    "capabilities": [],
                    "status": "error"
                }
        
        return available_tools


# Convenience functions for common patterns
async def execute_google_oauth2_action(service: ToolExecutionService, user_id: str, action: str, **params) -> ToolExecutionResponse:
    """Convenience function for Google OAuth2 operations"""
    request = ToolExecutionRequest(
        tool_name="google_tool",
        capability="oauth2_management", 
        action=action,
        parameters=params,
        user_id=user_id
    )
    return await service.execute_tool_capability(request)


async def execute_gmail_action(service: ToolExecutionService, user_id: str, action: str, **params) -> ToolExecutionResponse:
    """Convenience function for Gmail operations"""
    request = ToolExecutionRequest(
        tool_name="google_tool",
        capability="gmail_operations",
        action=action, 
        parameters=params,
        user_id=user_id
    )
    return await service.execute_tool_capability(request)