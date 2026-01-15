"""
Plugin Management Routes - Frontend dashboard ve API endpoints
"""

from flask import Blueprint, request, jsonify, render_template
import logging
from .mcp_core import registry

logger = logging.getLogger(__name__)

# Create plugin management blueprint
plugin_bp = Blueprint('plugins', __name__, url_prefix='/plugins')

@plugin_bp.route('/dashboard')
def plugin_dashboard():
    """Plugin management dashboard"""
    return render_template('plugin_dashboard.html')

@plugin_bp.route('/api/tools/internal')
def get_internal_tools():
    """Get list of internal (core) tools"""
    try:
        from tools import get_internal_tools
        internal_tool_names = get_internal_tools()
        
        tools = []
        for tool_name in internal_tool_names:
            tool = registry.get_tool(tool_name)
            if tool:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "version": tool.version,
                    "capabilities": tool.capabilities,
                    "actions": list(tool.actions.keys()),
                    "enabled": tool.is_enabled
                })
            else:
                tools.append({
                    "name": tool_name,
                    "description": "Core system tool",
                    "version": "system",
                    "capabilities": [],
                    "actions": [],
                    "enabled": True
                })
        
        return jsonify({
            "success": True,
            "tools": tools,
            "count": len(tools)
        })
        
    except Exception as e:
        logger.error(f"Error getting internal tools: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "tools": [],
            "count": 0
        })

@plugin_bp.route('/api/tools/external')
def get_external_tools():
    """Get list of external (plugin) tools"""
    try:
        from tools import get_external_tools
        external_tool_names = get_external_tools()
        
        tools = []
        for tool_name in external_tool_names:
            tool = registry.get_tool(tool_name)
            if tool:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "version": tool.version,
                    "capabilities": tool.capabilities,
                    "actions": list(tool.actions.keys()),
                    "enabled": tool.is_enabled
                })
            else:
                tools.append({
                    "name": tool_name,
                    "description": "External plugin tool",
                    "version": "unknown",
                    "capabilities": [],
                    "actions": [],
                    "enabled": False
                })
        
        return jsonify({
            "success": True,
            "tools": tools,
            "count": len(tools)
        })
        
    except Exception as e:
        logger.error(f"Error getting external tools: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "tools": [],
            "count": 0
        })

@plugin_bp.route('/api/<action>', methods=['POST'])
def plugin_api(action):
    """Generic plugin management API endpoint"""
    try:
        data = request.get_json()
        
        # Get tool manager from registry
        tool_manager = registry.get_tool('tool_manager')
        if not tool_manager:
            return jsonify({
                "success": False,
                "error": "Tool manager not available"
            })
        
        # Extract parameters
        tool_name = data.get('tool')
        action_name = data.get('action')
        
        if tool_name != 'tool_manager':
            return jsonify({
                "success": False,
                "error": "Invalid tool name"
            })
        
        # Execute the action
        result = tool_manager.execute_action(
            action_name,
            **{k: v for k, v in data.items() if k not in ['tool', 'action']}
        )
        
        return jsonify({
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "metadata": result.metadata
        })
        
    except Exception as e:
        logger.error(f"Plugin API error for action {action}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@plugin_bp.route('/api/system/status')
def system_status():
    """Get plugin system status"""
    try:
        # Get tool manager for system info
        tool_manager = registry.get_tool('tool_manager')
        
        if tool_manager:
            health_result = tool_manager.health_check()
            health_data = health_result.data if health_result.success else {}
        else:
            health_data = {"status": "tool_manager_not_available"}
        
        # Get plugin loader status
        try:
            from plugins.plugin_loader import get_plugin_loader
            plugin_loader = get_plugin_loader()
            plugins = plugin_loader.list_plugins()
            plugin_status = {
                "available": True,
                "total_plugins": len(plugins),
                "enabled_plugins": len([p for p in plugins if p.get("enabled", False)]),
                "loaded_plugins": len([p for p in plugins if p.get("loaded", False)])
            }
        except Exception as e:
            plugin_status = {
                "available": False,
                "error": str(e)
            }
        
        # Get registry status
        registry_tools = list(registry.tools.keys())
        
        return jsonify({
            "success": True,
            "data": {
                "tool_manager": health_data,
                "plugin_loader": plugin_status,
                "registry": {
                    "total_tools": len(registry_tools),
                    "tools": registry_tools
                },
                "system_healthy": health_data.get("status") == "healthy"
            }
        })
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

# Plugin template creation route
@plugin_bp.route('/api/create_template', methods=['POST'])
def create_plugin_template():
    """Create a new plugin template"""
    try:
        data = request.get_json()
        plugin_name = data.get('plugin_name')
        plugin_dir = data.get('plugin_dir')
        
        if not plugin_name:
            return jsonify({
                "success": False,
                "error": "Plugin name is required"
            })
        
        from plugins.plugin_loader import get_plugin_loader
        plugin_loader = get_plugin_loader()
        
        success = plugin_loader.create_plugin_template(plugin_name, plugin_dir)
        
        if success:
            return jsonify({
                "success": True,
                "data": {
                    "message": f"Plugin template '{plugin_name}' created successfully",
                    "plugin_name": plugin_name
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create plugin template"
            })
            
    except Exception as e:
        logger.error(f"Template creation error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })