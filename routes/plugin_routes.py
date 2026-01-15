from flask import Blueprint, request, jsonify
import logging
import os
from werkzeug.utils import secure_filename
from os_araci.plugins.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)

plugin_bp = Blueprint('plugin', __name__)

# Initialize components
plugin_registry = None  # Will be initialized in main app

def init_plugin_routes(registry):
    """Initialize plugin routes with required components"""
    global plugin_registry
    plugin_registry = registry

@plugin_bp.route('/api/plugins', methods=['GET'])
def list_plugins():
    """Tüm pluginleri listele"""
    try:
        plugins = plugin_registry.get_all_plugins()
        return jsonify({"status": "success", "plugins": plugins})
    except Exception as e:
        logger.error(f"Pluginler listelenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins', methods=['POST'])
def register_plugin():
    """Yeni bir plugin kaydet"""
    try:
        plugin_info = request.json
        
        plugin_id = plugin_registry.register_plugin(plugin_info)
        return jsonify({"status": "success", "plugin_id": plugin_id}), 201
    except ValueError as e:
        logger.error(f"Plugin kaydedilirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Plugin kaydedilirken beklenmeyen hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>', methods=['GET'])
def get_plugin(plugin_id):
    """Belirli bir plugin detayını al"""
    try:
        plugin = plugin_registry.get_plugin(plugin_id)
        if not plugin:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        return jsonify({"status": "success", "plugin": plugin})
    except Exception as e:
        logger.error(f"Plugin detayları alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>', methods=['DELETE'])
def unregister_plugin(plugin_id):
    """Bir plugini kaldır"""
    try:
        success = plugin_registry.unregister_plugin(plugin_id)
        if not success:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Plugin kaldırılırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>/status', methods=['GET'])
def get_plugin_status(plugin_id):
    """Plugin durumunu getir"""
    try:
        plugin = plugin_registry.get_plugin(plugin_id)
        if not plugin:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        
        return jsonify({
            "status": "success", 
            "enabled": plugin.get("enabled", False),
            "plugin_status": plugin.get("status", "unknown")
        })
    except Exception as e:
        logger.error(f"Plugin durumu alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>/status', methods=['PATCH'])
async def update_plugin_status(plugin_id):
    """Plugin durumunu güncelle (etkinleştir/devre dışı bırak)"""
    try:
        data = request.json
        enabled = data.get("enabled", False)
        
        success = await plugin_registry.update_plugin_status(plugin_id, enabled)
        if not success:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        return jsonify({"status": "success", "enabled": enabled})
    except Exception as e:
        logger.error(f"Plugin durumu güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>/upload', methods=['POST'])
def upload_plugin_file(plugin_id):
    """Plugin için dosya yükle"""
    try:
        # Plugin var mı kontrol et
        plugin = plugin_registry.get_plugin(plugin_id)
        if not plugin:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        
        # Dosya yüklenmiş mi kontrol et
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        if file:
            # Güvenli dosya adı oluştur
            filename = secure_filename(file.filename)
            
            # Plugin dizinini oluştur
            plugin_dir = os.path.join("./plugins", plugin_id)
            os.makedirs(plugin_dir, exist_ok=True)
            
            # Dosyayı kaydet
            file_path = os.path.join(plugin_dir, filename)
            file.save(file_path)
            
            return jsonify({
                "status": "success", 
                "message": "File uploaded successfully",
                "file_path": file_path,
                "filename": filename
            })
    except Exception as e:
        logger.error(f"Dosya yüklenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>/workflow', methods=['GET'])
def get_plugin_workflow(plugin_id):
    """Plugin iş akışını getir"""
    try:
        plugin = plugin_registry.get_plugin(plugin_id)
        if not plugin:
            return jsonify({"status": "error", "message": "Plugin not found"}), 404
        
        workflow = plugin.get("workflow", {})
        return jsonify({
            "status": "success",
            "workflow": workflow
        })
    except Exception as e:
        logger.error(f"Plugin workflow alınırken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@plugin_bp.route('/api/plugins/<plugin_id>/workflow', methods=['POST'])
async def update_plugin_workflow(plugin_id):
    """Plugin iş akışını güncelle"""
    try:
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
    except Exception as e:
        logger.error(f"Plugin workflow güncellenirken hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500