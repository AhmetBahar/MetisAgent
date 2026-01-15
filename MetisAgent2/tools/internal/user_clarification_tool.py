"""
User Clarification Tool - Handle tool conflicts and user choice requests
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class UserClarificationTool(MCPTool):
    """Tool for handling user clarification requests in conflict situations"""
    
    def __init__(self):
        super().__init__(
            name="user_clarification",
            description="Handle tool conflicts and user choice requests",
            version="1.0.0"
        )
        
        # Register capabilities
        self.add_capability("conflict_resolution")
        self.add_capability("user_interaction")
        self.add_capability("choice_presentation")
        
        # Register actions
        self.register_action(
            "request_clarification",
            self._request_clarification,
            required_params=["request", "options"],
            optional_params=["user_id", "context"]
        )
        
        self.register_action(
            "present_tool_conflict",
            self._present_tool_conflict,
            required_params=["conflicting_tools", "user_request"],
            optional_params=["user_id", "explanations"]
        )
        
        self.register_action(
            "format_choice_response",
            self._format_choice_response,
            required_params=["choices"],
            optional_params=["title", "instructions"]
        )
    
    def _request_clarification(self, request: str, options: List[Dict], 
                              user_id: str = "default", context: Dict = None, **kwargs) -> MCPToolResult:
        """Request clarification from user with multiple options"""
        try:
            # Format the clarification message
            message_parts = [
                f"📋 **İsteğiniz**: {request}",
                "",
                "🤔 **Hangi yaklaşımı tercih edersiniz?**",
                ""
            ]
            
            # Add context if available
            if context:
                context_type = context.get("conflict_type", "general")
                if context_type == "instagram":
                    message_parts.extend([
                        "**Instagram için seçenekler:**"
                    ])
            
            # Add options
            for option in options:
                tool_name = option.get("tool_name", "Unknown")
                description = option.get("description", "No description")
                message_parts.append(f"• **{tool_name}**: {description}")
            
            message_parts.extend([
                "",
                "💡 **Nasıl yanıtlayabilirsiniz:**"
            ])
            
            # Add response examples
            for option in options:
                tool_name = option.get("tool_name", "Unknown")
                example = option.get("example_response", f"{tool_name} kullan")
                message_parts.append(f"• '{example}' → {option.get('short_description', tool_name)}")
            
            message_parts.extend([
                "",
                "Ya da tercihinizi açıkça belirtin."
            ])
            
            formatted_message = "\n".join(message_parts)
            
            return MCPToolResult(
                success=True,
                data={
                    "clarification_message": formatted_message,
                    "options": options,
                    "requires_user_input": True,
                    "conflict_resolved": False,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error requesting clarification: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _present_tool_conflict(self, conflicting_tools: List[str], user_request: str,
                              user_id: str = "default", explanations: Dict = None, **kwargs) -> MCPToolResult:
        """Present tool conflict with explanations"""
        try:
            # Prepare options from conflicting tools
            options = []
            
            for tool_name in conflicting_tools:
                explanation = explanations.get(tool_name, f"{tool_name} operations") if explanations else f"{tool_name} operations"
                
                # Generate example responses based on tool name
                if "instagram" in tool_name.lower():
                    example = "Instagram tool kullan"
                    short_desc = "Doğrudan hesap işlemleri"
                elif "social_media" in tool_name.lower():
                    example = "Sosyal medya tool kullan"
                    short_desc = "İçerik planlama"
                elif "gmail" in tool_name.lower():
                    example = "Gmail helper kullan"
                    short_desc = "Gmail işlemleri"
                else:
                    example = f"{tool_name} kullan"
                    short_desc = f"{tool_name} işlemleri"
                
                options.append({
                    "tool_name": tool_name.replace("_", " ").title(),
                    "description": explanation,
                    "example_response": example,
                    "short_description": short_desc
                })
            
            # Determine conflict context
            context = {}
            if any("instagram" in tool.lower() for tool in conflicting_tools):
                context["conflict_type"] = "instagram"
            elif any("email" in tool.lower() or "gmail" in tool.lower() for tool in conflicting_tools):
                context["conflict_type"] = "email"
            else:
                context["conflict_type"] = "general"
            
            # Use request_clarification to handle the presentation
            return self._request_clarification(
                request=user_request,
                options=options,
                user_id=user_id,
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error presenting tool conflict: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _format_choice_response(self, choices: List[str], title: str = "Seçenekler",
                               instructions: str = "Lütfen birini seçin:", **kwargs) -> MCPToolResult:
        """Format a choice response for the user"""
        try:
            message_parts = [
                f"📋 **{title}**",
                "",
                instructions,
                ""
            ]
            
            for i, choice in enumerate(choices, 1):
                message_parts.append(f"{i}. {choice}")
            
            message_parts.extend([
                "",
                "💡 Numarayı yazarak veya seçeneği açıkça belirterek yanıtlayabilirsiniz."
            ])
            
            formatted_message = "\n".join(message_parts)
            
            return MCPToolResult(
                success=True,
                data={
                    "choice_message": formatted_message,
                    "choices": choices,
                    "requires_user_input": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error formatting choice response: {e}")
            return MCPToolResult(success=False, error=str(e))

    def health_check(self) -> MCPToolResult:
        """Check user clarification tool health"""
        try:
            return MCPToolResult(
                success=True,
                data={
                    "status": "healthy",
                    "capabilities": self.capabilities,
                    "actions": list(self.actions.keys()),
                    "conflicts_supported": ["instagram", "email", "image", "general"]
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the User Clarification tool with the registry"""
    tool = UserClarificationTool()
    return registry.register_tool(tool)