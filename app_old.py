from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS, cross_origin
from flask_sock import Sock
import json
import os
import subprocess
import platform
import logging
import datetime
import time
from typing import Dict, Any, Optional
import uuid
from os_araci.mcp_core.registry import MCPRegistry, ToolSourceType
from os_araci.coordination.coordinator import MCPCoordinator
import importlib
from dotenv import load_dotenv
from os_araci.coordination.coordinator_a2a import MCPCoordinatorA2A
from os_araci.mcp_core.tool_discovery import ToolDiscovery
from os_araci.auth.auth_manager import AuthManager
from os_araci.tools.memory_manager import MemoryManager
from os_araci.db.chroma_manager import ChromaManager
from os_araci.websocket.handler import WebSocketHandler
from os_araci.websocket.message_bridge import MessageBridge
from os_araci.websocket.event_emitter import EventEmitter
from os_araci.core.event_loop_manager import event_loop_manager, run_async
from os_araci.websocket.scalable_handler import ScalableWebSocketHandler
from os_araci.plugins.plugin_registry import PluginRegistry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Çevre değişkenlerini kontrol et
def check_environment():
    """Ortam değişkenlerini kontrol et ve durumu logla"""
    try:
        # .env dosyasının yolunu belirt
        dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        logger.info(f".env dosyasını arıyor: {dotenv_path}")
        
        # .env dosyasının varlığını kontrol et
        if os.path.exists(dotenv_path):
            logger.info(f".env dosyası bulundu: {dotenv_path}")
            # Açıkça belirtilen .env dosyasını yükle
            load_dotenv(dotenv_path)
        else:
            logger.warning(f".env dosyası bulunamadı: {dotenv_path}")
            logger.warning("API anahtarlarını manuel olarak ayarlamanız gerekebilir.")
            
        # Kritik ortam değişkenlerini kontrol et ve temizle
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"]
        
        for key_name in api_keys:
            api_key = os.environ.get(key_name, '').strip()  # strip() ekle
            if api_key:
                os.environ[key_name] = api_key  # Temizlenmiş değeri geri yaz
                logger.info(f"{key_name} yüklendi: {api_key[:5]}...")
            else:
                logger.warning(f"{key_name} ortam değişkeni bulunamadı! İlgili LLM çağrıları başarısız olabilir.")
            
        return True
    except Exception as e:
        logger.error(f"Ortam değişkenleri kontrol edilirken hata: {str(e)}")
        return False

# A2A-WebSocket bridge'i kur
def setup_a2a_websocket_bridge():
    """A2A mesajlarını WebSocket'e köprüle"""
    def on_persona_status_change(data):
        if ws_handler:
            ws_handler.broadcast('persona_status_update', data)
    
    def on_task_update(data):
        if ws_handler:
            ws_handler.broadcast('task_update', data)
    
    def on_task_started(data):
        if ws_handler:
            ws_handler.broadcast('task_started', data)
    
    def on_task_completed(data):
        if ws_handler:
            ws_handler.broadcast('task_completed', data)
    
    def on_persona_started(data):
        if ws_handler:
            ws_handler.broadcast('persona_started', data)
    
    # Event listener'ları kaydet
    if event_emitter:
        event_emitter.on('persona_status_update', on_persona_status_change)
        event_emitter.on('task_update', on_task_update)
        event_emitter.on('task_started', on_task_started)
        event_emitter.on('task_completed', on_task_completed)
        event_emitter.on('persona_started', on_persona_started)

check_environment()

# Uygulama oluştur
app = Flask(__name__, static_folder='frontend/build')
cors = CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5000", "*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

sock = Sock(app)  # WebSocket desteği ekle

# Veritabanı yöneticisini başlat
db_manager = ChromaManager()
db_manager.init_default_personas()

ws_handler = WebSocketHandler(sock)
event_emitter = EventEmitter(ws_handler)
message_bridge = MessageBridge(ws_handler)

plugin_registry = PluginRegistry("./plugins")

# MCP Registry'yi tools ile birlikte başlat
from os_araci.tools import register_all_tools
registry = register_all_tools()

# Memory Manager'ı manuel olarak ekle
try:
    from os_araci.tools.memory_manager import MemoryManager
    print("📥 MemoryManager import edildi")
    memory_manager = MemoryManager(registry)
    print("🔧 MemoryManager instance oluşturuldu")
    registry.register_local_tool(memory_manager)
    print("✅ Memory Manager manuel olarak eklendi")
except Exception as e:
    print(f"❌ Memory Manager manuel ekleme hatası: {e}")
    import traceback
    traceback.print_exc()

print(f"🔧 Registry araçları: {list(registry.get_all_metadata().keys())}")

# Coordinator'ı event emitter ile başlat
coordinator = MCPCoordinator(registry, event_emitter=event_emitter)

# Ek araçları da keşfet (file_manager, llm_tool vs.)
discovered_tools = registry.discover_tools('os_araci.tools')
registry.initialize_all()

# A2A protokolü ve Auth Manager (başlangıçta None)
coordinator_a2a = None
auth_manager = AuthManager()

# Global scalable handler
scalable_ws_handler = None

# LLM için sistem prompt
TASK_GENERATION_PROMPT = """
You are a system automation expert that helps users break down tasks into executable steps...
[Prompt içeriği aynı]
"""

# ===============================
# 1. API DURUM VE SAĞLIK ENDPOINTLERİ
# ===============================

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response, 200

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "ok", "message": "Server is running!"})

@app.route('/api/status', methods=['GET'])
def api_status():
    """API durumunu kontrol et"""
    return jsonify({
        "status": "online",
        "version": "2.0.0",
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_tools": list(registry.get_all_tools().keys())
    })

@app.route('/api/registry/ping', methods=['GET'])
def registry_ping():
    """Basit ping endpoint'i"""
    return jsonify({
        "status": "success",
        "message": "pong",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/routes', methods=['GET'])
def list_routes():
    """Tüm route'ları listele"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

# ===============================
# 2. AUTHENTICATION ENDPOINTLERİ
# ===============================

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Yeni kullanıcı kaydı"""
    try:
        data = request.get_json()
        logger.info(f"Kayıt verisi: {data}")
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            logger.warning("Eksik alanlar var")
            return jsonify({"status": "error", "message": "Tüm alanlar gereklidir"}), 400
        
        logger.info(f"Kullanıcı oluşturuluyor: {username}")
        result = auth_manager.create_user(username, password, permissions=["user"])
        
        logger.info(f"Kullanıcı oluşturma sonucu: {result}")
        
        if result.get("status") == "success":
            return jsonify(result), 201
        else:
            logger.warning(f"Kullanıcı kaydı başarısız: {result.get('message')}")
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Kullanıcı kaydı sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def login_user():
    """Kullanıcı girişi"""
    if request.method == 'OPTIONS':
        # Preflight request
        return jsonify({"status": "ok"}), 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password required"}), 400
        
        logger.info(f"Login isteği alındı: {username}")
        result = auth_manager.authenticate_user(username, password)
        logger.info(f"Doğrulama sonucu: {result}")
        
        if result.get("status") == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 401
        
    except Exception as e:
        logger.error(f"Kullanıcı girişi sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auth/check_user/<username>', methods=['GET'])
def check_user(username):
    """Test: Kullanıcının varlığını kontrol et"""
    try:
        user = auth_manager.get_user(username)
        if user:
            return jsonify({"exists": True, "message": f"Kullanıcı mevcut: {username}"}), 200
        else:
            return jsonify({"exists": False, "message": f"Kullanıcı bulunamadı: {username}"}), 200
    except Exception as e:
        logger.error(f"Kullanıcı kontrolü sırasında hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ===============================
# 3. MEMORY ENDPOINTLERİ
# ===============================

@app.route('/api/memory/store', methods=['POST'])
def store_memory():
    """Bellek kaydı oluştur API endpoint'i"""
    try:
        data = request.get_json()
        
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "store_memory", 
                                      content=data.get('content'),
                                      category=data.get('category', 'general'),
                                      tags=data.get('tags', []))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kaydı oluşturulurken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/retrieve', methods=['GET'])
def retrieve_memories():
    """Bellek kayıtlarını getir API endpoint'i"""
    try:
        query = request.args.get('query')
        category = request.args.get('category')
        tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
        limit = int(request.args.get('limit', 10))
        
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "retrieve_memories", 
                                      query=query,
                                      category=category,
                                      tags=tags,
                                      limit=limit)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kayıtları getirilirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/update/<int:memory_id>', methods=['PUT'])
def update_memory(memory_id):
    """Bellek kaydını güncelle API endpoint'i"""
    try:
        data = request.get_json()
        
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "update_memory", 
                                      memory_id=memory_id,
                                      content=data.get('content'),
                                      category=data.get('category'),
                                      tags=data.get('tags'))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kaydı güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/delete/<int:memory_id>', methods=['DELETE'])
def delete_memory(memory_id):
    """Bellek kaydını sil API endpoint'i"""
    try:
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "delete_memory", memory_id=memory_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kaydı silinirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/clear', methods=['POST'])
def clear_all_memories():
    """Tüm bellek kayıtlarını temizle API endpoint'i"""
    try:
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "clear_all_memories")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kayıtları temizlenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/search', methods=['GET'])
def search_memories_by_similarity():
    """Benzerliğe göre bellek kayıtlarını ara API endpoint'i"""
    try:
        query = request.args.get('query')
        limit = int(request.args.get('limit', 5))
        
        if not query:
            return jsonify({"status": "error", "message": "Query parameter required"}), 400
        
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "search_by_similarity", 
                                      query=query,
                                      limit=limit)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Benzerlik araması yapılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memory/user/<username>', methods=['POST'])
