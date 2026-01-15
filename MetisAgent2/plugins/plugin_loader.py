"""
Dynamic Plugin Loader for MetisAgent2
Provides dynamic loading/unloading of external tools as plugins
"""

import os
import sys
import json
import logging
import importlib
import importlib.util
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class PluginInfo:
    """Plugin information structure"""
    name: str
    version: str
    description: str
    author: str
    main_module: str
    dependencies: List[str]
    capabilities: List[str]
    enabled: bool = True
    installed_at: str = ""
    last_updated: str = ""

class PluginLoader:
    """Dynamic plugin loader and manager"""
    
    def __init__(self, plugins_dir: str = None):
        """Initialize plugin loader"""
        self.plugins_dir = Path(plugins_dir or (Path(__file__).parent / "installed"))
        self.plugins_dir.mkdir(exist_ok=True)
        
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_registry: Dict[str, PluginInfo] = {}
        
        # Plugin manifest file
        self.manifest_file = self.plugins_dir / "plugin_manifest.json"
        
        logger.info(f"Plugin loader initialized: {self.plugins_dir}")
        
        # Load existing plugin registry
        self._load_plugin_registry()
    
    def _load_plugin_registry(self):
        """Load plugin registry from manifest file"""
        try:
            if self.manifest_file.exists():
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    
                for plugin_data in manifest_data.get('plugins', []):
                    plugin_info = PluginInfo(**plugin_data)
                    self.plugin_registry[plugin_info.name] = plugin_info
                    
                logger.info(f"Loaded {len(self.plugin_registry)} plugins from registry")
        except Exception as e:
            logger.error(f"Error loading plugin registry: {e}")
    
    def _save_plugin_registry(self):
        """Save plugin registry to manifest file"""
        try:
            manifest_data = {
                'version': '1.0',
                'plugins': [asdict(plugin) for plugin in self.plugin_registry.values()]
            }
            
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(self.plugin_registry)} plugins to registry")
        except Exception as e:
            logger.error(f"Error saving plugin registry: {e}")
    
    def install_plugin(self, plugin_path: str, force: bool = False) -> bool:
        """Install a plugin from a directory or zip file"""
        try:
            plugin_path = Path(plugin_path)
            
            if not plugin_path.exists():
                logger.error(f"Plugin path does not exist: {plugin_path}")
                return False
            
            # Read plugin.json metadata
            plugin_json = plugin_path / "plugin.json"
            if not plugin_json.exists():
                logger.error(f"Plugin metadata not found: {plugin_json}")
                return False
            
            with open(plugin_json, 'r', encoding='utf-8') as f:
                plugin_metadata = json.load(f)
            
            plugin_name = plugin_metadata['name']
            
            # Check if plugin already exists
            if plugin_name in self.plugin_registry and not force:
                logger.warning(f"Plugin {plugin_name} already installed. Use force=True to overwrite")
                return False
            
            # Create plugin directory
            plugin_install_dir = self.plugins_dir / plugin_name
            plugin_install_dir.mkdir(exist_ok=True)
            
            # Copy plugin files
            import shutil
            if plugin_path.is_dir():
                shutil.copytree(plugin_path, plugin_install_dir, dirs_exist_ok=True)
            else:
                # Extract zip file
                import zipfile
                with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                    zip_ref.extractall(plugin_install_dir)
            
            # Create plugin info
            from datetime import datetime
            plugin_info = PluginInfo(
                name=plugin_metadata['name'],
                version=plugin_metadata['version'],
                description=plugin_metadata.get('description', ''),
                author=plugin_metadata.get('author', 'Unknown'),
                main_module=plugin_metadata['main_module'],
                dependencies=plugin_metadata.get('dependencies', []),
                capabilities=plugin_metadata.get('capabilities', []),
                enabled=True,
                installed_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
            # Add to registry
            self.plugin_registry[plugin_name] = plugin_info
            self._save_plugin_registry()
            
            logger.info(f"Plugin {plugin_name} installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error installing plugin: {e}")
            return False
    
    def load_plugin(self, plugin_name: str, registry=None) -> bool:
        """Load a plugin and register it with the tool registry"""
        try:
            if plugin_name not in self.plugin_registry:
                logger.error(f"Plugin {plugin_name} not found in registry")
                return False
            
            plugin_info = self.plugin_registry[plugin_name]
            
            if not plugin_info.enabled:
                logger.warning(f"Plugin {plugin_name} is disabled")
                return False
            
            if plugin_name in self.loaded_plugins:
                logger.warning(f"Plugin {plugin_name} is already loaded")
                return True
            
            # Load plugin module
            plugin_dir = self.plugins_dir / plugin_name
            main_module_path = plugin_dir / f"{plugin_info.main_module}.py"
            
            if not main_module_path.exists():
                logger.error(f"Plugin main module not found: {main_module_path}")
                return False
            
            # Import the plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}",
                main_module_path
            )
            plugin_module = importlib.util.module_from_spec(spec)
            
            # Add plugin directory to Python path temporarily
            sys.path.insert(0, str(plugin_dir))
            
            try:
                spec.loader.exec_module(plugin_module)
                
                # Register with tool registry if provided
                if registry and hasattr(plugin_module, 'register_tool'):
                    success = plugin_module.register_tool(registry)
                    if success:
                        self.loaded_plugins[plugin_name] = plugin_module
                        logger.info(f"Plugin {plugin_name} loaded and registered successfully")
                        return True
                    else:
                        logger.error(f"Failed to register plugin {plugin_name}")
                        return False
                else:
                    self.loaded_plugins[plugin_name] = plugin_module
                    logger.info(f"Plugin {plugin_name} loaded successfully (no registry)")
                    return True
                    
            finally:
                # Remove plugin directory from Python path
                if str(plugin_dir) in sys.path:
                    sys.path.remove(str(plugin_dir))
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str, registry=None) -> bool:
        """Unload a plugin"""
        try:
            if plugin_name not in self.loaded_plugins:
                logger.warning(f"Plugin {plugin_name} is not loaded")
                return True
            
            plugin_module = self.loaded_plugins[plugin_name]
            
            # Unregister from tool registry if possible
            if registry and hasattr(plugin_module, 'unregister_tool'):
                plugin_module.unregister_tool(registry)
            elif registry:
                # Try to remove tool from registry by name
                registry.unregister_tool(plugin_name)
            
            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]
            
            # Remove from sys.modules if present
            module_name = f"plugin_{plugin_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            logger.info(f"Plugin {plugin_name} unloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str, registry=None) -> bool:
        """Reload a plugin"""
        try:
            # Unload first
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name, registry)
            
            # Then load again
            return self.load_plugin(plugin_name, registry)
            
        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {e}")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin"""
        try:
            if plugin_name not in self.plugin_registry:
                logger.error(f"Plugin {plugin_name} not found")
                return False
            
            self.plugin_registry[plugin_name].enabled = True
            self._save_plugin_registry()
            
            logger.info(f"Plugin {plugin_name} enabled")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling plugin {plugin_name}: {e}")
            return False
    
    def disable_plugin(self, plugin_name: str, registry=None) -> bool:
        """Disable a plugin"""
        try:
            if plugin_name not in self.plugin_registry:
                logger.error(f"Plugin {plugin_name} not found")
                return False
            
            # Unload if loaded
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name, registry)
            
            # Disable in registry
            self.plugin_registry[plugin_name].enabled = False
            self._save_plugin_registry()
            
            logger.info(f"Plugin {plugin_name} disabled")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling plugin {plugin_name}: {e}")
            return False
    
    def uninstall_plugin(self, plugin_name: str, registry=None) -> bool:
        """Uninstall a plugin completely"""
        try:
            # Unload first
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name, registry)
            
            # Remove from registry
            if plugin_name in self.plugin_registry:
                del self.plugin_registry[plugin_name]
                self._save_plugin_registry()
            
            # Remove plugin directory
            plugin_dir = self.plugins_dir / plugin_name
            if plugin_dir.exists():
                import shutil
                shutil.rmtree(plugin_dir)
            
            logger.info(f"Plugin {plugin_name} uninstalled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_name}: {e}")
            return False
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins"""
        plugins = []
        
        for plugin_name, plugin_info in self.plugin_registry.items():
            plugin_data = asdict(plugin_info)
            plugin_data['loaded'] = plugin_name in self.loaded_plugins
            plugins.append(plugin_data)
        
        return plugins
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific plugin"""
        if plugin_name not in self.plugin_registry:
            return None
        
        plugin_info = self.plugin_registry[plugin_name]
        plugin_data = asdict(plugin_info)
        plugin_data['loaded'] = plugin_name in self.loaded_plugins
        
        return plugin_data
    
    def load_all_enabled_plugins(self, registry=None) -> int:
        """Load all enabled plugins"""
        loaded_count = 0
        
        for plugin_name, plugin_info in self.plugin_registry.items():
            if plugin_info.enabled:
                if self.load_plugin(plugin_name, registry):
                    loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} enabled plugins")
        return loaded_count
    
    def create_plugin_template(self, plugin_name: str, plugin_dir: str = None) -> bool:
        """Create a plugin template"""
        try:
            plugin_dir = Path(plugin_dir or f"./{plugin_name}_plugin")
            plugin_dir.mkdir(exist_ok=True)
            
            # Create plugin.json
            plugin_json = {
                "name": plugin_name,
                "version": "1.0.0",
                "description": f"{plugin_name} plugin for MetisAgent2",
                "author": "Plugin Developer",
                "main_module": plugin_name,
                "dependencies": [],
                "capabilities": [
                    f"{plugin_name}_operations"
                ]
            }
            
            with open(plugin_dir / "plugin.json", 'w', encoding='utf-8') as f:
                json.dump(plugin_json, f, indent=2)
            
            # Create main module
            main_module_content = f'''"""
{plugin_name.title()} Plugin for MetisAgent2
"""

import logging
import sys
import os
from typing import Dict, Any, List
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class {plugin_name.title()}Tool(MCPTool):
    """{plugin_name.title()} tool implementation"""
    
    def __init__(self):
        """Initialize {plugin_name} tool"""
        super().__init__(
            name="{plugin_name}",
            description="{plugin_name.title()} operations and functionality",
            version="1.0.0"
        )
        
        # Register capabilities
        self.add_capability("{plugin_name}_operations")
        
        # Register actions
        self.register_action(
            "hello",
            self._hello,
            required_params=["name"],
            optional_params=["message"]
        )
    
    def _hello(self, name: str, message: str = "Hello") -> MCPToolResult:
        """Simple hello action"""
        try:
            response = f"{{message}} {{name}}! This is the {{self.name}} plugin."
            
            return MCPToolResult(
                success=True,
                data={{"response": response, "timestamp": datetime.now().isoformat()}},
                metadata={{"action": "hello", "plugin": self.name}}
            )
            
        except Exception as e:
            logger.error(f"Error in hello action: {{e}}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={{"action": "hello", "plugin": self.name}}
            )

def register_tool(registry):
    """Register {plugin_name} tool with the registry"""
    try:
        tool = {plugin_name.title()}Tool()
        registry.register_tool(tool)
        logger.info("{plugin_name.title()} plugin registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register {plugin_name} plugin: {{e}}")
        return False

def unregister_tool(registry):
    """Unregister {plugin_name} tool from the registry"""
    try:
        registry.unregister_tool("{plugin_name}")
        logger.info("{plugin_name.title()} plugin unregistered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to unregister {plugin_name} plugin: {{e}}")
        return False
'''
            
            with open(plugin_dir / f"{plugin_name}.py", 'w', encoding='utf-8') as f:
                f.write(main_module_content)
            
            # Create README
            readme_content = f"""# {plugin_name.title()} Plugin

{plugin_name.title()} plugin for MetisAgent2.

## Installation

1. Copy this directory to the plugins/installed/ directory
2. Use the plugin loader to install and load the plugin

## Usage

The plugin provides the following actions:
- `hello`: Simple greeting action

## Development

Modify the `{plugin_name}.py` file to add more functionality.
"""
            
            with open(plugin_dir / "README.md", 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            logger.info(f"Plugin template created at: {plugin_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating plugin template: {e}")
            return False

# Global plugin loader instance
_plugin_loader = None

def get_plugin_loader() -> PluginLoader:
    """Get global plugin loader instance"""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader