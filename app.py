from flask import Flask
from flask_cors import CORS
from flask_sock import Sock
import logging
import os
import time
from dotenv import load_dotenv
from os_araci.mcp_core.registry import MCPRegistry, ToolSourceType
from os_araci.coordination.coordinator import MCPCoordinator

# Import modular routes
from api_routes.core_routes import register_core_routes
from api_routes.auth_routes import register_auth_routes
from api_routes.registry_routes import register_registry_routes
from api_routes.memory_routes import register_memory_routes
from api_routes.task_routes import register_task_routes
from api_routes.persona_routes import register_persona_routes
from api_routes.plugin_routes import register_plugin_routes
from api_routes.a2a_routes import register_a2a_routes
from api_routes.llm_routes import register_llm_routes
from api_routes.editor_routes import register_editor_routes
# settings_routes deprecated - using MetisAgent2 settings system

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Ortam değişkenlerini kontrol et ve durumu logla"""
    try:
        dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        logger.info(f".env dosyasını arıyor: {dotenv_path}")
        
        if os.path.exists(dotenv_path):
            logger.info(f".env dosyası bulundu: {dotenv_path}")
            load_dotenv(dotenv_path)
        else:
            logger.warning(f".env dosyası bulunamadı: {dotenv_path}")
            
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"]
        for key_name in api_keys:
            api_key = os.environ.get(key_name, '').strip()
            if api_key:
                os.environ[key_name] = api_key
                logger.info(f"{key_name} yüklendi: {api_key[:5]}...")
            else:
                logger.warning(f"{key_name} ortam değişkeni bulunamadı!")
            
        return True
    except Exception as e:
        logger.error(f"Ortam değişkenleri kontrol edilirken hata: {str(e)}")
        return False

check_environment()

# Flask uygulaması
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
CORS(app)
sock = Sock(app)

# MCP Registry ve Coordinator'ı başlat
try:
    registry = MCPRegistry()
    coordinator = MCPCoordinator(registry)
    logger.info("MCP Registry ve Coordinator başlatıldı")
except Exception as e:
    logger.error(f"MCP bileşenleri başlatılırken hata: {str(e)}")
    registry = None
    coordinator = None

# Initialize additional components (needed for some routes)
try:
    from os_araci.coordination.coordinator_a2a import MCPCoordinatorA2A
    from os_araci.personas.persona_factory import PersonaFactory
    from os_araci.plugins.plugin_registry import PluginRegistry
    from os_araci.tools.memory_manager import MemoryManager
    from os_araci.websocket.scalable_handler import ScalableWebSocketHandler
    from os_araci.websocket.event_emitter import EventEmitter
    from os_araci.db.chroma_manager import ChromaManager
    
    # Database manager for personas
    db_manager = ChromaManager()
    db_manager.init_default_personas()
    
    coordinator_a2a = None  # Will be initialized later like in old app
    persona_factory = PersonaFactory()
    plugin_registry = PluginRegistry()
    memory_manager = MemoryManager()
    ws_handler = ScalableWebSocketHandler()
    event_emitter = EventEmitter()
    
    logger.info("Additional components initialized")
except Exception as e:
    logger.warning(f"Some components could not be initialized: {str(e)}")
    coordinator_a2a = None
    persona_factory = None
    plugin_registry = None
    memory_manager = None
    ws_handler = None
    event_emitter = None
    db_manager = None

# Register all route modules
register_core_routes(app, registry, coordinator)
register_auth_routes(app)
register_registry_routes(app, registry)
register_memory_routes(app, registry, memory_manager)
register_task_routes(app, coordinator, registry)
register_persona_routes(app, coordinator_a2a, persona_factory)
register_plugin_routes(app, plugin_registry)
register_a2a_routes(app, coordinator_a2a)
register_llm_routes(app, coordinator)
register_editor_routes(app, registry)

# Register settings blueprint
# settings_bp deprecated - using MetisAgent2 settings system

# WebSocket endpoints
@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint"""
    try:
        if ws_handler:
            ws_handler.handle_connection(ws)
        else:
            # Simple fallback WebSocket handler
            logger.info("WebSocket connected (fallback handler)")
            while True:
                try:
                    message = ws.receive()
                    if message:
                        logger.info(f"WebSocket message received: {message}")
                        ws.send(f"Echo: {message}")
                except Exception as e:
                    logger.error(f"WebSocket message error: {str(e)}")
                    break
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")

@sock.route('/ws/agent')
def websocket_agent(ws):
    """Agent WebSocket endpoint for frontend"""
    try:
        if ws_handler:
            ws_handler.handle_connection(ws)
        else:
            # Simple fallback WebSocket handler for frontend
            logger.info("Agent WebSocket connected (fallback handler)")
            ws.send('{"type":"connection","status":"connected"}')
            while True:
                try:
                    message = ws.receive()
                    if message:
                        logger.info(f"Agent WebSocket message: {message}")
                        
                        # Parse and handle message
                        try:
                            import json
                            msg_data = json.loads(message)
                            command = msg_data.get('command')
                            
                            if command == 'send_message':
                                # Handle chat message
                                response = {
                                    "type": "message_response",
                                    "messageId": msg_data.get('messageId'),
                                    "response": "Bu bir test yanıtıdır. MCP araçları henüz WebSocket'e entegre edilmemiş.",
                                    "timestamp": int(time.time() * 1000)
                                }
                                ws.send(json.dumps(response))
                            else:
                                # Basic response for other commands
                                ws.send('{"type":"response","status":"received"}')
                        except Exception as parse_error:
                            logger.error(f"Message parse error: {str(parse_error)}")
                            ws.send('{"type":"error","message":"Invalid message format"}')
                except Exception as e:
                    logger.error(f"Agent WebSocket message error: {str(e)}")
                    break
    except Exception as e:
        logger.error(f"Agent WebSocket connection error: {str(e)}")

# Static file serving for frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend files"""
    try:
        from flask import send_from_directory
        frontend_path = os.path.join(os.path.dirname(__file__), 'metis-agent-frontend', 'build')
        if path != "" and os.path.exists(os.path.join(frontend_path, path)):
            return send_from_directory(frontend_path, path)
        else:
            return send_from_directory(frontend_path, 'index.html')
    except Exception as e:
        logger.error(f"Frontend serving error: {str(e)}")
        return f"Frontend not available: {str(e)}", 404

if __name__ == '__main__':
    logger.info("MCP-based Flask uygulaması başlatılıyor...")
    # Port updated to 6000 for Axis integration
    app.run(debug=True, host='0.0.0.0', port=6000)
