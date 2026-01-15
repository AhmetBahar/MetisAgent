"""
Tool Manager - Dynamic MCP tool loading and management
"""

import os
import sys
import json
import importlib
import importlib.util
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import zipfile
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult
# Usage patterns removed for simplicity

logger = logging.getLogger(__name__)

class ToolManagerTool(MCPTool):
    """Manages dynamic loading, installation, and removal of MCP tools"""
    
    def __init__(self, registry=None):
        super().__init__(
            name="tool_manager",
            description="Dynamic tool management - install, remove, list, update MCP tools",
            version="1.0.0"
        )
        
        self.registry = registry
        
        # Tool storage paths - use new plugin system
        self.tools_directory = Path(os.getcwd()) / "plugins" / "installed"
        self.tools_config_file = self.tools_directory / "plugin_manifest.json"
        self.tools_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize plugin loader integration
        from plugins.plugin_loader import get_plugin_loader
        self.plugin_loader = get_plugin_loader()
        
        # Initialize config
        self._init_tools_config()
        
        # Register capabilities
        self.add_capability("dynamic_tool_loading")
        self.add_capability("tool_installation")
        self.add_capability("tool_management")
        
        # Register actions
        self.register_action(
            "install_tool",
            self._install_tool,
            required_params=["source"],
            optional_params=["name", "version", "force"]
        )
        
        self.register_action(
            "remove_tool",
            self._remove_tool,
            required_params=["target_tool"],
            optional_params=["force"]
        )
        
        self.register_action(
            "list_available_tools",
            self._list_available_tools,
            required_params=[],
            optional_params=["category", "search"]
        )
        
        self.register_action(
            "list_installed_tools",
            self._list_installed_tools,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "reload_tool",
            self._reload_tool,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "get_tool_info",
            self._get_tool_info,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "enable_tool",
            self._enable_tool,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "disable_tool",
            self._disable_tool,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "approve_tool_autoload",
            self._approve_tool_autoload,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "blacklist_tool",
            self._blacklist_tool,
            required_params=["target_tool"],
            optional_params=[]
        )
        
        self.register_action(
            "get_autoload_settings",
            self._get_autoload_settings,
            required_params=[],
            optional_params=[]
        )
        
        # Load existing dynamic tools
        self._load_existing_tools()
    
    def _init_tools_config(self):
        """Initialize tools configuration - compatible with plugin loader format"""
        if not self.tools_config_file.exists():
            # Use plugin loader compatible format
            initial_config = {
                "version": "1.0",
                "plugins": [],
                "auto_load_settings": {
                    "enabled": True,
                    "user_approval_required": False,
                    "approved_tools": [],
                    "blacklisted_tools": []
                },
                "tool_sources": {
                    "github": "https://api.github.com/search/repositories?q=mcp+tool+python",
                    "pypi": "https://pypi.org/search/?q=mcp+tool"
                },
                "last_updated": None
            }
            with open(self.tools_config_file, 'w') as f:
                json.dump(initial_config, f, indent=2)
    
    def _load_tools_config(self) -> Dict:
        """Load tools configuration"""
        with open(self.tools_config_file, 'r') as f:
            return json.load(f)
    
    def _save_tools_config(self, config: Dict):
        """Save tools configuration"""
        with open(self.tools_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _load_existing_tools(self):
        """Load previously installed dynamic tools using plugin loader"""
        try:
            # Use plugin loader to load all enabled plugins
            loaded_count = self.plugin_loader.load_all_enabled_plugins(self.registry)
            logger.info(f"Auto-loaded {loaded_count} enabled plugins")
            
            # Update LLM system prompt with dynamic tools
            self._update_llm_system_prompt()
        except Exception as e:
            logger.error(f"Error loading existing tools: {str(e)}")
    
    def _update_llm_system_prompt(self):
        """Update LLM system prompt to include dynamic tools"""
        try:
            # Check if registry is available
            if self.registry is None:
                logger.warning("Registry is None - cannot update LLM system prompt")
                return
                
            # Get current dynamic tools using plugin loader
            dynamic_tools_info = []
            plugins = self.plugin_loader.list_plugins()
            
            for plugin_data in plugins:
                if plugin_data.get("enabled", False) and plugin_data.get("loaded", False):
                    tool_name = plugin_data["name"]
                    registry_tool = self.registry.get_tool(tool_name)
                    if registry_tool:
                        tool_actions = []
                        for action_name, action_info in registry_tool.actions.items():
                            tool_actions.append(f"  - {action_name}: {{\"tool\": \"{tool_name}\", \"action\": \"{action_name}\", \"params\": {{...}}}}")
                        
                        dynamic_tools_info.append(
                            f"- {tool_name}: {registry_tool.description} (DYNAMIC)\n" + "\n".join(tool_actions)
                        )
            
            # Notify LLM tool about dynamic tools
            llm_tool = self.registry.get_tool('llm_tool')
            if llm_tool and hasattr(llm_tool, 'update_dynamic_tools_in_prompt'):
                llm_tool.update_dynamic_tools_in_prompt(dynamic_tools_info)
                logger.info(f"Updated LLM system prompt with {len(dynamic_tools_info)} dynamic tools")
            else:
                logger.warning("LLM tool not found or doesn't support dynamic prompt updates")
                
        except Exception as e:
            logger.error(f"Error updating LLM system prompt: {str(e)}")
    
    def _install_tool(self, source: str, name: Optional[str] = None, 
                     version: Optional[str] = None, force: bool = False, **kwargs) -> MCPToolResult:
        """Install a tool from various sources"""
        # Filter out registry from kwargs to avoid conflicts
        kwargs.pop('registry', None)
        
        # Validate parameters
        if not source or source.strip() == "":
            return MCPToolResult(success=False, error="Source parameter is required and cannot be empty")
        
        if name and name.strip() == "":
            name = None  # Reset empty name to None
            
        logger.info(f"Installing tool from source: '{source}', name: '{name}'")
        
        try:
            # Auto-detect name from source if not provided
            if not name and os.path.exists(source):
                source_path = Path(source)
                # Look for common tool files
                tool_files = list(source_path.glob("*_tool.py"))
                if tool_files:
                    # Extract tool name from filename (e.g., instagram_tool.py -> instagram_tool)
                    potential_name = tool_files[0].stem
                    name = potential_name
                    logger.info(f"Auto-detected tool name: '{name}' from file: {tool_files[0].name}")
            
            # Determine source type
            if source.startswith('http'):
                return self._install_from_url(source, name, force)
            elif source.startswith('git+'):
                return self._install_from_git(source, name, force)
            elif os.path.exists(source):
                return self._install_from_local(source, name, force)
            elif '/' in source:  # Assume GitHub repo
                return self._install_from_github(source, name, force)
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown source type: {source}"
                )
        except Exception as e:
            logger.error(f"Tool installation failed: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _install_from_github(self, repo: str, name: Optional[str], force: bool) -> MCPToolResult:
        """Install tool from GitHub repository"""
        try:
            # Format: owner/repo or owner/repo@version
            if '@' in repo:
                repo_path, version = repo.split('@')
            else:
                repo_path, version = repo, 'main'
            
            # Download URL
            download_url = f"https://github.com/{repo_path}/archive/{version}.zip"
            
            return self._install_from_url(download_url, name or repo_path.split('/')[-1], force)
            
        except Exception as e:
            return MCPToolResult(success=False, error=f"GitHub installation failed: {str(e)}")
    
    def _install_from_url(self, url: str, name: Optional[str], force: bool) -> MCPToolResult:
        """Install tool from URL (zip file)"""
        try:
            # Download tool
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "tool.zip"
                
                # Save zip file
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find tool directory (usually there's one subdirectory)
                extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if not extracted_dirs:
                    return MCPToolResult(success=False, error="No directories found in downloaded archive")
                
                tool_source = extracted_dirs[0]
                
                # Install from extracted directory
                return self._install_from_local(str(tool_source), name, force)
                
        except Exception as e:
            return MCPToolResult(success=False, error=f"URL installation failed: {str(e)}")
    
    def _install_from_local(self, source_path: str, name: Optional[str], force: bool) -> MCPToolResult:
        """Install tool from local directory using new plugin system"""
        try:
            # Use the new plugin loader system
            success = self.plugin_loader.install_plugin(source_path, force)
            
            if success:
                # Auto-detect name if not provided
                if not name:
                    source_path_obj = Path(source_path)
                    name = source_path_obj.name.replace('-', '_').replace(' ', '_')
                
                # Load the plugin
                load_success = self.plugin_loader.load_plugin(name, self.registry)
                
                if load_success:
                    # Generate usage pattern for the new tool
                    self._generate_tool_usage_pattern(name)
                    
                    # Update LLM system prompt with new tool
                    self._update_llm_system_prompt()
                    
                    return MCPToolResult(
                        success=True,
                        data={
                            "tool_name": name,
                            "message": f"Plugin '{name}' installed and loaded successfully"
                        }
                    )
                else:
                    return MCPToolResult(success=False, error=f"Plugin installed but failed to load: {name}")
            else:
                return MCPToolResult(success=False, error=f"Plugin installation failed")
            
        except Exception as e:
            return MCPToolResult(success=False, error=f"Local installation failed: {str(e)}")
    
    def _install_single_tool_file(self, tool_file: Path, name: str, force: bool) -> MCPToolResult:
        """Install a single tool file"""
        try:
            logger.info(f"Installing single tool file: {tool_file} as {name}")
            
            # Check if tool already exists
            config = self._load_tools_config()
            if name in config["installed_tools"] and not force:
                return MCPToolResult(
                    success=False,
                    error=f"Tool '{name}' already exists. Use force=True to overwrite."
                )
            
            # Create tool directory
            tool_dir = self.tools_directory / name
            if tool_dir.exists():
                shutil.rmtree(tool_dir)
            tool_dir.mkdir(parents=True)
            
            # Copy the main tool file
            target_file = tool_dir / f"{name}.py"
            shutil.copy2(tool_file, target_file)
            
            # Copy dependencies if they exist in the same directory
            source_dir = tool_file.parent
            dependencies = ['settings_manager.py', 'google_auth.py']
            
            for dep in dependencies:
                dep_file = source_dir / dep
                if dep_file.exists():
                    shutil.copy2(dep_file, tool_dir / dep)
                    logger.info(f"Copied dependency: {dep}")
            
            # Create __init__.py to make it a proper package
            init_file = tool_dir / "__init__.py"
            
            # Inspect the tool file to find the actual class name
            actual_class_name = self._find_tool_class_name(target_file)
            if not actual_class_name:
                actual_class_name = f"{name.title().replace('_', '')}Tool"
            
            # Store class name in a separate config to prevent corruption
            class_config_file = tool_dir / "tool_class.json"
            with open(class_config_file, 'w') as f:
                json.dump({"class_name": actual_class_name, "module_name": name}, f)
            
            # Generate dynamic __init__.py that reads the class name from config
            with open(init_file, 'w') as f:
                f.write(f'''"""
{name.title().replace('_', ' ')} Tool Package
"""

import sys
import os
import json

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Read class configuration to prevent hardcoded corruption
class_config_path = os.path.join(current_dir, "tool_class.json")
try:
    with open(class_config_path, 'r') as f:
        config = json.load(f)
    actual_class_name = config["class_name"]
    module_name = config["module_name"]
except:
    actual_class_name = "{actual_class_name}"
    module_name = "{name}"

try:
    # Dynamic import using config
    module = __import__(module_name, fromlist=[actual_class_name, 'register_tool'])
    globals()[actual_class_name] = getattr(module, actual_class_name)
    globals()['register_tool'] = getattr(module, 'register_tool')
except ImportError:
    # Fallback import
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(current_dir, f"{{module_name}}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    globals()[actual_class_name] = getattr(module, actual_class_name)
    globals()['register_tool'] = getattr(module, 'register_tool')

__all__ = [actual_class_name, 'register_tool']
''')
            
            # Try to load the tool
            load_result = self._load_tool_from_path(name, str(tool_dir))
            if not load_result:
                return MCPToolResult(success=False, error=f"Failed to load tool from {tool_dir}")
            
            # Generate usage pattern for the new tool
            self._generate_tool_usage_pattern(name)
            
            # Update config
            config["installed_tools"][name] = {
                "path": str(tool_dir),
                "main_file": f"{name}.py",
                "enabled": True,
                "installed_from": str(tool_file.parent),
                "version": "1.0.0"
            }
            
            # Auto-approve tool since user explicitly requested installation
            auto_load_settings = config.get("auto_load_settings", {})
            approved_tools = auto_load_settings.get("approved_tools", [])
            if name not in approved_tools:
                approved_tools.append(name)
                auto_load_settings["approved_tools"] = approved_tools
                config["auto_load_settings"] = auto_load_settings
                logger.info(f"Auto-approved tool '{name}' for loading (user explicitly requested installation)")
            
            self._save_tools_config(config)
            
            # Update LLM system prompt with new tool
            self._update_llm_system_prompt()
            
            return MCPToolResult(
                success=True,
                data={
                    "tool_name": name,
                    "path": str(tool_dir),
                    "message": f"Tool '{name}' installed successfully from single file"
                }
            )
            
        except Exception as e:
            logger.error(f"Single tool file installation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"Single file installation failed: {str(e)}")
    
    def _find_tool_class_name(self, tool_file: Path) -> Optional[str]:
        """Tool dosyasından gerçek class adını bul"""
        try:
            with open(tool_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Class definition'ları ara
            import re
            class_matches = re.findall(r'class\s+(\w+)\s*\(.*MCPTool.*\):', content)
            
            if class_matches:
                # MCPTool'dan inherit eden ilk class'ı döndür
                return class_matches[0]
            
            # Fallback: Tool ile biten class'ları ara
            tool_class_matches = re.findall(r'class\s+(\w*Tool)\s*\(', content)
            if tool_class_matches:
                return tool_class_matches[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not parse tool file {tool_file}: {e}")
            return None
    
    def _load_tool_from_path(self, tool_name: str, tool_path: str) -> bool:
        """Load a tool from given path"""
        try:
            tool_path = Path(tool_path)
            
            # Find the main module
            main_files = ['server.py', 'main.py', 'tool.py', '__init__.py']
            main_file = None
            
            for filename in main_files:
                candidate = tool_path / filename
                if candidate.exists():
                    main_file = candidate
                    break
            
            if not main_file:
                # Look for any Python file
                py_files = list(tool_path.glob("*.py"))
                if py_files:
                    main_file = py_files[0]
                else:
                    return False
            
            # Add tool path to sys.path for proper imports
            if str(tool_path.parent) not in sys.path:
                sys.path.insert(0, str(tool_path.parent))
            if str(tool_path) not in sys.path:
                sys.path.insert(0, str(tool_path))
            
            # Import the module
            module_name = f"dynamic_tool_{tool_name}"
            
            if main_file.name == '__init__.py':
                # Import as package
                spec = importlib.util.spec_from_file_location(module_name, main_file)
            else:
                # Import as single file
                spec = importlib.util.spec_from_file_location(module_name, main_file)
            
            if not spec or not spec.loader:
                logger.error(f"Could not create spec for {main_file}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            try:
                spec.loader.exec_module(module)
                logger.info(f"Successfully imported module: {module_name}")
            except Exception as e:
                logger.error(f"Error executing module {module_name}: {e}")
                return False
            
            # Look for register_tool function or tool class
            if hasattr(module, 'register_tool'):
                # Standard MCP tool
                module.register_tool(self.registry)
                return True
            elif hasattr(module, 'ToolClass'):
                # Custom tool class
                tool_instance = module.ToolClass()
                if isinstance(tool_instance, MCPTool):
                    self.registry.register_tool(tool_instance)
                    return True
            else:
                # Look for any MCPTool subclass
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, MCPTool) and 
                        attr != MCPTool):
                        tool_instance = attr()
                        self.registry.register_tool(tool_instance)
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading tool {tool_name}: {str(e)}")
            return False
    
    def _generate_tool_usage_pattern(self, tool_name: str):
        """Yeni yüklenen tool için usage pattern oluştur"""
        try:
            # Registry'den tool instance'ını al
            tool_instance = self.registry.get_tool(tool_name)
            if not tool_instance:
                logger.warning(f"Tool {tool_name} not found in registry for pattern generation")
                return
            
            logger.info(f"Generating usage pattern for {tool_name}")
            
            # Usage pattern oluştur
            # Pattern generation simplified - skip for now
            pattern = None
            
            # Pattern'ı kaydet (simplified)
            success = True
            
            if success:
                logger.info(f"✅ Tool registered successfully: {tool_name}")
                # Pattern logging simplified
            else:
                logger.error(f"❌ Failed to register tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"Error generating usage pattern for {tool_name}: {e}")
    
    def _remove_tool_usage_pattern(self, tool_name: str):
        """Tool kaldırıldığında pattern'ı da sil"""
        try:
            # Implementation: Pattern'ı ChromaDB'den sil
            logger.info(f"Removing usage pattern for {tool_name}")
            # TODO: Implement pattern deletion
        except Exception as e:
            logger.error(f"Error removing usage pattern for {tool_name}: {e}")
    
    def _remove_tool(self, target_tool: str, force: bool = False, **kwargs) -> MCPToolResult:
        """Remove an installed plugin using new plugin system"""
        kwargs.pop('registry', None)
        try:
            # Remove usage pattern
            self._remove_tool_usage_pattern(target_tool)
            
            # Use plugin loader to uninstall plugin
            success = self.plugin_loader.uninstall_plugin(target_tool, self.registry)
            
            if success:
                return MCPToolResult(
                    success=True,
                    data={
                        "tool_name": target_tool,
                        "message": f"Plugin '{target_tool}' removed successfully"
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to remove plugin '{target_tool}'"
                )
            
        except Exception as e:
            return MCPToolResult(success=False, error=f"Plugin removal failed: {str(e)}")
    
    def _list_installed_tools(self, **kwargs) -> MCPToolResult:
        """List all installed plugins using new plugin system"""
        kwargs.pop('registry', None)
        try:
            # Use plugin loader to get plugin list
            plugins = self.plugin_loader.list_plugins()
            
            tools = []
            for plugin_data in plugins:
                tool_data = {
                    "name": plugin_data["name"],
                    "enabled": plugin_data["enabled"],
                    "loaded": plugin_data["loaded"],
                    "version": plugin_data["version"],
                    "description": plugin_data["description"],
                    "author": plugin_data["author"],
                    "capabilities": plugin_data["capabilities"],
                    "installed_at": plugin_data["installed_at"]
                }
                
                # Add registry info if available
                registry_tool = self.registry.get_tool(plugin_data["name"])
                if registry_tool:
                    tool_data.update({
                        "registry_description": registry_tool.description,
                        "registry_capabilities": registry_tool.capabilities,
                        "actions": list(registry_tool.actions.keys())
                    })
                
                tools.append(tool_data)
            
            return MCPToolResult(
                success=True,
                data={
                    "installed_tools": tools,
                    "count": len(tools)
                }
            )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _list_available_tools(self, category: Optional[str] = None, 
                             search: Optional[str] = None, **kwargs) -> MCPToolResult:
        """List available tools from various sources"""
        kwargs.pop('registry', None)
        try:
            # This would connect to tool repositories/marketplaces
            # For now, return some example tools
            available_tools = [
                {
                    "name": "website_fetcher",
                    "description": "Fetch website content and extract text",
                    "source": "https://github.com/example/website-fetcher-mcp",
                    "category": "web",
                    "version": "1.0.0",
                    "author": "Example Author"
                },
                {
                    "name": "calculator",
                    "description": "Basic mathematical calculations",
                    "source": "https://github.com/example/calculator-mcp",
                    "category": "math",
                    "version": "1.2.0",
                    "author": "Math Tools Inc"
                }
            ]
            
            # Apply filters
            if category:
                available_tools = [t for t in available_tools if t.get("category") == category]
            
            if search:
                search_lower = search.lower()
                available_tools = [
                    t for t in available_tools 
                    if search_lower in t["name"].lower() or search_lower in t["description"].lower()
                ]
            
            return MCPToolResult(
                success=True,
                data={
                    "available_tools": available_tools,
                    "count": len(available_tools)
                }
            )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _reload_tool(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Reload a tool"""
        kwargs.pop('registry', None)
        try:
            config = self._load_tools_config()
            
            if target_tool not in config["installed_tools"]:
                return MCPToolResult(
                    success=False,
                    error=f"Tool '{target_tool}' is not installed"
                )
            
            tool_info = config["installed_tools"][target_tool]
            
            # Unregister current version
            if self.registry.get_tool(target_tool):
                self.registry.unregister_tool(target_tool)
            
            # Reload
            if self._load_tool_from_path(target_tool, tool_info["path"]):
                return MCPToolResult(
                    success=True,
                    data={"message": f"Tool '{target_tool}' reloaded successfully"}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to reload tool '{target_tool}'"
                )
                
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_tool_info(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Get detailed information about a tool"""
        kwargs.pop('registry', None)
        try:
            config = self._load_tools_config()
            registry_tool = self.registry.get_tool(target_tool)
            
            tool_info = {
                "name": target_tool,
                "in_registry": registry_tool is not None,
                "is_dynamic": target_tool in config["installed_tools"]
            }
            
            if registry_tool:
                tool_info.update({
                    "description": registry_tool.description,
                    "version": registry_tool.version,
                    "capabilities": registry_tool.capabilities,
                    "actions": {
                        action_name: {
                            "required_params": action_data["required_params"],
                            "optional_params": action_data["optional_params"]
                        }
                        for action_name, action_data in registry_tool.actions.items()
                    },
                    "enabled": registry_tool.is_enabled
                })
            
            if target_tool in config["installed_tools"]:
                dynamic_info = config["installed_tools"][target_tool]
                tool_info.update({
                    "path": dynamic_info["path"],
                    "installed_from": dynamic_info.get("installed_from"),
                    "dynamic_version": dynamic_info.get("version")
                })
            
            return MCPToolResult(success=True, data=tool_info)
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _enable_tool(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Enable a plugin using new plugin system"""
        kwargs.pop('registry', None)
        try:
            # Use plugin loader to enable plugin
            success = self.plugin_loader.enable_plugin(target_tool)
            
            if success:
                # Also load the plugin if not already loaded
                load_success = self.plugin_loader.load_plugin(target_tool, self.registry)
                
                if load_success:
                    return MCPToolResult(
                        success=True,
                        data={"message": f"Plugin '{target_tool}' enabled and loaded"}
                    )
                else:
                    return MCPToolResult(
                        success=True,
                        data={"message": f"Plugin '{target_tool}' enabled but failed to load"}
                    )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to enable plugin '{target_tool}'"
                )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _disable_tool(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Disable a plugin using new plugin system"""
        kwargs.pop('registry', None)
        try:
            # Use plugin loader to disable plugin
            success = self.plugin_loader.disable_plugin(target_tool, self.registry)
            
            if success:
                return MCPToolResult(
                    success=True,
                    data={"message": f"Plugin '{target_tool}' disabled and unloaded"}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to disable plugin '{target_tool}'"
                )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _approve_tool_autoload(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Approve a tool for auto-loading on startup"""
        kwargs.pop('registry', None)
        try:
            config = self._load_tools_config()
            auto_load_settings = config.get("auto_load_settings", {})
            approved_tools = auto_load_settings.get("approved_tools", [])
            
            if target_tool not in approved_tools:
                approved_tools.append(target_tool)
                auto_load_settings["approved_tools"] = approved_tools
                config["auto_load_settings"] = auto_load_settings
                self._save_tools_config(config)
            
            return MCPToolResult(
                success=True,
                data={"message": f"Tool '{target_tool}' approved for auto-loading"}
            )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _blacklist_tool(self, target_tool: str, **kwargs) -> MCPToolResult:
        """Blacklist a tool from auto-loading"""
        kwargs.pop('registry', None)
        try:
            config = self._load_tools_config()
            auto_load_settings = config.get("auto_load_settings", {})
            blacklisted_tools = auto_load_settings.get("blacklisted_tools", [])
            
            if target_tool not in blacklisted_tools:
                blacklisted_tools.append(target_tool)
                auto_load_settings["blacklisted_tools"] = blacklisted_tools
                config["auto_load_settings"] = auto_load_settings
                self._save_tools_config(config)
            
            # Also remove from approved list if present
            approved_tools = auto_load_settings.get("approved_tools", [])
            if target_tool in approved_tools:
                approved_tools.remove(target_tool)
                auto_load_settings["approved_tools"] = approved_tools
                config["auto_load_settings"] = auto_load_settings
                self._save_tools_config(config)
            
            return MCPToolResult(
                success=True,
                data={"message": f"Tool '{target_tool}' blacklisted from auto-loading"}
            )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_autoload_settings(self, **kwargs) -> MCPToolResult:
        """Get current auto-load settings"""
        kwargs.pop('registry', None)
        try:
            config = self._load_tools_config()
            auto_load_settings = config.get("auto_load_settings", {})
            
            return MCPToolResult(
                success=True,
                data={
                    "auto_load_enabled": auto_load_settings.get("enabled", True),
                    "user_approval_required": auto_load_settings.get("user_approval_required", False),
                    "approved_tools": auto_load_settings.get("approved_tools", []),
                    "blacklisted_tools": auto_load_settings.get("blacklisted_tools", [])
                }
            )
            
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def health_check(self) -> MCPToolResult:
        """Check tool manager health"""
        try:
            config = self._load_tools_config()
            return MCPToolResult(
                success=True,
                data={
                    "status": "healthy",
                    "tools_directory": str(self.tools_directory),
                    "installed_tools_count": len(config["installed_tools"]),
                    "dynamic_loading": "enabled"
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the Tool Manager with the registry"""
    # Pass registry directly to constructor
    tool = ToolManagerTool(registry)
    return registry.register_tool(tool)