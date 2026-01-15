#!/usr/bin/env python3
"""
MetisAgent3 Bridge Server - Frontend-Backend Connector

CLAUDE.md COMPLIANT:
- Pure proxy layer between React frontend and MetisAgent3 backend  
- NO tool interference - just transparent API bridging
- RESTful API endpoints matching frontend expectations
- Authentication passthrough to MetisAgent3
- WebSocket support for real-time features
- Error handling and logging
- Zero business logic - pure bridge functionality
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
from pathlib import Path

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add project root to Python path  
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import MetisAgent3 core services
from core.managers.user_manager import UserManager
from core.managers.tool_manager import ToolManager
from core.services.conversation_service import ConversationService
from core.services.tool_execution_service import ToolExecutionService, ToolExecutionRequest
from core.services.settings_card_service import SettingsCardService
from core.services.tool_card_discovery_service import ToolCardDiscoveryService
from core.services.persona_service import PersonaService
from core.orchestrator.application_orchestrator import ApplicationOrchestrator
from core.contracts.base_types import ExecutionContext
from core.contracts import ToolMetadata, ToolConfiguration, ToolType, CapabilityType, ToolCapability

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['JSON_SORT_KEYS'] = False

# Enable permissive CORS for development (allow any origin)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# SocketIO event handlers for workflow rooms
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected via WebSocket")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected from WebSocket")

@socketio.on('join_workflow_room')
def handle_join_workflow_room(data):
    user_id = data.get('user_id', 'anonymous')
    room = f"workflow_{user_id}"
    from flask_socketio import join_room, emit
    join_room(room)
    logger.info(f"🏠 Client joined workflow room: {room}")
    emit('room_joined', {'room': room, 'user_id': user_id})

@socketio.on('leave_workflow_room')
def handle_leave_workflow_room(data):
    user_id = data.get('user_id', 'anonymous')
    room = f"workflow_{user_id}"
    from flask_socketio import leave_room, emit
    leave_room(room)
    logger.info(f"🚪 Client left workflow room: {room}")
    emit('room_left', {'room': room, 'user_id': user_id})

class BridgeServer:
    """Pure bridge server between React frontend and MetisAgent3 backend"""
    
    def __init__(self):
        """Initialize bridge server with MetisAgent3 services"""
        self.user_manager = None
        self.tool_manager = None
        self.conversation_service = None
        self.persona_service = None
        self.orchestrator = None
        self.loop = None
        self.initialized = False
        
    def initialize_services_sync(self):
        """Initialize services synchronously"""
        try:
            # Create and store persistent event loop for bridge server
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._initialize_services())
            # Don't close loop - keep it for future async operations
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
    
    async def _initialize_services(self):
        """Initialize MetisAgent3 backend services"""
        try:
            logger.info("🚀 Initializing MetisAgent3 backend services...")
            
            # Initialize core services
            self.user_manager = UserManager()
            self.conversation_service = ConversationService()
            self.persona_service = PersonaService()

            # Initialize application orchestrator first - it creates tool_manager with graph_memory
            from core.storage.sqlite_storage import SQLiteUserStorage
            self.storage = SQLiteUserStorage()
            self.orchestrator = ApplicationOrchestrator(
                storage=self.storage
                # Let orchestrator create its own tool_manager with graph_memory
            )

            # Use orchestrator's tool_manager (has graph_memory for tool sync)
            self.tool_manager = self.orchestrator.tool_manager

            # Initialize tool execution service
            self.tool_execution_service = ToolExecutionService(
                tool_manager=self.tool_manager,
                user_manager=self.user_manager
            )

            # Initialize settings card service with tool discovery
            self.settings_card_service = SettingsCardService(
                tool_execution_service=self.tool_execution_service
            )

            # Initialize card discovery service
            self.card_discovery_service = ToolCardDiscoveryService()
            self.settings_card_service.set_card_discovery_service(self.card_discovery_service)

            # Auto-discover and register all tool cards (async will be called later)
            plugins_directory = str(Path(__file__).parent / "plugins")
            self.plugins_directory = plugins_directory
            self._cards_discovered = False
            
            # CRITICAL: Initialize orchestrator to sync tools to graph memory
            orchestrator_ready = await self.orchestrator.initialize()
            if not orchestrator_ready:
                logger.error("❌ ApplicationOrchestrator initialization failed")
                self.initialized = False
                return
            
            # Tools are now auto-loaded by orchestrator per blueprint specification
            # No manual tool loading needed - orchestrator handles system tools via _init_tool_manager()
            
            self.initialized = True
            
            # Auto-load enabled plugins at startup
            await auto_load_enabled_plugins()
            
            logger.info("✅ Bridge server initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bridge server: {e}")
            self.initialized = False
    
    def is_ready(self) -> bool:
        """Check if bridge server is ready to handle requests"""
        return self.initialized and all([
            self.user_manager,
            self.tool_manager, 
            self.conversation_service,
            self.orchestrator
        ])

    def build_default_capabilities(self, extra: list = None):
        caps = [
            ToolCapability(
                name="invoke",
                description="Invoke remote API capability",
                capability_type=CapabilityType.EXECUTE,
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )
        ]
        if extra:
            caps.extend(extra)
        return caps
    
    def get_user_id_from_email_sync(self, email: str) -> str:
        """Get user_id from email synchronously"""
        try:
            # Run async user lookup in the same event loop
            user_profile = self.loop.run_until_complete(
                self.user_manager.get_user_by_email(email)
            )
            
            if user_profile:
                return user_profile.user_id
            return email  # Fallback to email
            
        except Exception as e:
            logger.warning(f"Failed to get user_id for {email}: {e}")
            return email  # Fallback to email
    
    def lookup_session_sync(self, session_token: str) -> Optional[dict]:
        """Look up user from session token synchronously"""
        try:
            # Run async session lookup in the same event loop
            auth_session = self.loop.run_until_complete(
                self.user_manager.auth_service.validate_session(session_token)
            )
            
            if auth_session:
                # Get user profile synchronously
                user_profile = self.loop.run_until_complete(
                    self.user_manager.get_user(auth_session.user_id)
                )
                
                return {
                    "user_id": auth_session.user_id,
                    "email": user_profile.email if user_profile else auth_session.user_id,
                    "session_id": session_token
                }
            return None
            
        except Exception as e:
            logger.warning(f"Failed to lookup session {session_token[:8]}...: {e}")
            return None
    
    def authenticate_user_sync(self, email: str, password: str) -> dict:
        """Synchronous wrapper for user authentication"""
        try:
            # Run async authentication in the same event loop
            auth_session = self.loop.run_until_complete(
                self.user_manager.auth_service.authenticate_user(email, password)
            )
            
            if auth_session:
                # Get user profile synchronously
                user_profile = self.loop.run_until_complete(
                    self.user_manager.get_user(auth_session.user_id)
                )
                
                return {
                    "success": True,
                    "session": auth_session,
                    "user_profile": user_profile
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Model listing functions
async def get_openai_models(api_key: str) -> List[str]:
    """Get available OpenAI models for the API key"""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models_data = response.json()
            # Filter for chat models and sort by preference
            chat_models = []
            model_priority = [
                "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", 
                "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
            ]
            
            available_models = [model["id"] for model in models_data.get("data", [])]
            
            # Add models in priority order if available
            for model in model_priority:
                if model in available_models:
                    chat_models.append(model)
            
            # Add any other gpt models not in priority list
            for model in available_models:
                if model.startswith("gpt-") and model not in chat_models:
                    chat_models.append(model)
            
            return chat_models[:10]  # Limit to 10 models
        else:
            logger.warning(f"OpenAI models API error: {response.status_code}")
            return ["gpt-4o-mini"]  # Fallback
            
    except Exception as e:
        logger.warning(f"Failed to get OpenAI models: {e}")
        return ["gpt-4o-mini"]  # Fallback


async def get_anthropic_models(api_key: str) -> List[str]:
    """Get available Anthropic models for the API key"""
    try:
        # Anthropic doesn't have a models API endpoint like OpenAI
        # We need to test with a small request to see which models work
        import requests
        
        # Test models in order of preference
        test_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ]
        
        available_models = []
        
        for model in test_models:
            try:
                headers = {
                    "x-api-key": api_key,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                
                payload = {
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "test"}]
                }
                
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=5
                )
                
                if response.status_code in [200, 400]:  # 400 might be rate limit but model exists
                    available_models.append(model)
                    if len(available_models) >= 3:  # Don't test all models, save API calls
                        break
                        
            except Exception:
                continue
        
        return available_models if available_models else ["claude-3-5-sonnet-20241022"]
        
    except Exception as e:
        logger.warning(f"Failed to get Anthropic models: {e}")
        return ["claude-3-5-sonnet-20241022"]  # Fallback


# Global bridge server instance
bridge = BridgeServer()

# Initialize services manually (will be called at startup)
def initialize_bridge():
    """Initialize bridge server services"""
    bridge.initialize_services_sync()


# Health Check Endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Bridge server health check"""
    try:
        is_ready = bridge.is_ready()
        
        status = {
            "status": "healthy" if is_ready else "initializing",
            "bridge_server": "running",
            "metis_agent3_backend": "connected" if is_ready else "initializing", 
            "timestamp": datetime.now().isoformat(),
            "services": {
                "user_manager": bridge.user_manager is not None,
                "tool_manager": bridge.tool_manager is not None,
                "conversation_service": bridge.conversation_service is not None,
                "orchestrator": bridge.orchestrator is not None
            }
        }
        
        return jsonify({
            "success": True,
            "data": status
        }), 200 if is_ready else 503
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Provider Information Endpoint with Real API Key Validation
@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get available LLM providers with real model validation based on user's API keys"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False, 
                "error": "Bridge server not ready"
            }), 503
        
        # Get authenticated user's actual user_id
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def get_real_providers():
            try:
                from core.tools.llm_tool import LLMTool
                llm_tool = LLMTool(storage=bridge.storage)
                
                providers = []
                
                # Check OpenAI
                openai_key = await llm_tool._get_api_key(actual_user_id, "openai")
                if openai_key:
                    openai_models = await get_openai_models(openai_key)
                    providers.append({
                        "id": "openai",
                        "name": "OpenAI", 
                        "available": len(openai_models) > 0,
                        "models": openai_models,
                        "default_model": openai_models[0] if openai_models else "gpt-4o-mini"
                    })
                else:
                    providers.append({
                        "id": "openai",
                        "name": "OpenAI",
                        "available": False,
                        "models": [],
                        "default_model": "gpt-4o-mini"
                    })
                
                # Check Anthropic
                anthropic_key = await llm_tool._get_api_key(actual_user_id, "anthropic")
                if anthropic_key:
                    anthropic_models = await get_anthropic_models(anthropic_key)
                    providers.append({
                        "id": "anthropic",
                        "name": "Anthropic",
                        "available": len(anthropic_models) > 0,
                        "models": anthropic_models,
                        "default_model": anthropic_models[0] if anthropic_models else "claude-3-5-sonnet-20241022"
                    })
                else:
                    providers.append({
                        "id": "anthropic", 
                        "name": "Anthropic",
                        "available": False,
                        "models": [],
                        "default_model": "claude-3-5-sonnet-20241022"
                    })
                
                return {
                    "success": True,
                    "data": providers
                }
                
            except Exception as e:
                logger.error(f"Real providers check error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_real_providers())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get providers error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Authentication Endpoints
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    """Handle login requests"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
            
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        # Use bridge server's synchronous authentication wrapper
        auth_result = bridge.authenticate_user_sync(email, password)
        
        if auth_result["success"]:
            auth_session = auth_result["session"]
            user_profile = auth_result["user_profile"]
            
            # Store user session (both Flask session and return token for localStorage)
            session['user_id'] = auth_session.user_id
            session['email'] = email
            
            return jsonify({
                "success": True,
                "status": "success",  # Frontend expects this
                "user": {
                    "user_id": user_profile.user_id,
                    "email": user_profile.email,
                    "username": user_profile.display_name,
                    "display_name": user_profile.display_name
                },
                "token": auth_session.session_id,
                "session_token": auth_session.session_id  # Frontend expects this field
            })
        else:
            return jsonify({
                "success": False,
                "error": auth_result["error"]
            }), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/validate', methods=['POST', 'OPTIONS'])
def validate():
    """Handle session validation requests"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Check both Flask session and Authorization header
        user_id = session.get('user_id')
        auth_header = request.headers.get('Authorization')
        
        # If we have session or valid token, consider valid
        if user_id or (auth_header and auth_header.startswith('Bearer ')):
            return jsonify({
                "valid": True,
                "user_id": user_id
            })
        else:
            return jsonify({
                "valid": False
            }), 401
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({"valid": False}), 500


@app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    """Handle logout requests"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        session.clear()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    """Handle user registration"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        username = data.get('username', '').strip() or email.split('@')[0]

        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400

        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

        # Create user profile
        from core.contracts import UserProfile
        import asyncio
        import uuid

        new_user_id = str(uuid.uuid4())
        user_profile = UserProfile(
            user_id=new_user_id,
            email=email,
            display_name=username,
            is_active=True,
            created_at=datetime.utcnow(),
            preferences={"theme": "light", "language": "tr"}
        )

        # Create user
        loop = asyncio.new_event_loop()
        try:
            # Check if user exists
            existing_user = loop.run_until_complete(
                bridge.orchestrator.user_manager.get_user_by_email(email)
            )
            if existing_user:
                return jsonify({"success": False, "error": "Email already registered"}), 400

            # Create user
            user_id = loop.run_until_complete(
                bridge.orchestrator.user_manager.create_user(user_profile)
            )

            # Set password
            password_set = loop.run_until_complete(
                bridge.orchestrator.user_manager.set_user_password(new_user_id, password)
            )

            if not password_set:
                logger.warning(f"Failed to set password for user {new_user_id}")
        finally:
            loop.close()

        logger.info(f"User registered successfully: {email}")
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user_id": new_user_id
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/users/<email>', methods=['DELETE'])
def delete_user_by_email(email):
    """Delete a user by email (admin only)"""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            # Get user by email
            user = loop.run_until_complete(
                bridge.orchestrator.user_manager.get_user_by_email(email)
            )
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404

            # Delete user from storage
            storage = bridge.orchestrator.user_manager.storage
            with storage.db.transaction() as conn:
                conn.execute("DELETE FROM users WHERE email = ?", (email,))
                conn.execute("DELETE FROM user_attributes WHERE user_id = ?", (user.user_id,))

            logger.info(f"User deleted: {email}")
            return jsonify({"success": True, "message": f"User {email} deleted"})
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/users/<email>/email', methods=['PUT'])
def update_user_email(email):
    """Update a user's email (admin only)"""
    try:
        data = request.get_json()
        new_email = data.get('new_email', '').strip()
        if not new_email:
            return jsonify({"success": False, "error": "new_email required"}), 400

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            # Get user by current email
            user = loop.run_until_complete(
                bridge.orchestrator.user_manager.get_user_by_email(email)
            )
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404

            # Update email in storage
            storage = bridge.orchestrator.user_manager.storage
            with storage.db.transaction() as conn:
                conn.execute("UPDATE users SET email = ? WHERE user_id = ?", (new_email, user.user_id))

            logger.info(f"User email updated: {email} -> {new_email}")
            return jsonify({"success": True, "message": f"Email updated to {new_email}"})
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Update email error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Chat Endpoint - Main LLM interaction
@app.route('/api/chat', methods=['POST'])
def chat():
    """Bridge chat requests to MetisAgent3 orchestrator"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                "success": False,
                "error": "Message is required"
            }), 400
        
        # Extract frontend parameters
        provider = data.get('provider', 'openai')
        conversation_id = data.get('conversation_id', 'default')
        system_prompt = data.get('system_prompt')
        
        # Select appropriate default model based on provider (and sanitize mismatches)
        model = data.get('model')
        if not model:
            if provider == 'anthropic':
                model = 'claude-3-7-sonnet-latest'  # Default Anthropic model
            else:
                model = 'gpt-4o-mini'  # Default OpenAI model
        else:
            # Guard against provider/model mismatch
            try:
                mlow = str(model).lower()
                if provider == 'openai' and 'claude' in mlow:
                    logger.warning(f"Model/provider mismatch (openai/{model}), normalizing to gpt-4o-mini")
                    model = 'gpt-4o-mini'
                elif provider == 'anthropic' and ('gpt-' in mlow or 'gpt4' in mlow or 'openai' in mlow):
                    logger.warning(f"Model/provider mismatch (anthropic/{model}), normalizing to claude-3-7-sonnet-latest")
                    model = 'claude-3-7-sonnet-latest'
            except Exception:
                pass
        
        # Extract user context from Authorization header or session
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]  # Remove 'Bearer ' prefix
            # Look up user from session token
            auth_result = bridge.lookup_session_sync(session_token)
            if auth_result:
                session_user_id = auth_result.get('user_id', 'anonymous')
                email = auth_result.get('email', session_user_id)
            else:
                session_user_id = 'anonymous'
                email = 'anonymous'
        else:
            # Fallback to Flask session
            session_user_id = session.get('user_id', 'anonymous')
            email = session.get('email', session_user_id)
        
        # Create execution context - map email to internal user_id
        # Priority: request user_id > session user_id > anonymous
        request_user_id = data.get('user_id')
        
        if request_user_id:
            # Use explicit user_id from request
            actual_user_id = request_user_id
        elif '@' in str(email):
            # Convert email to internal user_id if available
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            # Fallback to session user_id
            actual_user_id = session_user_id
        
        # Debug logging for user_id mapping
        logger.info(f"🔍 User ID Mapping: session_user_id={session_user_id}, email={email}, actual_user_id={actual_user_id}")
            
        context = ExecutionContext(
            user_id=actual_user_id,
            session_id=conversation_id,
            conversation_id=conversation_id,
            system_prompt=system_prompt
        )
        
        # Bridge to MetisAgent3 orchestrator
        async def process_chat():
            try:
                # Setup workflow callback for real-time updates
                def workflow_callback(event_type, data):
                    try:
                        # Emit to user-specific room
                        room = f"workflow_{actual_user_id}"
                        socketio.emit(event_type, data, room=room)
                        logger.info(f"📡 WebSocket event sent to room {room}: {event_type}")
                    except Exception as e:
                        logger.error(f"WebSocket emit error: {e}")
                
                result = await bridge.orchestrator.process_user_request(
                    user_request=message,
                    context=context,
                    llm_provider=provider,
                    llm_model=model,
                    system_prompt=system_prompt,
                    workflow_callback=workflow_callback
                )
                
                # Save messages to conversation if successful
                if result.success and result.data.get("response"):
                    try:
                        # Add user message
                        await bridge.conversation_service.add_message(
                            conversation_id=conversation_id,
                            user_id=actual_user_id,
                            role="user",
                            content=message,
                            metadata={"provider": provider, "model": model}
                        )
                        
                        # Add assistant response
                        await bridge.conversation_service.add_message(
                            conversation_id=conversation_id,
                            user_id=actual_user_id,
                            role="assistant",
                            content=result.data.get("response", ""),
                            metadata={
                                "provider": provider,
                                "model": model,
                                "processing_method": result.metadata.get("processing_method", "unknown")
                            }
                        )
                        
                        # Update conversation summary with user message preview
                        user_preview = f"User: {message[:100]}..." if len(message) > 100 else f"User: {message}"
                        if hasattr(bridge.conversation_service, 'update_conversation_summary'):
                            try:
                                await bridge.conversation_service.update_conversation_summary(
                                    conversation_id=conversation_id,
                                    user_id=actual_user_id,
                                    summary=user_preview
                                )
                                logger.info(f"📝 Updated conversation summary: {user_preview}")
                            except Exception as e:
                                logger.warning(f"Summary update failed: {e}")
                        
                        logger.info(f"💾 Saved messages to conversation {conversation_id}")
                        
                    except Exception as msg_error:
                        logger.error(f"Failed to save messages to conversation: {msg_error}")
                
                return {
                    "success": result.success,
                    "data": {
                        "response": result.data.get("response", "") if result.success else "",
                        "conversation_id": conversation_id,
                        "provider": provider,
                        "model": model,
                        "metadata": result.metadata
                    },
                    "error": result.error if not result.success else None
                }
                
            except Exception as e:
                logger.error(f"Chat processing error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute async chat processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_chat())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Tools Endpoint - Get available tools
@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get available tools from MetisAgent3 tool manager"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        async def get_tool_list():
            try:
                tools = await bridge.tool_manager.list_tools()
                tool_info = []
                
                for tool_name in tools:
                    metadata = bridge.tool_manager.registry.get_tool_metadata(tool_name)
                    if metadata:
                        tool_info.append({
                            "name": metadata.name,
                            "description": metadata.description,
                            "version": metadata.version,
                            "type": metadata.tool_type.value,
                            "capabilities": [
                                {
                                    "name": cap.name,
                                    "description": cap.description,
                                    "type": cap.capability_type.value
                                }
                                for cap in metadata.capabilities
                            ],
                            "tags": list(metadata.tags)
                        })
                
                return {
                    "success": True,
                    "data": {
                        "tools": tool_info,
                        "total": len(tool_info)
                    }
                }
                
            except Exception as e:
                logger.error(f"Tool list error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_tool_list())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get tools error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Tools Registration Endpoints (Bridge-managed)
@app.route('/api/tools/register_external', methods=['POST'])
def register_external_tool():
    """Register an API-backed external tool via plugin (no restart required)"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        base_url = (data.get('base_url') or data.get('api_base_url') or '').strip()
        auth = data.get('auth') or {}
        version = (data.get('version') or '1.0.0').strip()
        description = data.get('description') or ''
        tags = set(data.get('tags') or [])
        capabilities_input = data.get('capabilities') or []

        if not name or not base_url:
            return jsonify({"success": False, "error": "name and base_url are required"}), 400

        # Build metadata and config
        metadata = ToolMetadata(
            name=name,
            description=description,
            version=version,
            tool_type=ToolType.PLUGIN,
            capabilities=bridge.build_default_capabilities(),
            tags=tags
        )
        config = ToolConfiguration(
            tool_name=name,
            enabled=True,
            config={
                "plugin_type": "api",
                "api_base_url": base_url,
                "auth": auth
            }
        )

        async def load():
            return await bridge.tool_manager.load_tool(metadata, config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ok = loop.run_until_complete(load())
        loop.close()

        return jsonify({"success": bool(ok)})
    except Exception as e:
        logger.error(f"register_external_tool error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tools/register_remote', methods=['POST'])
def register_remote_tool():
    """Register a remote MCP/API tool via plugin (treated as API proxy)"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        remote_url = (data.get('remote_url') or data.get('base_url') or '').strip()
        auth = data.get('auth') or data.get('auth_info') or {}
        version = (data.get('version') or '1.0.0').strip()
        description = data.get('description') or ''
        tags = set(data.get('tags') or [])

        if not name or not remote_url:
            return jsonify({"success": False, "error": "name and remote_url are required"}), 400

        metadata = ToolMetadata(
            name=name,
            description=description,
            version=version,
            tool_type=ToolType.PLUGIN,
            capabilities=bridge.build_default_capabilities(),
            tags=tags
        )
        config = ToolConfiguration(
            tool_name=name,
            enabled=True,
            config={
                "plugin_type": "api",
                "api_base_url": remote_url,
                "auth": auth
            }
        )

        async def load():
            return await bridge.tool_manager.load_tool(metadata, config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ok = loop.run_until_complete(load())
        loop.close()

        return jsonify({"success": bool(ok)})
    except Exception as e:
        logger.error(f"register_remote_tool error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tools/<tool_name>', methods=['DELETE'])
def delete_tool(tool_name: str):
    """Unload and remove a tool from ToolManager"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        async def unload():
            return await bridge.tool_manager.unload_tool(tool_name)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ok = loop.run_until_complete(unload())
        loop.close()
        return jsonify({"success": bool(ok)})
    except Exception as e:
        logger.error(f"delete_tool error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Tool Execution Endpoint
@app.route('/api/tools/<tool_name>/execute', methods=['POST'])
def execute_tool(tool_name):
    """Execute specific tool capability via MetisAgent3"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        action = data.get('action')  # capability name
        params = data.get('params', {})
        
        if not action:
            return jsonify({
                "success": False,
                "error": "Action (capability) is required"
            }), 400
        
        # Create execution context
        user_id = session.get('user_id', 'anonymous')
        context = ExecutionContext(
            user_id=user_id,
            session_id=f"tool_{tool_name}_{action}",
        )
        
        async def execute_tool_capability():
            try:
                # Get tool instance
                tool_instance = bridge.tool_manager.tools.get(tool_name)
                if not tool_instance:
                    return {
                        "success": False,
                        "error": f"Tool '{tool_name}' not found"
                    }
                
                # Execute capability
                result = await tool_instance.execute(action, params, context)
                
                return {
                    "success": result.success,
                    "data": result.data if result.success else None,
                    "error": result.error if not result.success else None,
                    "metadata": result.metadata
                }
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_tool_capability())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Execute tool error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Conversation Management
@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """List all conversations for user"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Get authenticated user's actual user_id
        # Priority: request user_id > session user_id > anonymous
        request_user_id = request.args.get('user_id')
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if request_user_id:
            actual_user_id = request_user_id
        elif '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
        
        async def get_conversations():
            try:
                logger.info(f"📋 Listing conversations for user_id: {actual_user_id}")
                # Get all conversations for user
                conversations = await bridge.conversation_service.list_conversations(actual_user_id)
                
                # Transform to frontend format
                conversation_list = []
                for conv in conversations:
                    # Extract ConversationThread attributes properly
                    conv_id = getattr(conv, 'id', None)
                    conv_title = getattr(conv, 'title', f"Conversation {str(conv_id)[:8]}..." if conv_id else "Untitled")
                    conv_created = getattr(conv, 'first_message_at', None)
                    conv_updated = getattr(conv, 'last_message_at', None)
                    conv_messages = getattr(conv, 'total_messages', 0)
                    conv_summary = getattr(conv, 'summary', None)
                    
                    # Format dates if they exist
                    created_str = conv_created.isoformat() if conv_created else None
                    updated_str = conv_updated.isoformat() if conv_updated else None
                    
                    conversation_list.append({
                        'id': conv_id,
                        'title': conv_title,
                        'created_at': created_str,
                        'updated_at': updated_str,
                        'message_count': conv_messages,
                        'preview': conv_summary[:100] + '...' if conv_summary else 'No messages'
                    })
                
                return {
                    "success": True,
                    "data": {
                        "conversations": conversation_list,
                        "total": len(conversation_list)
                    }
                }
                
            except Exception as e:
                logger.error(f"Failed to get conversations: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute async conversation fetching
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_conversations())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Conversation list endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation history"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Get authenticated user's actual user_id
        # Priority: request user_id > session user_id > anonymous
        request_user_id = request.args.get('user_id')
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if request_user_id:
            user_id = request_user_id
        elif '@' in str(email):
            user_id = bridge.get_user_id_from_email_sync(email)
            logger.info(f"📧 Email {email} mapped to user_id: {user_id}")
        else:
            user_id = session_user_id
        
        logger.info(f"📋 Final user_id for conversation lookup: {user_id}")
        
        async def get_conversation_data():
            try:
                logger.info(f"📚 Getting conversation {conversation_id} for user {user_id}")
                # Get conversation metadata
                conversation = await bridge.conversation_service.get_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id
                )
                logger.info(f"📚 Conversation found: {conversation is not None}")
                
                # Get conversation messages
                messages = await bridge.conversation_service.get_messages(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    limit=100  # Last 100 messages
                )
                
                if conversation:
                    # Format messages for frontend
                    formatted_messages = []
                    for msg in messages:
                        formatted_messages.append({
                            "role": getattr(msg, 'role', 'user'),
                            "content": getattr(msg, 'content', ''),
                            "timestamp": getattr(msg, 'created_at', '').isoformat() if hasattr(getattr(msg, 'created_at', ''), 'isoformat') else str(getattr(msg, 'created_at', '')),
                            "metadata": getattr(msg, 'metadata', {})
                        })
                    
                    return {
                        "success": True,
                        "data": {
                            "conversation_id": conversation_id,
                            "messages": formatted_messages,
                            "metadata": {
                                "title": getattr(conversation, 'title', ''),
                                "created_at": getattr(conversation, 'first_message_at', ''),
                                "updated_at": getattr(conversation, 'last_message_at', ''),
                                "total_messages": len(formatted_messages)
                            }
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Conversation not found"
                    }
                    
            except Exception as e:
                logger.error(f"Get conversation error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_conversation_data())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get conversation endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id):
    """Clear conversation history"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        user_id = session.get('user_id', 'anonymous')
        
        async def clear_conversation_data():
            try:
                success = await bridge.conversation_service.clear_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                
                return {
                    "success": success,
                    "message": f"Conversation {conversation_id} cleared" if success else "Failed to clear conversation"
                }
                
            except Exception as e:
                logger.error(f"Clear conversation error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(clear_conversation_data())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Clear conversation endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/oauth2/google/callback', methods=['GET'])
def google_oauth2_callback():
    """Handle Google OAuth2 callback for Google Tool plugin"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"OAuth2 callback error: {error}")
            return f"<html><body><h2>Authentication Error</h2><p>{error}</p></body></html>", 400
        
        if not code:
            logger.error("OAuth2 callback missing authorization code")
            return "<html><body><h2>Authentication Error</h2><p>Missing authorization code</p></body></html>", 400
        
        # Store OAuth2 tokens using Google Tool
        try:
            # Get user from session (fallback to default user)
            session_user_id = session.get('user_id', 'anonymous')
            email = session.get('email', session_user_id)
            
            if '@' in str(email):
                actual_user_id = bridge.get_user_id_from_email_sync(email)
            else:
                actual_user_id = session_user_id
            
            async def store_token():
                try:
                    # Get Google Tool instance  
                    google_tool = bridge.tool_manager.tools.get('google_tool')
                    if not google_tool:
                        return False, "Google Tool not available"
                    
                    # Create execution context
                    context = ExecutionContext(user_id=actual_user_id)
                    
                    # Store OAuth2 token
                    result = await google_tool.execute(
                        {
                            'capability': 'oauth2_management',
                            'action': 'store_token',
                            'code': code,
                            'user_id': actual_user_id
                        },
                        context
                    )
                    
                    if result.get('success'):
                        return True, result.get('message', 'Token stored successfully')
                    else:
                        return False, result.get('error', 'Unknown error')
                        
                except Exception as e:
                    logger.error(f"Token storage error: {e}")
                    return False, str(e)
            
            # Execute async token storage
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(store_token())
            loop.close()
            
            if success:
                logger.info(f"✅ OAuth2 tokens stored successfully for user {actual_user_id}")
                status_class = "success"
                status_icon = "✅"
                status_message = "Google Authentication Successful!"
                detail_message = "Your Google credentials have been securely stored."
            else:
                logger.error(f"❌ Failed to store OAuth2 tokens: {message}")
                status_class = "error"
                status_icon = "❌"
                status_message = "Authentication Storage Failed"
                detail_message = f"Error: {message}"
                
        except Exception as e:
            logger.error(f"OAuth2 callback processing error: {e}")
            status_class = "error"
            status_icon = "❌"
            status_message = "Authentication Processing Failed"
            detail_message = f"Error: {str(e)}"
        
        return f"""
        <html>
        <head>
            <title>Google Authentication</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .info {{ color: #666; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h2 class="{status_class}">{status_icon} {status_message}</h2>
            <p>You can now close this window and return to MetisAgent3.</p>
            <p class="info">{detail_message}</p>
            <script>
                // Auto-close after 5 seconds
                setTimeout(() => window.close(), 5000);
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}")
        return f"<html><body><h2>Authentication Error</h2><p>{str(e)}</p></body></html>", 500


# Plugin Management Endpoints
@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    """List available and installed plugins"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Get available plugins from plugins directory
        plugins_dir = Path("./plugins")
        available_plugins = []
        
        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir() and (plugin_dir / "manifest.json").exists():
                    try:
                        with open(plugin_dir / "manifest.json", 'r') as f:
                            manifest = json.load(f)
                        
                        # Check if plugin is registered in tool manager
                        plugin_name = manifest.get("name")
                        is_installed = plugin_name in bridge.orchestrator.tool_manager.tools
                        
                        plugin_info = {
                            "name": plugin_name,
                            "display_name": manifest.get("display_name", plugin_name),
                            "description": manifest.get("description", ""),
                            "version": manifest.get("version", "1.0.0"),
                            "author": manifest.get("author", "Unknown"),
                            "tags": manifest.get("tags", []),
                            "capabilities": [cap.get("name") for cap in manifest.get("capabilities", [])],
                            "is_installed": is_installed,
                            "is_enabled": is_installed,  # For now, installed = enabled
                            "plugin_path": str(plugin_dir),
                            "dependencies": manifest.get("dependencies", [])
                        }
                        
                        available_plugins.append(plugin_info)
                        
                    except Exception as e:
                        logger.warning(f"Failed to load plugin manifest {plugin_dir}: {e}")
                        continue
        
        return jsonify({
            "success": True,
            "plugins": available_plugins,
            "count": len(available_plugins),
            "message": f"Found {len(available_plugins)} available plugins"
        })
        
    except Exception as e:
        logger.error(f"List plugins error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to list plugins"
        }), 500


@app.route('/api/plugins/<plugin_name>/install', methods=['POST'])
def install_plugin(plugin_name):
    """Install/Register a plugin"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Check if plugin exists
        plugin_dir = Path("./plugins") / plugin_name
        manifest_file = plugin_dir / "manifest.json"
        config_file = plugin_dir / "tool_config.json"
        
        if not manifest_file.exists():
            return jsonify({
                "success": False,
                "error": f"Plugin {plugin_name} not found",
                "message": "Plugin manifest not found"
            }), 404
        
        async def register_plugin():
            try:
                # Load plugin configuration
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    tool_meta = config_data.get("tool_metadata", manifest)
                    tool_config = config_data.get("tool_configuration", {})
                else:
                    tool_meta = manifest
                    tool_config = {
                        "tool_name": plugin_name,
                        "enabled": True,
                        "config": manifest.get("configuration_schema", {})
                    }
                
                # Create tool metadata
                from core.contracts import ToolMetadata, ToolConfiguration, ToolCapability, CapabilityType, ToolType
                
                capabilities = []
                for cap_data in tool_meta.get("capabilities", []):
                    capability = ToolCapability(
                        name=cap_data["name"],
                        description=cap_data["description"],
                        capability_type=CapabilityType(cap_data["capability_type"]),
                        input_schema=cap_data.get("input_schema", {}),
                        output_schema=cap_data.get("output_schema", {}),
                        required_permissions=cap_data.get("required_permissions", []),
                        examples=cap_data.get("examples", [])
                    )
                    capabilities.append(capability)
                
                metadata = ToolMetadata(
                    name=tool_meta["name"],
                    description=tool_meta["description"],
                    version=tool_meta["version"],
                    tool_type=ToolType(tool_meta.get("tool_type", "plugin")),
                    author=tool_meta.get("author"),
                    capabilities=capabilities,
                    dependencies=tool_meta.get("dependencies", []),
                    tags=set(tool_meta.get("tags", []))
                )
                
                # Create tool configuration
                configuration = ToolConfiguration(
                    tool_name=tool_config.get("tool_name", plugin_name),
                    enabled=tool_config.get("enabled", True),
                    config=tool_config.get("config", {}),
                    user_permissions=tool_config.get("user_permissions", []),
                    rate_limits=tool_config.get("rate_limits", {})
                )
                
                # Load tool with tool manager
                success = await bridge.orchestrator.tool_manager.load_tool(metadata, configuration)
                
                if success:
                    # Check health
                    health = await bridge.orchestrator.tool_manager.check_tool_health(plugin_name)
                    capabilities = await bridge.orchestrator.tool_manager.get_tool_capabilities(plugin_name)
                    
                    return {
                        "success": True,
                        "plugin_name": plugin_name,
                        "health": health.value if hasattr(health, 'value') else str(health),
                        "capabilities": capabilities,
                        "message": f"Plugin {plugin_name} installed successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Registration failed",
                        "message": f"Failed to register plugin {plugin_name}"
                    }
                
            except Exception as e:
                logger.error(f"Plugin registration error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Plugin registration failed: {str(e)}"
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(register_plugin())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Install plugin error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to install plugin {plugin_name}"
        }), 500


@app.route('/api/plugins/<plugin_name>/uninstall', methods=['POST'])
def uninstall_plugin(plugin_name):
    """Uninstall/Unregister a plugin"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        async def unregister_plugin():
            try:
                # Unload from tool manager
                success = await bridge.orchestrator.tool_manager.unload_tool(plugin_name)
                
                return {
                    "success": success,
                    "plugin_name": plugin_name,
                    "message": f"Plugin {plugin_name} uninstalled" if success else f"Failed to uninstall {plugin_name}"
                }
                
            except Exception as e:
                logger.error(f"Plugin unregistration error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Plugin uninstallation failed: {str(e)}"
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(unregister_plugin())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Uninstall plugin error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to uninstall plugin {plugin_name}"
        }), 500


@app.route('/api/plugins/<plugin_name>/configure', methods=['POST'])
def configure_plugin(plugin_name):
    """Configure plugin settings"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No configuration data provided"
            }), 400
        
        config_updates = data.get('config', {})
        
        async def update_plugin_config():
            try:
                # Get current tool configuration
                tool = bridge.orchestrator.tool_manager.tools.get(plugin_name)
                if not tool:
                    return {
                        "success": False,
                        "error": f"Plugin {plugin_name} not found"
                    }
                
                # Update configuration
                current_config = tool.config.config.copy()
                current_config.update(config_updates)
                
                # Create updated configuration
                from core.contracts import ToolConfiguration
                updated_config = ToolConfiguration(
                    tool_name=plugin_name,
                    enabled=tool.config.enabled,
                    config=current_config,
                    user_permissions=tool.config.user_permissions,
                    rate_limits=tool.config.rate_limits
                )
                
                # Update tool configuration
                tool.config = updated_config
                
                return {
                    "success": True,
                    "plugin_name": plugin_name,
                    "updated_config": current_config,
                    "message": f"Plugin {plugin_name} configured successfully"
                }
                
            except Exception as e:
                logger.error(f"Plugin configuration error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Plugin configuration failed: {str(e)}"
                }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(update_plugin_config())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Configure plugin error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to configure plugin {plugin_name}"
        }), 500


# ==========================================
# Persona Management Endpoints
# ==========================================

@app.route('/api/personas', methods=['GET'])
def get_personas():
    """Get all personas"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        user_id = session.get('user_id', 'anonymous')
        personas = bridge.persona_service.get_all_personas(user_id)

        return jsonify({
            "success": True,
            "data": [p.to_dict() for p in personas],
            "count": len(personas),
            "message": f"Found {len(personas)} personas"
        })
    except Exception as e:
        logger.error(f"Get personas error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Get specific persona by ID"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        persona = bridge.persona_service.get_persona(persona_id)
        if persona:
            return jsonify({
                "success": True,
                "data": persona.to_dict(),
                "message": f"Found persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Get persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas', methods=['POST'])
def create_persona():
    """Create new persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        user_id = session.get('user_id', 'anonymous')

        persona = bridge.persona_service.create_persona(
            name=data.get('name', 'New Persona'),
            user_id=user_id,
            persona_id=data.get('id'),
            description=data.get('description', ''),
            avatar=data.get('avatar', '🤖'),
            capabilities=data.get('capabilities', []),
            config=data.get('config', {})
        )

        return jsonify({
            "success": True,
            "data": persona.to_dict(),
            "message": f"Created persona: {persona.id}"
        }), 201
    except Exception as e:
        logger.error(f"Create persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>', methods=['PUT'])
def update_persona(persona_id):
    """Update persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        persona = bridge.persona_service.update_persona(
            persona_id=persona_id,
            name=data.get('name'),
            description=data.get('description'),
            avatar=data.get('avatar'),
            capabilities=data.get('capabilities'),
            config=data.get('config')
        )

        if persona:
            return jsonify({
                "success": True,
                "data": persona.to_dict(),
                "message": f"Updated persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Update persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>', methods=['DELETE'])
def delete_persona(persona_id):
    """Delete persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        deleted = bridge.persona_service.delete_persona(persona_id)
        if deleted:
            return jsonify({
                "success": True,
                "message": f"Deleted persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found or cannot be deleted: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Delete persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/status', methods=['GET'])
def get_persona_status(persona_id):
    """Get persona status"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        status = bridge.persona_service.get_persona_status(persona_id)
        if status:
            return jsonify({
                "success": True,
                "data": status,
                "message": f"Status for persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Get persona status error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/start', methods=['POST'])
def start_persona(persona_id):
    """Start persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        persona = bridge.persona_service.set_persona_status(persona_id, "active")
        if persona:
            return jsonify({
                "success": True,
                "data": {"status": "active"},
                "message": f"Started persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Start persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/stop', methods=['POST'])
def stop_persona(persona_id):
    """Stop persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        persona = bridge.persona_service.set_persona_status(persona_id, "inactive")
        if persona:
            return jsonify({
                "success": True,
                "data": {"status": "inactive"},
                "message": f"Stopped persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Stop persona error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/data', methods=['GET'])
def get_persona_data(persona_id):
    """Get persona data"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        persona = bridge.persona_service.get_persona(persona_id)
        if persona:
            return jsonify({
                "success": True,
                "data": persona.to_dict(),
                "message": f"Data for persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Get persona data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/data', methods=['POST'])
def update_persona_data(persona_id):
    """Update persona data"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        update_data = data.get('data', data)
        persona = bridge.persona_service.update_persona(
            persona_id=persona_id,
            name=update_data.get('name'),
            description=update_data.get('description'),
            avatar=update_data.get('avatar'),
            capabilities=update_data.get('capabilities'),
            config=update_data.get('config')
        )

        if persona:
            return jsonify({
                "success": True,
                "data": persona.to_dict(),
                "message": f"Updated persona: {persona_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404
    except Exception as e:
        logger.error(f"Update persona data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/personas/<persona_id>/execute-task', methods=['POST'])
def execute_persona_task(persona_id):
    """Execute task with persona"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json()
        if not data or not data.get('task'):
            return jsonify({"success": False, "error": "Task is required"}), 400

        persona = bridge.persona_service.get_persona(persona_id)
        if not persona:
            return jsonify({
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }), 404

        user_id = session.get('user_id', 'anonymous')
        task_data = data.get('task')

        # Create task record
        task = bridge.persona_service.create_task(
            persona_id=persona_id,
            user_id=user_id,
            task_type=task_data.get('type', 'general'),
            task_data=task_data
        )

        # Update task as completed (actual execution would happen here)
        bridge.persona_service.update_task(
            task_id=task.id,
            status="completed",
            result={"message": f"Task executed by {persona.name}"}
        )

        return jsonify({
            "success": True,
            "data": task.to_dict(),
            "message": f"Task executed with persona: {persona_id}"
        })
    except Exception as e:
        logger.error(f"Execute persona task error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/a2a/task', methods=['POST'])
def execute_a2a_task():
    """Execute A2A protocol task"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503

        data = request.get_json()
        if not data or not data.get('task'):
            return jsonify({"success": False, "error": "Task is required"}), 400

        task_data = data.get('task')
        context = data.get('context', {})
        target_persona = data.get('target_persona', 'assistant')

        persona = bridge.persona_service.get_persona(target_persona)
        if not persona:
            return jsonify({
                "success": False,
                "error": f"Target persona not found: {target_persona}"
            }), 404

        user_id = session.get('user_id', 'anonymous')

        # Create task record
        task = bridge.persona_service.create_task(
            persona_id=target_persona,
            user_id=user_id,
            task_type="a2a",
            task_data={"task": task_data, "context": context}
        )

        # Update task as completed
        bridge.persona_service.update_task(
            task_id=task.id,
            status="completed",
            result={"message": f"A2A task routed to {persona.name}"}
        )

        return jsonify({
            "success": True,
            "data": task.to_dict(),
            "message": "A2A task executed successfully"
        })
    except Exception as e:
        logger.error(f"Execute A2A task error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# API Key Management Endpoints
@app.route('/api/api-keys/<provider>', methods=['POST'])
def save_api_key(provider):
    """Save API key for provider"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        data = request.get_json()
        if not data or not data.get('api_key'):
            return jsonify({"success": False, "error": "API key is required"}), 400
        
        api_key = data.get('api_key').strip()
        
        # Get authenticated user's actual user_id
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def save_key():
            try:
                # Map provider to storage key name
                provider_key_map = {
                    'openai': 'api_key_openai',
                    'anthropic': 'anthropic_api_key'
                }
                
                if provider not in provider_key_map:
                    return {"success": False, "error": f"Provider '{provider}' not supported"}
                
                key_name = provider_key_map[provider]
                await bridge.storage.set_user_attribute(actual_user_id, key_name, api_key)
                
                return {"success": True, "message": f"{provider.title()} API key saved"}
                
            except Exception as e:
                logger.error(f"Save API key error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(save_key())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Save API key error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/api-keys/<provider>', methods=['DELETE'])
def delete_api_key(provider):
    """Delete API key for provider"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user's actual user_id
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def delete_key():
            try:
                # Map provider to storage key name
                provider_key_map = {
                    'openai': 'api_key_openai',
                    'anthropic': 'anthropic_api_key'
                }
                
                if provider not in provider_key_map:
                    return {"success": False, "error": f"Provider '{provider}' not supported"}
                
                key_name = provider_key_map[provider]
                await bridge.storage.delete_user_attribute(actual_user_id, key_name)
                
                return {"success": True, "message": f"{provider.title()} API key deleted"}
                
            except Exception as e:
                logger.error(f"Delete API key error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(delete_key())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Delete API key error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/api-keys/<provider>/test', methods=['POST'])
def test_api_key(provider):
    """Test API key validity for provider"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user's actual user_id
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def test_key():
            try:
                from core.tools.llm_tool import LLMTool
                llm_tool = LLMTool(storage=bridge.storage)
                
                api_key = await llm_tool._get_api_key(actual_user_id, provider)
                
                if not api_key:
                    return {"success": False, "error": f"No API key found for {provider}"}
                
                # Test the key by getting models
                if provider == 'openai':
                    models = await get_openai_models(api_key)
                elif provider == 'anthropic':
                    models = await get_anthropic_models(api_key)
                else:
                    return {"success": False, "error": f"Provider '{provider}' not supported"}
                
                if len(models) > 0:
                    return {
                        "success": True, 
                        "message": f"{provider.title()} API key is valid",
                        "models": models
                    }
                else:
                    return {"success": False, "error": f"{provider.title()} API key is invalid"}
                
            except Exception as e:
                logger.error(f"Test API key error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_key())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test API key error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Active Workflows Endpoint
@app.route('/api/workflows', methods=['GET'])
def get_active_workflows():
    """Get currently active workflows"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Get recent completed workflows to show as "recently completed"
        # Since workflows complete very quickly, show recent ones in active view
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            user_id = bridge.get_user_id_from_email_sync(email)
        else:
            user_id = session_user_id
        
        # Get last 5 workflows to show as "recently completed"
        recent_workflows = bridge.orchestrator.get_workflow_history(user_id=user_id, limit=5)
        
        # Format for active workflows view (with completed status)
        active_workflows = []
        for workflow in recent_workflows:
            active_workflows.append({
                "id": workflow["workflow_id"],
                "name": workflow["user_request"][:50] + ("..." if len(workflow["user_request"]) > 50 else ""),
                "status": workflow["status"],
                "progress": 100 if workflow["status"] == "completed" else 0,
                "steps_total": len(workflow["steps"]),
                "steps_completed": len([s for s in workflow["steps"] if s["status"] == "completed"]),
                "start_time": workflow["start_time"],
                "duration_ms": workflow["duration_ms"],
                "user_request": workflow["user_request"],
                "steps": workflow["steps"]
            })
        
        return jsonify({
            "success": True,
            "data": {
                "workflows": active_workflows,
                "total": len(active_workflows)
            }
        })
        
    except Exception as e:
        logger.error(f"Get active workflows error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Workflow History Endpoint
@app.route('/api/workflows/history', methods=['GET'])
def get_workflow_history():
    """Get completed workflow history with step-by-step details"""
    try:
        if not bridge.is_ready():
            return jsonify({
                "success": False,
                "error": "Bridge server not ready"
            }), 503
        
        # Get query parameters
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 20))
        
        # Get session user if no user_id provided
        if not user_id:
            session_user_id = session.get('user_id', 'anonymous')
            email = session.get('email', session_user_id)
            
            if '@' in str(email):
                user_id = bridge.get_user_id_from_email_sync(email)
            else:
                user_id = session_user_id
        
        # Get workflow history from orchestrator
        workflows = bridge.orchestrator.get_workflow_history(user_id=user_id, limit=limit)
        
        return jsonify({
            "success": True,
            "data": {
                "workflows": workflows,
                "total": len(workflows),
                "user_id": user_id
            }
        })
        
    except Exception as e:
        logger.error(f"Get workflow history error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# WebSocket Events for Real-time Features
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('Client connected via WebSocket')
    emit('status', {'message': 'Connected to MetisAgent3 Bridge Server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('Client disconnected from WebSocket')


@socketio.on('chat_message')
def handle_websocket_chat(data):
    """Handle real-time chat via WebSocket"""
    try:
        if not bridge.is_ready():
            emit('error', {'message': 'Bridge server not ready'})
            return
        
        message = data.get('message', '').strip()
        if not message:
            emit('error', {'message': 'Message is required'})
            return
        
        # This would process the chat message asynchronously
        # and emit updates back to the client
        emit('chat_response', {
            'message': f'Received: {message}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket chat error: {e}")
        emit('error', {'message': str(e)})


def create_app():
    """Create and configure Flask application"""
    return app


# Google OAuth2 Settings Endpoints (via Google Tool)
@app.route('/api/settings/auth/google/login', methods=['POST'])
def google_oauth_login():
    """Start Google OAuth2 flow via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def start_oauth():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"success": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Call OAuth2 management capability
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'authorize',
                        'user_id': actual_user_id
                    },
                    context
                )
                
                if result.get('success'):
                    return {
                        "success": True,
                        "auth_url": result.get('auth_url'),
                        "message": result.get('message', 'OAuth flow started')
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', 'Unknown error')
                    }
                    
            except Exception as e:
                logger.error(f"Google OAuth start error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(start_oauth())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google OAuth login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/auth/status', methods=['GET'])
def google_oauth_status():
    """Check Google OAuth2 status via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def check_status():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"authenticated": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Call OAuth2 management capability
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'check_status',
                        'user_id': actual_user_id
                    },
                    context
                )
                
                if result.get('success'):
                    return {
                        "authenticated": result.get('authenticated', False),
                        "message": result.get('message', ''),
                        "user": result.get('user', {"email": actual_user_id}),
                        "expires_at": result.get('expiry')
                    }
                else:
                    return {
                        "authenticated": False,
                        "error": result.get('error', 'Unknown error')
                    }
                    
            except Exception as e:
                logger.error(f"Google OAuth status error: {e}")
                return {"authenticated": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(check_status())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google OAuth status error: {e}")
        return jsonify({"authenticated": False, "error": str(e)}), 500


@app.route('/api/settings/auth/logout', methods=['POST'])
def google_oauth_logout():
    """Disconnect Google OAuth2 via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def revoke_oauth():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"success": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Call OAuth2 management capability
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'revoke',
                        'user_id': actual_user_id
                    },
                    context
                )
                
                if result.get('success'):
                    return {
                        "success": True,
                        "message": result.get('message', 'OAuth disconnected')
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', 'Unknown error')
                    }
                    
            except Exception as e:
                logger.error(f"Google OAuth revoke error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(revoke_oauth())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google OAuth logout error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/auth/google/mapping', methods=['GET'])
def get_google_user_mapping():
    """Get Google user mapping via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def get_mapping():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"success": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Get user mapping
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'get_user_mapping',
                        'user_id': actual_user_id
                    },
                    context
                )
                
                return result
                    
            except Exception as e:
                logger.error(f"Google user mapping get error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_mapping())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google user mapping error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/auth/google/mapping', methods=['POST'])
def set_google_user_mapping():
    """Set Google user mapping via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request data is required"}), 400
        
        google_email = data.get('google_email', '').strip()
        google_name = data.get('google_name', '').strip()
        
        if not google_email:
            return jsonify({"success": False, "error": "Google email is required"}), 400
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def set_mapping():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"success": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Set user mapping
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'set_user_mapping',
                        'user_id': actual_user_id,
                        'google_email': google_email,
                        'google_name': google_name
                    },
                    context
                )
                
                return result
                    
            except Exception as e:
                logger.error(f"Google user mapping set error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(set_mapping())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google user mapping set error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/auth/google/mapping', methods=['DELETE'])
def delete_google_user_mapping():
    """Delete Google user mapping via Google Tool"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
            
        async def delete_mapping():
            try:
                # Get Google Tool instance
                google_tool = bridge.tool_manager.tools.get('google_tool')
                if not google_tool:
                    return {"success": False, "error": "Google Tool not available"}
                
                # Create execution context
                context = ExecutionContext(user_id=actual_user_id)
                
                # Delete user mapping
                result = await google_tool.execute(
                    {
                        'capability': 'oauth2_management',
                        'action': 'delete_user_mapping',
                        'user_id': actual_user_id
                    },
                    context
                )
                
                return result
                    
            except Exception as e:
                logger.error(f"Google user mapping delete error: {e}")
                return {"success": False, "error": str(e)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(delete_mapping())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Google user mapping delete error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Generic Tool Execution Endpoint  
@app.route('/api/tools/execute', methods=['POST'])
def execute_tool_capability():
    """Generic tool execution endpoint - handles all tool capability executions"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request data is required"}), 400
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
        
        # Extract action from parameters if not directly provided
        parameters = data.get('parameters', {})
        action = data.get('action', '').strip()
        if not action and 'action' in parameters:
            action = parameters.get('action', '').strip()
        
        # Create tool execution request
        tool_request = ToolExecutionRequest(
            tool_name=data.get('tool_name', '').strip(),
            capability=data.get('capability', '').strip(),
            action=action,
            parameters=parameters,
            user_id=actual_user_id
        )
        
        # Debug logging
        logger.info(f"Tool execution request: tool_name={tool_request.tool_name}, capability={tool_request.capability}, action={tool_request.action}, parameters={tool_request.parameters}")
        
        async def execute_tool():
            """Execute tool capability asynchronously"""
            return await bridge.tool_execution_service.execute_tool_capability(tool_request)
        
        # Execute tool capability
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_tool())
        loop.close()
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Generic tool execution error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "tool_name": data.get('tool_name', 'unknown') if 'data' in locals() else 'unknown',
            "capability": data.get('capability', 'unknown') if 'data' in locals() else 'unknown',
            "action": data.get('action', 'unknown') if 'data' in locals() else 'unknown'
        }), 500


@app.route('/api/tools/available', methods=['GET'])
def get_available_tools():
    """Get list of available tools and their capabilities"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        tools = bridge.tool_execution_service.get_available_tools()
        
        return jsonify({
            "success": True,
            "tools": tools,
            "count": len(tools)
        })
        
    except Exception as e:
        logger.error(f"Get available tools error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Settings Cards Endpoints
@app.route('/api/settings/cards', methods=['GET'])
def get_settings_cards():
    """Get user's settings cards with optional category filtering"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
        
        # Get category filter from query params
        category = request.args.get('category', 'all')
        
        async def get_cards():
            """Get settings cards asynchronously"""
            # Discover cards on first request
            if not bridge._cards_discovered:
                await bridge.settings_card_service.discover_and_register_tool_cards(
                    bridge.plugins_directory, bridge.tool_manager
                )
                bridge._cards_discovered = True
            
            return await bridge.settings_card_service.get_user_cards(actual_user_id, category)
        
        # Execute card retrieval
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cards = loop.run_until_complete(get_cards())
        loop.close()
        
        return jsonify({
            "success": True,
            "cards": cards,
            "category": category,
            "user_id": actual_user_id
        })
        
    except Exception as e:
        logger.error(f"Get settings cards error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/cards/categories', methods=['GET'])
def get_card_categories():
    """Get available settings card categories"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        # Discover cards if not done yet
        if not bridge._cards_discovered:
            async def discover_cards():
                await bridge.settings_card_service.discover_and_register_tool_cards(
                    bridge.plugins_directory, bridge.tool_manager
                )
                bridge._cards_discovered = True
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(discover_cards())
            loop.close()
        
        categories = bridge.settings_card_service.get_card_categories()
        
        return jsonify({
            "success": True,
            "categories": categories
        })
        
    except Exception as e:
        logger.error(f"Get card categories error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/settings/cards/<card_id>/action/<action_id>', methods=['POST'])
def execute_card_action(card_id, action_id):
    """Execute a settings card action"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        data = request.get_json() or {}
        parameters = data.get('parameters', {})
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
        
        async def execute_action():
            """Execute card action asynchronously"""
            return await bridge.settings_card_service.execute_card_action(
                card_id, action_id, actual_user_id, parameters
            )
        
        # Execute card action
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_action())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Execute card action error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "card_id": card_id,
            "action_id": action_id
        }), 500


@app.route('/api/settings/cards/<card_id>/save', methods=['POST'])
def save_card_values(card_id):
    """Save settings card form values"""
    try:
        if not bridge.is_ready():
            return jsonify({"success": False, "error": "Bridge server not ready"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request data is required"}), 400
        
        values = data.get('values', {})
        
        # Get authenticated user ID
        session_user_id = session.get('user_id', 'anonymous')
        email = session.get('email', session_user_id)
        
        if '@' in str(email):
            actual_user_id = bridge.get_user_id_from_email_sync(email)
        else:
            actual_user_id = session_user_id
        
        async def save_values():
            """Save card values asynchronously"""
            return await bridge.settings_card_service.save_card_values(
                card_id, values, actual_user_id
            )
        
        # Execute card save
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(save_values())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Save card values error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "card_id": card_id
        }), 500


async def auto_load_enabled_plugins():
    """Auto-load all enabled plugins at startup"""
    try:
        logger.info("🔌 Auto-loading enabled plugins...")
        
        plugins_dir = Path("./plugins")
        if not plugins_dir.exists():
            return
        
        loaded_count = 0
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('.'):
                manifest_file = plugin_dir / "manifest.json"
                if manifest_file.exists():
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    if manifest.get("enabled", False):
                        plugin_name = manifest.get("name", plugin_dir.name)
                        logger.info(f"Loading enabled plugin: {plugin_name}")
                        
                        # Use the same logic as install_plugin
                        success = await load_single_plugin(plugin_name)
                        if success:
                            loaded_count += 1
                        else:
                            logger.warning(f"Failed to auto-load plugin: {plugin_name}")
        
        logger.info(f"✅ Auto-loaded {loaded_count} enabled plugins")
        
    except Exception as e:
        logger.error(f"❌ Plugin auto-loading failed: {e}")

async def load_single_plugin(plugin_name):
    """Load a single plugin"""
    try:
        plugin_dir = Path("./plugins") / plugin_name
        manifest_file = plugin_dir / "manifest.json"
        config_file = plugin_dir / "tool_config.json"
        
        if not manifest_file.exists():
            return False
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            tool_meta = config_data.get("tool_metadata", manifest)
            tool_config = config_data.get("tool_configuration", {})
        else:
            tool_meta = manifest
            tool_config = {
                "tool_name": plugin_name,
                "enabled": True,
                "config": manifest.get("configuration_schema", {})
            }
        
        # Create metadata and config objects (same as install_plugin)
        from core.contracts import ToolMetadata, ToolConfiguration, ToolType, ToolCapability, CapabilityType

        # Parse capabilities from manifest
        capabilities = []
        for cap_data in tool_meta.get("capabilities", []):
            capability = ToolCapability(
                name=cap_data["name"],
                description=cap_data["description"],
                capability_type=CapabilityType(cap_data["capability_type"]),
                input_schema=cap_data.get("input_schema", {}),
                output_schema=cap_data.get("output_schema", {}),
                required_permissions=cap_data.get("required_permissions", []),
                examples=cap_data.get("examples", [])
            )
            capabilities.append(capability)

        metadata = ToolMetadata(
            name=tool_meta["name"],
            description=tool_meta["description"],
            version=tool_meta["version"],
            tool_type=ToolType(tool_meta["tool_type"]),
            capabilities=capabilities,
            author=tool_meta.get("author"),
            dependencies=tool_meta.get("dependencies", []),
            tags=set(tool_meta.get("tags", []))
        )
        
        configuration = ToolConfiguration(
            tool_name=tool_config["tool_name"],
            enabled=tool_config["enabled"],
            config=tool_config["config"],
            user_permissions=tool_config.get("user_permissions", []),
            rate_limits=tool_config.get("rate_limits", {})
        )
        
        success = await bridge.orchestrator.tool_manager.load_tool(metadata, configuration)
        return success
        
    except Exception as e:
        logger.error(f"Failed to load plugin {plugin_name}: {e}")
        return False

if __name__ == '__main__':
    logger.info("🌟 Starting MetisAgent3 Bridge Server...")
    logger.info("🔗 Bridge: Frontend (React) ↔️ Bridge Server ↔️ MetisAgent3 Backend")
    logger.info("📡 Server: http://localhost:6001")
    logger.info("🎯 Frontend Proxy: port 3000 → 6001")
    
    # Initialize bridge services before starting server
    logger.info("⚡ Initializing MetisAgent3 backend services...")
    initialize_bridge()
    
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5001,
        debug=False,  # Set to False for production
        allow_unsafe_werkzeug=True
    )
