"""
MetisAgent2 - Simplified MCP Tool-based Flask Application
"""

from flask import Flask, request, g
from flask_cors import CORS
import logging
import os
import uuid

def create_app():
    """Create and configure Flask application"""
    import os
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    app = Flask(__name__, template_folder=template_dir)
    
    # Set up static file serving for generated images
    generated_images_path = os.path.join(os.getcwd(), "generated_images")
    if not os.path.exists(generated_images_path):
        os.makedirs(generated_images_path, exist_ok=True)
    
    @app.route('/generated_images/<filename>')
    def serve_generated_image(filename):
        """Serve generated images as static files"""
        from flask import send_from_directory
        return send_from_directory(generated_images_path, filename)
    
    # Configure secret key for sessions
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
    
    # Configure max content length for large base64 images
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB limit
    
    # Configure CORS
    CORS(app, 
         origins=["http://localhost:3000"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Correlation-ID"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization", "X-Correlation-ID"]
    )
    
    # Correlation ID middleware
    @app.before_request
    def add_correlation_id():
        """Add correlation ID to all requests"""
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        g.correlation_id = correlation_id
        request.correlation_id = correlation_id
    
    @app.after_request
    def set_correlation_header(response):
        """Add correlation ID to response headers"""
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id
        return response
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Disable noisy SocketIO/EngineIO logs
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('engineio.server').setLevel(logging.WARNING)
    
    # Import and register blueprints
    from .routes import api_bp
    from .auth_routes import auth_bp
    from .oauth2_routes import oauth2_bp
    from blueprints.user_storage_api import user_storage_api
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    app.register_blueprint(oauth2_bp)
    app.register_blueprint(user_storage_api)
    
    # Register settings blueprint
    try:
        from .settings_routes import settings_bp
        app.register_blueprint(settings_bp)
        logging.info("Settings blueprint registered")
    except ImportError as e:
        logging.warning(f"Settings blueprint not available: {e}")
    
    # Register plugin management blueprint
    try:
        from .plugin_routes import plugin_bp
        app.register_blueprint(plugin_bp)
        logging.info("Plugin management blueprint registered")
    except ImportError as e:
        logging.warning(f"Plugin management blueprint not available: {e}")
    
    # Initialize WebSocket manager
    from .websocket_manager import websocket_manager
    socketio = websocket_manager.init_app(app)
    
    # Initialize tools on startup
    _initialize_tools()
    
    # Connect workflow orchestrator to WebSocket manager
    try:
        from .workflow_orchestrator import orchestrator
        orchestrator.set_websocket_manager(websocket_manager)
        logging.info("Workflow orchestrator connected to WebSocket manager")
    except Exception as e:
        logging.error(f"Failed to connect orchestrator to WebSocket: {e}")
    
    # Initialize unified planner after tools are loaded
    try:
        from .mcp_core import registry
        orchestrator.initialize_planner(registry)
        logging.info("WORKFLOW-FIRST: Unified planner initialized - all requests will use workflow orchestration")
    except Exception as e:
        logging.error(f"Failed to initialize unified planner: {e}")
    
    # Store socketio reference in app for global access
    app.socketio = socketio
    
    return app

def _initialize_tools():
    """Initialize core and dynamic tools on startup"""
    try:
        from tools import register_all_tools
        from .mcp_core import registry
        
        # Register core tools
        tools_registered = register_all_tools(registry)
        logging.info(f"Registered {len(tools_registered)} core tools: {tools_registered}")
        
        # Auto-load approved dynamic tools
        tool_manager = registry.get_tool('tool_manager')
        if tool_manager:
            # Load existing dynamic tools
            tool_manager._load_existing_tools()
            logging.info("Dynamic tools auto-load completed")
        
        # Sync all tools to graph memory for system user
        try:
            from tool_capability_manager import get_capability_manager
            capability_manager = get_capability_manager()
            capability_manager.sync_all_tools_to_memory("system")
            logging.info("Tool capabilities synced to graph memory")
        except Exception as e:
            logging.error(f"Failed to sync tool capabilities: {e}")
        
    except Exception as e:
        logging.error(f"Error initializing tools: {str(e)}")