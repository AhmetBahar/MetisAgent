"""
A2A (Agent-to-Agent) routes - agent communication and task management
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_a2a_routes(app, coordinator_a2a=None):
    """Register A2A communication routes"""
    
    @app.route('/api/a2a/task', methods=['POST'])
    def handle_a2a_task():
        """A2A görev işle API endpoint'i"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400
            
            if coordinator_a2a:
                result = coordinator_a2a.handle_a2a_task(data)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "A2A coordinator not available"}), 500
                
        except Exception as e:
            logger.error(f"A2A görev işlenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("A2A routes registered")