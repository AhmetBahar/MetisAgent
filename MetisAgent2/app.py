"""
MetisAgent2 - Main Flask application entry point
"""

from app import create_app
import logging
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable noisy SocketIO/EngineIO logs
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)  
logging.getLogger('engineio.server').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create Flask application
app = create_app()

if __name__ == '__main__':
    logger.info("Starting MetisAgent2 server...")
    
    # Initialize tool capabilities in graph memory
    try:
        from tool_capability_manager import initialize_tool_capabilities
        logger.info("Initializing tool capabilities...")
        initialize_tool_capabilities()
        logger.info("✅ Tool capabilities initialized")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize tool capabilities: {e}")
    
    # Initialize LLM-based tool routing (CLAUDE.md compliant)
    try:
        from app.tool_coordinator import coordinator
        from app.mcp_core import registry
        from tool_capability_manager import tool_capability_manager
        
        llm_tool = registry.get_tool('llm_tool')
        if llm_tool and tool_capability_manager:
            coordinator.initialize_llm_router(llm_tool, tool_capability_manager)
            logger.info("✅ LLM-based tool routing initialized (CLAUDE.md compliant)")
        else:
            logger.warning("⚠️ LLM tool or capability manager not available for routing")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize LLM tool routing: {e}")
    
    # Use configuration from environment
    server_config = config.server_config
    logger.info(f"Server configuration: {server_config}")
    
    # Get SocketIO instance from app
    socketio = getattr(app, 'socketio', None)
    
    if socketio:
        logger.info("Starting server with SocketIO support...")
        socketio.run(
            app,
            host=server_config['host'],
            port=server_config['port'],
            debug=server_config['debug'],
            allow_unsafe_werkzeug=True
        )
    else:
        logger.warning("SocketIO not available, starting regular Flask server")
        app.run(
            host=server_config['host'],
            port=server_config['port'],
            debug=server_config['debug']
        )