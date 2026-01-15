"""
Tool Coordinator - Handles intelligent tool routing based on LLM responses
"""

import json
import logging
import re
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from .mcp_core import registry, MCPToolResult
from .workflow_orchestrator import orchestrator, WorkflowStatus
from config.llm_tool_router import LLMToolRouter

logger = logging.getLogger(__name__)

# Gmail aggregator utilities
FROM_RE = re.compile(r'(?:"?([^"]*)"?\s)?<?([^<>@\s]+@[^<>@\s]+)>?')

def _extract_from(headers: list) -> str:
    """
    headers: [{'name':'From','value':'Alice <alice@example.com>'}, ...]
    returns: 'Alice <alice@example.com>' or just email
    """
    for h in headers or []:
        if h.get("name", "").lower() == "from":
            v = h.get("value", "")
            m = FROM_RE.search(v)
            if m:
                name, email = (m.group(1) or "").strip(), m.group(2).strip()
                return f"{name} <{email}>" if name else email
            return v
    return ""

def run_internal_action(action_name: str, params: dict, context: dict) -> dict:
    if action_name == "aggregate_gmail_senders":
        # context, step_2 çıktısını içermeli
        step_id = params.get("source_step", "step_2")
        step_out = context.get(step_id, {})
        msgs = step_out.get("data", {}).get("messages", [])
        result = []
        for m in msgs:
            headers = m.get("payload", {}).get("headers", [])
            sender = _extract_from(headers)
            subject = next((h.get("value") for h in headers if h.get("name","").lower()=="subject"), "")
            date = next((h.get("value") for h in headers if h.get("name","").lower()=="date"), "")
            result.append({
                "id": m.get("id"),
                "sender": sender,
                "subject": subject,
                "date": date
            })
        return {"success": True, "data": {"senders": result}}
    raise ValueError(f"Unknown internal action: {action_name}")

