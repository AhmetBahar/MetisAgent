"""
Sequential Thinking Tool - MCP Server Integration
Simple wrapper for Sequential Thinking MCP Server
"""

import json
import os
import subprocess
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class SequentialThinkingTool(MCPTool):
    """Sequential Thinking MCP Server Integration Tool"""
    
    def __init__(self):
        super().__init__(
            name="sequential_thinking",
            description="Multi-step workflow planning and complex problem solving",
            version="1.0.0"
        )
        
        # Store registry reference at initialization to avoid circular imports
        self.registry_ref = None
        
        # MCP Server path
        self.server_path = "./node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js"
        self.server_process = None
        
        # Check if MCP server exists
        if os.path.exists(self.server_path):
            logger.info(f"Found Sequential Thinking MCP server at: {self.server_path}")
        else:
            logger.error(f"Sequential Thinking MCP server not found at: {self.server_path}")
            
        # Register actions
        self._register_actions()
    
    def _get_registry(self):
        """Get registry reference safely without circular import"""
        if self.registry_ref is None:
            # Only import when needed and not during tool initialization
            try:
                from app.mcp_core import registry
                self.registry_ref = registry
            except ImportError as e:
                logger.error(f"Failed to import registry: {e}")
                return None
        return self.registry_ref
    
    def _register_actions(self):
        """Register actions for the tool"""
        self.register_action(
            "plan_workflow",
            self._plan_workflow,
            required_params=["user_request"],
            optional_params=["available_tools", "constraints", "user_id"]
        )
        
        self.register_action(
            "break_down_task",
            self._break_down_task,
            required_params=["task_description"],
            optional_params=["context", "complexity_level", "user_id"]
        )
        
        self.register_action(
            "evaluate_complexity",
            self._evaluate_complexity,
            required_params=["problem_description"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "match_tools_intelligently",
            self._match_tools_intelligently,
            required_params=["user_request"],
            optional_params=["available_tools", "user_id"]
        )
        
        self.register_action(
            "optimize_sequence",
            self._optimize_sequence,
            required_params=["current_plan"],
            optional_params=["optimization_criteria", "user_id"]
        )
        
        self.register_action(
            "analyze_dependencies",
            self._analyze_dependencies,
            required_params=["steps"],
            optional_params=["user_id"]
        )
        
        # Context-aware workflow planning
        self.register_action(
            "plan_context_aware_workflow",
            self._plan_context_aware_workflow,
            required_params=["user_request"],
            optional_params=["user_id", "context_hints"]
        )
        
        self.register_action(
            "discover_tool_capabilities",
            self._discover_tool_capabilities,
            required_params=[],
            optional_params=["user_id"]
        )
    
    def _start_mcp_server(self):
        """Start the MCP server if not running"""
        if self.server_process and self.server_process.poll() is None:
            return True
            
        try:
            self.server_process = subprocess.Popen(
                ["node", self.server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("Sequential Thinking MCP server started")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    def _call_mcp_server(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call real MCP server - should be implemented by actual MCP integration"""
        # This should be handled by the MCP framework itself
        # The tool actions will be called directly by the MCP system
        raise NotImplementedError("This method should not be called - MCP actions are handled directly")
    
    def _plan_workflow(self, user_request: str, available_tools: List[str] = None, 
                      constraints: Dict[str, Any] = None, user_id: str = None) -> MCPToolResult:
        """Plan a multi-step workflow for the given request using LLM-based dynamic planning"""
        try:
            logger.info(f"Planning workflow for: {user_request[:50]}...")
            
            # PURE LLM PLANNING - No rule-based system  
            logger.info(f"PURE LLM PLANNING: Starting intelligent workflow analysis for: {user_request}")
            
            # Call LLM-based workflow planning instead of fallback
            steps = None  # Let LLM planning run
            
            # Skip fallback - go directly to LLM planning
            logger.info(f"BYPASSING FALLBACK: Going to LLM-based intelligent planning")
            
            # Call LLM-based workflow generation
            steps = self._generate_workflow_with_llm(user_request, available_tools, user_id)
            
            if not steps:
                logger.error("LLM workflow generation failed")
                return MCPToolResult(success=False, error="LLM workflow planning failed")
            
            workflow_data = {
                "title": "Sequential Thinking Workflow",
                "description": "Multi-step workflow planned by Sequential Thinking",
                "complexity": "medium",
                "estimated_duration": sum(step.get("estimated_duration", 30) for step in steps),
                "steps": steps,
                "success_criteria": "All steps completed successfully",
                "error_handling": "Retry failed steps with backoff"
            }
            
            logger.info(f"Generated workflow with {len(steps)} steps")
            
            return MCPToolResult(
                success=True,
                data=workflow_data,
                metadata={"method": "plan_workflow", "user_id": user_id}
            )
                
        except Exception as e:
            logger.error(f"Workflow planning failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "plan_workflow", "user_id": user_id}
            )
    
    def _generate_workflow_with_llm(self, user_request: str, available_tools: List[str] = None, user_id: str = None) -> List[Dict[str, Any]]:
        """Generate workflow steps using LLM-based dynamic planning - REDESIGNED"""
        with open("/tmp/method_entry_immediate.txt", "w") as f:
            f.write(f"METHOD ENTRY: {user_request}\n")
        try:
            # Simple print debugging 
            print(f"🔥 SEQUENTIAL THINKING: _generate_workflow_with_llm CALLED with: {user_request}")
            print(f"🔥 Time: {__import__('datetime').datetime.now()}")
            with open("/tmp/generate_method_debug.txt", "w") as f:
                f.write(f"_generate_workflow_with_llm CALLED\n")
                f.write(f"user_request param: {user_request}\n")
                f.write(f"Time: {__import__('datetime').datetime.now()}\n")
            # Import LLM tool - DIRECT IMPORT to avoid registry circular dependency
            try:
                from tools.internal.llm_tool import LLMTool
                llm_tool = LLMTool()
                with open("/tmp/method_entry.txt", "a") as f:
                    f.write("🔥 DIRECT LLM TOOL CREATED\n")
            except Exception as import_error:
                with open("/tmp/method_entry.txt", "a") as f:
                    f.write(f"🔥 LLM IMPORT ERROR: {import_error}\n")
                llm_tool = None
            
            if not llm_tool:
                logger.error("LLM tool not available for dynamic planning - CANNOT PROCEED")
                return MCPToolResult(success=False, error="LLM tool required for intelligent planning")
            
            # HYBRID APPROACH: Global registry for tools, user-specific graph memory for data
            # Use global registry directly for tool access and conflict detection
            dynamic_prompt = None
            available_tools_dict = {}
            
            logger.info(f"SEQUENTIAL THINKING: Using global registry approach for user {user_id}")
            
            # Skip graph memory tool lookup, go directly to registry
            # (Graph memory stays user-isolated for data, but tools are global)
            
            # Use registry directly for all tool access
            logger.info(f"SEQUENTIAL THINKING: Loading tools from global registry for conflict detection")
            registry = self._get_registry()
            if not registry:
                logger.error("Registry not available")
                return []
            all_tools = registry.list_tools()
            
            # Build tools info for LLM from registry
            available_tools_info = {}
            for tool_info in all_tools:
                # Debug: Check tool_info type to prevent 'str' errors
                if not isinstance(tool_info, dict):
                    logger.warning(f"Tool info is not dict: {type(tool_info)}, skipping")
                    continue
                    
                tool_name = tool_info.get("name", "unknown")
                
                # Fix: Actions is a dict in get_info(), not a list
                actions_dict = tool_info.get("actions", {})
                if isinstance(actions_dict, dict):
                    actions = list(actions_dict.keys())  # Get action names
                else:
                    actions = []  # Fallback
                    
                description = tool_info.get("description", f"{tool_name} operations")
                
                available_tools_info[tool_name] = {
                    "description": description,
                    "actions": actions,
                    "capabilities": description
                }
            
            # Generate prompt from registry tools
            tool_lines = [f"- {tool}: {info['description']} ({', '.join(info['actions'])})" for tool, info in available_tools_info.items()]
            dynamic_prompt = f"AVAILABLE TOOLS:\n{chr(10).join(tool_lines)}\n\nANALYZE THE REQUEST AND CREATE LOGICAL STEPS USING THESE EXACT TOOLS AND ACTIONS."
            
            logger.info(f"SEQUENTIAL THINKING: Using global registry with {len(available_tools_info)} tools")
            available_tools_dict = available_tools_info
            
            # Check for tool conflicts before planning
            # Convert available_tools_dict to proper format for conflict detection
            if isinstance(available_tools_dict, list):
                # Convert list to dict for conflict detection
                tools_dict = {}
                for tool in available_tools_dict:
                    if isinstance(tool, dict) and 'name' in tool:
                        tools_dict[tool['name']] = tool
                    elif isinstance(tool, str):
                        tools_dict[tool] = {"name": tool}
                available_tools_dict = tools_dict
                logger.info(f"CONFLICT DETECTION: Converted list to dict, {len(available_tools_dict)} tools")
            
            # If graph memory tools are empty but registry fallback has tools, use registry for conflict detection
            if not available_tools_dict and 'available_tools_info' in locals():
                logger.info(f"CONFLICT DETECTION: Using registry fallback tools for conflict detection")
                available_tools_dict = available_tools_info
            
            print(f"🔥 CALLING CONFLICT DETECTION with: {user_request}")
            conflict_result = self._detect_tool_conflicts(user_request, available_tools_dict)
            print(f"🔥 CONFLICT RESULT: {conflict_result}")
            
            if conflict_result.get("has_conflicts", False):
                # Return clarification request instead of workflow
                clarification_message = self._create_clarification_response(
                    conflict_result["conflicts"], 
                    user_request
                )
                
                logger.info(f"TOOL CONFLICT DETECTED: {len(conflict_result['conflicts'])} conflicts found")
                logger.info(f"CONFLICT DEBUG: About to return clarification workflow")
                print(f"🔥 CONFLICT WORKFLOW RETURN: {conflict_result}")
                
                # Return a special "clarification needed" workflow
                # Prepare options for user_clarification tool
                options = []
                for conflict_data in conflict_result["conflicts"]:
                    for tool_name in conflict_data["conflicting_tools"]:
                        explanation = conflict_data["explanations"].get(tool_name, f"{tool_name} operations")
                        options.append({
                            "tool_name": tool_name.replace("_", " ").title(),
                            "description": explanation
                        })
                
                return [{
                    "step_id": "clarification_needed",
                    "title": "Tool Selection Required",
                    "description": clarification_message,
                    "tool_name": "user_clarification",
                    "action_name": "request_clarification",
                    "parameters": {
                        "request": user_request,
                        "options": options,
                        "user_id": "system",
                        "context": conflict_result
                    },
                    "requires_user_input": True,
                    "conflict_info": conflict_result,
                    "original_request": user_request
                }]
            
            # Build planning prompt with dynamic tools
            planning_prompt = f"""
TASK: You are a workflow planner that ONLY returns JSON. Do NOT call tools. Do NOT execute actions. ONLY return workflow JSON.

USER REQUEST: "{user_request}"

{dynamic_prompt}

ANALYZE THE REQUEST AND CREATE LOGICAL STEPS USING THESE EXACT TOOLS AND ACTIONS.

LLM should intelligently determine which tools and actions are needed based on the user request intent.

CRITICAL: You must ONLY return JSON in this exact format. Do NOT call any tools. Do NOT execute any actions.

{{
  "steps": [
    {{
      "step_id": "step_1",
      "tool_name": "appropriate_tool",
      "action_name": "appropriate_action", 
      "description": "Description of what this step accomplishes"
    }}
  ],
  "reasoning": "Explanation of why these tools and steps were chosen"
}}

RULES:
- ONLY return JSON, no other text
- Do NOT call tools or execute actions  
- Use exact tool/action names from available tools
- Keep workflows simple and focused on user intent
- Let tools handle their own complex internal workflows"""
            
            # Debug prompt content
            logger.info(f"SEQUENTIAL THINKING DEBUG: Dynamic prompt: {dynamic_prompt[:200]}...")
            
            # DEBUG: Write debug info to file
            try:
                with open("/home/ahmet/MetisAgent/MetisAgent2/prompt_debug.txt", "w", encoding="utf-8") as f:
                    f.write(f"🔥 PROMPT DEBUG - Dynamic prompt length: {len(dynamic_prompt) if dynamic_prompt else 0}\n")
                    f.write(f"🔥 PROMPT DEBUG - Dynamic prompt content: '{dynamic_prompt[:500] if dynamic_prompt else 'NONE'}'\n")
                    f.write(f"🔥 PROMPT DEBUG - Final planning prompt:\n")
                    f.write(planning_prompt)
                    f.write(f"\n🔥 Total planning prompt length: {len(planning_prompt)}\n")
            except Exception as e:
                logger.error(f"Failed to write prompt debug: {e}")
            
            # Call LLM
            logger.info(f"SEQUENTIAL THINKING DEBUG: Calling LLM for workflow generation")
            logger.info(f"SEQUENTIAL THINKING DEBUG: User request = '{user_request}'")
            logger.info(f"SEQUENTIAL THINKING DEBUG: Planning prompt length = {len(planning_prompt)} chars")
            
            # Write debug info to file BEFORE LLM call
            try:
                with open("/tmp/llm_debug_before.txt", "w", encoding="utf-8") as f:
                    f.write(f"USER REQUEST: {user_request}\n")
                    f.write("="*50 + "\n")
                    f.write(f"PROMPT SENT TO LLM:\n{planning_prompt}\n")
                    f.write("="*50 + "\n")
                    f.write("CALLING LLM NOW...\n")
            except Exception as e:
                logger.error(f"Failed to write debug file: {e}")
            
            result = llm_tool.execute_action("chat",
                message=planning_prompt,
                user_id=user_id or "system"
            )
            
            if not result.success or not result.data:
                logger.error(f"SEQUENTIAL THINKING: LLM call failed - {result.error if result else 'No result'}")
                return MCPToolResult(success=False, error="LLM planning failed, no fallback available")
            
            response_text = result.data.get("response", "")
            logger.info(f"SEQUENTIAL THINKING DEBUG: LLM response length = {len(response_text)} chars")
            logger.info(f"SEQUENTIAL THINKING DEBUG: LLM full response = {response_text}")
            
            # Write to debug file for analysis - use home directory
            try:
                debug_file = "/home/ahmet/MetisAgent/MetisAgent2/llm_debug.txt"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(f"USER REQUEST: {user_request}\n")
                    f.write("="*50 + "\n")
                    f.write(f"PROMPT SENT TO LLM:\n{planning_prompt}\n")
                    f.write("="*50 + "\n")
                    f.write(f"LLM RESPONSE:\n{response_text}\n")
                    f.write("="*50 + "\n")
                print(f"🔥 DEBUG: LLM debug written to {debug_file}")
            except Exception as e:
                print(f"🔥 DEBUG FILE ERROR: {e}")
                logger.error(f"Failed to write debug file: {e}")
            
            # Parse JSON response
            import json
            import re
            
            try:
                # Parse JSON response - expect steps format only
                logger.info(f"SEQUENTIAL THINKING DEBUG: Parsing JSON from LLM response...")
                
                # Try to parse the full response as JSON
                try:
                    llm_response = json.loads(response_text)
                    logger.info(f"SEQUENTIAL THINKING DEBUG: Successfully parsed JSON response")
                except:
                    # Extract JSON from text if needed
                    json_match = re.search(r'\{.*?"steps".*?\}', response_text, re.DOTALL)
                    if json_match:
                        llm_response = json.loads(json_match.group())
                        logger.info(f"SEQUENTIAL THINKING DEBUG: Extracted JSON from text")
                    else:
                        raise ValueError("No valid JSON with steps found")
                
                # Expect steps format
                if "steps" not in llm_response:
                    raise ValueError("Response missing 'steps' field")
                    
                steps_data = llm_response.get("steps", [])
                reasoning = llm_response.get("reasoning", "LLM workflow")
                
                logger.info(f"SEQUENTIAL THINKING DEBUG: Found {len(steps_data)} steps - {reasoning}")
                
                if steps_data:
                    
                    logger.info(f"SEQUENTIAL THINKING DEBUG: LLM generated {len(steps_data)} steps - {reasoning}")
                    logger.info(f"SEQUENTIAL THINKING DEBUG: Steps data: {steps_data}")
                    
                    print(f"🔥 LLM GENERATED {len(steps_data)} STEPS: {steps_data}")
                    
                    # Convert LLM steps to workflow format
                    converted_steps = []
                    for i, step_data in enumerate(steps_data):
                        # Clean step data
                        step_id = step_data.get("step_id", f"step_{i+1}")
                        tool_name = step_data.get("tool_name", "llm_tool")
                        action_name = step_data.get("action_name", "chat")
                        description = step_data.get("description", f"Step {i+1}")
                        depends_on = step_data.get("depends_on")
                        
                        # Build workflow step
                        converted_step = {
                            "id": step_id,
                            "title": description,
                            "description": description,
                            "tool_name": tool_name,
                            "action_name": action_name,
                            "params": self._generate_params_for_step(step_data, user_request),
                            "dependencies": [depends_on] if depends_on else [],
                            "estimated_duration": 30,
                            "validation": "Step completed successfully"
                        }
                        converted_steps.append(converted_step)
                        
                        logger.info(f"STEP {i+1}: {description} → {tool_name}.{action_name}()")
                    
                    print(f"🔥 CONVERTED {len(converted_steps)} STEPS TO WORKFLOW FORMAT")
                    for i, step in enumerate(converted_steps):
                        print(f"🔥 STEP {i+1}: {step['title']} ({step['tool_name']}.{step['action_name']})")
                    
                    if converted_steps:
                        return converted_steps
                else:
                    logger.warning("SEQUENTIAL THINKING DEBUG: No JSON workflow found in LLM response")
                    logger.info("SEQUENTIAL THINKING DEBUG: Using rule-based fallback - no JSON found")
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"SEQUENTIAL THINKING DEBUG: Failed to parse LLM workflow: {e}")
                logger.info("SEQUENTIAL THINKING DEBUG: Using rule-based fallback - JSON parse error")
            
            # NO FALLBACK - Pure LLM only
            logger.error("SEQUENTIAL THINKING: JSON parsing failed, no fallback available")
            return MCPToolResult(success=False, error="LLM workflow parsing failed")
            
        except Exception as e:
            logger.error(f"LLM workflow generation error: {e}")
            return MCPToolResult(success=False, error=f"LLM planning failed: {str(e)}")
    
    def _generate_params_for_step(self, step_data: Dict[str, Any], user_request: str) -> Dict[str, Any]:
        """Generate parameters for a workflow step based on tool and action"""
        tool_name = step_data.get("tool_name")
        action_name = step_data.get("action_name")
        
        if tool_name == "gmail_helper":
            if action_name == "get_positional_email":
                return {
                    "user_request": user_request
                }
            elif action_name == "get_email_details":
                return {
                    "message_id": "to_be_extracted"
                }
            elif action_name == "_send_email":
                return {
                    "recipient": "to_be_extracted",
                    "subject": "Email via MetisAgent2",
                    "body": user_request
                }
            elif action_name == "_send_email_with_attachment":
                return {
                    "recipient": "to_be_extracted",
                    "subject": "Email via MetisAgent2",
                    "body": user_request,
                    "attachment_path": "to_be_extracted"
                }
            elif action_name == "_list_emails":
                return {
                    "max_results": 10,
                    "query": ""
                }
            else:
                return {}
        elif tool_name == "simple_visual_creator":
            if action_name == "create_image":
                return {
                    "prompt": user_request,
                    "providers": ["openai"],
                    "size": "1024x1024"
                }
            elif action_name == "load_and_display_image":
                return {
                    "image_source": "from_previous_step"
                }
        elif tool_name == "gmail_helper":
            if action_name == "_send_email":
                return {
                    "recipient": "to_be_extracted",
                    "subject": "Email via MetisAgent2",
                    "body": user_request
                }
            elif action_name == "_send_email_with_attachment":
                return {
                    "recipient": "to_be_extracted",
                    "subject": "Email via MetisAgent2",
                    "body": user_request,
                    "attachment_path": "to_be_extracted"
                }
            elif action_name == "_list_emails":
                return {
                    "max_results": 10,
                    "query": ""
                }
            elif action_name == "_get_email_details":
                return {
                    "message_id": "to_be_extracted"
                }
            else:
                return {}
        elif tool_name == "command_executor":
            return {
                "command": user_request
            }
        elif tool_name == "llm_tool":
            return {
                "message": user_request,
                "provider": "openai"
            }
        elif tool_name == "social_media_workflow":
            return {
                "user_request": user_request
            }
        
        return {}
    
    def _create_workflow_from_llm_decision(self, user_request: str, tool_name: str, action_name: str) -> List[Dict[str, Any]]:
        """Create workflow based on LLM's tool selection"""
        try:
            if tool_name == "simple_visual_creator":
                steps = [{
                    "id": "step_1",
                    "title": "Generate Visual",
                    "description": f"Generate visual for: {user_request}",
                    "tool_name": "simple_visual_creator",
                    "action_name": "create_image",
                    "params": {
                        "prompt": user_request,
                        "providers": ["openai"],
                        "size": "1024x1024"
                    },
                    "dependencies": [],
                    "estimated_duration": 45,
                    "validation": "Image generated successfully"
                }]
                
                return steps
            
            elif tool_name == "gmail_helper":
                final_action = action_name or "_send_email"
                
                if final_action == "_send_email":
                    params = {
                        "recipient": "to_be_extracted",
                        "subject": "Email via MetisAgent2",
                        "body": user_request
                    }
                    title = "Send Email"
                    validation = "Email sent successfully"
                elif final_action == "_send_email_with_attachment":
                    params = {
                        "recipient": "to_be_extracted",
                        "subject": "Email via MetisAgent2",
                        "body": user_request,
                        "attachment_path": "to_be_extracted"
                    }
                    title = "Send Email with Attachment"
                    validation = "Email with attachment sent successfully"
                elif final_action == "_list_emails":
                    params = {
                        "max_results": 10,
                        "query": ""
                    }
                    title = "List Emails"
                    validation = "Emails listed successfully"
                elif final_action == "_get_email_details":
                    params = {
                        "message_id": "to_be_extracted"
                    }
                    title = "Get Email Details"
                    validation = "Email details retrieved successfully"
                else:
                    params = {}
                    title = "Gmail Operation"
                    validation = "Operation completed successfully"
                
                return [{
                    "id": "step_1", 
                    "title": title,
                    "description": f"Gmail operation: {user_request}",
                    "tool_name": "gmail_helper",
                    "action_name": final_action,
                    "params": params,
                    "dependencies": [],
                    "estimated_duration": 30,
                    "validation": validation
                }]
            
            elif tool_name == "command_executor":
                return [{
                    "id": "step_1",
                    "title": "Execute Command",
                    "description": f"Execute command: {user_request}",
                    "tool_name": "command_executor",
                    "action_name": "execute",
                    "params": {
                        "command": user_request
                    },
                    "dependencies": [],
                    "estimated_duration": 30,
                    "validation": "Command executed successfully"
                }]
            
            else:  # llm_tool or fallback
                return [{
                    "id": "step_1",
                    "title": "Process Request",
                    "description": f"Process request: {user_request}",
                    "tool_name": "llm_tool",
                    "action_name": "chat",
                    "params": {
                        "message": user_request,
                        "provider": "openai"
                    },
                    "dependencies": [],
                    "estimated_duration": 30,
                    "validation": "Request processed successfully"
                }]
                
        except Exception as e:
            logger.error(f"Error creating workflow from LLM decision: {e}")
            return []
    
# RULE-BASED SYSTEM REMOVED - Pure LLM planning only
    
    def _create_emergency_fallback_workflow(self, user_request: str) -> List[Dict[str, Any]]:
        """Create basic workflow when LLM fails - use LLM tool as last resort"""
        try:
            logger.info("EMERGENCY FALLBACK: Creating minimal workflow with LLM tool")
            return [{
                "id": "emergency_step_1",
                "title": "Process Request",
                "description": f"Process user request: {user_request}",
                "tool_name": "llm_tool",
                "action_name": "chat",
                "params": {
                    "message": user_request,
                    "provider": "openai"
                },
                "dependencies": [],
                "estimated_duration": 30,
                "validation": "Request processed"
            }]
                
        except Exception as e:
            logger.error(f"EMERGENCY FALLBACK: Even emergency fallback failed: {e}")
            return []
    
    def _break_down_task(self, task_description: str, context: str = None, 
                        complexity_level: str = "medium", user_id: str = None) -> MCPToolResult:
        """Break down a complex task into smaller steps"""
        try:
            # Simple task breakdown logic
            steps = [
                f"Analyze: {task_description}",
                f"Plan execution strategy", 
                f"Execute task components",
                f"Validate results"
            ]
            
            return MCPToolResult(
                success=True,
                data={
                    "task": task_description,
                    "breakdown": steps,
                    "complexity": complexity_level,
                    "context": context
                },
                metadata={"method": "break_down_task", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Task breakdown failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "break_down_task", "user_id": user_id}
            )
    
    def _evaluate_complexity(self, problem_description: str, user_id: str = None) -> MCPToolResult:
        """Evaluate the complexity of a problem"""
        try:
            # Simple complexity evaluation
            word_count = len(problem_description.split())
            
            if word_count < 10:
                complexity = "low"
            elif word_count < 30:
                complexity = "medium"
            else:
                complexity = "high"
            
            return MCPToolResult(
                success=True,
                data={
                    "problem": problem_description,
                    "complexity": complexity,
                    "word_count": word_count,
                    "estimated_steps": min(max(word_count // 5, 1), 10)
                },
                metadata={"method": "evaluate_complexity", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Complexity evaluation failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "evaluate_complexity", "user_id": user_id}
            )
    
    def _match_tools_intelligently(self, user_request: str, available_tools: List[str] = None,
                                  user_id: str = None) -> MCPToolResult:
        """Match tools to user request intelligently"""
        try:
            # Simple keyword-based matching
            request_lower = user_request.lower()
            matched_tools = []
            
            tool_keywords = {
                "gmail_helper": ["email", "mail", "gmail", "send", "message"],
                "google_oauth2_manager": ["google", "oauth", "auth"],
                "google_drive": ["drive", "upload", "download", "file", "folder", "share", "dosya", "klasör"],
                "google_calendar": ["calendar", "event", "appointment", "schedule", "takvim", "etkinlik", "randevu"],
                "command_executor": ["command", "execute", "run", "terminal", "bash", "zip", "extract", "compress", "sıkıştır"],
                "simple_visual_creator": ["image", "picture", "visual", "create", "generate", "görsel", "resim"],
                "selenium_browser": ["browser", "web", "navigate", "click", "scrape", "tarayıcı"],
                "instagram_tool": ["instagram", "insta", "post", "story", "upload", "paylaş"],
                "social_media_workflow": ["social", "campaign", "medya", "sosyal", "kampanya", "post", "paylaş"]
            }
            
            for tool, keywords in tool_keywords.items():
                if any(keyword in request_lower for keyword in keywords):
                    matched_tools.append(tool)
            
            return MCPToolResult(
                success=True,
                data={
                    "request": user_request,
                    "matched_tools": matched_tools,
                    "confidence": len(matched_tools) / len(tool_keywords) if tool_keywords else 0
                },
                metadata={"method": "match_tools_intelligently", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Tool matching failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "match_tools_intelligently", "user_id": user_id}
            )
    
    def _optimize_sequence(self, current_plan: Dict[str, Any], optimization_criteria: str = None,
                          user_id: str = None) -> MCPToolResult:
        """Optimize the sequence of steps in a plan"""
        try:
            # Simple optimization - return plan as-is for now
            optimized_plan = current_plan.copy()
            optimized_plan["optimized"] = True
            optimized_plan["optimization_criteria"] = optimization_criteria or "default"
            
            return MCPToolResult(
                success=True,
                data=optimized_plan,
                metadata={"method": "optimize_sequence", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Sequence optimization failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "optimize_sequence", "user_id": user_id}
            )
    
    def _analyze_dependencies(self, steps: List[Dict[str, Any]], user_id: str = None) -> MCPToolResult:
        """Analyze dependencies between workflow steps"""
        try:
            dependencies = {}
            
            for i, step in enumerate(steps):
                step_id = step.get("id", f"step_{i}")
                step_deps = step.get("dependencies", [])
                dependencies[step_id] = step_deps
            
            return MCPToolResult(
                success=True,
                data={
                    "steps_count": len(steps),
                    "dependencies": dependencies,
                    "has_dependencies": any(deps for deps in dependencies.values())
                },
                metadata={"method": "analyze_dependencies", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Dependency analysis failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "analyze_dependencies", "user_id": user_id}
            )
    
    def _discover_tool_capabilities(self, user_id: str = None) -> MCPToolResult:
        """Discover available tool capabilities"""
        try:
            # Get registry and discover tools
            registry = self._get_registry()
            if registry is None:
                return MCPToolResult(success=False, error="Registry not available")
            
            tools_info = {}
            for tool_name in registry.tools.keys():
                tool = registry.get_tool(tool_name)
                if tool:
                    tools_info[tool_name] = {
                        "name": tool_name,
                        "description": getattr(tool, 'description', 'No description'),
                        "actions": list(tool.actions.keys()) if hasattr(tool, 'actions') else []
                    }
            
            return MCPToolResult(
                success=True,
                data={
                    "discovered_tools": tools_info,
                    "tool_count": len(tools_info),
                    "capabilities": list(tools_info.keys())
                },
                metadata={"method": "discover_tool_capabilities", "user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"method": "discover_tool_capabilities", "user_id": user_id}
            )
    
    def _plan_context_aware_workflow(self, user_request: str, user_id: str = "system", 
                                   context_hints: List[str] = None) -> MCPToolResult:
        """Plan workflow with context awareness - uses LLM and Graph Memory for intelligent decisions"""
        try:
            registry = self._get_registry()
            if registry is None:
                return MCPToolResult(success=False, error="Registry not available")
            
            # Get graph memory and LLM tools
            graph_memory = registry.get_tool("graph_memory")
            llm_tool = registry.get_tool("llm_tool")
            
            if not graph_memory or not llm_tool:
                return MCPToolResult(success=False, error="Required tools (graph_memory, llm_tool) not available")
            
            # Step 1: Analyze user request for context clues using LLM
            context_analysis_prompt = f"""
            Analyze this user request for context references:
            "{user_request}"
            
            Identify:
            1. Temporal references (son, latest, önceki, previous, ilk, first)
            2. Object types (imaj, dosya, email, komut, file, image, command)
            3. Actions needed (düzenle, göster, aç, edit, show, open)
            
            Return JSON format:
            {{
                "has_context_reference": true/false,
                "temporal_indicator": "latest/previous/first/none",
                "object_type": "image/file/email/command/unknown",
                "action_needed": "edit/show/open/create/unknown",
                "context_query": "search query for graph memory"
            }}
            """
            
            llm_result = llm_tool._chat(
                message=context_analysis_prompt,
                provider="openai",
                user_id=user_id,
                conversation_name="context_analysis"
            )
            
            if not llm_result.success:
                return MCPToolResult(success=False, error="Context analysis failed")
            
            # Parse LLM response
            try:
                logger.info(f"Context analysis raw data: {llm_result.data}")
                llm_content = llm_result.data.get("content") or llm_result.data.get("response") or "{}"
                logger.info(f"Context analysis LLM raw response: {llm_content}")
                context_info = json.loads(llm_content)
                logger.info(f"Context analysis parsed: {context_info}")
            except Exception as e:
                logger.error(f"Context analysis JSON parse failed: {e}, raw_data: {llm_result.data}")
                context_info = {"has_context_reference": False}
            
            # Step 2: If context reference found, query graph memory
            context_data = None
            if context_info.get("has_context_reference"):
                context_query = context_info.get("context_query", user_request)
                memory_result = graph_memory._get_context_operation(context_query, user_id)
                
                if memory_result.success:
                    context_data = memory_result.data
                    logger.info(f"Context found: {context_data}")
            
            # Step 3: Get dynamic tool info
            tools_result = graph_memory._get_user_tools(user_id)
            available_tools_info = {}
            
            if tools_result.success:
                user_tools = tools_result.data.get("tools", {})
                if isinstance(user_tools, dict):
                    available_tools_info = user_tools
                    logger.info(f"Context-aware planning: Using {len(available_tools_info)} user tools from graph memory")
                else:
                    logger.warning(f"User tools is not dict: {type(user_tools)}, falling back to registry")
                    tools_result = None  # Force fallback
            if not tools_result or not tools_result.success or not available_tools_info:
                # Fallback: Get from registry
                try:
                    all_tools = registry.list_tools()
                    for tool_info in all_tools:
                        if isinstance(tool_info, dict) and 'name' in tool_info:
                            tool_name = tool_info['name']
                            
                            # Fix: Actions is a dict in get_info(), not a list
                            actions_dict = tool_info.get('actions', {})
                            if isinstance(actions_dict, dict):
                                actions = list(actions_dict.keys())  # Get action names
                            else:
                                actions = []  # Fallback
                                
                            available_tools_info[tool_name] = {
                                "description": tool_info.get('description', ''),
                                "actions": actions
                            }
                except Exception as e:
                    logger.error(f"Registry fallback failed: {e}")
                    
                logger.info(f"Context-aware planning: Using registry fallback with {len(available_tools_info)} tools")
            
            # Format tools for prompt
            tool_lines = [f"- {tool}: {info.get('description', '')} (Actions: {', '.join(info.get('actions', []))})" 
                         for tool, info in available_tools_info.items()]
            dynamic_tools_prompt = f"Available Tools:\n{chr(10).join(tool_lines)}" if tool_lines else "Available Tools: No tools available"
            
            # Step 4: Create workflow based on context + user request
            workflow_planning_prompt = f"""
            Plan a workflow for this request: "{user_request}"
            
            Context Analysis: {json.dumps(context_info, indent=2)}
            Found Context Data: {json.dumps(context_data, indent=2) if context_data else "None"}
            
            {dynamic_tools_prompt}
            
            Create a step-by-step workflow. Consider:
            - If context data exists, use it (file paths, previous operations)
            - Select appropriate tools for each step
            - Handle dependencies between steps
            
            Return JSON workflow format:
            {{
                "workflow_steps": [
                    {{
                        "step_id": "step_1",
                        "title": "Step Title",
                        "tool_name": "tool_name",
                        "action_name": "action_name",
                        "parameters": {{}},
                        "uses_context": true/false,
                        "context_reference": "what context is used"
                    }}
                ],
                "estimated_duration": 60,
                "complexity": "simple/medium/complex"
            }}
            """
            
            workflow_result = llm_tool._chat(
                message=workflow_planning_prompt,
                provider="openai",
                user_id=user_id,
                conversation_name="workflow_planning"
            )
            
            if not workflow_result.success:
                return MCPToolResult(success=False, error="Workflow planning failed")
            
            # Parse workflow
            try:
                workflow_data = json.loads(workflow_result.data.get("content", "{}"))
                workflow_steps = workflow_data.get("workflow_steps", [])
            except:
                workflow_steps = []
            
            return MCPToolResult(
                success=True,
                data={
                    "context_analysis": context_info,
                    "context_data": context_data,
                    "workflow_steps": workflow_steps,
                    "method": "context_aware_planning"
                },
                metadata={"user_id": user_id, "context_aware": True}
            )
            
        except Exception as e:
            logger.error(f"Context-aware workflow planning failed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _detect_tool_conflicts(self, user_request: str, available_tools: Dict) -> Dict:
        """Detect potential tool conflicts and suggest clarification"""
        try:
            # Define known conflict patterns
            conflict_patterns = {
                "instagram": {
                    "tools": ["instagram_tool", "social_media_workflow"],
                    "clarification": {
                        "instagram_tool": "Direct Instagram automation (posting, commenting, real account interaction)",
                        "social_media_workflow": "Content planning, campaign management, multi-platform strategy"
                    }
                },
                "email": {
                    "tools": ["gmail_helper", "email_automation_tool"],
                    "clarification": {
                        "gmail_helper": "Gmail-specific operations (send, read, manage Gmail)",
                        "email_automation_tool": "Multi-provider email automation and campaigns"
                    }
                },
                "image": {
                    "tools": ["simple_visual_creator", "image_processor"],
                    "clarification": {
                        "simple_visual_creator": "AI image generation (DALL-E, Gemini, HuggingFace)",
                        "image_processor": "Image editing, manipulation, and transformation"
                    }
                }
            }
            
            # Check user request for conflict keywords
            request_lower = user_request.lower()
            potential_conflicts = []
            
            logger.info(f"CONFLICT DEBUG: Checking request '{request_lower}' against {len(conflict_patterns)} patterns")
            logger.info(f"CONFLICT DEBUG: Available tools: {list(available_tools.keys())}")
            
            for keyword, conflict_info in conflict_patterns.items():
                logger.info(f"CONFLICT DEBUG: Checking keyword '{keyword}' in request")
                if keyword in request_lower:
                    # Check if multiple conflicting tools are available
                    available_conflicting_tools = [
                        tool for tool in conflict_info["tools"] 
                        if tool in available_tools
                    ]
                    
                    if len(available_conflicting_tools) > 1:
                        potential_conflicts.append({
                            "keyword": keyword,
                            "conflicting_tools": available_conflicting_tools,
                            "explanations": {
                                tool: conflict_info["clarification"][tool] 
                                for tool in available_conflicting_tools 
                                if tool in conflict_info["clarification"]
                            }
                        })
            
            return {
                "has_conflicts": len(potential_conflicts) > 0,
                "conflicts": potential_conflicts
            }
            
        except Exception as e:
            logger.error(f"Tool conflict detection failed: {e}")
            return {"has_conflicts": False, "conflicts": []}
    
    def _create_clarification_response(self, conflicts: List[Dict], user_request: str) -> str:
        """Create user-friendly clarification message for tool conflicts"""
        try:
            clarification_parts = [
                f"📋 **İsteğiniz**: {user_request}",
                "",
                "🤔 **Hangi yaklaşımı tercih edersiniz?**",
                ""
            ]
            
            for conflict in conflicts:
                clarification_parts.append(f"**{conflict['keyword'].title()} için seçenekler:**")
                
                for tool, description in conflict['clarifications'].items():
                    # Create user-friendly tool names
                    display_name = tool.replace("_", " ").replace("tool", "").strip().title()
                    clarification_parts.append(f"• **{display_name}**: {description}")
                
                clarification_parts.append("")
            
            clarification_parts.extend([
                "💡 **Nasıl yanıtlayabilirsiniz:**",
                "• 'Instagram tool kullan' → Doğrudan hesap işlemleri",
                "• 'Sosyal medya tool kullan' → İçerik planlama",
                "• 'Gmail helper kullan' → Gmail işlemleri",
                "",
                "Ya da tercihinizi açıkça belirtin."
            ])
            
            return "\n".join(clarification_parts)
            
        except Exception as e:
            logger.error(f"Clarification response creation failed: {e}")
            return f"Lütfen hangi aracı kullanmak istediğinizi belirtin: {', '.join([tool for conflict in conflicts for tool in conflict['tools']])}"

def register_tool(registry):
    """Register Sequential Thinking tool with the registry"""
    try:
        tool = SequentialThinkingTool()
        registry.register_tool(tool)
        logger.info("Sequential Thinking tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register Sequential Thinking tool: {e}")
        return False