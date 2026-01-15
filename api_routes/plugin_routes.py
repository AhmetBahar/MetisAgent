"""
Plugin routes - plugin management and workflow
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_plugin_routes(app, plugin_registry=None):
    """Register plugin management routes"""
    
    @app.route('/api/plugins', methods=['GET'])
    def get_plugins():
        """Tüm eklentileri listele"""
        try:
            if plugin_registry:
                plugins = plugin_registry.get_all_plugins()
                return jsonify({
                    "status": "success",
                    "plugins": plugins
                })
            else:
                return jsonify({
                    "status": "success",
                    "plugins": []
                })
        except Exception as e:
            logger.error(f"Eklentiler listelenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins', methods=['POST'])
    def register_plugin():
        """Yeni eklenti kaydet"""
        try:
            data = request.get_json()
            plugin_config = data.get('plugin_config', {})
            
            if not plugin_config:
                return jsonify({"status": "error", "message": "Plugin configuration required"}), 400
            
            if plugin_registry:
                result = plugin_registry.register_plugin(plugin_config)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
                
        except Exception as e:
            logger.error(f"Eklenti kaydedilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>', methods=['GET'])
    def get_plugin(plugin_id):
        """Eklenti detaylarını getir"""
        try:
            if plugin_registry:
                plugin = plugin_registry.get_plugin(plugin_id)
                if plugin:
                    return jsonify({
                        "status": "success",
                        "plugin": plugin
                    })
                else:
                    return jsonify({"status": "error", "message": "Plugin not found"}), 404
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>', methods=['DELETE'])
    def unregister_plugin(plugin_id):
        """Eklenti kaydını sil"""
        try:
            if plugin_registry:
                result = plugin_registry.unregister_plugin(plugin_id)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti kaydı silinirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>/status', methods=['GET'])
    def get_plugin_status(plugin_id):
        """Eklenti durumunu getir"""
        try:
            if plugin_registry:
                status = plugin_registry.get_plugin_status(plugin_id)
                return jsonify({
                    "status": "success",
                    "plugin_status": status
                })
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti durumu getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>/status', methods=['PATCH'])
    def update_plugin_status(plugin_id):
        """Eklenti durumunu güncelle"""
        try:
            data = request.get_json()
            new_status = data.get('status')
            
            if not new_status:
                return jsonify({"status": "error", "message": "Status required"}), 400
            
            if plugin_registry:
                result = plugin_registry.update_plugin_status(plugin_id, new_status)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti durumu güncellenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>/upload', methods=['POST'])
    def upload_plugin_file(plugin_id):
        """Eklenti dosyası yükle"""
        try:
            if 'file' not in request.files:
                return jsonify({"status": "error", "message": "No file provided"}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({"status": "error", "message": "No file selected"}), 400
            
            if plugin_registry:
                result = plugin_registry.upload_plugin_file(plugin_id, file)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
                
        except Exception as e:
            logger.error(f"Eklenti dosyası yüklenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>/workflow', methods=['GET'])
    def get_plugin_workflow(plugin_id):
        """Eklenti iş akışını getir"""
        try:
            if plugin_registry:
                workflow = plugin_registry.get_plugin_workflow(plugin_id)
                return jsonify({
                    "status": "success",
                    "workflow": workflow
                })
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti iş akışı getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/plugins/<plugin_id>/workflow', methods=['POST'])
    def update_plugin_workflow(plugin_id):
        """Eklenti iş akışını güncelle"""
        try:
            data = request.get_json()
            workflow_data = data.get('workflow', {})
            
            if plugin_registry:
                result = plugin_registry.update_plugin_workflow(plugin_id, workflow_data)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Plugin registry not available"}), 500
        except Exception as e:
            logger.error(f"Eklenti iş akışı güncellenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("Plugin routes registered")