"""
Flask routes for MetisAgent2 API
"""

from flask import Blueprint, request, jsonify, send_from_directory
from functools import wraps
import logging
from typing import Optional, List, Dict, Any
from .mcp_core import registry
from .tool_coordinator import coordinator
from .session_manager import session_manager
from .auth_manager import auth_manager
from .workflow_orchestrator import orchestrator
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import register_all_tools

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Tools are already registered in app/__init__.py
# Removed duplicate registration to prevent registry conflicts

def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        session_token = auth_header[7:]
        user_info = auth_manager.validate_session(session_token)
        
        if not user_info:
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        # Add user info to request context
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """Optional authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        request.current_user = None
        
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
            user_info = auth_manager.validate_session(session_token)
            if user_info:
                request.current_user = user_info
        
        return f(*args, **kwargs)
    
    return decorated_function

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        tool_health = registry.health_check_all()
        healthy_tools = sum(1 for result in tool_health.values() if result.success)
        total_tools = len(tool_health)
        
        return jsonify({
            'status': 'healthy' if healthy_tools == total_tools else 'degraded',
            'tools': {
                'healthy': healthy_tools,
                'total': total_tools,
                'details': {name: result.to_dict() for name, result in tool_health.items()}
            },
            'version': '2.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@api_bp.route('/tools', methods=['GET'])
def list_tools():
    """List all registered tools"""
    try:
        tools = registry.list_tools()
        return jsonify({
            'tools': tools,
            'count': len(tools)
        })
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/tools/<tool_name>', methods=['GET'])
def get_tool_info(tool_name):
    """Get information about a specific tool"""
    try:
        tool = registry.get_tool(tool_name)
        if not tool:
            return jsonify({'error': f'Tool {tool_name} not found'}), 404
        
        return jsonify(tool.get_info())
    except Exception as e:
        logger.error(f"Failed to get tool info for {tool_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/tools/<tool_name>/execute', methods=['POST'])
def execute_tool_action(tool_name):
    """Execute an action on a specific tool"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        action = data.get('action')
        if not action:
            return jsonify({'error': 'Action not specified'}), 400
        
        params = data.get('params', {})
        
        result = registry.execute_tool_action(tool_name, action, **params)
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to execute {tool_name}.{action}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat', methods=['POST'])
@optional_auth
def chat():
    """Enhanced chat endpoint with intelligent tool routing and multi-user support"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message not provided'}), 400
        
        # Extract user session info
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        # DEBUG: Log authentication headers and data
        auth_header = request.headers.get('Authorization')
        logger.info(f"DEBUG CHAT AUTH: header={auth_header}, current_user={getattr(request, 'current_user', None)}, data_user_id={user_id}")
        
        # Check if user is authenticated
        if hasattr(request, 'current_user') and request.current_user:
            # Authenticated user
            user_id = request.current_user['user_id']
            session = session_manager.get_or_create_session(user_id, session_id)
            conversation_id = session.conversation_id
            logger.info(f"Authenticated user: {user_id}")
        elif user_id:
            # Legacy user_id from frontend (fallback)
            session = session_manager.get_or_create_session(user_id, session_id)
            conversation_id = session.conversation_id
            logger.info(f"Legacy user: {user_id}")
        else:
            # Check if there's any authenticated OAuth2 user we can use
            try:
                from tools.settings_manager import get_settings_manager
                settings_manager = get_settings_manager()
                authenticated_users = settings_manager.get_all_users()
                if authenticated_users:
                    # Use the first authenticated user with OAuth2 credentials
                    for potential_user in authenticated_users:
                        oauth_creds = settings_manager.get_oauth2_credentials(potential_user, 'google')
                        if oauth_creds:
                            user_id = potential_user  
                            session = session_manager.get_or_create_session(user_id, session_id)
                            conversation_id = session.conversation_id
                            logger.info(f"Using authenticated OAuth2 user: {user_id}")
                            break
                    else:
                        # No authenticated users found - create anonymous
                        session = session_manager.create_session(None)
                        conversation_id = session.conversation_id
                        user_id = session.user_id  
                        logger.info(f"Anonymous user session: {user_id}")
                else:
                    # No authenticated users found - create anonymous
                    session = session_manager.create_session(None)
                    conversation_id = session.conversation_id
                    user_id = session.user_id  
                    logger.info(f"Anonymous user session: {user_id}")
            except Exception as e:
                logger.error(f"Error checking OAuth2 users: {e}")
                # Fallback to anonymous
                session = session_manager.create_session(None)
                conversation_id = session.conversation_id
                user_id = session.user_id  
                logger.info(f"Anonymous user session (fallback): {user_id}")
        
        # Extract optional parameters
        provider = data.get('provider', 'openai')
        model = data.get('model')
        system_prompt = data.get('system_prompt')
        enable_tools = data.get('enable_tools', True)
        
        # CONTEXT-AWARE PROCESSING: TEMPORARILY DISABLED FOR CONFLICT TESTING
        logger.info(f"CONTEXT-AWARE: DISABLED - Direct message processing: {message}")
        context_workflow_needed = False
        
        # Use Sequential Thinking with context awareness
        workflow_orchestration_enabled = True
        
        if workflow_orchestration_enabled:
            logger.info(f"WORKFLOW ORCHESTRATION TRIGGERED for: {message}")
            
            # Create workflow plan (don't execute yet)
            effective_user_id = user_id or 'anonymous'
            logger.info(f"Creating workflow plan with user_id: {effective_user_id}")
            
            # DEBUG: Write to file to confirm routes is calling orchestrator
            with open("/tmp/routes_debug.txt", "w") as f:
                f.write(f"ROUTES: Calling orchestrator with: {message}\n")
                f.write(f"Time: {__import__('datetime').datetime.now()}\n")
                f.write(f"User ID: {effective_user_id}\n")
                f.write(f"Conversation ID: {conversation_id}\n")
            
            workflow = orchestrator.create_workflow_from_user_input(
                message, effective_user_id, conversation_id
            )
            
            # Check if this is a planning query vs execution request
            is_planning_query = coordinator._is_planning_query(message)
            
            # SPECIAL CASE: Instagram conflict detection - ONLY for initial instagram queries
            if "instagram" in message.lower() and not any(keyword in message.lower() for keyword in ["sosyal medya", "social media", "workflow"]):
                logger.info(f"INSTAGRAM CONFLICT - Returning tool selection response")
                conflict_response = "🤔 **Instagram için hangi aracı kullanmak istiyorsunuz?**\n\n"
                conflict_response += "• **Instagram Tool**: Doğrudan Instagram hesap işlemleri (post, story, yorum)\n"
                conflict_response += "• **Social Media Workflow**: İçerik planlama, kampanya yönetimi, multi-platform strateji\n\n"
                conflict_response += "💡 **Yanıt örnekleri:**\n"
                conflict_response += "• 'Instagram tool kullan' → Doğrudan hesap işlemleri\n"
                conflict_response += "• 'Sosyal medya tool kullan' → İçerik planlama\n\n"
                conflict_response += f"*Workflow ID: {workflow.id}*"
                
                return jsonify({
                    'success': True,
                    'data': {
                        'response': conflict_response,
                        'workflow_id': workflow.id,
                        'workflow_status': 'awaiting_user_input',
                        'has_workflow': True,
                        'is_planning_only': False,
                        'tool_calls': [],
                        'tool_results': [],
                        'has_tool_calls': False,
                        'requires_user_choice': True
                    },
                    'session': session.to_dict(),
                    'timestamp': datetime.now().isoformat()
                })
            
            if is_planning_query:
                logger.info(f"PLANNING QUERY - Analyzing workflow without execution")
                # Analyze the workflow and provide planning response
                planning_response = coordinator._create_planning_response(workflow, message)
                workflow_response = planning_response
                execution_result = None
                
                # Return planning result (no workflow pane needed)
                return jsonify({
                    'success': True,
                    'data': {
                        'response': workflow_response,
                        'workflow_id': None,  # No workflow to track
                        'workflow_status': None,  # No status to show
                        'has_workflow': False,  # Don't show workflow pane
                        'is_planning_only': True,  # This is just analysis
                        'tool_calls': [],
                        'tool_results': [],
                        'has_tool_calls': False
                    },
                    'session': session.to_dict(),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.info(f"EXECUTION REQUEST - Running workflow")
                
                # EMERGENCY FIX: Check for user clarification steps before execution
                with open("/tmp/workflow_steps_debug.txt", "w") as f:
                    f.write(f"Workflow Steps Debug:\n")
                    f.write(f"Total Steps: {len(workflow.steps)}\n")
                    for i, step in enumerate(workflow.steps):
                        f.write(f"Step {i}: {step.title} - Tool: {step.tool_name} - UserInput: {step.requires_user_input}\n")
                
                has_user_clarification = any(
                    step.tool_name == 'user_clarification' and step.requires_user_input
                    for step in workflow.steps
                )
                
                if has_user_clarification:
                    # Special handling for conflict resolution
                    workflow_response = "🤔 **Instagram için hangi aracı kullanmak istiyorsunuz?**\n\n"
                    workflow_response += "• **Instagram Tool**: Doğrudan Instagram hesap işlemleri (post, story, yorum)\n"
                    workflow_response += "• **Social Media Workflow**: İçerik planlama, kampanya yönetimi, multi-platform strateji\n\n"
                    workflow_response += "💡 **Yanıt örnekleri:**\n"
                    workflow_response += "• 'Instagram tool kullan' → Doğrudan hesap işlemleri\n"
                    workflow_response += "• 'Sosyal medya tool kullan' → İçerik planlama\n\n"
                    workflow_response += f"*Workflow ID: {workflow.id}*"
                else:
                    # Execute workflow normally
                    execution_result = orchestrator.execute_workflow(workflow.id)
                    workflow_response = coordinator._create_workflow_response(workflow, execution_result)
                
                # Extract image data from final step result if available
                response_data = {
                    'response': workflow_response,
                    'workflow_id': workflow.id,
                    'workflow_status': workflow.status.value,
                    'has_workflow': True,
                    'is_planning_only': False,
                    'tool_calls': [],
                    'tool_results': [],
                    'has_tool_calls': False
                }
                
                # Add image data from ANY step that has image result (not just final step)
                image_found = False
                logger.info(f"🔍 ROUTES DEBUG - Checking {len(workflow.steps)} steps for image data")
                
                for step_idx, step in enumerate(reversed(workflow.steps)):  # Check from last to first
                    logger.info(f"🔍 ROUTES DEBUG - Step {step_idx}: {step.title} has_result={bool(step.result)}")
                    
                    if step.result:
                        logger.info(f"🔍 ROUTES DEBUG - Step result keys: {list(step.result.keys())}")
                        if step.result.get('success') and step.result.get('data'):
                            step_data = step.result['data']
                            logger.info(f"🔍 ROUTES DEBUG - Step data keys: {list(step_data.keys())}")
                            logger.debug(f"🔍 ROUTES DEBUG - Has base64_image: {bool(step_data.get('base64_image'))}")
                            logger.info(f"🔍 ROUTES DEBUG - Has display_ready: {bool(step_data.get('display_ready'))}")
                            
                            if step_data.get('base64_image'):  # Remove display_ready requirement for debugging
                                # Found step with image data
                                final_data = step_data
                                image_found = True
                                logger.info(f"🎯 ROUTES IMAGE FIX - Found image in step: {step.title}")
                                break
                
                if image_found and (final_data.get('saved_path') or final_data.get('base64_image')):
                            # **EFFICIENT FIX**: Use file serving instead of base64 transfer
                            saved_path = final_data.get('saved_path')
                            filename = final_data.get('local_filename') or final_data.get('filename')
                            
                            if saved_path and filename:
                                # Create URL for static file serving (API prefixed)
                                image_url = f"/api/generated_images/{filename}"
                                response_data['image_url'] = image_url
                                response_data['saved_path'] = saved_path
                                logger.info(f"🔗 EFFICIENT IMAGE - Using file URL: {image_url}")
                            else:
                                # Fallback to base64 if no file path
                                response_data['base64_image'] = final_data.get('base64_image')
                                logger.debug(f"📦 FALLBACK - Using base64 transfer")
                            
                            response_data['filename'] = filename
                            response_data['display_ready'] = final_data.get('display_ready', True)
                            response_data['has_image'] = True  # Frontend flag for image display
                
                # Check for Gmail data processing
                if not image_found:
                    try:
                        for step_idx, step in enumerate(reversed(workflow.steps)):
                            if step.result and step.result.get('success') and step.result.get('data'):
                                step_data = step.result['data']
                                
                                # Check if this is Gmail data (has messages)
                                if 'messages' in step_data:
                                    logger.info(f"📧 ROUTES GMAIL - Processing Gmail data from step: {step.title}")
                                    messages = step_data.get('messages', [])
                                    logger.info(f"📧 ROUTES GMAIL - Messages type: {type(messages)}, Length: {len(messages) if hasattr(messages, '__len__') else 'N/A'}")
                                    
                                    # Handle different message formats - dict vs list
                                    latest_message = None
                                    if isinstance(messages, dict):
                                        # If messages is a dict, get values and find latest
                                        for key, value in messages.items():
                                            if isinstance(value, list) and len(value) > 0:
                                                latest_message = value[0]  # Get first message from the list
                                                break
                                        if not latest_message:
                                            # Fallback: try to get first value if it's directly a message
                                            message_list = list(messages.values()) if messages else []
                                            if message_list and isinstance(message_list[0], dict):
                                                latest_message = message_list[0]
                                    elif isinstance(messages, list) and len(messages) > 0:
                                        # If messages is already a list
                                        latest_message = messages[0]
                                    
                                    if latest_message:
                                        logger.info(f"📧 ROUTES GMAIL - Latest message keys: {list(latest_message.keys()) if isinstance(latest_message, dict) else type(latest_message)}")
                                        
                                        if not isinstance(latest_message, dict):
                                            logger.error(f"📧 ROUTES GMAIL - Latest message is not dict: {latest_message}")
                                            continue
                                            
                                        sender = latest_message.get('from', f"Message ID: {latest_message.get('id', 'Unknown')}")
                                        subject = latest_message.get('subject', f"Thread ID: {latest_message.get('threadId', 'No subject')}")
                                        date = latest_message.get('date', 'Tarih bilgisi gerekiyor - backend fix yapılacak')
                                        
                                        # Create Gmail response
                                        gmail_response = f"📧 **En son gelen mail:**\n\n**Gönderen:** {sender}\n**Konu:** {subject}\n**Tarih:** {date}"
                                        
                                        response_data['gmail_result'] = gmail_response
                                        response_data['has_gmail_data'] = True
                                        response_data['sender'] = sender
                                        response_data['subject'] = subject
                                        response_data['date'] = date
                                        
                                        logger.info(f"📧 ROUTES GMAIL - Extracted sender: {sender}")
                                        
                                        # Override workflow response with Gmail data
                                        response_data['response'] = gmail_response
                                        logger.info(f"📧 ROUTES GMAIL - Response overridden with Gmail data")
                                        break
                                    else:
                                        logger.warning(f"📧 ROUTES GMAIL - No valid messages found in Gmail data. Type: {type(messages)}, Content: {messages}")
                    except Exception as gmail_error:
                        logger.error(f"📧 ROUTES GMAIL - Error processing Gmail data: {gmail_error}")
                        logger.error(f"📧 ROUTES GMAIL - Error type: {type(gmail_error)}")
                        import traceback
                        logger.error(f"📧 ROUTES GMAIL - Traceback: {traceback.format_exc()}")
                        # Continue without Gmail data rather than crash
                
                if image_found and final_data:
                    response_data['content_type'] = 'image'  # Content type indicator
                            
                    # Explicit image object for frontend compatibility
                    response_data['image_data'] = {
                        'base64': final_data['base64_image'],
                        'filename': final_data.get('filename'),
                        'format': final_data.get('format', 'PNG'),
                        'size': final_data.get('file_size'),
                        'display_ready': True
                    }
                    
                    logger.debug(f"WORKFLOW IMAGE - Sent to frontend: {final_data.get('local_filename')} ({final_data.get('format', 'PNG')}, {len(final_data.get('base64_image', ''))} bytes)")
                    logger.info(f"🔍 ROUTES FINAL - Response data keys: {list(response_data.keys())}")
                    logger.debug(f"🔍 ROUTES FINAL - Has base64_image: {bool(response_data.get('base64_image'))}")
                    logger.info(f"🔍 ROUTES FINAL - Has has_image: {bool(response_data.get('has_image'))}")
                
                # Check for decisions in workflow response OR workflow steps
                decision_data = None
                if execution_result:
                    decision_data = _check_for_decisions(execution_result, workflow)
                
                # DECISION FIX: Also check workflow steps for decision requirements
                if not decision_data:
                    decision_data = _check_workflow_steps_for_decisions(workflow)
                
                if decision_data:
                    response_data.update(decision_data)
                    # Store decision ID in workflow for later lookup
                    workflow.pending_decision_id = decision_data.get('decision_id')
                    logger.info(f"Decision detected in workflow {workflow.id}: {decision_data.get('decision_id')}")
                
                # Return execution result (with workflow pane)
                return jsonify({
                    'success': True,
                    'data': response_data,
                'session': session.to_dict(),
                'timestamp': datetime.now().isoformat()
            })
        else:
            # This should never happen with workflow-first approach
            logger.error(f"WORKFLOW-FIRST: Unexpected fallback path for: {message}")
            return jsonify({
                'success': False,
                'error': 'Workflow orchestration failed - system error'
            }), 500
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _check_for_decisions(workflow_result: Dict, workflow) -> Optional[Dict]:
    """Check workflow result for decision requirements"""
    try:
        # Check workflow response for decision patterns
        response_text = workflow_result.get('response', '')
        
        # Look for decision indicators in response
        if any(indicator in response_text.lower() for indicator in [
            'choose', 'seçin', 'hangi', 'which', 'option', 'seçenek'
        ]):
            # Generate decision ID
            decision_id = f"decision_{workflow.id}_{int(datetime.now().timestamp())}"
            
            # Try to extract options from response
            decision_options = _extract_decision_options(response_text)
            
            if decision_options:
                return {
                    'requires_decision': True,
                    'decision_id': decision_id,
                    'decision_title': 'Please choose an option:',
                    'decision_description': 'Select one of the following options to continue:',
                    'decision_options': decision_options
                }
        
        # Check tool results for decision requirements
        tool_results = workflow_result.get('tool_results', [])
        for result in tool_results:
            if result.get('success') and isinstance(result.get('data'), dict):
                data = result['data']
                if data.get('requires_decision'):
                    decision_id = f"decision_{workflow.id}_{int(datetime.now().timestamp())}"
                    return {
                        'requires_decision': True,
                        'decision_id': decision_id,
                        'decision_title': data.get('decision_title', 'Please choose an option:'),
                        'decision_description': data.get('decision_description', ''),
                        'decision_options': data.get('decision_options', [])
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking for decisions: {e}")
        return None

def _check_workflow_steps_for_decisions(workflow) -> Optional[Dict]:
    """Check workflow steps for decision requirements"""
    try:
        for step in workflow.steps:
            step_params = getattr(step, 'params', {})
            if step_params.get('requires_decision'):
                # Generate decision ID
                decision_id = f"decision_{workflow.id}_{int(datetime.now().timestamp())}"
                
                return {
                    'requires_decision': True,
                    'decision_id': decision_id,
                    'decision_title': step_params.get('decision_title', 'Please choose an option:'),
                    'decision_description': step_params.get('decision_description', ''),
                    'decision_options': step_params.get('decision_options', [])
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking workflow steps for decisions: {e}")
        return None

def _extract_decision_options(text: str) -> List[str]:
    """Extract decision options from text"""
    try:
        options = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for bullet points or numbered lists
            if line.startswith(('•', '▪', '-', '*')) or (len(line) > 2 and line[1] == '.'):
                option = line.lstrip('•▪-*0123456789. ').strip()
                if option and len(option) > 3:  # Skip too short options
                    options.append(option)
        
        # If no structured options found, try to find quoted options
        if not options:
            import re
            quoted_options = re.findall(r"'([^']+)'|\"([^\"]+)\"", text)
            for match in quoted_options:
                option = match[0] or match[1]
                if option and len(option) > 3:
                    options.append(option)
        
        return options[:5]  # Max 5 options
        
    except Exception as e:
        logger.error(f"Error extracting decision options: {e}")
        return []

@api_bp.route('/workflows', methods=['GET'])
@optional_auth
def get_workflows():
    """Get user's active workflows"""
    try:
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id', 'anonymous') if current_user else 'anonymous'
        workflows = coordinator.get_user_workflows(user_id)
        
        return jsonify({
            'success': True,
            'workflows': workflows,
            'total': len(workflows)
        })
        
    except Exception as e:
        logger.error(f"Error getting workflows: {str(e)}")
        return jsonify({'error': 'Failed to get workflows', 'details': str(e)}), 500

