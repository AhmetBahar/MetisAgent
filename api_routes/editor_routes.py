"""
Editor routes - in-memory text editor functionality
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_editor_routes(app, registry=None):
    """Register editor routes"""
    
    @app.route('/api/editor/preview-changes', methods=['POST'])
    def preview_editor_changes():
        """Editör değişikliklerini önizle API endpoint'i"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400
            
            if registry:
                result = registry.execute_tool("text_editor", {
                    "action": "preview_changes",
                    "data": data
                })
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Registry not available"}), 500
                
        except Exception as e:
            logger.error(f"Editör önizleme sırasında hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("Editor routes registered")