class ToolCoordinator:
    """Coordinates tool execution based on LLM responses"""
    
    def __init__(self):
        # Workflow evaluation cache to avoid repeated LLM calls
        self.workflow_eval_cache = {}
        self.cache_max_size = 100
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize configurable tool router
        # Initialize LLM-based tool router (CLAUDE.md compliant)
        self.llm_tool_router = None  # Will be initialized after LLM tool is ready
        self.tool_capability_manager = None  # Will be injected
        logger.info("Tool Coordinator initialized with LLM-based routing (CLAUDE.md compliant)")
        
        # Tool relevance cache
        self.tool_relevance_cache = {}
    
    def initialize_llm_router(self, llm_tool, tool_capability_manager):
        """Initialize LLM-based tool router after dependencies are ready"""
        try:
            self.tool_capability_manager = tool_capability_manager
            self.llm_tool_router = LLMToolRouter(
                llm_tool=llm_tool,
                tool_capability_manager=tool_capability_manager
            )
            logger.info("✅ LLM-based tool router initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM tool router: {e}")
        
        # Initialize graph memory for operation logging
        self.graph_memory = None
        self._initialize_memory_logging()
    
    def process_llm_response(self, response_text: str, conversation_id: str = "default", user_id: str = None) -> Dict[str, Any]:
        """Process LLM response for tool calls (workflow check happens at user input level)"""
        try:
            # Check if response contains JSON with tool calls
            tool_response = self._extract_tool_calls(response_text)
            
            if tool_response and 'tool_calls' in tool_response:
                # Execute tool calls
                tool_results = []
                for tool_call in tool_response['tool_calls']:
                    result = self._execute_tool_call(tool_call, user_id=user_id)
                    tool_results.append(result)
                
                # Add tool results to conversation for next interaction
                self._add_tool_results_to_conversation(conversation_id, tool_results)
                
                # Let LLM analyze the results itself by calling it again
                analysis_response = self._get_llm_analysis(tool_response['tool_calls'], tool_results, conversation_id)
                
                # Return processed response
                return {
                    'response': analysis_response,
                    'tool_calls': tool_response['tool_calls'],
                    'tool_results': tool_results,
                    'has_tool_calls': True
                }
            else:
                # Check if response indicates need for tools based on patterns
                suggested_tools = self._analyze_for_tool_suggestions(response_text)
                
                return {
                    'response': response_text,
                    'tool_calls': [],
                    'tool_results': [],
                    'has_tool_calls': False,
                    'suggested_tools': suggested_tools
                }
                
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return {
                'response': response_text,
                'tool_calls': [],
                'tool_results': [],
                'has_tool_calls': False,
                'error': str(e)
            }
    
    def _add_tool_results_to_conversation(self, conversation_id: str, tool_results: List[Dict]):
        """Add tool execution results to conversation for LLM context"""
        try:
            from .mcp_core import registry
            llm_tool = registry.get_tool('llm_tool')
            
            if llm_tool and hasattr(llm_tool, 'conversations'):
                if conversation_id in llm_tool.conversations:
                    # Create a summary of tool results (exclude large data like base64)
                    results_summary = "Tool execution results:\n"
                    for i, result in enumerate(tool_results):
                        if result['success']:
                            if result['data'] and result['data'].get('stdout'):
                                results_summary += f"Command {i+1} output:\n{result['data']['stdout']}\n"
                            if result['data'] and result['data'].get('stderr'):
                                results_summary += f"Command {i+1} error:\n{result['data']['stderr']}\n"
                            # Handle image generation results without including base64
                            if result['data'] and result['data'].get('base64_image'):
                                filename = result['data'].get('local_filename', 'image.png')
                                prompt = result['data'].get('prompt', 'No prompt')
                                results_summary += f"Command {i+1}: Image generated successfully - {filename}\n"
                                results_summary += f"Prompt: {prompt[:100]}...\n"
                        else:
                            results_summary += f"Command {i+1} failed: {result['error']}\n"
                    
                    # Add as system message
                    llm_tool.conversations[conversation_id].append({
                        "role": "system",
                        "content": results_summary,
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "tool_results"
                    })
                    
        except Exception as e:
            logger.error(f"Error adding tool results to conversation: {str(e)}")
    
    def _get_llm_analysis(self, tool_calls: List[Dict], tool_results: List[Dict], conversation_id: str) -> str:
        """Get LLM's analysis of the tool execution results"""
        try:
            from .mcp_core import registry
            
            # Check if we have successful results to analyze
            has_successful_results = any(result.get('success', False) for result in tool_results)
            if not has_successful_results:
                return 'Tool execution failed.'
            
            # Skip LLM analysis for image generation tools to avoid context issues
            for result in tool_results:
                if result.get('tool_call', {}).get('tool') in ['simple_visual_creator', 'visual_creator']:
                    if result.get('success'):
                        # Check for single image or multi-provider images
                        data = result.get('data', {})
                        if data.get('base64_image'):
                            return 'Image generated successfully and is ready for display.'
                        elif data.get('generation_type') == 'multi_provider_parallel':
                            success_count = data.get('success_count', 0)
                            total_attempts = data.get('total_attempts', 0)
                            return f'Multi-provider image generation completed! Generated {success_count} images from {total_attempts} providers. Choose your favorite from the options displayed.'
            
            # Create analysis prompt with explicit tool results (exclude large data)
            results_summary = "Tool execution results:\n"
            for i, result in enumerate(tool_results):
                if result['success']:
                    tool_name = result.get('tool_call', {}).get('tool', 'unknown')
                    action_name = result.get('tool_call', {}).get('action', 'unknown')
                    results_summary += f"\n{i+1}. Tool: {tool_name}, Action: {action_name}\n"
                    if result.get('data'):
                        # Exclude base64 image data from analysis prompt
                        data_copy = result['data'].copy()
                        if 'base64_image' in data_copy:
                            data_copy['base64_image'] = '[BASE64 IMAGE DATA EXCLUDED]'
                        results_summary += f"   Result: {json.dumps(data_copy, indent=2)}\n"
                else:
                    results_summary += f"\n{i+1}. Tool execution failed: {result.get('error', 'Unknown error')}\n"
            
            analysis_prompt = f"Please analyze these tool execution results and provide a clear, helpful summary:\n\n{results_summary}\n\nRespond ONLY with a natural, conversational summary. Do NOT use JSON format. Just provide a direct, helpful explanation of what was found:"
            
            # Execute LLM to get analysis
            result = registry.execute_tool_action(
                'llm_tool', 
                'chat',
                message=analysis_prompt,
                conversation_id=conversation_id,
                enable_tools=False  # Don't allow tools in analysis to prevent loops
            )
            
            if result.success:
                return result.data.get('response', 'Analysis completed.')
            else:
                return 'Tool executed successfully.'
                
        except Exception as e:
            logger.error(f"Error getting LLM analysis: {str(e)}")
            return 'Tool executed successfully.'
    
    def _extract_tool_calls(self, response_text: str) -> Optional[Dict]:
        """Extract tool calls from LLM response if present"""
        try:
            # Check if entire response is JSON first
            response_clean = response_text.strip()
            if response_clean.startswith('{') and response_clean.endswith('}'):
                try:
                    parsed = json.loads(response_clean)
                    if 'tool_calls' in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            # Look for JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    parsed = json.loads(json_str)
                    if 'tool_calls' in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            # Look for JSON objects with balanced braces
            def find_json_objects(text):
                results = []
                start_idx = 0
                while True:
                    start = text.find('{', start_idx)
                    if start == -1:
                        break
                    
                    # Find matching closing brace
                    brace_count = 0
                    end = start
                    for i in range(start, len(text)):
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i
                                break
                    
                    if brace_count == 0:
                        try:
                            json_str = text[start:end+1]
                            parsed = json.loads(json_str)
                            if 'tool_calls' in parsed:
                                results.append(parsed)
                        except json.JSONDecodeError:
                            pass
                    
                    start_idx = start + 1
                
                return results
            
            json_objects = find_json_objects(response_text)
            if json_objects:
                return json_objects[0]  # Return first valid JSON with tool_calls
            
            # Handle direct tool queries (fallback)
            response_lower = response_text.lower()
            if any(phrase in response_lower for phrase in ['hangi tool', 'hangi araç', 'available tools', 'list tools']):
                # Create a synthetic tool call to list tools
                return {
                    "response": "I'll list the available tools for you",
                    "tool_calls": [
                        {
                            "tool": "registry",
                            "action": "list_tools",
                            "params": {}
                        }
                    ]
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting tool calls: {str(e)}")
            return None
    
    def _execute_tool_call(self, tool_call: Dict, user_id: str = None) -> Dict[str, Any]:
        """Execute a single tool call"""
        try:
            tool_name = tool_call.get('tool')
            action_name = tool_call.get('action')
            params = tool_call.get('params', {})
            
            # Debug log
            logger.info(f"Debug tool call - tool: {tool_name}, action: {action_name}, params: {params}")
            
            if not tool_name or not action_name:
                return {
                    'success': False,
                    'error': 'Missing tool or action name',
                    'tool_call': tool_call
                }
            
            # Handle special registry actions
            if tool_name == 'registry' and action_name == 'list_tools':
                tools_list = registry.list_tools()
                tool_names = [tool['name'] for tool in tools_list]
                return {
                    'success': True,
                    'data': {
                        'tools': tools_list,
                        'count': len(tools_list),
                        'message': f"Available tools: {', '.join(tool_names)}"
                    },
                    'tool_call': tool_call
                }
            
            # Clean up parameters (keep empty strings for OAuth2 user_id injection)
            cleaned_params = {}
            for key, value in params.items():
                if value is not None:
                    cleaned_params[key] = value
            
            # Handle user_id mapping for OAuth2 tools
            if tool_name in ['google_oauth2_manager', 'gmail_helper', 'google_drive', 'google_calendar']:
                logger.info(f"OAuth2/Google tool detected ({tool_name}). User_id: {user_id}")
                
                # Anonymous users cannot use OAuth2 - return clear error
                if user_id and user_id.startswith('anonymous_'):
                    logger.warning(f"Anonymous user {user_id} attempting OAuth2 operation")
                    return {
                        'success': False,
                        'error': 'Google services require user authentication. Please login with a registered account first.',
                        'tool_call': tool_call,
                        'requires_auth': True
                    }
                
                if user_id:
                    # For OAuth2 tools, always use the system user_id
                    # The OAuth2 manager will handle Gmail mapping internally using settings_manager
                    cleaned_params['user_id'] = user_id
                    logger.info(f"OAuth2 tool using system user_id: {user_id}")
                    
                    # Log the Gmail mapping for debugging
                    try:
                        # Use legacy method directly since registry might not be ready
                        from tools.internal.settings_manager import get_settings_manager
                        settings_manager = get_settings_manager()
                        gmail_mapping = settings_manager.get_user_mapping(user_id, 'google')
                        logger.info(f"Gmail mapping for {user_id}: {gmail_mapping}")
                    except Exception as e:
                        logger.error(f"Error checking Gmail mapping: {e}")
                else:
                    logger.warning(f"No authenticated user_id provided for OAuth2 tool call")
            
            # Set defaults for command executor
            if tool_name == 'command_executor' and action_name == 'execute':
                if 'timeout' not in cleaned_params:
                    cleaned_params['timeout'] = 30
                if 'allow_dangerous' not in cleaned_params:
                    cleaned_params['allow_dangerous'] = False
                # Remove empty working_directory
                if 'working_directory' in cleaned_params and not cleaned_params['working_directory']:
                    del cleaned_params['working_directory']
            
            logger.info(f"Executing tool call: {tool_name}.{action_name} with params: {cleaned_params}")
            
            # Execute tool action
            result = registry.execute_tool_action(tool_name, action_name, **cleaned_params)
            
            # Universal operation logging to graph memory
            self._log_operation_to_memory(tool_name, action_name, result, user_id, cleaned_params)
            
            return {
                'success': result.success,
                'data': result.data,
                'error': result.error,
                'tool_call': tool_call,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Error executing tool call: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tool_call': tool_call
            }
    
    def _analyze_for_tool_suggestions(self, response_text: str) -> List[str]:
        """Analyze response text for potential tool suggestions using LLM intelligence"""
        try:
            # Get available tools
            available_tools = registry.list_tools()
            tools_info = {}
            
            for tool in available_tools:
                tools_info[tool['name']] = {
                    'description': tool['description'],
                    'actions': list(tool['actions'].keys())
                }
            
            analysis_prompt = f"""
You are a tool suggestion system. Analyze the response text and suggest relevant tools if needed.

AVAILABLE TOOLS:
{json.dumps(tools_info, indent=2)}

RESPONSE TEXT TO ANALYZE:
{response_text}

ANALYSIS CRITERIA:
1. Does the response mention specific actions that tools can perform?
2. Are there user requests that require tool execution?
3. Does the response indicate missing functionality that tools provide?
4. Would tools enhance the response with actual data or actions?

SUGGESTION RULES:
- Only suggest tools that would directly help with the response content
- Do not suggest tools for general conversation
- Focus on tools that can provide concrete actions or data
- Consider multi-language requests (Turkish/English)

RESPONSE FORMAT (JSON):
{{
  "suggested_tools": ["tool_name1", "tool_name2"],
  "reasoning": "Why these tools are suggested",
  "confidence": 0.8
}}

Analyze and suggest tools:
"""
            
            # Get LLM analysis
            analysis_result = registry.execute_tool_action(
                'llm_tool',
                'chat', 
                message=analysis_prompt,
                conversation_id=f"tool_analysis_{hash(response_text)}",
                enable_tools=False
            )
            
            if analysis_result.success:
                analysis_response = analysis_result.data.get('response', '{}')
                
                # Parse JSON response
                try:
                    start_idx = analysis_response.find('{')
                    end_idx = analysis_response.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = analysis_response[start_idx:end_idx]
                        parsed = json.loads(json_str)
                        
                        suggested_tools = parsed.get('suggested_tools', [])
                        confidence = parsed.get('confidence', 0.0)
                        
                        # Only return suggestions with high confidence
                        if confidence > 0.6:
                            return suggested_tools
                        
                except Exception as e:
                    logger.error(f"Error parsing tool suggestion response: {e}")
            
            # Fallback to empty list if LLM analysis fails
            return []
            
        except Exception as e:
            logger.error(f"Error in LLM tool suggestion analysis: {e}")
            # Fallback to regex patterns as backup
            return self._fallback_regex_analysis(response_text)
    
    def _fallback_regex_analysis(self, response_text: str) -> List[str]:
        """Fallback regex analysis using configurable tool router"""
        try:
            # Use the configurable tool router for suggestions
            # Use LLM-based routing instead of regex patterns (CLAUDE.md compliant)
            if self.llm_tool_router:
                tool_match = self.llm_tool_router.route_request(response_text, user_id="system")
                if tool_match.confidence > 0.3:
                    suggestions = [tool_match.tool_name]
                    alternatives = tool_match.context_analysis.get("alternative_tools", [])
                    suggestions.extend(alternatives[:2])
                    logger.info(f"LLM tool router suggestions: {suggestions} (confidence: {tool_match.confidence:.2f})")
                    return suggestions
            
            # Fallback to simple keyword analysis if LLM router not available
            logger.warning("LLM router not available, using keyword fallback")
            return self._fallback_tool_analysis(response_text)
            
            # Final fallback for command execution only
            response_lower = response_text.lower()
            command_patterns = ['execute', 'run', 'command', 'terminal', 'bash', 'shell']
            if any(pattern in response_lower for pattern in command_patterns):
                return ['command_executor']
            
            return []
            
        except Exception as e:
            logger.error(f"Error in configurable tool router fallback: {e}")
            return []
    
    def _suggest_tool_by_capabilities(self, user_message: str, available_tools: List[Dict]) -> Optional[Dict]:
        """Suggest a tool based on user message using configurable tool router"""
        try:
            # Use configurable tool router for intelligent tool selection
            best_tool, confidence, matched_patterns = self.tool_router.find_best_tool(user_message)
            
            if confidence > 0.3:
                # Find the tool details from available_tools
                for tool in available_tools:
                    if tool['name'] == best_tool:
                        logger.info(f"Tool router found best match: {best_tool} (confidence: {confidence:.2f}, patterns: {matched_patterns})")
                        return tool
            
            # Fallback to original capability-based matching if needed
            message_lower = user_message.lower()
            
            # Define minimal keyword-to-capability mappings as fallback
            capability_keywords = {
                'web_scraping': ['website', 'url', 'web', 'scrape', 'site', 'sayfa'],
                'tool_installation': ['install', 'add', 'yükle', 'ekle', 'tool'],
                'image_generation': ['image', 'görsel', 'picture', 'create', 'generate', 'oluştur', 'resim']
            }
            
            # Score each tool based on capabilities match
            tool_scores = {}
            for tool in available_tools:
                score = 0
                for capability in tool.get('capabilities', []):
                    if capability in capability_keywords:
                        keywords = capability_keywords[capability]
                        for keyword in keywords:
                            if keyword in message_lower:
                                score += 1
                
                if score > 0:
                    tool_scores[tool['name']] = {'score': score, 'tool': tool}
            
            # Return the highest scoring tool
            if tool_scores:
                best_tool = max(tool_scores.values(), key=lambda x: x['score'])
                return best_tool['tool']
            
            return None
            
        except Exception as e:
            logger.error(f"Error in configurable tool capability detection: {e}")
            return None
    
    def create_enhanced_prompt(self, user_message: str, conversation_context: List[Dict] = None) -> str:
        """Create an enhanced prompt that encourages tool usage when appropriate"""
        
        # Get all available tools including dynamic ones
        available_tools = registry.list_tools()
        tool_names = [tool['name'] for tool in available_tools]
        
        # Analyze user message for tool needs using configurable router
        try:
            best_tool, confidence, _ = self.tool_router.find_best_tool(user_message)
            needs_commands = (best_tool == 'command_executor' and confidence > 0.3)
        except Exception as e:
            logger.error(f"Error detecting command needs: {e}")
            needs_commands = False
        
        # Check for web automation needs using configurable router
        try:
            best_tool, confidence, _ = self.tool_router.find_best_tool(user_message)
            needs_web_automation = (best_tool == 'selenium_browser' and confidence > 0.3)
        except Exception as e:
            logger.error(f"Error detecting web automation needs: {e}")
            needs_web_automation = False
        
        # Check for image display needs
        needs_image_display = any(pattern in user_message.lower() for pattern in [
            'göster', 'show', 'display', 'görüntüle', 'ekranda'
        ]) and any(img_pattern in user_message.lower() for img_pattern in [
            'screenshot', 'resim', 'image', 'görüntü'
        ])
        
        # Check for complex multi-step operations that need task breakdown
        needs_task_breakdown = (
            (' ve ' in user_message.lower() and any(action in user_message.lower() for action in ['al', 'git', 'yap', 'oku', 'göster'])) or
            (' and ' in user_message.lower() and any(action in user_message.lower() for action in ['take', 'show', 'display'])) or
            any(multi_word in user_message.lower() for multi_word in ['then', 'sonra', 'ardından', 'multi-step', 'çok adım', 'sequence', 'sırayla'])
        )
        
        # Check for Gemini web vs API distinction
        gemini_web_indicators = ['gemini web', 'gemini site', 'gemini sitesi', 'gemini aç', 'gemini git']
        gemini_api_indicators = ['gemini api', 'gemini auth', 'gemini oauth', 'gemini login']
        
        is_gemini_web = any(indicator in user_message.lower() for indicator in gemini_web_indicators)
        is_gemini_api = any(indicator in user_message.lower() for indicator in gemini_api_indicators)
        
        # Check for OAuth2/Google API needs using configurable router
        try:
            best_tool, confidence, _ = self.tool_router.find_best_tool(user_message)
            needs_oauth2 = (best_tool in ['google_oauth2_manager', 'gmail_helper'] and confidence > 0.3)
        except Exception as e:
            logger.error(f"Error detecting OAuth2 needs: {e}")
            needs_oauth2 = False
        
        # Check for specific tool mentions
        mentioned_tools = [tool for tool in tool_names if tool.lower() in user_message.lower()]
        
        # Dynamic capability-based detection
        suggested_tool = self._suggest_tool_by_capabilities(user_message, available_tools)
        
        # Handle complex multi-step operations with task breakdown
        if needs_task_breakdown:
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: This is a complex multi-step operation. You MUST create a structured task breakdown using LLM reasoning and then execute tools sequentially.

APPROACH:
1. First, analyze the request and break it down into atomic tasks
2. Create a mental todo list of required actions
3. Execute tools in proper sequence
4. Each tool call should be a single, focused action

For example, "browser başlat, git, screenshot al, göster" should be broken down as:
1. Start browser (selenium_browser.start_browser)
2. Navigate to URL (selenium_browser.navigate)  
3. Get page title (selenium_browser.get_title)
4. Take screenshot (selenium_browser.screenshot)
5. Close browser (selenium_browser.close_browser)
6. Display screenshot (simple_visual_creator.load_and_display_image)

CRITICAL RULES:
- One action per tool call
- Follow logical sequence (start → navigate → action → close → display)
- Use proper parameters for each action
- Handle errors gracefully
- Always close browser sessions

AVAILABLE TOOL ACTIONS:
- selenium_browser: start_browser, navigate, get_title, screenshot, close_browser
- simple_visual_creator: load_and_display_image
- google_oauth2_manager: gmail_list_messages, get_oauth2_status
- command_executor: execute

Format: {{"response": "Task breakdown explanation", "tool_calls": [{{"tool": "selenium_browser", "action": "start_browser", "params": {{"browser": "chrome", "headless": true}}}}, {{"tool": "selenium_browser", "action": "navigate", "params": {{"url": "https://example.com"}}}}, ...]}}"""
            return enhanced_message
            
        # Handle simple image display requests
        elif needs_image_display:
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object for image display tasks. Use simple_visual_creator tool for:
- Displaying existing images/screenshots
- Loading and showing saved images
- Image file viewing

Format: {{"response": "Your explanation", "tool_calls": [{{"tool": "simple_visual_creator", "action": "load_and_display_image", "params": {{"image_path": "path_to_image"}}}}]}}

KEY IMAGE DISPLAY ACTIONS:
- load_and_display_image: Display existing image file (REQUIRED: image_path)

CRITICAL: Use the exact filename from previous operations. Common screenshot names:
- minor_com_tr_screenshot.png
- screenshot.png
- gemini_response.png
- debug_*.png

Example: {{"tool": "simple_visual_creator", "action": "load_and_display_image", "params": {{"image_path": "minor_com_tr_screenshot.png"}}}}"""
            return enhanced_message

        # Handle Gemini-specific routing
        elif is_gemini_web or (needs_web_automation and not is_gemini_api):
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object for web automation tasks. Use selenium_browser tool for:
- Opening websites and web navigation
- Web scraping and data extraction  
- Browser automation (headless or visible)
- Taking screenshots
- Interacting with web elements
- Gemini web site interactions (gemini.google.com)

Format: {{"response": "Your explanation", "tool_calls": [{{"tool": "selenium_browser", "action": "start_browser", "params": {{"browser": "chrome", "headless": true}}}}, {{"tool": "selenium_browser", "action": "navigate", "params": {{"url": "https://minor.com.tr"}}}}, {{"tool": "selenium_browser", "action": "get_title", "params": {{}}}}, {{"tool": "selenium_browser", "action": "screenshot", "params": {{"filename": "minor_screenshot.png"}}}}, {{"tool": "selenium_browser", "action": "close_browser", "params": {{}}}}, {{"tool": "simple_visual_creator", "action": "load_and_display_image", "params": {{"image_path": "minor_screenshot.png"}}}}]}}

KEY SELENIUM ACTIONS (EACH IS SEPARATE):
- start_browser: Start browser session (REQUIRED: browser="chrome", optional: headless=true)
- navigate: Go to URL (REQUIRED: url) - for Gemini use "https://gemini.google.com"
- find_element: Find web elements (REQUIRED: selector)
- type_text: Enter text in inputs (REQUIRED: selector, text)
- click: Click elements (REQUIRED: selector)
- screenshot: Take page screenshot (REQUIRED: filename)
- get_title: Get page title (no params)
- close_browser: Close browser session (no params)

CRITICAL SELENIUM WORKFLOW:
1. ALWAYS start with: start_browser (browser="chrome", headless=true)
2. Then use: navigate (url="https://...")
3. Then use: get_title (no params)
4. Then use: screenshot (filename="screenshot.png")
5. Then use: close_browser (no params)
6. FINALLY use: simple_visual_creator load_and_display_image (image_path="screenshot.png")

EXAMPLE COMPLETE WORKFLOW:
{{"tool": "selenium_browser", "action": "start_browser", "params": {{"browser": "chrome", "headless": true}}}},
{{"tool": "selenium_browser", "action": "navigate", "params": {{"url": "https://minor.com.tr"}}}},
{{"tool": "selenium_browser", "action": "get_title", "params": {{}}}},
{{"tool": "selenium_browser", "action": "screenshot", "params": {{"filename": "minor_screenshot.png"}}}},
{{"tool": "selenium_browser", "action": "close_browser", "params": {{}}}},
{{"tool": "simple_visual_creator", "action": "load_and_display_image", "params": {{"image_path": "minor_screenshot.png"}}}}"""
            return enhanced_message
            
        elif needs_oauth2:
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object for Google API/OAuth2 tasks. Use google_oauth2_manager tool for:
- Gmail API access (reading, sending emails, getting email subjects)
- Google Drive API access
- Google Calendar API access
- Gemini API access (AI chat, content generation)
- OAuth2 authentication flow
- Google services integration
- Email operations (latest email, email subject, inbox)

Format: {{"response": "Your explanation", "tool_calls": [{{"tool": "google_oauth2_manager", "action": "appropriate_action", "params": {{"param": "value"}}}}]}}

KEY OAUTH2 ACTIONS:
- get_oauth2_status: Check OAuth2 configuration (optional: user_id)
- get_auth_url: Start OAuth2 flow (REQUIRED: services=["gmail","drive","basic"], optional: user_id)
- gmail_list_messages: List Gmail messages (REQUIRED: user_id, optional: query="", max_results=10)
- gmail_get_message: Get specific email details (REQUIRED: user_id, message_id)
- gmail_send_message: Send email via Gmail (REQUIRED: user_id, to, subject, body)
- drive_list_files: List Google Drive files (REQUIRED: user_id, optional: query, max_results)
- calendar_list_events: List calendar events (REQUIRED: user_id, optional: calendar_id)
- get_user_info: Get authorized user info (REQUIRED: user_id)

CRITICAL: Most actions require user_id parameter. The system will automatically inject the correct Gmail account for authenticated users.
IMPORTANT: Never use placeholder emails like 'your_email@example.com' - leave user_id empty and the system will inject the correct email.

Example for latest email: {{"tool": "google_oauth2_manager", "action": "gmail_list_messages", "params": {{"max_results": 1}}}}
Example for email details: {{"tool": "google_oauth2_manager", "action": "gmail_get_message", "params": {{"message_id": "MESSAGE_ID_FROM_PREVIOUS_CALL"}}}}

FOR EMAIL SUBJECT: Use gmail_list_messages to get latest emails, then gmail_get_message for details
FOR GEMINI API: First setup OAuth2 with basic scopes, then use Google AI API (future implementation)"""
            return enhanced_message

        elif needs_commands:
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object if this requires system commands. Format:
{{"response": "Your explanation", "tool_calls": [{{"tool": "command_executor", "action": "execute", "params": {{"command": "appropriate_command"}}}}]}}"""
            return enhanced_message
        
        elif suggested_tool:
            # Check for removal requests and provide exact tool names
            is_removal = any(word in user_message.lower() for word in ['kaldır', 'remove', 'uninstall', 'delete'])
            is_visual = suggested_tool['name'] == 'visual_creator'
            
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object when using tools. Use EXACT tool names from the list above.
Format: {{"response": "Your explanation", "tool_calls": [{{"tool": "{suggested_tool['name']}", "action": "appropriate_action", "params": {{"param": "value"}}}}]}}

SUGGESTED TOOL: {suggested_tool['name']} - {suggested_tool['description']}
AVAILABLE ACTIONS: {', '.join(suggested_tool['actions'].keys())}"""

            # For removal, add specific instruction about exact naming
            if is_removal and suggested_tool['name'] == 'tool_manager':
                enhanced_message += f"""

CRITICAL FOR REMOVAL: Look at the available tools list. If you see "website_fetcher_tool", use exactly "website_fetcher_tool" (not "website_fetcher")."""
            
            # For visual creation, add specific parameter instruction
            elif is_visual or suggested_tool['name'] == 'simple_visual_creator':
                enhanced_message += f"""

CRITICAL FOR VISUAL CREATION - FLEXIBLE PARAMETERS:
- Use either "generate_image" or "create_image" action
- Use "prompt", "description", or "theme" parameter (all work)
- EXACT format: {{"tool": "simple_visual_creator", "action": "generate_image", "params": {{"prompt": "your image description here"}}}}"""
            
            return enhanced_message
        
        elif mentioned_tools:
            enhanced_message = f"""{user_message}

AVAILABLE TOOLS: {', '.join(tool_names)}

IMPORTANT: You MUST respond with a JSON object when using tools. Format:
{{"response": "Your explanation", "tool_calls": [{{"tool": "tool_name", "action": "action_name", "params": {{"param": "value"}}}}]}}"""
            return enhanced_message
        
        return user_message
    
    def _has_todo_operations(self, response_text: str) -> bool:
        """Check if the response contains TodoWrite operations"""
        try:
            # Check for TodoWrite tool calls in JSON format
            tool_response = self._extract_tool_calls(response_text)
            if tool_response and 'tool_calls' in tool_response:
                for tool_call in tool_response['tool_calls']:
                    if tool_call.get('tool') == 'TodoWrite':
                        return True
            
            # Check for todo-related patterns in text
            todo_patterns = [
                'todowrite', 'todo_write', 'todo list', 'task list',
                'progress tracking', 'track progress', 'todo:',
                'tasks:', '☐', '✓', '- [ ]', '- [x]'
            ]
            
            response_lower = response_text.lower()
            return any(pattern in response_lower for pattern in todo_patterns)
            
        except Exception as e:
            logger.error(f"Error checking for todo operations: {e}")
            return False

    def _requires_workflow_orchestration(self, user_input: str) -> bool:
        """LLM-based determination of workflow orchestration need with caching"""
        try:
            # Check cache first
            input_hash = hash(user_input.lower().strip())
            cached_result = self._get_cached_evaluation(input_hash)
            
            if cached_result is not None:
                logger.info(f"CACHED WORKFLOW RESULT for '{user_input}': {cached_result}")
                return cached_result
            
            # First, do a quick LLM call to see if the response will contain todos
            # This allows us to catch single-step operations that will generate todo lists
            try:
                preview_result = registry.execute_tool_action(
                    'llm_tool',
                    'chat',
                    message=user_input,
                    conversation_id=f"todo_preview_{int(time.time())}",
                    enable_tools=True
                )
                
                if preview_result.success:
                    preview_response = preview_result.data.get('response', '')
                    if self._has_todo_operations(preview_response):
                        logger.info(f"TODO OPERATIONS DETECTED - Forcing workflow orchestration for: {user_input}")
                        self._cache_evaluation(input_hash, True)
                        return True
            except Exception as e:
                logger.warning(f"Error in todo preview check: {e}")
            
            # No regex patterns - let LLM evaluate intelligently
            
            # LLM-based evaluation for complex cases
            evaluation_prompt = self._create_workflow_evaluation_prompt(user_input)
            
            # Call LLM for evaluation
            eval_result = registry.execute_tool_action(
                'llm_tool',
                'chat',
                message=evaluation_prompt,
                conversation_id=f"workflow_eval_{int(time.time())}",
                enable_tools=False
            )
            
            if eval_result.success:
                response = eval_result.data.get('response', '').lower()
                needs_workflow = self._parse_workflow_evaluation(response)
                
                logger.info(f"LLM WORKFLOW EVALUATION for '{user_input}': {needs_workflow}")
                self._cache_evaluation(input_hash, needs_workflow)
                return needs_workflow
            else:
                logger.warning(f"LLM evaluation failed, using fallback for: {user_input}")
                fallback_result = self._fallback_workflow_detection(user_input)
                self._cache_evaluation(input_hash, fallback_result)
                return fallback_result
                
        except Exception as e:
            logger.error(f"Error in workflow evaluation: {str(e)}")
            fallback_result = self._fallback_workflow_detection(user_input)
            return fallback_result
    
    def _is_planning_query(self, user_input: str) -> bool:
        """Workflow-first approach: Always EXECUTION (CLAUDE.md: stop iterating)"""
        logger.info(f"WORKFLOW-FIRST: All requests → EXECUTION ('{user_input}')")
        return False  # Always execution - workflow-first architecture
    
    def _create_planning_response(self, workflow, user_input: str) -> str:
        """Create a planning response based on workflow analysis"""
        try:
            # Create user-friendly response about requirements
            planning_prompt = f"""
You are a helpful assistant. The user asked: "{user_input}"

The system has analyzed this request and determined the following requirements:

TASK: {workflow.title}
GOAL: {workflow.description}

Based on the analysis, here are the key requirements and steps:
"""
            
            for i, step in enumerate(workflow.steps, 1):
                planning_prompt += f"""
{i}. {step.title}: {step.description}
"""
            
            planning_prompt += f"""

INSTRUCTIONS:
1. Answer the user's question about what's needed for this task
2. Focus on REQUIREMENTS, not technical implementation
3. Explain what the user needs to prepare or have ready
4. Mention any prerequisites or dependencies
5. Use a friendly, helpful tone
6. Use Turkish if the user asked in Turkish
7. Don't mention technical details like tool names, actions, or parameters
8. Focus on what the USER needs to know and prepare

Provide a clear, user-friendly answer about the requirements for this task.
"""
            
            # Get LLM analysis
            analysis_result = registry.execute_tool_action(
                'llm_tool',
                'chat', 
                message=planning_prompt,
                conversation_id=f"planning_{workflow.id}",
                enable_tools=False
            )
            
            if analysis_result.success:
                return analysis_result.data.get('response', 'Workflow analysis completed.')
            else:
                return f"Workflow planned with {len(workflow.steps)} steps: {workflow.title}"
                
        except Exception as e:
            logger.error(f"Error creating planning response: {e}")
            return f"Workflow analysis: {workflow.title} - {len(workflow.steps)} steps planned."
    
    def _get_cached_evaluation(self, input_hash: int) -> Optional[bool]:
        """Get cached workflow evaluation result"""
        if input_hash in self.workflow_eval_cache:
            cached_entry = self.workflow_eval_cache[input_hash]
            
            # Check if cache entry is still valid
            if time.time() - cached_entry['timestamp'] < self.cache_ttl:
                return cached_entry['result']
            else:
                # Remove expired entry
                del self.workflow_eval_cache[input_hash]
        
        return None
    
    def _cache_evaluation(self, input_hash: int, result: bool):
        """Cache workflow evaluation result"""
        # Clean cache if it's getting too large
        if len(self.workflow_eval_cache) >= self.cache_max_size:
            # Remove oldest entries
            sorted_cache = sorted(
                self.workflow_eval_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            # Remove oldest 20% of entries
            remove_count = self.cache_max_size // 5
            for key, _ in sorted_cache[:remove_count]:
                del self.workflow_eval_cache[key]
        
        # Add new entry
        self.workflow_eval_cache[input_hash] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def _create_workflow_evaluation_prompt(self, user_input: str) -> str:
        """Create intelligent evaluation prompt for LLM workflow detection"""
        available_tools = registry.list_tools()
        tool_capabilities = {tool['name']: tool['description'] for tool in available_tools}
        
        prompt = f"""
You are a sophisticated workflow intelligence system. Analyze this user request to determine if it requires orchestrated multi-step execution.

USER REQUEST: "{user_input}"

AVAILABLE TOOLS:
{json.dumps(tool_capabilities, indent=2)}

INTELLIGENT ANALYSIS FRAMEWORK:

🎯 WORKFLOW INDICATORS (Requires Orchestration):
1. **Conditional Logic**: "if", "varsa", "eğer", "when", "depending on"
2. **Sequential Operations**: "then", "sonra", "ardından", "after", "next"  
3. **Dependent Actions**: "and", "ve", operations that depend on previous results
4. **Complex Gmail Operations**: checking + downloading + processing attachments
5. **Multi-Stage Processing**: fetch → analyze → transform → save → report
6. **Error Handling Needs**: operations that might fail and need retry/alternatives

🚀 SINGLE-STEP INDICATORS (Direct Tool Call):
1. **Simple Queries**: "what", "who", "when", basic information requests
2. **Single Commands**: one specific action without dependencies  
3. **Conversational**: greetings, thanks, clarifications
4. **Direct Tool Usage**: "run X command", "execute Y", "show Z"

📧 GMAIL-SPECIFIC ANALYSIS:
- "Gmail son mail konusu" → SINGLE_STEP (just get subject)
- "Gmail son maili kontrol et, ek varsa indir" → WORKFLOW_REQUIRED (check + conditional download)
- "En son maili oku ve attachment'ları kaydet" → WORKFLOW_REQUIRED (read + save files)
- "Mail gönderen kimdi?" → SINGLE_STEP (just get sender info)

🔍 CURRENT REQUEST ANALYSIS:
Request: "{user_input}"

Step 1: Identify main actions in request
Step 2: Check for conditional logic (if/when/varsa)
Step 3: Determine if actions depend on each other
Step 4: Assess complexity and error handling needs

CRITICAL EXAMPLES:
✅ WORKFLOW_REQUIRED:
- "Gmail'deki son maili kontrol et, ek dosya varsa indir ve sonuçları göster"
  → Reason: 1) Check email 2) Conditional attachment check 3) Download if exists 4) Report results
- "Gmail'deki son 3 mailin subject bilgisini getir"
  → Reason: 1) List emails to get IDs 2) Get each email details for subjects - requires multiple API calls
- "Sistemi kontrol et ve rapor oluştur"
  → Reason: 1) System check 2) Analysis 3) Report generation
- "X'i ara ve sonuçları özetle"
  → Reason: 1) Search 2) Analysis 3) Summarization

❌ SINGLE_STEP:
- "Gmail'e bağlı mı kontrol et"
  → Reason: Single status check
- "ls komutunu çalıştır"
  → Reason: Single command execution
- "Merhaba, nasılsın?"
  → Reason: Conversational, no tools needed

LANGUAGE UNDERSTANDING:
- Turkish: "kontrol et", "varsa", "indir", "sonuçları göster" = conditional multi-step
- English: "check", "if any", "download", "show results" = conditional multi-step

RESPONSE FORMAT (JSON):
{{
  "decision": "WORKFLOW_REQUIRED" or "SINGLE_STEP",
  "confidence": 0.9,
  "reasoning": "Detailed explanation of why this decision was made",
  "identified_steps": ["step1", "step2", "step3"] or [],
  "conditional_logic": true/false,
  "dependency_chain": true/false
}}

Analyze the request intelligently and provide your decision:
"""
        return prompt
    
    def _parse_workflow_evaluation(self, llm_response: str) -> bool:
        """Parse intelligent LLM response to determine workflow need"""
        try:
            # Try to parse JSON response first
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                decision = parsed.get('decision', '').upper()
                confidence = parsed.get('confidence', 0.0)
                reasoning = parsed.get('reasoning', '')
                
                logger.info(f"LLM Workflow Decision: {decision} (confidence: {confidence})")
                logger.info(f"LLM Reasoning: {reasoning}")
                
                if decision == 'WORKFLOW_REQUIRED' and confidence > 0.7:
                    return True
                elif decision == 'SINGLE_STEP' and confidence > 0.7:
                    return False
            
        except Exception as e:
            logger.error(f"Error parsing JSON workflow evaluation: {e}")
        
        # Fallback: analyze text content
        response_lower = llm_response.lower()
        
        # Look for decision keywords
        if 'workflow_required' in response_lower:
            logger.info("Fallback: Found WORKFLOW_REQUIRED keyword")
            return True
        elif 'single_step' in response_lower:
            logger.info("Fallback: Found SINGLE_STEP keyword")
            return False
        
        # Enhanced fallback analysis
        workflow_indicators = [
            'multiple steps', 'multi-step', 'sequential', 'conditional',
            'varsa', 'eğer', 'depends on', 'then', 'sonra', 'ardından',
            'çok adım', 'birden fazla', 'sıralı', 'koşullu'
        ]
        
        single_indicators = [
            'single step', 'one action', 'simple query', 'direct',
            'tek adım', 'basit', 'doğrudan', 'sadece'
        ]
        
        workflow_score = sum(1 for indicator in workflow_indicators if indicator in response_lower)
        single_score = sum(1 for indicator in single_indicators if indicator in response_lower)
        
        result = workflow_score > single_score
        logger.info(f"Fallback Analysis: workflow_score={workflow_score}, single_score={single_score}, result={result}")
        
        return result
    
    def _initialize_memory_logging(self):
        """Initialize graph memory connection for universal operation logging"""
        try:
            self.graph_memory = registry.get_tool("graph_memory")
            if not self.graph_memory:
                logger.warning("Graph memory tool not available - operation logging disabled")
        except Exception as e:
            logger.error(f"Failed to initialize memory logging: {e}")
    
    def _log_operation_to_memory(self, tool_name: str, action_name: str, result: MCPToolResult, 
                               user_id: str = None, parameters: Dict = None):
        """Universal operation logging for all tool executions"""
        try:
            if not self.graph_memory or not user_id:
                return
            
            # Enhanced result data with context info
            enhanced_result = {
                "success": result.success,
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "action_name": action_name,
                "error": result.error if not result.success else None
            }
            
            # Add specific context based on tool type
            if tool_name == "simple_visual_creator" and result.success:
                enhanced_result["file_path"] = result.data.get("saved_path")
                enhanced_result["prompt"] = parameters.get("prompt")
                enhanced_result["provider"] = result.data.get("provider")
            elif tool_name == "command_executor" and result.success:
                enhanced_result["command"] = parameters.get("command")
                enhanced_result["output"] = result.data.get("output", "")[:200]  # First 200 chars
            elif tool_name == "gmail_helper" and result.success:
                if "list" in action_name:
                    enhanced_result["email_count"] = len(result.data.get("messages", []))
                elif "get" in action_name:
                    enhanced_result["message_id"] = parameters.get("message_id")
                    enhanced_result["subject"] = result.data.get("subject", "")
            
            # Log to graph memory
            self.graph_memory._log_tool_operation(
                tool_name=tool_name,
                action_name=action_name,
                result=enhanced_result,
                user_id=user_id,
                parameters=parameters or {}
            )
            
            logger.debug(f"Operation logged to memory: {tool_name}.{action_name} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log operation to memory: {e}")
    
    def _fallback_workflow_detection(self, user_input: str) -> bool:
        """Fallback detection using enhanced patterns"""
        user_lower = user_input.lower()
        
        # Enhanced fallback patterns
        workflow_patterns = [
            # Gmail/Email operations
            r'(gmail|email|mail).*(subject|konusu|başlığı)',
            r'(inbox|gelen.*kutusu).*(son|latest|last)',
            r'(subject|konusu|başlığı).*(paylaş|getir|al)',
            
            # Multi-action indicators
            r'(ve|and).*(göster|show|display)',
            r'(sonra|then|ardından)',
            r'(kontrol.*et|check).*(rapor|report)',
            
            # Complex operations
            r'(araştır|research).*(özetle|summarize)',
            r'(analiz|analyze).*(rapor|report)',
            r'(indir|download).*(çıkar|extract)'
        ]
        
        return any(re.search(pattern, user_lower) for pattern in workflow_patterns)
    
    def _create_workflow_response(self, workflow, execution_result) -> str:
        """Create human-readable response from workflow execution"""
        
        # Debug workflow info
        with open("/tmp/workflow_response_debug.txt", "w") as f:
            f.write(f"Workflow Response Debug:\n")
            f.write(f"Workflow Status: {workflow.status} (value: {workflow.status.value})\n")
            f.write(f"Workflow Title: {workflow.title}\n")
            f.write(f"Total Steps: {len(workflow.steps)}\n")
            for i, step in enumerate(workflow.steps):
                f.write(f"Step {i}: {step.title} - Status: {step.status.value} - Tool: {step.tool_name} - UserInput: {step.requires_user_input}\n")
        if workflow.status == WorkflowStatus.COMPLETED:
            successful_steps = len([s for s in workflow.steps if s.status.value == 'completed'])
            total_steps = len(workflow.steps)
            
            response = f"✅ **Workflow Completed Successfully**\n\n"
            response += f"**Task**: {workflow.title}\n"
            response += f"**Steps Completed**: {successful_steps}/{total_steps}\n\n"
            
            # Add results from final step
            if workflow.steps and workflow.steps[-1].result:
                final_result = workflow.steps[-1].result
                if final_result.get('success') and final_result.get('data'):
                    final_data = final_result['data']
                    
                    # Check if this is an image result
                    if final_data.get('base64_image') or final_data.get('saved_path'):
                        response += f"**Result**: Image generated successfully\n"
                    else:
                        # For non-image results, show brief summary only
                        if 'subject' in final_data:
                            subject = final_data.get('subject', 'No Subject')
                            sender = final_data.get('sender', 'Unknown')
                            response += f"**Result**: 📧 Email Subject: {subject}\n"
                        elif 'message' in final_data:
                            response += f"**Result**: {final_data['message']}\n"
            
            response += f"\n*Workflow ID: {workflow.id}*"
            
        elif workflow.status.value == 'failed':
            failed_step = next((s for s in workflow.steps if s.status.value == 'failed'), None)
            
            # Debug failed step info
            with open("/tmp/failed_step_debug.txt", "w") as f:
                if failed_step:
                    f.write(f"Failed Step Found:\n")
                    f.write(f"Step Title: {failed_step.title}\n")
                    f.write(f"Tool Name: {failed_step.tool_name}\n")
                    f.write(f"Requires User Input: {failed_step.requires_user_input}\n")
                    f.write(f"Status: {failed_step.status}\n")
                    f.write(f"Conflict Info: {failed_step.conflict_info}\n")
                else:
                    f.write("No failed step found\n")
            
            # Check if this is a user clarification step (conflict resolution)
            if (failed_step and failed_step.requires_user_input and 
                failed_step.tool_name == 'user_clarification'):
                
                # Debug step result
                with open("/tmp/failed_step_debug.txt", "w") as f:
                    f.write(f"Failed Step Debug:\n")
                    f.write(f"Step Title: {failed_step.title}\n")
                    f.write(f"Tool Name: {failed_step.tool_name}\n")
                    f.write(f"Requires User Input: {failed_step.requires_user_input}\n")
                    f.write(f"Result: {failed_step.result}\n")
                    f.write(f"Conflict Info: {failed_step.conflict_info}\n")
                
                # Extract clarification message from step result or conflict info
                clarification_msg = "🤔 **Instagram için hangi aracı kullanmak istiyorsunuz?**\n\n"
                clarification_msg += "• **Instagram Tool**: Doğrudan Instagram hesap işlemleri (post, story, yorum)\n"
                clarification_msg += "• **Social Media Workflow**: İçerik planlama, kampanya yönetimi, multi-platform strateji\n\n"
                clarification_msg += "💡 **Yanıt örnekleri:**\n"
                clarification_msg += "• 'Instagram tool kullan' → Doğrudan hesap işlemleri\n"
                clarification_msg += "• 'Sosyal medya tool kullan' → İçerik planlama"
                
                if (failed_step.result and failed_step.result.get('data') and 
                    failed_step.result['data'].get('clarification_message')):
                    clarification_msg = failed_step.result['data']['clarification_message']
                
                response = f"🤔 **Tool Selection Required**\n\n"
                response += f"**Task**: {workflow.title}\n\n"
                response += clarification_msg
                response += f"\n\n*Workflow ID: {workflow.id}*"
                
            else:
                # Regular failure
                response = f"❌ **Workflow Failed**\n\n"
                response += f"**Task**: {workflow.title}\n"
                if failed_step:
                    response += f"**Failed at**: {failed_step.title}\n"
                    response += f"**Error**: {failed_step.error}\n"
            
        else:
            response = f"⏳ **Workflow In Progress**\n\n"
            response += f"**Task**: {workflow.title}\n"
            response += f"**Status**: {workflow.status.value}\n"
            
        return response
    
    def _format_final_result(self, data) -> str:
        """Format final workflow result for user display"""
        if isinstance(data, dict):
            # Gmail subject extraction
            if 'subject' in data:
                subject = data.get('subject', 'No Subject')
                sender = data.get('sender', 'Unknown')
                return f"📧 **Latest Email Subject**: {subject}\n**From**: {sender}"
            
            # Generic data formatting
            if 'message' in data:
                return data['message']
            
            # Fallback
            return str(data)
        
        return str(data)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status for frontend"""
        return orchestrator.get_workflow_status(workflow_id)
    
    def get_user_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all workflows for a user"""
        return orchestrator.get_active_workflows(user_id)
    
    def _clean_base64_from_result_data(self, data: Any) -> Any:
        """Clean base64 image data from workflow result data to prevent LLM context overflow"""
        if not data:
            return data
        
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if key in ['base64_image', 'b64_json', 'base64_data']:
                    if isinstance(value, str) and len(value) > 100:
                        cleaned[key] = f"[IMAGE_DATA_REFERENCE_{len(value)}_CHARS]"
                    else:
                        cleaned[key] = value
                elif isinstance(value, (dict, list)):
                    cleaned[key] = self._clean_base64_from_result_data(value)
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, list):
            return [self._clean_base64_from_result_data(item) for item in data]
        else:
            return data
    
    def get_relevant_tools(self, user_input: str) -> List[Any]:
        """
        LLM-based tool relevance detection for workflow planning
        Returns list of ToolMatch objects with tool_name, action_name, confidence
        CLAUDE.md compliant: No regex, no hardcoded patterns, LLM evaluation only
        """
        try:
            # Check cache first
            cache_key = f"tool_relevance_{hash(user_input)}"
            if cache_key in self.tool_relevance_cache:
                cached_time, cached_result = self.tool_relevance_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_result
            
            # Get available tools
            available_tools = registry.list_tools()
            
            # LLM-based tool analysis prompt
            tools_description = {}
            for tool in available_tools:
                tools_description[tool['name']] = {
                    'description': tool['description'],
                    'actions': list(tool['actions'].keys())
                }
            
            # Use LLM to analyze tool relevance (no hardcoded patterns)
            analysis_prompt = f"""
Analyze the user input and determine which tools are most relevant for completing the task.

USER INPUT: "{user_input}"

AVAILABLE TOOLS:
{json.dumps(tools_description, indent=2)}

ANALYSIS CRITERIA:
1. What is the primary action the user wants to perform?
2. Which tools have capabilities that match this action?
3. Are there secondary tools needed to complete the workflow?
4. Consider multi-language support (Turkish/English)

TOOL RELEVANCE RULES:
- gmail_helper: Email operations, Gmail sending/reading, attachments
- google_oauth2_manager: Google authentication, OAuth2 flow
- simple_visual_creator: Image generation, visual content, DALL-E
- command_executor: System commands, file operations, terminal
- selenium_browser: Web automation, browser control, screenshots
- llm_tool: Chat, conversation, text analysis
- memory_manager: Data storage, retrieval, context

OUTPUT FORMAT (JSON):
{{
    "relevant_tools": [
        {{
            "tool_name": "gmail_helper",
            "action_name": "send_email_with_attachment", 
            "confidence": 0.9,
            "reasoning": "User wants to send file via Gmail"
        }}
    ],
    "primary_intent": "brief description of user intent"
}}

Be precise and only return tools that are directly relevant to the user's request.
"""
            
            # Direct OpenAI API call (bypass LLM tool schema issues)
            import os
            import requests
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not available for tool relevance analysis")
                return []
            
            # Direct OpenAI API call
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'user', 'content': analysis_prompt}
                    ],
                    'temperature': 0.1
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return []
            
            response_data = response.json()
            response_text = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Parse LLM response
            try:
                # Extract JSON from LLM response (response_text already defined above)
                
                # Find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(0))
                else:
                    logger.warning("No JSON found in LLM response for tool analysis")
                    return []
                
                # Convert to ToolMatch objects
                tool_matches = []
                for tool_info in analysis_data.get('relevant_tools', []):
                    # Create simple tool match object
                    tool_match = type('ToolMatch', (), {
                        'tool_name': tool_info.get('tool_name'),
                        'action_name': tool_info.get('action_name'),
                        'confidence': tool_info.get('confidence', 0.5)
                    })()
                    tool_matches.append(tool_match)
                
                # Cache result
                self.tool_relevance_cache[cache_key] = (time.time(), tool_matches)
                
                # Clean old cache entries
                if len(self.tool_relevance_cache) > self.cache_max_size:
                    oldest_key = min(self.tool_relevance_cache.keys(), 
                                   key=lambda k: self.tool_relevance_cache[k][0])
                    del self.tool_relevance_cache[oldest_key]
                
                logger.info(f"LLM tool analysis: Found {len(tool_matches)} relevant tools for: {user_input[:50]}...")
                return tool_matches
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM tool analysis response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Error in LLM-based tool relevance analysis: {e}")
            return []

# Global coordinator instance
coordinator = ToolCoordinator()