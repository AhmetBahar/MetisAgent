"""
LLM routes - LLM integration and task generation
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_llm_routes(app, coordinator=None):
    """Register LLM integration routes"""
    
    @app.route('/api/llm/generate-tasks', methods=['POST'])
    def generate_tasks():
        """LLM ile görev oluştur API endpoint'i"""
        try:
            data = request.get_json()
            prompt = data.get('prompt', '')
            
            if not prompt:
                return jsonify({"status": "error", "message": "Prompt required"}), 400
            
            if coordinator:
                result = coordinator.generate_tasks_with_llm(prompt)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
                
        except Exception as e:
            logger.error(f"LLM görev oluşturulurken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("LLM routes registered")