def set_memory_user(username):
    """Bellek yöneticisi için aktif kullanıcıyı ayarla API endpoint'i"""
    try:
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = registry.call_handler(tool_id, "set_user", username=username)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Bellek kullanıcısı ayarlanırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================
# 3.5. PERSONA CONTEXT ENDPOINTLERİ  
# ===============================

@app.route('/api/personas/<persona_id>/context/<user_id>', methods=['GET'])
def get_persona_context(persona_id, user_id):
    """Persona context'ini getir"""
    try:
        # Memory manager'ı bul
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = memory_manager.get_persona_context(persona_id, user_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Persona context getirme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/context/<user_id>', methods=['POST'])
def save_persona_context(persona_id, user_id):
    """Persona context'ini kaydet"""
    try:
        data = request.get_json()
        context_data = data.get('context', {})
        
        # Memory manager'ı bul
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = memory_manager.save_persona_context(persona_id, user_id, context_data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Persona context kaydetme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/context/<user_id>', methods=['PUT'])
def update_persona_context(persona_id, user_id):
    """Persona context'ini güncelle"""
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        
        # Memory manager'ı bul
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = memory_manager.update_persona_state(persona_id, user_id, updates)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Persona context güncelleme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/context/<user_id>', methods=['DELETE'])
def clear_persona_context(persona_id, user_id):
    """Persona context'ini temizle"""
    try:
        # Memory manager'ı bul
        memory_manager = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'memory_manager':
                memory_manager = registry.get_tool_by_id(tool_id)
                break
                
        if not memory_manager:
            return jsonify({"status": "error", "message": "Memory manager not found"}), 404
        
        result = memory_manager.clear_persona_session(persona_id, user_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Persona context temizleme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================
# 4. PERSONA ENDPOINTLERİ
# ===============================

@app.route('/api/personas', methods=['GET'])
def list_personas():
    """Tüm kayıtlı personaları listele"""
    try:
        if coordinator_a2a:
            personas = run_async(coordinator_a2a.get_personas())
        else:
            personas = db_manager.get_all_personas()
        
        return jsonify({
            "status": "success",
            "personas": personas
        })
    except Exception as e:
        logger.error(f"Personalar listelenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas', methods=['POST'])
def create_persona():
    """Yeni bir persona ekle"""
    try:
        data = request.get_json()
        
        required_fields = ['id', 'name', 'description', 'capabilities']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"Eksik alan: {field}"}), 400
        
        if coordinator_a2a:
            result = run_async(coordinator_a2a.create_persona(data))
        else:
            result = db_manager.create_persona(data)
        
        if result["status"] == "success":
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Persona oluşturulurken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Belirli bir personanın detaylarını getir"""
    try:
        # Veritabanından persona bilgisini al
        persona = db_manager.get_persona(persona_id)
        
        if not persona:
            return jsonify({"status": "error", "message": f"Persona bulunamadı: {persona_id}"}), 404
        
        # Plugin registry'den plugin info'yu al
        plugin_info = plugin_registry.get_plugin(persona_id)
        
        # Eğer plugin registry'de persona varsa, persona bilgilerine workflow_steps ekle
        if plugin_info and 'workflow_steps' in plugin_info:
            persona['workflow_steps'] = plugin_info['workflow_steps']
        
        # Eğer persona_id social-media ise, varsayılan workflow steps ekle
        # Bu sosyal medya personasında tanımlı olan adımları ekliyoruz
        elif persona_id == 'social-media':
            persona['workflow_steps'] = [
                {"id": "briefing", "label": "Brifing"},
                {"id": "creative_idea", "label": "Yaratıcı Fikir"},
                {"id": "post_content", "label": "İçerik"},
                {"id": "sharing_content", "label": "Paylaşım"},
                {"id": "visual_production", "label": "Görsel"},
                {"id": "approval", "label": "Onay"},
                {"id": "scheduling", "label": "Zamanlama"},
                {"id": "monitoring", "label": "İzleme"},
                {"id": "reporting", "label": "Raporlama"}
            ]
            persona['current_step'] = 'briefing'  # Varsayılan adım

        # Runtime durumunu da ekle
        if coordinator_a2a:
            try:
                status = run_async(coordinator_a2a.get_persona_status(persona_id))
                persona['is_online'] = status.get('is_online', False)
                persona['runtime_status'] = status.get('runtime_status', 'offline')
            except:
                persona['is_online'] = False
                persona['runtime_status'] = 'offline'
        
        return jsonify({
            "status": "success",
            "persona": persona
        })
    except Exception as e:
        logger.error(f"Persona detayları alınırken hata: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/personas/<persona_id>', methods=['PUT'])
def update_persona(persona_id):
    """Mevcut bir personayı güncelle"""
    try:
        data = request.get_json()
        
        if coordinator_a2a:
            result = run_async(coordinator_a2a.update_persona(persona_id, data))
        else:
            result = db_manager.update_persona(persona_id, data)
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Persona güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>', methods=['DELETE'])
def delete_persona(persona_id):
    """Bir personayı sil"""
    try:
        if coordinator_a2a:
            result = run_async(coordinator_a2a.delete_persona(persona_id))
        else:
            result = db_manager.delete_persona(persona_id)
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Persona silinirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/status', methods=['GET'])
def get_persona_status(persona_id):
    """Personanın runtime durumunu kontrol et"""
    try:
        if not coordinator_a2a:
            return jsonify({"status": "error", "message": "A2A protokolü aktif değil"}), 503
        
        status = run_async(coordinator_a2a.get_persona_status(persona_id))
        return jsonify(status)
    except Exception as e:
        logger.error(f"Persona durumu alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/start', methods=['POST'])
def start_persona(persona_id):
    """Personayı başlat"""
    try:
        if not coordinator_a2a:
            return jsonify({"status": "error", "message": "A2A protokolü aktif değil"}), 503
        
        result = run_async(coordinator_a2a.start_persona(persona_id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Persona başlatılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/stop', methods=['POST'])
def stop_persona(persona_id):
    """Personayı durdur"""
    try:
        if not coordinator_a2a:
            return jsonify({"status": "error", "message": "A2A protokolü aktif değil"}), 503
        
        result = run_async(coordinator_a2a.stop_persona(persona_id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Persona durdurulurken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/restart', methods=['POST'])
def restart_persona(persona_id):
    """Personayı yeniden başlat"""
    try:
        if not coordinator_a2a:
            return jsonify({"status": "error", "message": "A2A protokolü aktif değil"}), 503
        
        result = run_async(coordinator_a2a.restart_persona(persona_id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Persona yeniden başlatılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/personas/<persona_id>/data', methods=['GET', 'POST'])
def persona_data(persona_id):
    """Persona verilerini getir veya güncelle"""
    try:
        if request.method == 'GET':
            # Persona var mı kontrol et
            persona = db_manager.get_persona(persona_id)
            if not persona:
                return jsonify({"status": "error", "message": f"Persona bulunamadı: {persona_id}"}), 404
            
            # Persona'nın verilerini getir (burası veritabanında veya başka bir kaynakta saklanıyor olabilir)
            # Örnek olarak boş bir context ile başlıyoruz
            context = {}
            
            # Sosyal medya personası için varsayılan context
            if persona_id == 'social-media':
                context = {
                    "current_step": "briefing"
                }
            
            return jsonify({
                "status": "success",
                "data": persona,
                "context": context
            })
        elif request.method == 'POST':
            # Gelen veriyi al
            data = request.get_json()
            persona_data = data.get('data', {})
            
            # Burada veriyi kaydetme işlemi yapılabilir (örn: veritabanına)
            # Şimdilik başarılı döndürelim
            
            return jsonify({
                "status": "success", 
                "message": "Persona verileri güncellendi",
                "updated_data": persona_data
            })
    except Exception as e:
        logger.error(f"Persona verileri işlenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/personas/<persona_id>/execute-task', methods=['POST'])
def execute_persona_task(persona_id):
    """Personada belirli bir görevi çalıştır"""
    try:
        data = request.get_json()
        task = data.get('task', {})
        
        # Persona var mı kontrol et
        persona = db_manager.get_persona(persona_id)
        if not persona:
            return jsonify({"status": "error", "message": f"Persona bulunamadı: {persona_id}"}), 404
        
        # Eğer A2A protokolü etkinse, bu mekanizmayı kullan
        if coordinator_a2a:
            result = run_async(coordinator_a2a.execute_task_with_persona(
                task=task,
                context={},
                target_persona=persona_id
            ))
            
            return jsonify({
                "status": "success",
                "result": result,
                "context_updates": result.get("context_updates", {})
            })
        else:
            # A2A protokolü yoksa, basit bir yanıt döndür
            return jsonify({
                "status": "success",
                "message": "Görev çalıştırıldı (simüle edildi)",
                "task": task,
                "context_updates": {}
            })
    except Exception as e:
        logger.error(f"Persona görevi çalıştırılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
# ===============================
# 5. A2A PROTOCOL ENDPOINTLERİ
# ===============================

@app.route('/api/a2a/task', methods=['POST'])
def execute_task_with_persona():
    """Görevi bir persona ile çalıştır"""
    if not coordinator_a2a:
        return jsonify({"status": "error", "message": "A2A protokolü kullanılamıyor"}), 500
        
    try:
        data = request.json
        task = data.get('task')
        context = data.get('context', {})
        target_persona = data.get('target_persona')
        timeout = data.get('timeout', 120.0)
        
        if not task:
            return jsonify({"status": "error", "message": "task required"}), 400
        
        result = run_async(coordinator_a2a.execute_task_with_persona(
            task=task,
            context=context,
            target_persona=target_persona,
            timeout=timeout
        ))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================
# 6. TASK VE CONTEXT ENDPOINTLERİ
# ===============================

@app.route('/api/task/execute', methods=['POST'])
def execute_task():
    """Tek bir görevi çalıştır"""
    try:
        data = request.get_json()
        task = data.get('task')
        
        if not task:
            return jsonify({'error': 'Task required'}), 400
        
        result = coordinator.execute_task(task)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/task/execute_with_context', methods=['POST'])
def execute_task_with_context():
    """Placeholder güncelleme ve LLM değerlendirmesi ile görev çalıştırır"""
    try:
        data = request.get_json()
        task = data.get('task')
        clear_context = data.get('clear_context', False)
        llm_settings = data.get('llm_settings', {}) 

        if not task:
            return jsonify({'error': 'Task required'}), 400
        
        if clear_context:
            coordinator.context_values = {}
        
        result = run_async(coordinator._execute_task(task, llm_settings))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/execute', methods=['POST'])
def execute_tasks():
    """Birden fazla görevi çalıştır"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])
        mode = data.get('mode', 'sequential')
        
        if not tasks:
            return jsonify({'error': 'Tasks required'}), 400
        
        if data.get('clear_context', False):
            coordinator.clear_context()
        
        results = coordinator.execute_tasks(tasks, mode)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Görevleri çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/execute_sequential', methods=['POST'])
def execute_tasks_sequential():
    """Görevleri sırayla çalıştırır, context'i güncelleyerek ilerler"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])
        fail_strategy = data.get('fail_strategy', 'continue')
        
        if not tasks:
            return jsonify({'error': 'Tasks required'}), 400
        
        if data.get('clear_context', True):
            coordinator.context_values = {}
        
        results = []
        
        for task in tasks:
            result = run_async(coordinator._execute_task(task))
            results.append(result)
            
            if result.get('status') == 'error' or (
                result.get('evaluation', {}).get('success') == False and 
                result.get('evaluation', {}).get('shouldContinue') == False):
                
                if fail_strategy == 'stop':
                    break
        
        return jsonify({
            'status': 'success',
            'results': results,
            'context': coordinator.context_values
        })
    except Exception as e:
        logger.error(f"Görevleri çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/context/get', methods=['GET'])
def get_context():
    """Mevcut context değerlerini döndürür"""
    return jsonify({
        'context': coordinator.context_values
    })

@app.route('/api/context/update', methods=['POST'])
def update_context():
    """Context değerlerini günceller"""
    try:
        data = request.get_json()
        context_updates = data.get('context', {})
        
        coordinator.context_values.update(context_updates)
        
        return jsonify({
            'status': 'success',
            'context': coordinator.context_values
        })
    except Exception as e:
        logger.error(f"Context güncelleme hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/coordinator/run_tasks_with_feedback', methods=['POST'])
def run_tasks_with_feedback_endpoint():
    """LLM geri bildirimi ile görevleri çalıştır API'si"""
    data = request.json
    tasks = data.get('tasks', [])
    
    try:
        result = run_async(coordinator.run_tasks_with_llm_feedback(tasks))
        
        standardized_result = []
        for task_result in result:
            if isinstance(task_result, dict) and 'task' in task_result and 'result' in task_result:
                if 'status' not in task_result:
                    if isinstance(task_result['result'], dict):
                        status = task_result['result'].get('status', 'unknown')
                    else:
                        status = 'unknown'
                    task_result['status'] = status
                
                standardized_result.append(task_result)
        
        return jsonify({
            "status": "success",
            "result": standardized_result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error running tasks with LLM feedback: {str(e)}\n{error_details}")
        return jsonify({
            "error": str(e), 
            "details": error_details,
            "status": "error"
        }), 500

# ===============================
# 7. REGISTRY ENDPOINTLERİ (TAM)
# ===============================

@app.route('/api/registry/tools', methods=['GET'])
def list_registered_tools():
    """Tüm kayıtlı araçları listele"""
    try:
        source_type = request.args.get('source_type')
        category = request.args.get('category')
        capability = request.args.get('capability')
        
        if source_type:
            try:
                source_type = ToolSourceType(source_type)
            except ValueError:
                return jsonify({"error": f"Geçersiz kaynak tipi: {source_type}"}), 400
        
        if capability:
            capabilities = [capability]
            tool_ids = registry.find_tools_by_capabilities(capabilities)
            tools_data = []
            
            for tool_id in tool_ids:
                metadata = registry.get_metadata(tool_id)
                if metadata:
                    if category and metadata.category != category:
                        continue
                    
                    tool_dict = metadata.to_dict()
                    tool_dict['id'] = tool_id
                    tools_data.append(tool_dict)
        elif category:
            tool_ids = registry.find_tools_by_category(category)
            tools_data = []
            
            for tool_id in tool_ids:
                metadata = registry.get_metadata(tool_id)
                if metadata:
                    tool_dict = metadata.to_dict()
                    tool_dict['id'] = tool_id
                    tools_data.append(tool_dict)
        else:
            all_metadata = registry.get_all_metadata()
            tools_data = []
            
            for tool_id, metadata in all_metadata.items():
                if source_type and metadata.source_type != source_type:
                    continue
                
                tool_dict = metadata.to_dict()
                tool_dict['id'] = tool_id
                tools_data.append(tool_dict)
        
        return jsonify({"tools": tools_data, "count": len(tools_data)})
        
    except Exception as e:
        logger.error(f"Araçlar listelenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/tool/<tool_id>', methods=['GET'])
def get_tool_details(tool_id):
    """Belirli bir aracın detaylarını getir"""
    try:
        metadata = registry.get_metadata(tool_id)
        if not metadata:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        tool = registry.get_tool_by_id(tool_id)
        if not tool:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        if metadata.source_type == ToolSourceType.LOCAL:
            if hasattr(tool, 'describe') and callable(tool.describe):
                details = tool.describe()
            else:
                details = {
                    "actions": tool.get_all_actions() if hasattr(tool, 'get_all_actions') else {}
                }
            
            return jsonify({
                "metadata": metadata.to_dict(),
                "details": details
            })
            
        elif metadata.source_type == ToolSourceType.EXTERNAL:
            if hasattr(tool, 'get_actions') and callable(tool.get_actions):
                actions = tool.get_actions()
                actions_info = {}
                
                for action in actions:
                    action_schema = tool.get_action_schema(action)
                    actions_info[action] = action_schema
                
                return jsonify({
                    "metadata": metadata.to_dict(),
                    "details": {
                        "actions": actions_info
                    }
                })
            else:
                return jsonify({
                    "metadata": metadata.to_dict(),
                    "details": {}
                })
                
        elif metadata.source_type == ToolSourceType.REMOTE:
            if hasattr(tool, 'get_metadata') and callable(tool.get_metadata):
                remote_metadata = tool.get_metadata()
                actions = tool.get_actions() if hasattr(tool, 'get_actions') else []
                
                return jsonify({
                    "metadata": metadata.to_dict(),
                    "remote_metadata": remote_metadata,
                    "actions": actions
                })
            else:
                return jsonify({
                    "metadata": metadata.to_dict(),
                    "details": {}
                })
        
        return jsonify({"error": f"Desteklenmeyen araç tipi: {metadata.source_type}"}), 400
        
    except Exception as e:
        logger.error(f"Araç detayları alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/tool/<tool_id>/actions', methods=['GET'])
def get_tool_actions(tool_id):
    """Belirli bir aracın aksiyonlarını listele"""
    try:
        metadata = registry.get_metadata(tool_id)
        if not metadata:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        tool = registry.get_tool_by_id(tool_id)
        if not tool:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        actions = []
        
        if metadata.source_type == ToolSourceType.LOCAL:
            if hasattr(tool, 'get_all_actions') and callable(tool.get_all_actions):
                actions = list(tool.get_all_actions().keys())
        elif metadata.source_type == ToolSourceType.EXTERNAL:
            if hasattr(tool, 'get_actions') and callable(tool.get_actions):
                actions = tool.get_actions()
        elif metadata.source_type == ToolSourceType.REMOTE:
            if hasattr(tool, 'get_actions') and callable(tool.get_actions):
                actions = tool.get_actions()
        
        return jsonify({"tool_id": tool_id, "actions": actions})
        
    except Exception as e:
        logger.error(f"Araç aksiyonları alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/tool/<tool_id>/action/<action_name>', methods=['GET'])
def get_action_details(tool_id, action_name):
    """Belirli bir aksiyonun detaylarını getir"""
    try:
        metadata = registry.get_metadata(tool_id)
        if not metadata:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        tool = registry.get_tool_by_id(tool_id)
        if not tool:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        if metadata.source_type == ToolSourceType.LOCAL:
            if hasattr(tool, 'get_action_info') and callable(tool.get_action_info):
                action_info = tool.get_action_info(action_name)
                if not action_info:
                    return jsonify({"error": f"Aksiyon bulunamadı: {action_name}"}), 404
                
                return jsonify({
                    "tool_id": tool_id,
                    "action": action_name,
                    "info": action_info
                })
            else:
                return jsonify({"error": "Aksiyon bilgisi alınamıyor"}), 500
                
        elif metadata.source_type == ToolSourceType.EXTERNAL:
            if hasattr(tool, 'get_action_schema') and callable(tool.get_action_schema):
                action_schema = tool.get_action_schema(action_name)
                if not action_schema:
                    return jsonify({"error": f"Aksiyon bulunamadı: {action_name}"}), 404
                
                return jsonify({
                    "tool_id": tool_id,
                    "action": action_name,
                    "schema": action_schema
                })
            else:
                return jsonify({"error": "Aksiyon şeması alınamıyor"}), 500
                
        elif metadata.source_type == ToolSourceType.REMOTE:
            if hasattr(tool, 'get_action_schema') and callable(tool.get_action_schema):
                action_schema = tool.get_action_schema(action_name)
                if not action_schema:
                    return jsonify({"error": f"Aksiyon bulunamadı: {action_name}"}), 404
                
                return jsonify({
                    "tool_id": tool_id,
                    "action": action_name,
                    "schema": action_schema
                })
            else:
                return jsonify({"error": "Aksiyon şeması alınamıyor"}), 500
        
        return jsonify({"error": f"Desteklenmeyen araç tipi: {metadata.source_type}"}), 400
        
    except Exception as e:
        logger.error(f"Aksiyon detayları alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/call/<tool_id>/<action_name>', methods=['POST'])
def call_tool_action(tool_id, action_name):
    """Belirli bir aracın aksiyonunu çağır"""
    try:
        params = request.get_json().get('params', {})
        
        result = registry.call_handler(tool_id, action_name, **params)
        
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
            return jsonify(result[0]), result[1]
        else:
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Aksiyon çağrılırken hata: {tool_id}.{action_name}, {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/tool/<tool_id>', methods=['DELETE'])
def remove_tool(tool_id):
    """Bir aracı kaldır"""
    try:
        metadata = registry.get_metadata(tool_id)
        if not metadata:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        success = registry.unregister(tool_id)
        
        if not success:
            return jsonify({"error": f"Araç kaldırılamadı: {tool_id}"}), 500
        
        return jsonify({
            "status": "success",
            "message": f"Araç kaldırıldı: {tool_id}"
        })
        
    except Exception as e:
        logger.error(f"Araç kaldırılırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/external/add', methods=['POST'])
def add_external_tool():
    """Dış kaynak aracı ekle"""
    try:
        data = request.get_json()
        name = data.get('name')
        config = data.get('config', {})
        capabilities = data.get('capabilities', [])
        
        if not name or not config:
            return jsonify({"error": "Ad ve yapılandırma gerekli"}), 400
        
        success = registry.register_external_tool(name, config, capabilities)
        
        if not success:
            return jsonify({"error": f"Dış kaynak aracı eklenemedi: {name}"}), 500
        
        tool_id = f"external.{name}.{config.get('version', '1.0.0')}"
        metadata = registry.get_metadata(tool_id)
        
        return jsonify({
            "status": "success",
            "message": f"Dış kaynak aracı eklendi: {name}",
            "tool_id": tool_id,
            "metadata": metadata.to_dict() if metadata else {}
        })
        
    except Exception as e:
        logger.error(f"Dış kaynak aracı eklenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/remote/add', methods=['POST'])
def add_remote_tool():
    """Uzak MCP aracı ekle"""
    try:
        data = request.get_json()
        name = data.get('name')
        remote_url = data.get('remote_url')
        auth_info = data.get('auth_info', {})
        
        if not name or not remote_url:
            return jsonify({"error": "Ad ve uzak URL gerekli"}), 400
        
        success = registry.register_remote_tool(name, remote_url, auth_info)
        
        if not success:
            return jsonify({"error": f"Uzak araç eklenemedi: {name}"}), 500
        
        tool_id = None
        for id, metadata in registry.get_all_metadata().items():
            if metadata.name == name and metadata.source_type == ToolSourceType.REMOTE:
                tool_id = id
                break
        
        metadata = registry.get_metadata(tool_id) if tool_id else None
        
        return jsonify({
            "status": "success",
            "message": f"Uzak araç eklendi: {name}",
            "tool_id": tool_id,
            "metadata": metadata.to_dict() if metadata else {}
        })
        
    except Exception as e:
        logger.error(f"Uzak araç eklenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/remote/sync', methods=['POST'])
def sync_remote_tools():
    """Uzak MCP sunucusundan araçları senkronize et"""
    try:
        data = request.get_json()
        remote_url = data.get('remote_url')
        auth_info = data.get('auth_info', {})
        
        if not remote_url:
            return jsonify({"error": "Uzak URL gerekli"}), 400
        
        synced_tools = registry.sync_remote_tools(remote_url, auth_info)
        
        return jsonify({
            "status": "success",
            "message": f"{len(synced_tools)} araç senkronize edildi",
            "synced_tools": synced_tools
        })
        
    except Exception as e:
        logger.error(f"Uzak araçlar senkronize edilirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/capabilities', methods=['GET'])
def list_capabilities():
    """Tüm araçlar tarafından desteklenen yetenekleri listele"""
    try:
        all_metadata = registry.get_all_metadata()
        
        capabilities = set()
        for metadata in all_metadata.values():
            capabilities.update(metadata.capabilities)
        
        return jsonify({
            "capabilities": sorted(list(capabilities))
        })
        
    except Exception as e:
        logger.error(f"Yetenekler listelenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/categories', methods=['GET'])
def list_categories():
    """Tüm araç kategorilerini listele"""
    try:
        all_metadata = registry.get_all_metadata()
        
        categories = set()
        for metadata in all_metadata.values():
            categories.add(metadata.category)
        
        return jsonify({
            "categories": sorted(list(categories))
        })
        
    except Exception as e:
        logger.error(f"Kategoriler listelenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/export', methods=['GET'])
def export_registry():
    """Registry yapılandırmasını dışa aktar"""
    try:
        export_path = os.path.join(os.getcwd(), 'registry_export.json')
        
        success = registry.export_configuration(export_path)
        
        if not success:
            return jsonify({"error": "Registry yapılandırması dışa aktarılamadı"}), 500
        
        return send_from_directory(os.getcwd(), 'registry_export.json', as_attachment=True)
        
    except Exception as e:
        logger.error(f"Registry yapılandırması dışa aktarılırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/import', methods=['POST'])
def import_registry():
    """Registry yapılandırmasını içe aktar"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Dosya gerekli"}), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Dosya seçilmedi"}), 400
        
        file_path = os.path.join(os.getcwd(), 'registry_import.json')
        file.save(file_path)
        
        success = registry.import_configuration(file_path)
        
        try:
            os.remove(file_path)
        except:
            pass
        
        if not success:
            return jsonify({"error": "Registry yapılandırması içe aktarılamadı"}), 500
        
        return jsonify({
            "status": "success",
            "message": "Registry yapılandırması içe aktarıldı"
        })
        
    except Exception as e:
        logger.error(f"Registry yapılandırması içe aktarılırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/tool/<tool_id>/health', methods=['GET'])
def check_tool_health(tool_id):
    """Belirli bir aracın sağlık durumunu kontrol et"""
    try:
        metadata = registry.get_metadata(tool_id)
        if not metadata:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        tool = registry.get_tool_by_id(tool_id)
        if not tool:
            return jsonify({"error": f"Araç bulunamadı: {tool_id}"}), 404
        
        health_status = {"status": "healthy", "message": "Araç çalışır durumda görünüyor"}
        
        if hasattr(tool, 'check_health') and callable(tool.check_health):
            custom_health = tool.check_health()
            if custom_health and "status" in custom_health:
                health_status = custom_health
        
        return jsonify({
            "tool_id": tool_id,
            "health": health_status
        })
        
    except Exception as e:
        logger.error(f"Araç sağlık kontrolü yapılırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/health', methods=['GET'])
def get_registry_health():
    """Tüm araçların sağlık durumunu getir"""
    try:
        tool_id = request.args.get('tool_id')
        health_status = registry.get_tool_health(tool_id)
        
        return jsonify({
            "status": "success",
            "health": health_status
        })
        
    except Exception as e:
        logger.error(f"Sağlık durumu alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/handshake', methods=['POST'])
def registry_handshake():
    """Uzak MCP sunucuları için handshake endpoint'i"""
    try:
        data = request.get_json()
        client = data.get('client', 'unknown')
        client_version = data.get('version', 'unknown')
        
        logger.info(f"Handshake isteği alındı: {client} v{client_version}")
        
        compatible = True
        
        return jsonify({
            "status": "success",
            "version": "2.0.0",
            "compatible": compatible,
            "message": "Handshake başarılı"
        })
        
    except Exception as e:
        logger.error(f"Handshake sırasında hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registry/schema', methods=['GET'])
def get_registry_schema():
    """Registry API şemasını döndür"""
    try:
        schema = {
            "endpoints": [
                {
                    "path": "/api/registry/tools",
                    "method": "GET",
                    "description": "Tüm kayıtlı araçları listele",
                    "parameters": [
                        {
                            "name": "source_type",
                            "type": "string",
                            "description": "Araç kaynak tipi (local, external, remote)",
                            "required": False
                        },
                        {
                            "name": "category",
                            "type": "string",
                            "description": "Araç kategorisi",
                            "required": False
                        },
                        {
                            "name": "capability",
                            "type": "string",
                            "description": "Araç yeteneği",
                            "required": False
                        }
                    ]
                },
                {
                    "path": "/api/registry/tool/{tool_id}",
                    "method": "GET",
                    "description": "Belirli bir aracın detaylarını getir",
                    "parameters": [
                        {
                            "name": "tool_id",
                            "type": "string",
                            "description": "Araç ID'si",
                            "required": True
                        }
                    ]
                },
                {
                    "path": "/api/registry/call/{tool_id}/{action_name}",
                    "method": "POST",
                    "description": "Belirli bir aracın aksiyonunu çağır",
                    "parameters": [
                        {
                            "name": "tool_id",
                            "type": "string",
                            "description": "Araç ID'si",
                            "required": True
                        },
                        {
                            "name": "action_name",
                            "type": "string",
                            "description": "Aksiyon adı",
                            "required": True
                        },
                        {
                            "name": "params",
                            "type": "object",
                            "description": "Aksiyon parametreleri",
                            "required": False
                        }
                    ]
                }
            ]
        }
        
        return jsonify(schema)
        
    except Exception as e:
        logger.error(f"API şeması alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ===============================
# 8. EDITOR ENDPOINTLERİ
# ===============================

@app.route('/api/editor/preview-changes', methods=['POST'])
def preview_llm_changes():
    """LLM tarafından yapılan değişiklikleri önizleme"""
    try:
        data = request.get_json()
        file_path = data.get('path')
        template_id = data.get('templateId')
        content = data.get('content', '')
        
        if not file_path or not template_id:
            return jsonify({'error': 'Missing required parameters: path, templateId'}), 400
        
        logger.info(f"Değişiklik önizleme isteği: {file_path}, şablon: {template_id}")
        
        editor_tool = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'in_memory_editor':
                editor_tool = registry.get_tool_by_id(tool_id)
                break
                
        if not editor_tool:
            logger.error("In-memory editor aracı bulunamadı")
            return jsonify({'error': 'In-memory editor tool not found'}), 500
        
        template_result = editor_tool.execute_action('get_change_template', template_name=template_id)
        if template_result.get('status') == 'error':
            logger.error(f"Şablon bulunamadı: {template_id}")
            return jsonify({'error': template_result.get('message', f'Template with ID {template_id} not found')}), 404
        
        template = template_result.get('template', {})
        
        original_content = content
        changes = []
        
        for change in template.get('changes', []):
            change_type = change.get('type')
            start_line = change.get('start_line', 0)
            end_line = change.get('end_line', 0)
            content_to_add = change.get('content', '')
            
            if change_type == 'insert':
                changes.append({
                    'type': 'add',
                    'startLine': start_line,
                    'content': content_to_add,
                    'description': f'Add {len(content_to_add.splitlines())} line(s) at line {start_line}'
                })
            elif change_type == 'replace':
                changes.append({
                    'type': 'replace',
                    'startLine': start_line,
                    'endLine': end_line,
                    'content': content_to_add,
                    'description': f'Replace lines {start_line}-{end_line} with {len(content_to_add.splitlines())} line(s)'
                })
            elif change_type == 'delete':
                changes.append({
                    'type': 'delete',
                    'startLine': start_line,
                    'endLine': end_line,
                    'description': f'Delete lines {start_line}-{end_line}'
                })
        
        temp_filename = f"temp_{file_path.replace('/', '_')}"
        editor_tool.execute_action('create_file', filename=temp_filename)
        editor_tool.execute_action('write_file', filename=temp_filename, content=original_content)
        
        apply_result = editor_tool.execute_action('apply_llm_change', filename=temp_filename, change_template=template)
        
        modified_content = '\n'.join(editor_tool.files.get(temp_filename, []))
        
        editor_tool.files.pop(temp_filename, None)
        
        logger.info(f"Değişiklik önizleme başarılı: {len(changes)} değişiklik")
        return jsonify({
            'success': True,
            'original': original_content,
            'modified': modified_content,
            'changes': changes,
            'templateName': template.get('name', 'Unnamed Template'),
            'templateDescription': template.get('description', '')
        }), 200
        
    except Exception as e:
        logger.error(f"Değişiklik önizleme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===============================
# 9. COMMAND & LLM ENDPOINTLERİ
# ===============================

@app.route('/api/command/execute', methods=['POST'])
def execute_command():
    """Güvenli bir şekilde sistem komutu çalıştır"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        working_dir = data.get('workingDir')
        timeout = data.get('timeout', 30)
        
        if not command:
            return jsonify({'error': 'Empty command'}), 400
        
        current_os = platform.system()
        
        dangerous_commands = []
        
        if current_os == 'Windows':
            dangerous_commands = [
                'rmdir /s /q C:', 'del /f /s /q C:', 'format C:', 
                'rd /s /q C:', '> C:', 'del /f /s /q', 
                'format', 'shutdown', 'rd /s /q', 'reg delete',
                'wmic process call create', 'net user', 'taskkill /f',
                'rundll32', 'wmic process delete', 'vssadmin delete shadows'
            ]
        else:
            dangerous_commands = [
                'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'rm -rf .', 
                'dd if=/dev/zero', 'mkfs', ':(){:|:&};:', '> /dev/sda',
                'chmod -R 777 /', 'mv /* /dev/null', 'wget -O- | sh',
                'curl | sh', '$(curl', '$(wget', 'eval', 'sudo rm'
            ]
        
        for dangerous in dangerous_commands:
            if dangerous in command:
                logger.warning(f"Tehlikeli komut engellendi: {command}")
                return jsonify({'error': 'Dangerous command detected'}), 403
        
        if command.startswith(('file_', 'dir_', 'get_', 'execute_', 'schedule_')):
            return handle_metis_tool_command(command)
        
        logger.info(f"Komut çalıştırılıyor: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode != 0:
                logger.warning(f"Komut hata kodu ile tamamlandı: {process.returncode}")
                return jsonify({
                    'success': False,
                    'output': stderr or stdout,
                    'returnCode': process.returncode
                }), 200
            
            logger.info(f"Komut başarıyla tamamlandı (kod: {process.returncode})")
            return jsonify({
                'success': True,
                'output': stdout,
                'returnCode': process.returncode
            }), 200
            
        except subprocess.TimeoutExpired:
            process.kill()
            logger.warning(f"Komut zaman aşımına uğradı ({timeout} saniye)")
            return jsonify({
                'success': False,
                'output': f'Command timed out after {timeout} seconds',
                'returnCode': -1
            }), 200
            
    except Exception as e:
        logger.error(f"Komut çalıştırma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'output': f'Error executing command: {str(e)}',
            'returnCode': -1
        }), 500

def handle_metis_tool_command(command):
    """Metis Agent'a özel komutları işleyen yardımcı fonksiyon"""
    try:
        cmd_parts = command.split('(')
        cmd_name = cmd_parts[0]
        params = cmd_parts[1].rstrip(')').replace('"', '').split(',')
        
        logger.info(f"Metis özel komutu çalıştırılıyor: {cmd_name} - Parametreler: {params}")
        
        if cmd_name == 'file_list':
            path = params[0].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('list_files', path=path)
            else:
                result = '\n'.join(os.listdir(path))
        
        elif cmd_name == 'file_read':
            path = params[0].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('read_file', path=path)
            else:
                with open(path, 'r') as f:
                    result = f.read()
        
        elif cmd_name == 'file_write':
            path = params[0].strip()
            content = params[1].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('write_file', path=path, content=content)
            else:
                with open(path, 'w') as f:
                    f.write(content)
                result = f"Content written to {path}"
        
        else:
            logger.warning(f"Bilinmeyen Metis Agent komutu: {cmd_name}")
            return jsonify({
                'success': False,
                'output': f'Unknown Metis Agent command: {cmd_name}',
                'returnCode': -1
            }), 400
        
        logger.info(f"Metis özel komutu başarıyla çalıştırıldı: {cmd_name}")
        return jsonify({
            'success': True,
            'output': result,
            'returnCode': 0
        }), 200
        
    except Exception as e:
        logger.error(f"Metis özel komut hatası: {str(e)}")
        return jsonify({
            'success': False,
            'output': f'Error executing Metis Agent command: {str(e)}',
            'returnCode': -1
        }), 500

@app.route('/api/llm/generate-tasks', methods=['POST'])
def generate_tasks():
    """LLM kullanarak metin açıklamadan görevler oluştur"""
    try:
        data = request.get_json()
        user_prompt = data.get('prompt', '')
        provider = data.get('provider', 'openai')
        model = data.get('model', '')
        temperature = data.get('temperature', 0.7)
        
        if not user_prompt:
            return jsonify({'error': 'Empty prompt'}), 400
        
        llm_tool = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'llm_tool':
                llm_tool = registry.get_tool_by_id(tool_id)
                break
                
        if not llm_tool:
            return jsonify({'error': 'LLM Tool not found'}), 500
        
        result = llm_tool.generate_tasks(
            prompt=user_prompt,
            provider=provider,
            model=model,
            temperature=temperature
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result['data']), 200
        
    except Exception as e:
        import traceback
        logger.error(f"Görev oluşturma sırasında beklenmeyen hata: {str(e)}")
        logger.error(f"Hata ayrıntıları: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# ===============================
# 10. LEGACY (CATCH-ALL) ARAÇ ENDPOINTLERİ
# ===============================

@app.route('/api/tools', methods=['GET'])
def list_tools():
    """Tüm kayıtlı araçları listele (eski API, geriye uyumluluk için)"""
    tools = {}
    for tool_id, metadata in registry.get_all_metadata().items():
        tool = registry.get_tool_by_id(tool_id)
        tools[metadata.name] = {
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "actions": list(tool.get_all_actions().keys()) if hasattr(tool, 'get_all_actions') else []
        }
    
    return jsonify({
        "tools": tools
    })

@app.route('/api/<tool_name>/<handler_name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def call_tool_handler(tool_name, handler_name):
    """Bir araç üzerinde belirli bir işleyiciyi çağır (eski API, geriye uyumluluk için)"""
    try:
        kwargs = {}
        
        if request.method == 'GET':
            kwargs = request.args.to_dict()
        else:
            if request.is_json:
                kwargs = request.json
            else:
                kwargs = request.form.to_dict()
                
                if request.files:
                    for name, file in request.files.items():
                        kwargs[name] = file
        
        tool = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == tool_name:
                tool = registry.get_tool_by_id(tool_id)
                break
                
        if not tool:
            return jsonify({"error": f"Araç bulunamadı: {tool_name}"}), 404
            
        if hasattr(tool, 'get_action') and callable(tool.get_action):
            action = tool.get_action(handler_name)
            if not action:
                return jsonify({"error": f"İşleyici bulunamadı: {handler_name}"}), 404
                
            try:
                result = action(**kwargs)
                
                if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
                    return jsonify(result[0]), result[1]
                else:
                    return jsonify(result)
            except Exception as e:
                logger.error(f"İşleyici çağrılırken hata: {tool_name}.{handler_name}, {str(e)}")
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": f"Araç işleyicileri desteklemiyor: {tool_name}"}), 500
                
    except Exception as e:
        logger.error(f"Handler çağrısı sırasında hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ===============================
# 11. WEBSOCKET ROUTE'LARI
# ===============================
@sock.route('/ws/agent')
def agent_websocket(ws):
    """Agent durumu için WebSocket bağlantısı"""
    ws_id = str(uuid.uuid4())
    logger.info(f"WebSocket bağlantısı kuruluyor: {ws_id}")
    
    try:
        ws_handler.add_client(ws_id, ws)
        
        # Welcome message
        welcome_message = {
            'type': 'connected',
            'data': {
                'ws_id': ws_id,
                'message': 'Agent WebSocket bağlantısı kuruldu'
            }
        }
        ws.send(json.dumps(welcome_message))
        
        # Initial state
        personas = db_manager.get_all_personas()
        initial_state = {
            'type': 'initial_state',
            'data': {'personas': personas}
        }
        ws.send(json.dumps(initial_state))
        
        # Message loop
        while True:
            message = ws.receive()
            if message is None:
                break
            
            try:
                data = json.loads(message)
                command = data.get('command')
                logger.info(f"WebSocket komutu alındı: {command}")
                
                if command == 'send_message':
                    persona_id = data.get('persona_id', 'assistant')
                    message_text = data.get('message')
                    
                    logger.info(f"Mesaj gönderiliyor - Persona: {persona_id}, Mesaj: {message_text}")
                    
                    # Hemen basit bir yanıt gönder
                    #response = {
                    #    'type': 'message_response',
                    #    'data': {
                    #        'persona_id': persona_id,
                    #        'message': message_text,
                    #        'response': f"Merhaba! '{message_text}' mesajınızı aldım. İşliyorum...",
                    #        'timestamp': time.time()
                    #    }
                    #}
                    #ws.send(json.dumps(response))
                    
                    # Persona işlemini dene
                    if coordinator_a2a:
                        try:
                            # Önce persona'yı başlat
                            logger.info(f"Persona başlatılıyor: {persona_id}")
                            start_result = run_async(coordinator_a2a.start_persona(persona_id))
                            logger.info(f"Persona başlatma sonucu: {start_result}")
                            
                            # Kısa bir bekleme
                            time.sleep(1)
                            
                            # Mesajı gönder
                            logger.info(f"Persona'ya mesaj gönderiliyor: {persona_id}")
                            result = run_async(coordinator_a2a.send_message_to_persona(
                                persona_id=persona_id,
                                message=message_text,
                                user_id=ws_id
                            ))
                            
                            # Gerçek yanıtı gönder
                            real_response = {
                                'type': 'message_response',
                                'data': {
                                    'persona_id': persona_id,
                                    'message': message_text,
                                    'response': result.get('response', 'Yanıt alınamadı'),
                                    'timestamp': time.time()
                                }
                            }
                            ws.send(json.dumps(real_response))
                            
                        except Exception as e:
                            logger.error(f"Persona mesaj işleme hatası: {str(e)}", exc_info=True)
                            
                            # Hata durumunda basit bir yanıt gönder
                            error_response = {
                                'type': 'message_response',
                                'data': {
                                    'persona_id': persona_id,
                                    'message': message_text,
                                    'response': f"Üzgünüm, şu anda yanıt veremiyorum. Teknik bir sorun var. (Hata: {str(e)})",
                                    'timestamp': time.time()
                                }
                            }
                            ws.send(json.dumps(error_response))
                    else:
                        # A2A protokolü yoksa basit yanıt
                        simple_response = {
                            'type': 'message_response',
                            'data': {
                                'persona_id': persona_id,
                                'message': message_text,
                                'response': "A2A protokolü şu anda kullanılamıyor. Basit bir yanıt: Merhaba, size nasıl yardımcı olabilirim?",
                                'timestamp': time.time()
                            }
                        }
                        ws.send(json.dumps(simple_response))
                
            except json.JSONDecodeError:
                logger.error("Geçersiz JSON")
            except Exception as e:
                logger.error(f"WebSocket mesaj işleme hatası: {str(e)}", exc_info=True)
                
    except Exception as e:
        logger.error(f"WebSocket hatası ({ws_id}): {str(e)}", exc_info=True)
    finally:
        ws_handler.remove_client(ws_id)
        logger.info(f"WebSocket bağlantısı kapatıldı: {ws_id}")

@sock.route('/api/llm/stream/<ws_id>')
def llm_stream(ws, ws_id):
    """LLM stream için WebSocket bağlantısı"""
    try:
        logger.info(f"WebSocket bağlantısı açıldı: {ws_id}")
        
        llm_tool = None
        for tool_id, metadata in registry.get_all_metadata().items():
            if metadata.name == 'llm_tool':
                llm_tool = registry.get_tool_by_id(tool_id)
                break
                
        if not llm_tool:
            logger.error("LLM Tool bulunamadı")
            ws.send(json.dumps({"type": "error", "content": "LLM Tool bulunamadı"}))
            return
            
        msg = ws.receive()
        data = json.loads(msg)
        
        llm_tool.handle_ws_connection(ws, ws_id, data)
        
        try:
            while True:
                msg = ws.receive()
                if msg is None:
                    break
                
                if msg == "stop":
                    break
        except Exception as e:
            logger.error(f"WebSocket veri alma hatası: {str(e)}")
        finally:
            logger.info(f"WebSocket bağlantısı kapatıldı: {ws_id}")
    except Exception as e:
        logger.error(f"WebSocket genel hata: {str(e)}")

# ===============================
# 12. FRONTEND SERVE (EN SON)
# ===============================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """React frontend'i servis et"""
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# ===============================
# 12.5 PLUGIN HANDLERS
# ===============================

@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    """Tüm pluginleri listele"""
    plugins = plugin_registry.get_all_plugins()
    return jsonify({"status": "success", "plugins": plugins})

@app.route('/api/plugins/<plugin_id>', methods=['GET'])
def get_plugin(plugin_id):
    """Belirli bir plugin detayını al"""
    plugin = plugin_registry.get_plugin(plugin_id)
    if not plugin:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    return jsonify({"status": "success", "plugin": plugin})

@app.route('/api/plugins', methods=['POST'])
def register_plugin():
    """Yeni bir plugin kaydet"""
    plugin_info = request.json
    
    try:
        plugin_id = plugin_registry.register_plugin(plugin_info)
        return jsonify({"status": "success", "plugin_id": plugin_id}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/plugins/<plugin_id>', methods=['DELETE'])
def unregister_plugin(plugin_id):
    """Bir plugini kaldır"""
    success = plugin_registry.unregister_plugin(plugin_id)
    if not success:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    return jsonify({"status": "success"})

@app.route('/api/plugins/<plugin_id>/status', methods=['PATCH'])
async def update_plugin_status(plugin_id):
    """Plugin durumunu güncelle (etkinleştir/devre dışı bırak)"""
    data = request.json
    enabled = data.get("enabled", False)
    
    success = await plugin_registry.update_plugin_status(plugin_id, enabled)
    if not success:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    return jsonify({"status": "success", "enabled": enabled})

@app.route('/api/plugins/<plugin_id>/upload', methods=['POST'])
def upload_plugin_file(plugin_id):
    """Plugin için dosya yükle"""
    # Plugin var mı kontrol et
    plugin = plugin_registry.get_plugin(plugin_id)
    if not plugin:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    
    # Dosya yüklenmiş mi kontrol et
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    # Dosya tipini kontrol et
    allowed_extensions = ['.py', '.json']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({"status": "error", "message": f"File type not allowed. Only {', '.join(allowed_extensions)} are allowed"}), 400
    
    # Dosyayı kaydet
    plugin_dir = os.path.join(plugin_registry.plugin_dir, plugin_id)
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
    
    file_path = os.path.join(plugin_dir, file.filename)
    file.save(file_path)
    
    # Plugin bilgilerini güncelle
    if file_ext == '.py':
        plugin["module_path"] = file_path
        if "class_name" not in plugin:
            # Sınıf adını dosya adından tahmin et
            plugin["class_name"] = os.path.splitext(file.filename)[0].replace('_', ' ').title().replace(' ', '')
        
        # Metadata'yı güncelle
        metadata_path = os.path.join(plugin_registry.plugin_dir, "metadata", f"{plugin_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(plugin, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        "status": "success", 
        "message": "File uploaded successfully",
        "file_path": file_path
    })

@app.route('/api/plugins/<plugin_id>/workflow', methods=['POST'])
async def update_plugin_workflow(plugin_id):
    """Plugin iş akışını güncelle"""
    # Plugin var mı kontrol et
    plugin = plugin_registry.get_plugin(plugin_id)
    if not plugin:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    
    data = request.json
    workflow_steps = data.get("workflow_steps", [])
    workflow_transitions = data.get("workflow_transitions", [])
    
    # Plugin bilgilerini güncelle
    await plugin_registry.update_plugin_workflow(plugin_id, workflow_steps, workflow_transitions)
    
    return jsonify({
        "status": "success", 
        "message": "Workflow updated successfully"
    })
# ===============================
# 13. CLEANUP HANDLERS
# ===============================

@app.teardown_appcontext
def shutdown_registry(exception=None):
    """Uygulama kapanırken temizlik yap"""
    pass

# ===============================
# 14. UYGULAMA BAŞLATMA
# ===============================

if __name__ == '__main__':
    try:
        # Event loop'u başlat
        event_loop_manager.ensure_loop()
        
        # A2A protokolünü başlat
        try:
            coordinator_a2a = MCPCoordinatorA2A(coordinator, event_emitter=event_emitter)
            run_async(coordinator_a2a.initialize())
            logger.info("A2A protokolü başlatıldı")
        except Exception as e:
            logger.error(f"A2A protokolü başlatma hatası: {str(e)}")
            coordinator_a2a = None
        
        # WebSocket bridge'i kur
        setup_a2a_websocket_bridge()
        
        # Flask uygulamasını başlat
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') == 'development'
        
        logger.info(f"Metis Agent başlatılıyor (port: {port}, debug: {debug})")
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("Uygulama manuel olarak durduruldu")
    except Exception as e:
        logger.error(f"Uygulama çalıştırılırken hata oluştu: {str(e)}")
    finally:
        # Cleanup
        event_loop_manager.shutdown()
        registry.shutdown_all()


# === Injection'dan eklenen WebSocketManager ===

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, any] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.persona_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self.message_cache = {}
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0
        }

    def add_connection(self, ws_id: str, ws, user_id: str = None):
        self.connections[ws_id] = {
            'ws': ws,
            'user_id': user_id,
            'connected_at': time.time(),
            'last_activity': time.time(),
            'subscriptions': set(),
            'message_count': 0
        }
        if user_id:
            self.user_connections[user_id].add(ws_id)
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.connections)
        logger.info(f"WebSocket bağlantısı eklendi: {ws_id} (kullanıcı: {user_id})")

    def remove_connection(self, ws_id: str):
        if ws_id in self.connections:
            conn = self.connections[ws_id]
            user_id = conn.get('user_id')
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(ws_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            for persona_id in conn.get('subscriptions', set()):
                self.persona_subscribers[persona_id].discard(ws_id)
            del self.connections[ws_id]
            self.stats['active_connections'] = len(self.connections)
            logger.info(f"WebSocket bağlantısı kaldırıldı: {ws_id}")

    def get_connection(self, ws_id: str):
        return self.connections.get(ws_id)

    def update_activity(self, ws_id: str):
        if ws_id in self.connections:
            self.connections[ws_id]['last_activity'] = time.time()
            self.connections[ws_id]['message_count'] += 1

    def subscribe_to_persona(self, ws_id: str, persona_id: str):
        if ws_id in self.connections:
            self.connections[ws_id]['subscriptions'].add(persona_id)
            self.persona_subscribers[persona_id].add(ws_id)

    def broadcast_to_persona_subscribers(self, persona_id: str, message: dict):
        subscribers = self.persona_subscribers.get(persona_id, set())
        for ws_id in subscribers.copy():
            self.send_to_connection(ws_id, message)

    def send_to_connection(self, ws_id: str, message: dict):
        conn = self.get_connection(ws_id)
        if conn and conn['ws']:
            try:
                conn['ws'].send(json.dumps(message))
                self.stats['messages_sent'] += 1
                return True
            except Exception as e:
                logger.error(f"WebSocket mesaj gönderme hatası ({ws_id}): {str(e)}")
                self.stats['errors'] += 1
                self.remove_connection(ws_id)
                return False
        return False

    def send_to_user(self, user_id: str, message: dict):
        ws_ids = self.user_connections.get(user_id, set())
        success_count = 0
        for ws_id in ws_ids.copy():
            if self.send_to_connection(ws_id, message):
                success_count += 1
        return success_count

    def get_stats(self):
        return {
            **self.stats,
            'connections_by_user': {user_id: len(ws_ids) for user_id, ws_ids in self.user_connections.items()},
            'persona_subscribers': {persona_id: len(ws_ids) for persona_id, ws_ids in self.persona_subscribers.items()},
            'active_connections': len(self.connections)
        }


ws_manager = WebSocketManager()

# === Güncellenmiş api_status endpoint ===

@app.route('/api/status', methods=['GET'])
def api_status():
    """API durumunu kontrol et"""
    return jsonify({
        "status": "online",
        "version": "2.1.0",
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_tools": list(registry.get_all_tools().keys()),
        "websocket_connections": ws_manager.stats['active_connections']
    })

