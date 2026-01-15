"""
Core API routes - status, test, basic functionality
"""
from flask import jsonify, request, make_response
import datetime
import logging

logger = logging.getLogger(__name__)

def register_core_routes(app, registry=None, coordinator=None):
    """Register core API routes"""
    
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
            "active_tools": list(registry.get_all_tools().keys()) if registry else []
        })

    @app.route('/api/routes', methods=['GET'])
    def list_routes():
        """Mevcut API rotalarını listele"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        return jsonify({"routes": routes})

    @app.route('/api/tools', methods=['GET'])
    def list_tools():
        """Mevcut MCP araçlarını listele"""
        if not registry:
            return jsonify({"error": "Registry not initialized"}), 500
        
        try:
            tools = registry.list_tools()
            return jsonify({"tools": tools})
        except Exception as e:
            logger.error(f"Araçlar listelenirken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/execute', methods=['POST'])
    def execute_tool():
        """MCP aracı çalıştır"""
        if not coordinator:
            return jsonify({"error": "Coordinator not initialized"}), 500
        
        try:
            data = request.json
            tool_name = data.get('tool_name')
            arguments = data.get('arguments', {})
            
            if not tool_name:
                return jsonify({"error": "tool_name required"}), 400
                
            result = coordinator.execute_tool(tool_name, arguments)
            return jsonify({"result": result})
            
        except Exception as e:
            logger.error(f"Araç çalıştırılırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    logger.info("Core routes registered")