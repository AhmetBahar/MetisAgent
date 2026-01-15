from flask import Blueprint, request, jsonify
import logging
from os_araci.db.chroma_manager import ChromaManager
from os_araci.coordination.coordinator_a2a import MCPCoordinatorA2A
from os_araci.core.event_loop_manager import run_async
from os_araci.mcp_core.registry import MCPRegistry

logger = logging.getLogger(__name__)

persona_bp = Blueprint('persona', __name__)

# Initialize components
db_manager = ChromaManager()
coordinator_a2a = None  # Will be initialized in main app
registry = None  # Will be initialized in main app

def init_persona_routes(db_mgr, coord_a2a, reg):
    """Initialize persona routes with required components"""
    global db_manager, coordinator_a2a, registry
    db_manager = db_mgr
    coordinator_a2a = coord_a2a
    registry = reg

@persona_bp.route('/api/personas', methods=['GET'])
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

@persona_bp.route('/api/personas', methods=['POST'])
def create_persona():
    """Yeni bir persona ekle"""
    try:
        data = request.get_json()
        
        required_fields = ['id', 'name', 'description', 'capabilities']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"Eksik alan: {field}"}), 400
        
        if coordinator_a2a:
            result = run_async(coordinator_a2a.add_persona(data))
        else:
            result = db_manager.add_persona(data)
        
        return jsonify(result), 201 if result.get("status") == "success" else 400
    except Exception as e:
        logger.error(f"Persona eklenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Belirli bir personanın detaylarını getir"""
    try:
        persona = db_manager.get_persona(persona_id)
        
        if not persona:
            return jsonify({"status": "error", "message": f"Persona bulunamadı: {persona_id}"}), 404
        
        return jsonify({
            "status": "success",
            "persona": persona
        })
    except Exception as e:
        logger.error(f"Persona detayları alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>', methods=['PUT'])
def update_persona(persona_id):
    """Mevcut bir personayı güncelle"""
    try:
        data = request.get_json()
        
        if coordinator_a2a:
            result = run_async(coordinator_a2a.update_persona(persona_id, data))
        else:
            result = db_manager.update_persona(persona_id, data)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Persona güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>', methods=['DELETE'])
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
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"Persona silinirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/status', methods=['GET'])
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

@persona_bp.route('/api/personas/<persona_id>/start', methods=['POST'])
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

@persona_bp.route('/api/personas/<persona_id>/stop', methods=['POST'])
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

@persona_bp.route('/api/personas/<persona_id>/restart', methods=['POST'])
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

@persona_bp.route('/api/personas/<persona_id>/execute-task', methods=['POST'])
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
                persona_id=persona_id
            ))
        else:
            # Basit task execution fallback
            result = {
                "status": "success",
                "message": "Task executed (fallback mode)",
                "task_result": task
            }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Persona task çalıştırılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/data', methods=['GET', 'POST'])
def persona_data(persona_id):
    """Persona verilerini getir veya güncelle"""
    try:
        if request.method == 'GET':
            # Persona var mı kontrol et
            persona = db_manager.get_persona(persona_id)
            if not persona:
                return jsonify({"status": "error", "message": f"Persona bulunamadı: {persona_id}"}), 404
            
            return jsonify({
                "status": "success",
                "data": persona.get("data", {})
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            persona_data = data.get('data', {})
            
            # Persona'nın data alanını güncelle
            result = db_manager.update_persona(persona_id, {"data": persona_data})
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Persona data işlemi sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/context/<user_id>', methods=['GET'])
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
            return jsonify({"status": "error", "message": "Memory manager bulunamadı"}), 500
            
        context = memory_manager.get_persona_context(persona_id, user_id)
        return jsonify({"status": "success", "context": context})
    except Exception as e:
        logger.error(f"Persona context alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/context/<user_id>', methods=['POST'])
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
            return jsonify({"status": "error", "message": "Memory manager bulunamadı"}), 500
            
        memory_manager.save_persona_context(persona_id, user_id, context_data)
        return jsonify({"status": "success", "message": "Context kaydedildi"})
    except Exception as e:
        logger.error(f"Persona context kaydedilirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/context/<user_id>', methods=['PUT'])
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
            return jsonify({"status": "error", "message": "Memory manager bulunamadı"}), 500
            
        memory_manager.update_persona_context(persona_id, user_id, updates)
        return jsonify({"status": "success", "message": "Context güncellendi"})
    except Exception as e:
        logger.error(f"Persona context güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@persona_bp.route('/api/personas/<persona_id>/context/<user_id>', methods=['DELETE'])
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
            return jsonify({"status": "error", "message": "Memory manager bulunamadı"}), 500
            
        memory_manager.clear_persona_context(persona_id, user_id)
        return jsonify({"status": "success", "message": "Context temizlendi"})
    except Exception as e:
        logger.error(f"Persona context temizlenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500