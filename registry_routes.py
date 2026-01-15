"""
Registry Routes Module
Extracted from app_old.py - Contains all registry-related API endpoints
"""

from flask import Flask, request, jsonify, send_from_directory, make_response
import json
import os
import datetime
import logging
from typing import Dict, Any, Optional
from os_araci.mcp_core.registry import MCPRegistry, ToolSourceType

# Configure logging
logger = logging.getLogger(__name__)

def create_registry_routes(app: Flask, registry: MCPRegistry):
    """
    Register all registry-related routes with the Flask app
    
    Args:
        app: Flask application instance
        registry: MCPRegistry instance
    """
    
    @app.route('/api/registry/ping', methods=['GET'])
    def registry_ping():
        """Basit ping endpoint'i"""
        return jsonify({
            "status": "success",
            "message": "pong",
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

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
            logger.error(f"Şema alınırken hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Return the route names for reference
    return [
        'registry_ping',
        'list_registered_tools',
        'get_tool_details',
        'get_tool_actions',
        'get_action_details',
        'call_tool_action',
        'remove_tool',
        'add_external_tool',
        'add_remote_tool',
        'sync_remote_tools',
        'list_capabilities',
        'list_categories',
        'export_registry',
        'import_registry',
        'check_tool_health',
        'get_registry_health',
        'registry_handshake',
        'get_registry_schema'
    ]