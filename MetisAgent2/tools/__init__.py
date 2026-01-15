"""
Tools package - Contains all MCP tools for MetisAgent2
Organized with internal (core system) and external (plugin) tools
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

def register_all_tools(registry):
    """Register all available tools with the registry - internal + external"""
    tools_registered = []
    
    # First, register INTERNAL (core system) tools
    internal_tools = register_internal_tools(registry)
    tools_registered.extend(internal_tools)
    
    # Then, register EXTERNAL (plugin) tools
    external_tools = register_external_tools(registry)
    tools_registered.extend(external_tools)
    
    logger.info(f"Tool registration complete: {len(internal_tools)} internal + {len(external_tools)} external = {len(tools_registered)} total")
    
    return tools_registered

def register_internal_tools(registry) -> List[str]:
    """Register INTERNAL (core system) tools that are always available"""
    tools_registered = []
    
    logger.info("🏗️  Registering INTERNAL tools...")
    
    try:
        # Core Infrastructure Tools
        from .internal.graph_memory_tool import register_tool as register_graph_memory
        if register_graph_memory(registry):
            tools_registered.append("graph_memory")
            
        from .internal.llm_tool import register_tool as register_llm_tool
        if register_llm_tool(registry):
            tools_registered.append("llm_tool")
            
        from .internal.sequential_thinking_tool import register_tool as register_sequential_thinking
        if register_sequential_thinking(registry):
            tools_registered.append("sequential_thinking")
            
        from .internal.settings_manager import register_tool as register_settings_manager
        if register_settings_manager(registry):
            tools_registered.append("settings_manager")
            
        from .internal.todo_manager import register_tool as register_todo_manager
        if register_todo_manager(registry):
            tools_registered.append("todo_manager")
            
        # System Operations Tools
        from .internal.command_executor import register_tool as register_command_executor
        if register_command_executor(registry):
            tools_registered.append("command_executor")
            
        from .internal.google_oauth2_manager import register_tool as register_google_oauth2_manager
        if register_google_oauth2_manager(registry):
            tools_registered.append("google_oauth2_manager")
            
        from .internal.user_clarification_tool import register_tool as register_user_clarification
        if register_user_clarification(registry):
            tools_registered.append("user_clarification")
            
        logger.info(f"✅ INTERNAL tools registered: {tools_registered}")
        
    except Exception as e:
        logger.error(f"❌ Error registering internal tools: {e}")
        
    return tools_registered

def register_external_tools(registry) -> List[str]:
    """Register EXTERNAL (plugin) tools that can be dynamically loaded"""
    tools_registered = []
    
    logger.info("🔌 Registering EXTERNAL tools...")
    
    try:
        # STATIC EXTERNAL TOOLS (hardcoded)
        static_tools = _register_static_external_tools(registry)
        tools_registered.extend(static_tools)
        
        # DYNAMIC PLUGIN TOOLS (from installed plugins)
        plugin_tools = _register_plugin_tools(registry)
        tools_registered.extend(plugin_tools)
            
        logger.info(f"✅ EXTERNAL tools registered: {tools_registered}")
        
    except Exception as e:
        logger.error(f"❌ Error registering external tools: {e}")
        
    return tools_registered

def _register_static_external_tools(registry) -> List[str]:
    """Register static external tools (hardcoded in tools/external/)"""
    tools_registered = []
    
    try:
        # Communication & Productivity Tools
        from .external.gmail_helper_tool import register_tool as register_gmail_helper
        if register_gmail_helper(registry):
            tools_registered.append("gmail_helper")
            
        from .external.google_calendar_tool import register_tool as register_google_calendar
        if register_google_calendar(registry):
            tools_registered.append("google_calendar")
            
        from .external.google_drive_tool import register_tool as register_google_drive
        if register_google_drive(registry):
            tools_registered.append("google_drive")
            
        # Web & Automation Tools  
        from .external.selenium_browser import register_tool as register_selenium_browser
        if register_selenium_browser(registry):
            tools_registered.append("selenium_browser")
            
        # Creative & Media Tools
        from .external.simple_visual_creator import register_tool as register_simple_visual_creator
        if register_simple_visual_creator(registry):
            tools_registered.append("simple_visual_creator")
            
    except Exception as e:
        logger.error(f"❌ Error registering static external tools: {e}")
        
    return tools_registered

def _register_plugin_tools(registry) -> List[str]:
    """Register dynamic plugin tools from plugins/installed/"""
    tools_registered = []
    
    try:
        import json
        import sys
        import importlib.util
        
        # Load plugin manifest
        manifest_path = os.path.join(os.getcwd(), "plugins", "installed", "plugin_manifest.json")
        if not os.path.exists(manifest_path):
            logger.warning("Plugin manifest not found, skipping dynamic plugin loading")
            return tools_registered
            
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        for plugin in manifest.get("plugins", []):
            if not plugin.get("enabled", False):
                logger.info(f"Plugin {plugin['name']} is disabled, skipping")
                continue
                
            plugin_name = plugin["name"]
            main_module = plugin["main_module"] 
            
            try:
                # Build plugin path
                plugin_dir = os.path.join(os.getcwd(), "plugins", "installed", plugin_name)
                plugin_file = os.path.join(plugin_dir, f"{main_module}.py")
                
                if not os.path.exists(plugin_file):
                    logger.warning(f"Plugin file not found: {plugin_file}")
                    continue
                
                # Dynamic import
                spec = importlib.util.spec_from_file_location(f"plugin_{main_module}", plugin_file)
                if spec is None or spec.loader is None:
                    logger.error(f"Could not load spec for plugin {plugin_name}")
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"plugin_{main_module}"] = module
                spec.loader.exec_module(module)
                
                # Register plugin tool
                if hasattr(module, 'register_tool'):
                    if module.register_tool(registry):
                        tools_registered.append(main_module)
                        logger.info(f"✅ Plugin tool registered: {main_module}")
                    else:
                        logger.warning(f"Plugin tool registration failed: {main_module}")
                else:
                    logger.warning(f"Plugin {plugin_name} has no register_tool function")
                    
            except Exception as e:
                logger.error(f"❌ Error loading plugin {plugin_name}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"❌ Error in dynamic plugin loading: {e}")
        
    return tools_registered

def get_internal_tools() -> List[str]:
    """Get list of internal tool names"""
    return [
        "graph_memory",
        "llm_tool", 
        "sequential_thinking",
        "settings_manager",
        "todo_manager",
        "command_executor",
        "google_oauth2_manager",
        "user_clarification"
    ]

def get_external_tools() -> List[str]:
    """Get list of external tool names"""
    return [
        "gmail_helper",
        "google_calendar",
        "google_drive", 
        "playwright_browser",
        "selenium_browser",
        "simple_visual_creator"
    ]

def is_internal_tool(tool_name: str) -> bool:
    """Check if a tool is internal (core system)"""
    return tool_name in get_internal_tools()

def is_external_tool(tool_name: str) -> bool:
    """Check if a tool is external (plugin)"""
    return tool_name in get_external_tools()

# Legacy compatibility - keep old function name
def register_all_tools_legacy(registry):
    """Legacy compatibility function"""
    return register_all_tools(registry)