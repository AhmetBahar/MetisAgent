#!/usr/bin/env python3
"""
LLM-Based Tool Routing System
CLAUDE.md uyumlu: LLM evaluation ile intelligent tool selection
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LLMToolMatch:
    """LLM-based tool match result"""
    tool_name: str
    confidence: float
    reasoning: str
    context_analysis: Dict[str, Any]

class LLMToolRouter:
    """LLM-based intelligent tool routing - CLAUDE.md compliant"""
    
    def __init__(self, llm_tool=None, tool_capability_manager=None):
        self.llm_tool = llm_tool
        self.tool_capability_manager = tool_capability_manager
        self.routing_settings = {
            "confidence_threshold": 0.3,
            "max_tools_considered": 3,
            "default_tool": "llm_tool",
            "language_detection": True,
            "context_analysis": True
        }
    
    def route_request(self, user_request: str, user_id: str = "system", context: Dict = None) -> LLMToolMatch:
        """
        LLM-based intelligent tool routing
        Analyzes user request and selects most appropriate tool
        """
        try:
            # Get available tools for user
            available_tools = self._get_available_tools(user_id)
            
            if not available_tools:
                logger.warning(f"No tools available for user {user_id}")
                return self._get_default_match()
            
            # Analyze request with LLM
            analysis_result = self._analyze_request_with_llm(
                user_request, available_tools, context
            )
            
            if not analysis_result:
                logger.warning("LLM analysis failed, using default tool")
                return self._get_default_match()
            
            # Create tool match from analysis
            return self._create_tool_match(analysis_result)
            
        except Exception as e:
            logger.error(f"Error in LLM tool routing: {e}")
            return self._get_default_match()
    
    def _get_available_tools(self, user_id: str) -> List[Dict]:
        """Get available tools for user from tool capability manager"""
        try:
            if not self.tool_capability_manager:
                logger.warning("Tool capability manager not available")
                return []
            
            # Get user tools from graph memory
            tools_prompt = self.tool_capability_manager.get_user_tool_prompt(user_id)
            
            if not tools_prompt:
                logger.warning(f"No tool prompt available for user {user_id}")
                return []
            
            # Parse tools from prompt (simple extraction)
            tools = self._parse_tools_from_prompt(tools_prompt)
            return tools
            
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return []
    
    def _parse_tools_from_prompt(self, tools_prompt: str) -> List[Dict]:
        """Parse tool information from dynamic tool prompt"""
        tools = []
        
        try:
            lines = tools_prompt.split('\n')
            current_tool = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('- ') and ':' in line:
                    # Tool line: "- tool_name: description (actions)"
                    parts = line[2:].split(':', 1)
                    if len(parts) == 2:
                        tool_name = parts[0].strip()
                        desc_and_actions = parts[1].strip()
                        
                        # Extract description and actions
                        if '(' in desc_and_actions and ')' in desc_and_actions:
                            desc_end = desc_and_actions.rfind('(')
                            description = desc_and_actions[:desc_end].strip()
                            actions_str = desc_and_actions[desc_end+1:-1]
                            actions = [a.strip() for a in actions_str.split(',')]
                        else:
                            description = desc_and_actions
                            actions = []
                        
                        tools.append({
                            "name": tool_name,
                            "description": description,
                            "actions": actions
                        })
            
            logger.info(f"Parsed {len(tools)} tools from prompt")
            return tools
            
        except Exception as e:
            logger.error(f"Error parsing tools from prompt: {e}")
            return []
    
    def _analyze_request_with_llm(self, user_request: str, available_tools: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Use LLM to analyze request and select best tool"""
        try:
            if not self.llm_tool:
                logger.error("LLM tool not available for routing analysis")
                return None
            
            # Build LLM prompt for tool selection
            analysis_prompt = self._build_tool_selection_prompt(
                user_request, available_tools, context
            )
            
            # Call LLM for analysis
            llm_result = self.llm_tool.execute_action(
                "chat",
                message=analysis_prompt,
                provider="openai", 
                model="gpt-4o-mini",
                conversation_name="tool_routing",
                user_id="system"
            )
            
            if not llm_result.success:
                logger.error(f"LLM analysis failed: {llm_result.error}")
                return None
            
            # Parse LLM response
            response_text = llm_result.data.get("response", "")
            analysis = self._parse_llm_analysis(response_text)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in LLM request analysis: {e}")
            return None
    
    def _build_tool_selection_prompt(self, user_request: str, available_tools: List[Dict], context: Dict = None) -> str:
        """Build intelligent tool selection prompt for LLM"""
        
        # Build tools list
        tools_info = []
        for tool in available_tools:
            tool_desc = f"- **{tool['name']}**: {tool['description']}"
            if tool.get('actions'):
                actions_str = ', '.join(tool['actions'][:5])  # First 5 actions
                tool_desc += f"\n  Actions: {actions_str}"
            tools_info.append(tool_desc)
        
        tools_text = '\n'.join(tools_info)
        
        # Context information
        context_info = ""
        if context:
            context_info = f"\n\n**Context:**\n{json.dumps(context, indent=2)}"
        
        prompt = f"""
INTELLIGENT TOOL SELECTION

**User Request:** "{user_request}"

**Available Tools:**
{tools_text}

{context_info}

**Task:** Analyze the user request and select the most appropriate tool.

**Analysis Criteria:**
1. **Intent Detection**: What is the user trying to accomplish?
2. **Domain Match**: Which tool's domain best matches the request?
3. **Capability Analysis**: Which tool has the right capabilities?
4. **Context Relevance**: Consider any provided context
5. **Workflow Complexity**: Does this need multi-step processing?

**Special Rules:**
- "Instagram post" / "sosyal medya" → social_media_workflow_tool (8-step professional workflow)
- "Gmail" / "email" → gmail_helper or google_oauth2_manager
- "görsel" / "image" / "visual" → simple_visual_creator
- "command" / "terminal" → command_executor  
- "workflow" / "multi-step" → sequential_thinking
- Default simple requests → llm_tool

**Return JSON only:**
{{
    "selected_tool": "tool_name",
    "confidence": 0.85,
    "reasoning": "Detailed explanation why this tool was selected",
    "alternative_tools": ["tool2", "tool3"],
    "workflow_complexity": "simple|moderate|complex",
    "requires_context": true|false
}}
"""
        
        return prompt
    
    def _parse_llm_analysis(self, response_text: str) -> Optional[Dict]:
        """Parse LLM analysis response"""
        try:
            # Extract JSON from response
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                
                analysis = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["selected_tool", "confidence", "reasoning"]
                if all(field in analysis for field in required_fields):
                    return analysis
                else:
                    logger.warning(f"Missing required fields in LLM analysis: {analysis}")
                    return None
            else:
                logger.warning(f"No JSON found in LLM response: {response_text}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in LLM analysis: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM analysis: {e}")
            return None
    
    def _create_tool_match(self, analysis: Dict) -> LLMToolMatch:
        """Create tool match from LLM analysis"""
        return LLMToolMatch(
            tool_name=analysis.get("selected_tool", self.routing_settings["default_tool"]),
            confidence=float(analysis.get("confidence", 0.5)),
            reasoning=analysis.get("reasoning", "LLM-based selection"),
            context_analysis=analysis
        )
    
    def _get_default_match(self) -> LLMToolMatch:
        """Get default tool match when routing fails"""
        return LLMToolMatch(
            tool_name=self.routing_settings["default_tool"],
            confidence=0.1,
            reasoning="Fallback to default tool due to routing failure",
            context_analysis={}
        )
    
    def update_routing_settings(self, new_settings: Dict):
        """Update routing configuration"""
        self.routing_settings.update(new_settings)
        logger.info(f"Updated routing settings: {new_settings}")