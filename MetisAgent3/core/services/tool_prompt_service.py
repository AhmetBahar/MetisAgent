"""
Tool Prompt Service - MCP-Compatible LLM Tool Integration

CLAUDE.md COMPLIANT:
- MCP (Model Context Protocol) compatible tool descriptions
- Function calling format for LLMs (OpenAI, Anthropic, etc.)
- Dynamic schema generation from tool metadata
- Structured input/output validation
- Context-aware tool prompting
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..contracts import ToolMetadata, ToolCapability, CapabilityType
from ..managers.memory_manager import GraphMemoryService

logger = logging.getLogger(__name__)


@dataclass
class ToolPromptContext:
    """Context for tool prompt generation"""
    user_id: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_preferences: Dict[str, Any] = None
    recent_tool_usage: List[str] = None
    
    def __post_init__(self):
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.recent_tool_usage is None:
            self.recent_tool_usage = []


class ToolPromptService:
    """MCP-Compatible tool prompting service for LLMs"""
    
    def __init__(self, graph_memory_service: Optional[GraphMemoryService] = None):
        self.graph_memory = graph_memory_service
        
    async def generate_function_calling_tools(self, user_id: str, context: Optional[ToolPromptContext] = None) -> List[Dict[str, Any]]:
        """Generate OpenAI/Anthropic function calling format tools"""
        try:
            if not self.graph_memory:
                return []  # No graph memory available
                
            user_tools = await self.graph_memory.get_user_tools(user_id)
            if not user_tools:
                return []
            
            function_tools = []
            
            for tool in user_tools:
                for capability in tool.get('capabilities', []):
                    function_def = self._capability_to_function_def(tool, capability)
                    if function_def:
                        function_tools.append(function_def)
            
            # Sort by recent usage and importance
            if context and context.recent_tool_usage:
                function_tools.sort(key=lambda t: (
                    t['function']['name'] in context.recent_tool_usage,
                    t.get('priority', 0)
                ), reverse=True)
            
            return function_tools
            
        except Exception as e:
            logger.error(f"Failed to generate function calling tools: {e}")
            return []
    
    def _capability_to_function_def(self, tool: Dict[str, Any], capability: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert MCP capability to OpenAI function calling format"""
        try:
            # Generate function name (tool_name.capability_name)
            function_name = f"{tool['name'].lower()}_{capability['name']}"
            
            # Build description with context
            description = f"{capability['description']}"
            if tool.get('tool_type'):
                description += f" (via {tool['tool_type']} tool)"
            
            # Convert input schema to function parameters
            input_schema = capability.get('input_schema', {})
            parameters = self._convert_input_schema(input_schema)
            
            # Add metadata for priority and categorization
            priority = self._calculate_capability_priority(capability)
            
            return {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": description,
                    "parameters": parameters
                },
                "priority": priority,
                "tool_name": tool['name'],
                "capability_name": capability['name'],
                "tool_type": tool.get('tool_type', 'unknown')
            }
            
        except Exception as e:
            logger.warning(f"Failed to convert capability to function: {e}")
            return None
    
    def _convert_input_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert tool input schema to OpenAI function parameters format"""
        if not input_schema:
            return {"type": "object", "properties": {}}
        
        # Handle different input schema formats
        if isinstance(input_schema, dict):
            properties = {}
            required = []
            
            for param_name, param_config in input_schema.items():
                if isinstance(param_config, dict):
                    prop_def = {
                        "type": param_config.get("type", "string"),
                        "description": param_config.get("description", f"Parameter: {param_name}")
                    }
                    
                    # Handle enums/choices
                    if "enum" in param_config:
                        prop_def["enum"] = param_config["enum"]
                    
                    # Handle default values
                    if "default" in param_config:
                        prop_def["default"] = param_config["default"]
                    
                    properties[param_name] = prop_def
                    
                    # Check if required
                    if param_config.get("required", False):
                        required.append(param_name)
                else:
                    # Simple format: {"param_name": "type"}
                    properties[param_name] = {
                        "type": str(param_config),
                        "description": f"Parameter: {param_name}"
                    }
            
            result = {
                "type": "object",
                "properties": properties
            }
            
            if required:
                result["required"] = required
            
            return result
        
        # Fallback for invalid schema
        return {"type": "object", "properties": {}}
    
    def _calculate_capability_priority(self, capability: Dict[str, Any]) -> int:
        """Calculate priority for capability ordering"""
        priority = 0
        
        # Higher priority for common capability types
        cap_type = capability.get('capability_type', '')
        if cap_type == 'read':
            priority += 10
        elif cap_type == 'write':
            priority += 8
        elif cap_type == 'execute':
            priority += 6
        elif cap_type == 'analyze':
            priority += 7
        elif cap_type == 'transform':
            priority += 5
        
        # Higher priority if has examples
        if capability.get('examples'):
            priority += 3
        
        # Higher priority for well-documented capabilities
        if len(capability.get('description', '')) > 50:
            priority += 2
            
        return priority
    
    async def generate_xml_tools_prompt(self, user_id: str, context: Optional[ToolPromptContext] = None) -> str:
        """Generate Anthropic Claude XML tools format"""
        try:
            user_tools = await self.graph_memory.get_user_tools(user_id)
            if not user_tools:
                return "<tools>\nNo tools available.\n</tools>"
            
            xml_parts = ["<tools>"]
            
            for tool in user_tools:
                for capability in tool.get('capabilities', []):
                    xml_tool = self._capability_to_xml_tool(tool, capability)
                    if xml_tool:
                        xml_parts.append(xml_tool)
            
            xml_parts.append("</tools>")
            
            return "\\n".join(xml_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate XML tools prompt: {e}")
            return f"<tools>\\nError: {e}\\n</tools>"
    
    def _capability_to_xml_tool(self, tool: Dict[str, Any], capability: Dict[str, Any]) -> Optional[str]:
        """Convert capability to Anthropic Claude XML tool format"""
        try:
            function_name = f"{tool['name'].lower()}_{capability['name']}"
            description = capability.get('description', '')
            
            xml_parts = [
                f'<tool name="{function_name}">',
                f'<description>{description}</description>'
            ]
            
            # Add parameters
            input_schema = capability.get('input_schema', {})
            if input_schema:
                xml_parts.append('<parameters>')
                
                for param_name, param_config in input_schema.items():
                    if isinstance(param_config, dict):
                        param_type = param_config.get('type', 'string')
                        param_desc = param_config.get('description', f'Parameter: {param_name}')
                        required = 'true' if param_config.get('required', False) else 'false'
                        
                        xml_parts.append(f'<parameter name="{param_name}" type="{param_type}" required="{required}">{param_desc}</parameter>')
                    else:
                        xml_parts.append(f'<parameter name="{param_name}" type="{param_config}">Parameter: {param_name}</parameter>')
                
                xml_parts.append('</parameters>')
            
            # Add examples if available
            examples = capability.get('examples', [])
            if examples:
                xml_parts.append('<examples>')
                for example in examples[:2]:  # Limit to 2 examples
                    if isinstance(example, dict):
                        input_data = example.get('input', {})
                        output_data = example.get('output', {})
                        xml_parts.append(f'<example>')
                        xml_parts.append(f'<input>{json.dumps(input_data)}</input>')
                        xml_parts.append(f'<output>{json.dumps(output_data)}</output>')
                        xml_parts.append(f'</example>')
                xml_parts.append('</examples>')
            
            xml_parts.append('</tool>')
            
            return "\\n".join(xml_parts)
            
        except Exception as e:
            logger.warning(f"Failed to convert capability to XML: {e}")
            return None
    
    async def generate_natural_language_prompt(self, user_id: str, context: Optional[ToolPromptContext] = None) -> str:
        """Generate natural language tool descriptions for LLMs"""
        try:
            user_tools = await self.graph_memory.get_user_tools(user_id)
            if not user_tools:
                return "You don't have any tools available at the moment."
            
            prompt_parts = [
                "# Available Tools and Capabilities",
                "",
                "You have access to the following tools. Each tool provides specific capabilities that you can use to help the user:",
                ""
            ]
            
            # Group tools by type
            tools_by_type = {}
            for tool in user_tools:
                tool_type = tool.get('tool_type', 'unknown')
                if tool_type not in tools_by_type:
                    tools_by_type[tool_type] = []
                tools_by_type[tool_type].append(tool)
            
            # Generate descriptions by type
            for tool_type, tools in tools_by_type.items():
                prompt_parts.append(f"## {tool_type.upper()} Tools")
                prompt_parts.append("")
                
                for tool in tools:
                    prompt_parts.append(f"### {tool['name']}")
                    prompt_parts.append(f"*{tool.get('description', 'No description available')}*")
                    prompt_parts.append("")
                    
                    capabilities = tool.get('capabilities', [])
                    if capabilities:
                        prompt_parts.append("**Capabilities:**")
                        for cap in capabilities:
                            cap_desc = cap.get('description', cap.get('name', 'Unknown capability'))
                            cap_name = cap.get('name', 'unknown')
                            prompt_parts.append(f"- `{cap_name}`: {cap_desc}")
                            
                            # Add usage examples if available
                            examples = cap.get('examples', [])
                            if examples:
                                example = examples[0]  # Show first example
                                if isinstance(example, dict) and 'input' in example:
                                    prompt_parts.append(f"  Example: `{json.dumps(example['input'])}`")
                        
                        prompt_parts.append("")
            
            # Add usage instructions
            prompt_parts.extend([
                "## How to Use Tools",
                "",
                "1. **Identify the need**: Determine what the user is asking for",
                "2. **Select appropriate tool**: Choose the tool and capability that best matches the task",
                "3. **Prepare parameters**: Structure the input according to the tool's requirements",
                "4. **Execute the tool**: Call the tool function with proper parameters",
                "5. **Process results**: Interpret and present the results to the user",
                "",
                "Remember to:",
                "- Always validate inputs before calling tools",
                "- Handle errors gracefully and inform the user of any issues",
                "- Chain multiple tool calls when needed for complex tasks",
                "- Consider tool dependencies and execution order",
                ""
            ])
            
            return "\\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate natural language prompt: {e}")
            return f"Error generating tool descriptions: {e}"
    
    async def validate_tool_call(self, tool_name: str, capability: str, arguments: Dict[str, Any], user_id: str) -> Tuple[bool, List[str]]:
        """Validate a tool call before execution (MCP-compatible)"""
        try:
            # Get tool metadata
            user_tools = await self.graph_memory.get_user_tools(user_id)
            target_tool = None
            target_capability = None
            
            for tool in user_tools:
                if tool['name'].lower() == tool_name.split('_')[0]:  # Handle tool_name_capability format
                    target_tool = tool
                    for cap in tool.get('capabilities', []):
                        if cap['name'] == capability:
                            target_capability = cap
                            break
                    break
            
            if not target_tool or not target_capability:
                return False, [f"Tool '{tool_name}' with capability '{capability}' not found or not accessible"]
            
            # Validate input schema
            input_schema = target_capability.get('input_schema', {})
            errors = []
            
            # Check required parameters
            for param_name, param_config in input_schema.items():
                if isinstance(param_config, dict) and param_config.get('required', False):
                    if param_name not in arguments:
                        errors.append(f"Required parameter '{param_name}' missing")
                    elif arguments[param_name] is None:
                        errors.append(f"Required parameter '{param_name}' cannot be null")
            
            # Check parameter types
            for param_name, param_value in arguments.items():
                if param_name in input_schema:
                    param_config = input_schema[param_name]
                    if isinstance(param_config, dict):
                        expected_type = param_config.get('type', 'string')
                        if not self._validate_parameter_type(param_value, expected_type):
                            errors.append(f"Parameter '{param_name}' should be of type '{expected_type}'")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Tool call validation failed: {e}")
            return False, [f"Validation error: {e}"]
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type according to JSON Schema types"""
        if value is None:
            return True  # Allow null unless explicitly required
        
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Unknown type, allow it
    
    async def get_tool_usage_analytics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get tool usage analytics for prompt optimization"""
        try:
            # This would integrate with tool operation logging
            # For now, return mock analytics
            return {
                "user_id": user_id,
                "period_days": days,
                "total_tool_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "most_used_tools": [],
                "most_used_capabilities": [],
                "success_rate_by_tool": {},
                "avg_execution_time_by_tool": {},
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get tool usage analytics: {e}")
            return {}

    async def generate_tool_prompt(self, available_tools: List[Dict[str, Any]], format_type: str = "openai") -> Dict[str, Any]:
        """Generate tool prompt from available tools list (without graph memory dependency)"""
        try:
            if format_type == "openai":
                return await self._generate_openai_format(available_tools)
            elif format_type == "anthropic":
                return await self._generate_anthropic_format(available_tools)
            elif format_type == "natural":
                return await self._generate_natural_format(available_tools)
            else:
                return {"error": f"Unknown format type: {format_type}"}
                
        except Exception as e:
            logger.error(f"Error generating tool prompt: {e}")
            return {"error": str(e)}
    
    async def _generate_openai_format(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate OpenAI function calling format"""
        functions = []
        
        for tool in tools:
            tool_name = tool.get("name", "unknown")
            for capability in tool.get("capabilities", []):
                cap_name = capability.get("name", "unknown")
                function_name = f"{tool_name}_{cap_name}"
                
                function_def = {
                    "name": function_name,
                    "description": f"{capability.get('description', '')} (via {tool_name})",
                    "parameters": self._convert_input_schema(capability.get("input_schema", {}))
                }
                functions.append(function_def)
        
        return {
            "functions": functions,
            "total_functions": len(functions),
            "format": "openai_function_calling"
        }
    
    async def _generate_anthropic_format(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Anthropic XML format"""
        xml_parts = ["<tools>"]
        
        for tool in tools:
            tool_name = tool.get("name", "unknown")
            tool_description = tool.get("description", "")
            
            xml_parts.append(f"<tool name='{tool_name}'>")
            xml_parts.append(f"  <description>{tool_description}</description>")
            xml_parts.append("  <capabilities>")
            
            for capability in tool.get("capabilities", []):
                cap_name = capability.get("name", "unknown")
                cap_desc = capability.get("description", "")
                input_schema = capability.get("input_schema", {})
                
                xml_parts.append(f"    <capability name='{cap_name}'>")
                xml_parts.append(f"      <description>{cap_desc}</description>")
                
                if input_schema:
                    xml_parts.append("      <parameters>")
                    for param, schema in input_schema.items():
                        param_type = schema.get("type", "string")
                        param_desc = schema.get("description", "")
                        required = "required" if schema.get("required", False) else "optional"
                        xml_parts.append(f"        <parameter name='{param}' type='{param_type}' {required}>{param_desc}</parameter>")
                    xml_parts.append("      </parameters>")
                
                xml_parts.append("    </capability>")
            
            xml_parts.append("  </capabilities>")
            xml_parts.append("</tool>")
        
        xml_parts.append("</tools>")
        xml_content = "\n".join(xml_parts)
        
        return {
            "xml_content": xml_content,
            "total_tools": len(tools),
            "format": "anthropic_xml"
        }
    
    async def _generate_natural_format(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate natural language format"""
        nl_parts = ["Available Tools and Capabilities:"]
        
        for i, tool in enumerate(tools, 1):
            tool_name = tool.get("name", "unknown")
            tool_description = tool.get("description", "")
            
            nl_parts.append(f"\n{i}. {tool_name}")
            if tool_description:
                nl_parts.append(f"   Description: {tool_description}")
            
            capabilities = tool.get("capabilities", [])
            if capabilities:
                nl_parts.append("   Capabilities:")
                for j, capability in enumerate(capabilities, 1):
                    cap_name = capability.get("name", "unknown")
                    cap_desc = capability.get("description", "")
                    nl_parts.append(f"     {i}.{j} {cap_name}: {cap_desc}")
        
        nl_content = "\n".join(nl_parts)
        
        return {
            "natural_language": nl_content,
            "total_tools": len(tools),
            "format": "natural_language"
        }

class MCPToolPromptingService:
    """MCP-specific tool prompting with protocol compliance"""
    
    def __init__(self, tool_prompt_service: ToolPromptService):
        self.tool_prompt_service = tool_prompt_service
    
    async def generate_mcp_tools_list_response(self, user_id: str) -> Dict[str, Any]:
        """Generate MCP-compatible tools/list response"""
        try:
            user_tools = await self.tool_prompt_service.graph_memory.get_user_tools(user_id)
            
            mcp_tools = []
            for tool in user_tools:
                for capability in tool.get('capabilities', []):
                    mcp_tool = {
                        "name": f"{tool['name'].lower()}_{capability['name']}",
                        "description": capability.get('description', ''),
                        "inputSchema": self.tool_prompt_service._convert_input_schema(
                            capability.get('input_schema', {})
                        )
                    }
                    mcp_tools.append(mcp_tool)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": mcp_tools
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate MCP tools list: {e}")
            return {
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }
    
    async def handle_mcp_tool_call(self, tool_name: str, arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle MCP-compatible tool call"""
        try:
            # Parse tool_name to extract tool and capability
            if '_' in tool_name:
                tool_base = tool_name.split('_')[0]
                capability = '_'.join(tool_name.split('_')[1:])
            else:
                tool_base = tool_name
                capability = "default"
            
            # Validate the call
            is_valid, errors = await self.tool_prompt_service.validate_tool_call(
                tool_name, capability, arguments, user_id
            )
            
            if not is_valid:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params",
                        "data": {"errors": errors}
                    }
                }
            
            # This would integrate with actual tool execution
            # For now, return success response format
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Tool {tool_name} called successfully with arguments: {json.dumps(arguments)}"
                        }
                    ],
                    "isError": False
                }
            }
            
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }
