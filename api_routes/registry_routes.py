"""
Registry routes - MCP tool registry management
"""
from flask import request, jsonify
import datetime
import logging
from os_araci.mcp_core.registry import ToolSourceType

logger = logging.getLogger(__name__)

def register_registry_routes(app, registry):
    """Register registry management routes"""
    
    @app.route('/api/registry/ping', methods=['GET'])
    def registry_ping():
        """Basit ping endpoint'i"""
        return jsonify({
            "status": "success",
            "message": "pong",
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    @app.route('/api/registry/tools', methods=['GET'])
    def get_registry_tools():
        """Kayıtlı araçları listele"""
        try:
            source_type_filter = request.args.get('source_type')
            category_filter = request.args.get('category')
            capability_filter = request.args.get('capability')
            
            tools = registry.get_all_tools()
            
            # Filtreleme işlemleri
            if source_type_filter:
                try:
                    source_type = ToolSourceType(source_type_filter.upper())
                    tools = {k: v for k, v in tools.items() if v.get('source_type') == source_type}
                except ValueError:
                    return jsonify({"error": f"Invalid source_type: {source_type_filter}"}), 400
            
            if category_filter:
                tools = {k: v for k, v in tools.items() if category_filter.lower() in [cat.lower() for cat in v.get('categories', [])]}
            
            if capability_filter:
                tools = {k: v for k, v in tools.items() if capability_filter.lower() in [cap.lower() for cap in v.get('capabilities', [])]}
            
            return jsonify({
                "status": "success",
                "tools": {k: {
                    "name": v.get('name', k),
                    "description": v.get('description', ''),
                    "categories": v.get('categories', []),
                    "capabilities": v.get('capabilities', []),
                    "source_type": v.get('source_type', ToolSourceType.LOCAL).name if hasattr(v.get('source_type'), 'name') else str(v.get('source_type', 'LOCAL')),
                    "actions": list(v.get('actions', {}).keys()) if isinstance(v.get('actions'), dict) else []
                } for k, v in tools.items()},
                "count": len(tools)
            })
        except Exception as e:
            logger.error(f"Registry tools alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/tool/<tool_id>', methods=['GET', 'DELETE'])
    def handle_tool(tool_id):
        """Araç detayı getir veya aracı kaldır"""
        if request.method == 'GET':
            try:
                tool = registry.get_tool(tool_id)
                if not tool:
                    return jsonify({"error": f"Tool not found: {tool_id}"}), 404
                
                return jsonify({
                    "status": "success",
                    "tool": {
                        "id": tool_id,
                        "name": tool.get('name', tool_id),
                        "description": tool.get('description', ''),
                        "categories": tool.get('categories', []),
                        "capabilities": tool.get('capabilities', []),
                        "source_type": tool.get('source_type', ToolSourceType.LOCAL).name if hasattr(tool.get('source_type'), 'name') else str(tool.get('source_type', 'LOCAL')),
                        "actions": tool.get('actions', {}),
                        "metadata": tool.get('metadata', {})
                    }
                })
            except Exception as e:
                logger.error(f"Tool bilgisi alınırken hata: {str(e)}")
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'DELETE':
            try:
                success = registry.remove_tool(tool_id)
                if success:
                    return jsonify({
                        "status": "success",
                        "message": f"Tool removed: {tool_id}"
                    })
                else:
                    return jsonify({"error": f"Failed to remove tool: {tool_id}"}), 400
            except Exception as e:
                logger.error(f"Tool kaldırılırken hata: {str(e)}")
                return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/tool/<tool_id>/actions', methods=['GET'])
    def get_tool_actions(tool_id):
        """Araç eylemlerini listele"""
        try:
            tool = registry.get_tool(tool_id)
            if not tool:
                return jsonify({"error": f"Tool not found: {tool_id}"}), 404
            
            actions = tool.get('actions', {})
            return jsonify({
                "status": "success",
                "tool_id": tool_id,
                "actions": actions
            })
        except Exception as e:
            logger.error(f"Tool actions alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/tool/<tool_id>/action/<action_name>', methods=['GET'])
    def get_action_details(tool_id, action_name):
        """Eylem detaylarını getir"""
        try:
            tool = registry.get_tool(tool_id)
            if not tool:
                return jsonify({"error": f"Tool not found: {tool_id}"}), 404
            
            actions = tool.get('actions', {})
            if action_name not in actions:
                return jsonify({"error": f"Action not found: {action_name}"}), 404
            
            return jsonify({
                "status": "success",
                "tool_id": tool_id,
                "action_name": action_name,
                "action": actions[action_name]
            })
        except Exception as e:
            logger.error(f"Action detayı alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/tool/<tool_id>/health', methods=['GET'])
    def check_tool_health(tool_id):
        """Araç sağlık durumunu kontrol et"""
        try:
            health_status = registry.check_tool_health(tool_id)
            return jsonify({
                "status": "success",
                "tool_id": tool_id,
                "health": health_status
            })
        except Exception as e:
            logger.error(f"Tool health check sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/call/<tool_id>/<action_name>', methods=['POST'])
    def call_tool_action(tool_id, action_name):
        """Araç eylemini çağır"""
        try:
            data = request.get_json() or {}
            arguments = data.get('arguments', {})
            
            result = registry.call_tool_action(tool_id, action_name, arguments)
            return jsonify({
                "status": "success",
                "tool_id": tool_id,
                "action_name": action_name,
                "result": result
            })
        except Exception as e:
            logger.error(f"Tool action çağırılırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/capabilities', methods=['GET'])
    def get_all_capabilities():
        """Tüm yetenekleri listele"""
        try:
            capabilities = registry.get_all_capabilities()
            return jsonify({
                "status": "success",
                "capabilities": capabilities
            })
        except Exception as e:
            logger.error(f"Capabilities alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/categories', methods=['GET'])
    def get_all_categories():
        """Tüm kategorileri listele"""
        try:
            categories = registry.get_all_categories()
            return jsonify({
                "status": "success",
                "categories": categories
            })
        except Exception as e:
            logger.error(f"Categories alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/schema', methods=['GET'])
    def get_api_schema():
        """API şemasını döndür"""
        try:
            schema = registry.get_api_schema()
            return jsonify(schema)
        except Exception as e:
            logger.error(f"API schema alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/health', methods=['GET'])
    def get_registry_health():
        """Registry sağlık durumu"""
        try:
            health = registry.get_health_status()
            return jsonify({
                "status": "success",
                "health": health
            })
        except Exception as e:
            logger.error(f"Registry health check sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/handshake', methods=['POST'])
    def mcp_handshake():
        """MCP handshake endpoint'i"""
        try:
            data = request.get_json() or {}
            protocol_version = data.get('protocol_version', '1.0')
            client_info = data.get('client_info', {})
            
            response = registry.handle_handshake(protocol_version, client_info)
            return jsonify(response)
        except Exception as e:
            logger.error(f"MCP handshake sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/export', methods=['GET'])
    def export_registry():
        """Registry yapılandırmasını dışa aktar"""
        try:
            config = registry.export_configuration()
            return jsonify({
                "status": "success",
                "configuration": config
            })
        except Exception as e:
            logger.error(f"Registry export sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/import', methods=['POST'])
    def import_registry():
        """Registry yapılandırmasını içe aktar"""
        try:
            data = request.get_json() or {}
            config = data.get('configuration', {})
            
            if not config:
                return jsonify({"error": "Configuration data required"}), 400
            
            success = registry.import_configuration(config)
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Configuration imported successfully"
                })
            else:
                return jsonify({"error": "Failed to import configuration"}), 400
        except Exception as e:
            logger.error(f"Registry import sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/external/add', methods=['POST'])
    def add_external_tool():
        """External araç ekle"""
        try:
            data = request.get_json() or {}
            tool_config = data.get('tool_config', {})
            
            if not tool_config:
                return jsonify({"error": "Tool configuration required"}), 400
            
            success = registry.add_external_tool(tool_config)
            if success:
                return jsonify({
                    "status": "success",
                    "message": "External tool added successfully"
                })
            else:
                return jsonify({"error": "Failed to add external tool"}), 400
        except Exception as e:
            logger.error(f"External tool eklenirken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/remote/add', methods=['POST'])
    def add_remote_tool():
        """Remote araç ekle"""
        try:
            data = request.get_json() or {}
            remote_config = data.get('remote_config', {})
            
            if not remote_config:
                return jsonify({"error": "Remote configuration required"}), 400
            
            success = registry.add_remote_tool(remote_config)
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Remote tool added successfully"
                })
            else:
                return jsonify({"error": "Failed to add remote tool"}), 400
        except Exception as e:
            logger.error(f"Remote tool eklenirken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/registry/remote/sync', methods=['POST'])
    def sync_remote_tools():
        """Remote araçları senkronize et"""
        try:
            data = request.get_json() or {}
            force_sync = data.get('force', False)
            
            result = registry.sync_remote_tools(force_sync)
            return jsonify({
                "status": "success",
                "sync_result": result
            })
        except Exception as e:
            logger.error(f"Remote tools sync sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    logger.info("Registry routes registered")