@api_bp.route('/workflows/<workflow_id>', methods=['GET'])
@optional_auth
def get_workflow_status(workflow_id):
    """Get specific workflow status"""
    try:
        workflow_status = coordinator.get_workflow_status(workflow_id)
        
        if 'error' in workflow_status:
            return jsonify({'error': workflow_status['error']}), 404
        
        return jsonify({
            'success': True,
            'workflow': workflow_status
        })
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        return jsonify({'error': 'Failed to get workflow status', 'details': str(e)}), 500

@api_bp.route('/decision', methods=['POST'])
@optional_auth
def submit_decision():
    """Submit decision for sequential thinking workflow"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        decision_id = data.get('decision_id')
        choice = data.get('choice')
        
        if not decision_id or choice is None:
            return jsonify({'error': 'decision_id and choice are required'}), 400
        
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id', 'anonymous') if current_user else 'anonymous'
        
        logger.info(f"Decision submission: {decision_id} -> {choice} from user {user_id}")
        
        # Find the workflow associated with this decision_id
        workflow = orchestrator.get_workflow_by_decision_id(decision_id)
        if not workflow:
            return jsonify({'error': 'Decision ID not found or expired'}), 404
        
        # Resume workflow with the decision
        result = orchestrator.resume_workflow_with_decision(workflow.id, decision_id, choice, user_id)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'data': {
                    'response': result.get('response', 'Decision processed successfully'),
                    'workflow_id': workflow.id,
                    'workflow_status': result.get('workflow_status', 'running'),
                    'tool_calls': result.get('tool_calls', []),
                    'tool_results': result.get('tool_results', []),
                    'has_workflow': True
                }
            })
        else:
            return jsonify({'error': result.get('error', 'Failed to process decision')}), 500
        
    except Exception as e:
        logger.error(f"Decision submission failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/workflows/<workflow_id>/cancel', methods=['POST'])
@optional_auth
def cancel_workflow(workflow_id):
    """Cancel a running workflow"""
    try:
        # TODO: Implement workflow cancellation
        return jsonify({
            'success': True,
            'message': 'Workflow cancellation requested'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling workflow: {str(e)}")
        return jsonify({'error': 'Failed to cancel workflow', 'details': str(e)}), 500

@api_bp.route('/execute', methods=['POST'])
def execute_command():
    """Execute command endpoint - simplified interface for command execution"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        command = data.get('command')
        if not command:
            return jsonify({'error': 'Command not provided'}), 400
        
        # Extract optional parameters
        timeout = data.get('timeout', 30)
        working_directory = data.get('working_directory')
        allow_dangerous = data.get('allow_dangerous', False)
        
        # Execute command action
        result = registry.execute_tool_action(
            'command_executor',
            'execute',
            command=command,
            timeout=timeout,
            working_directory=working_directory,
            allow_dangerous=allow_dangerous
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/validate-command', methods=['POST'])
def validate_command():
    """Validate command safety"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        command = data.get('command')
        if not command:
            return jsonify({'error': 'Command not provided'}), 400
        
        # Validate command
        result = registry.execute_tool_action(
            'command_executor',
            'validate',
            command=command
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Command validation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation history"""
    try:
        result = registry.execute_tool_action(
            'llm_tool',
            'get_conversation',
            conversation_id=conversation_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id):
    """Clear conversation history"""
    try:
        result = registry.execute_tool_action(
            'llm_tool',
            'clear_conversation',
            conversation_id=conversation_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to clear conversation {conversation_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/clear', methods=['POST'])
def clear_all_conversations():
    """Clear all conversation history"""
    try:
        # Get LLM tool and clear all conversations
        llm_tool = registry.get_tool('llm_tool')
        if llm_tool and hasattr(llm_tool, 'conversations'):
            llm_tool.conversations.clear()
        
        return jsonify({
            'success': True,
            'message': 'All conversations cleared'
        })
        
    except Exception as e:
        logger.error(f"Failed to clear all conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/providers', methods=['GET'])
def get_providers():
    """Get available LLM providers"""
    try:
        result = registry.execute_tool_action('llm_tool', 'get_providers')
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get providers: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Session Management Endpoints
@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new user session"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        session = session_manager.create_session(user_id)
        
        return jsonify({
            'success': True,
            'session': session.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session information"""
    try:
        session = session_manager.get_session(session_id)
        
        if session:
            return jsonify({
                'success': True,
                'session': session.to_dict()
            })
        else:
            return jsonify({'error': 'Session not found or expired'}), 404
            
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    try:
        success = session_manager.remove_session(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session deleted'
            })
        else:
            return jsonify({'error': 'Session not found'}), 404
            
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<user_id>/sessions', methods=['GET'])
def get_user_sessions(user_id):
    """Get all sessions for a user"""
    try:
        sessions = session_manager.get_user_sessions(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'sessions': [session.to_dict() for session in sessions],
            'total_sessions': len(sessions)
        })
        
    except Exception as e:
        logger.error(f"Failed to get user sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<user_id>/conversations', methods=['GET'])
def get_user_conversations(user_id):
    """Get all conversations for a user"""
    try:
        result = registry.execute_tool_action(
            'llm_tool',
            'get_user_conversations',
            user_id=user_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get user conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        session_stats = session_manager.get_stats()
        
        # Get LLM tool stats
        llm_tool = registry.get_tool('llm_tool')
        conversation_stats = {
            'total_conversations': len(llm_tool.conversations) if llm_tool else 0,
            'total_users_with_conversations': len(llm_tool.user_conversations) if llm_tool else 0
        }
        
        return jsonify({
            'success': True,
            'sessions': session_stats,
            'conversations': conversation_stats,
            'tools': {
                'total_tools': len(registry.tools),
                'tool_names': list(registry.tools.keys())
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/todos', methods=['GET'])
def todo_dashboard():
    """Serve todo dashboard interface"""
    from flask import render_template
    return render_template('todo_dashboard.html')

@api_bp.route('/todos/api/<user_id>', methods=['GET'])
def get_todos_api(user_id):
    """Get todos via API"""
    try:
        from tools.internal.todo_manager import get_todo_tool
        
        todo_tool = get_todo_tool()
        workflow_id = request.args.get('workflow_id')
        
        result = todo_tool.todo_get_all(user_id, workflow_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get todos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/todos/api/<user_id>/clear', methods=['POST'])
def clear_todos_api(user_id):
    """Clear todos via API"""
    try:
        from tools.internal.todo_manager import get_todo_tool
        
        todo_tool = get_todo_tool()
        workflow_id = request.json.get('workflow_id') if request.json else None
        
        result = todo_tool.todo_clear(user_id, workflow_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to clear todos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/compliance/check', methods=['POST'])
def run_compliance_subagent():
    """CLAUDE.md compliance check via subagent"""
    try:
        from tools.internal.compliance_integration_tool import auto_compliance_subagent
        
        # Trigger compliance subagent
        success = auto_compliance_subagent()
        
        return jsonify({
            'success': success,
            'message': 'Compliance check subagent triggered',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Compliance subagent failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/debug/workflow/clear-cache', methods=['POST'])
def clear_workflow_cache():
    """DEBUGGING: Clear workflow cache to force fresh execution"""
    try:
        from .workflow_orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        orchestrator.clear_workflow_cache()
        
        return jsonify({
            'success': True,
            'message': 'Workflow cache cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to clear workflow cache: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@api_bp.route('/generated_images/<filename>')
def serve_generated_image(filename):
    """Serve generated images as static files"""
    try:
        import os
        generated_images_path = os.path.join(os.getcwd(), "generated_images")
        return send_from_directory(generated_images_path, filename)
    except Exception as e:
        logger.error(f"Error serving image {filename}: {str(e)}")
        return jsonify({'error': 'Image not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500