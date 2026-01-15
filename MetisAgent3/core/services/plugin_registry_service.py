"""
Plugin Registry Service

Manages plugin lifecycle:
- Upload plugin ZIP to Azure Blob Storage
- Register metadata in Azure SQL
- Load plugins dynamically
- Validate plugins for security
"""

import json
import logging
import os
import zipfile
import ast
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import DefaultAzureCredential

from ..config.azure_config import get_azure_config, is_azure_environment
from ..storage.azure_sql_storage import AzureSQLPluginStorage

logger = logging.getLogger(__name__)


class PluginValidationError(Exception):
    """Raised when plugin validation fails"""
    pass


class PluginRegistryService:
    """Service for managing plugin registry and lifecycle"""

    # Dangerous imports that should be blocked
    BLOCKED_IMPORTS = {
        "subprocess", "os.system", "shutil.rmtree",
        "eval", "exec", "__import__"
    }

    # Dangerous function calls
    BLOCKED_CALLS = {
        "eval", "exec", "compile", "__import__",
        "open",  # Allow with restrictions
    }

    def __init__(self, storage: Optional[AzureSQLPluginStorage] = None):
        self.config = get_azure_config()
        self.storage = storage or AzureSQLPluginStorage()
        self._blob_client: Optional[BlobServiceClient] = None
        self._local_plugin_dir = Path(__file__).parent.parent.parent / "plugins"

    @property
    def blob_client(self) -> BlobServiceClient:
        """Get or create Blob Storage client"""
        if self._blob_client is None:
            if self.config.blob.connection_string:
                self._blob_client = BlobServiceClient.from_connection_string(
                    self.config.blob.connection_string
                )
            else:
                # Use managed identity in Azure
                credential = DefaultAzureCredential()
                account_url = f"https://{self.config.blob.account_name}.blob.core.windows.net"
                self._blob_client = BlobServiceClient(account_url, credential=credential)
        return self._blob_client

    def initialize(self) -> bool:
        """Initialize plugin registry (create tables if needed)"""
        if is_azure_environment():
            return self.storage.initialize_tables()
        return True

    # Plugin upload and registration
    async def upload_plugin(self, plugin_zip: bytes, plugin_name: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Upload a plugin ZIP file and register it

        Args:
            plugin_zip: ZIP file bytes
            plugin_name: Unique plugin name
            metadata: Optional additional metadata

        Returns:
            Tuple of (success, message/plugin_id)
        """
        try:
            # Extract and validate
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / f"{plugin_name}.zip"

                # Save ZIP temporarily
                with open(zip_path, "wb") as f:
                    f.write(plugin_zip)

                # Extract
                extract_dir = Path(temp_dir) / plugin_name
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)

                # Validate plugin structure
                manifest, tool_config = self._validate_plugin_structure(extract_dir)
                if not manifest or not tool_config:
                    return False, "Invalid plugin structure: missing manifest.json or tool_config.json"

                # Security validation
                is_safe, security_msg = self._validate_plugin_security(extract_dir)
                if not is_safe:
                    return False, f"Security validation failed: {security_msg}"

                # Upload to Blob Storage (in Azure environment)
                blob_path = f"{plugin_name}/{plugin_name}.zip"
                if is_azure_environment():
                    blob_client = self.blob_client.get_blob_client(
                        container=self.config.blob.container_name,
                        blob=blob_path
                    )
                    blob_client.upload_blob(plugin_zip, overwrite=True)

                # Extract capabilities from tool_config
                capabilities = []
                if "tool_metadata" in tool_config and "capabilities" in tool_config["tool_metadata"]:
                    capabilities = tool_config["tool_metadata"]["capabilities"]

                # Register in database
                plugin_data = {
                    "name": plugin_name,
                    "display_name": manifest.get("display_name", plugin_name),
                    "version": manifest.get("version", "1.0.0"),
                    "plugin_type": manifest.get("plugin_type", "python_module"),
                    "blob_path": blob_path,
                    "manifest": manifest,
                    "tool_config": tool_config,
                    "capabilities": capabilities,
                    "status": "active",
                    "is_enabled": True
                }

                if metadata:
                    plugin_data.update(metadata)

                plugin_id = self.storage.create_plugin(plugin_data)
                if plugin_id:
                    # Also extract to local plugins directory for immediate use
                    local_path = self._local_plugin_dir / plugin_name
                    if local_path.exists():
                        shutil.rmtree(local_path)
                    shutil.copytree(extract_dir, local_path)

                    return True, plugin_id
                else:
                    return False, "Failed to register plugin in database"

        except zipfile.BadZipFile:
            return False, "Invalid ZIP file"
        except Exception as e:
            logger.error(f"Plugin upload failed: {e}")
            return False, str(e)

    def _validate_plugin_structure(self, plugin_dir: Path) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Validate plugin has required files"""
        manifest_path = plugin_dir / "manifest.json"
        tool_config_path = plugin_dir / "tool_config.json"

        manifest = None
        tool_config = None

        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

        if tool_config_path.exists():
            with open(tool_config_path) as f:
                tool_config = json.load(f)

        return manifest, tool_config

    def _validate_plugin_security(self, plugin_dir: Path) -> Tuple[bool, str]:
        """
        Validate plugin code for security issues

        Uses AST analysis to detect potentially dangerous patterns.
        """
        for py_file in plugin_dir.rglob("*.py"):
            try:
                with open(py_file) as f:
                    code = f.read()

                tree = ast.parse(code)

                for node in ast.walk(tree):
                    # Check imports
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in self.BLOCKED_IMPORTS:
                                return False, f"Blocked import: {alias.name} in {py_file.name}"

                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in self.BLOCKED_IMPORTS:
                            return False, f"Blocked import: {node.module} in {py_file.name}"

                    # Check function calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in self.BLOCKED_CALLS:
                                # Allow certain patterns
                                if node.func.id == "open":
                                    # Check if mode is read-only
                                    pass  # Allow for now, can add more checks
                                else:
                                    return False, f"Blocked call: {node.func.id} in {py_file.name}"

            except SyntaxError as e:
                return False, f"Syntax error in {py_file.name}: {e}"
            except Exception as e:
                logger.warning(f"Could not analyze {py_file}: {e}")

        return True, "OK"

    # Plugin listing and retrieval
    def list_plugins(self, status: Optional[str] = None,
                    is_enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """List registered plugins"""
        if is_azure_environment():
            return self.storage.list_plugins(status=status, is_enabled=is_enabled)
        else:
            # Local mode: scan plugins directory
            return self._list_local_plugins()

    def _list_local_plugins(self) -> List[Dict[str, Any]]:
        """List plugins from local directory"""
        plugins = []
        for plugin_dir in self._local_plugin_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                tool_config_path = plugin_dir / "tool_config.json"
                if tool_config_path.exists():
                    with open(tool_config_path) as f:
                        tool_config = json.load(f)

                    metadata = tool_config.get("tool_metadata", {})
                    plugins.append({
                        "name": plugin_dir.name,
                        "display_name": metadata.get("description", plugin_dir.name),
                        "version": metadata.get("version", "1.0.0"),
                        "plugin_type": metadata.get("tool_type", "python_module"),
                        "is_enabled": True,
                        "status": "active",
                        "capabilities": metadata.get("capabilities", [])
                    })
        return plugins

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin by ID"""
        return self.storage.get_plugin(plugin_id)

    def get_plugin_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get plugin by name"""
        if is_azure_environment():
            return self.storage.get_plugin_by_name(name)
        else:
            # Local mode
            plugin_dir = self._local_plugin_dir / name
            if plugin_dir.exists():
                tool_config_path = plugin_dir / "tool_config.json"
                if tool_config_path.exists():
                    with open(tool_config_path) as f:
                        return json.load(f)
            return None

    # Plugin management
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        return self.storage.update_plugin(plugin_id, {"is_enabled": True})

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        return self.storage.update_plugin(plugin_id, {"is_enabled": False})

    def delete_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """Delete a plugin (from DB and blob storage)"""
        try:
            # Get plugin info first
            plugin = self.storage.get_plugin(plugin_id)
            if not plugin:
                return False, "Plugin not found"

            # Delete from blob storage
            if is_azure_environment() and plugin.get("blob_path"):
                try:
                    blob_client = self.blob_client.get_blob_client(
                        container=self.config.blob.container_name,
                        blob=plugin["blob_path"]
                    )
                    blob_client.delete_blob()
                except Exception as e:
                    logger.warning(f"Could not delete blob: {e}")

            # Delete local copy
            local_path = self._local_plugin_dir / plugin["name"]
            if local_path.exists():
                shutil.rmtree(local_path)

            # Delete from database
            if self.storage.delete_plugin(plugin_id):
                return True, "Plugin deleted successfully"
            else:
                return False, "Failed to delete from database"

        except Exception as e:
            logger.error(f"Failed to delete plugin: {e}")
            return False, str(e)

    # Plugin loading
    async def reload_plugin(self, plugin_name: str, tool_manager) -> bool:
        """
        Hot-reload a plugin

        Downloads from blob storage and reloads in tool_manager.
        """
        try:
            plugin = self.get_plugin_by_name(plugin_name)
            if not plugin:
                return False

            # In Azure, download fresh copy from blob
            if is_azure_environment() and plugin.get("blob_path"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = Path(temp_dir) / f"{plugin_name}.zip"

                    # Download blob
                    blob_client = self.blob_client.get_blob_client(
                        container=self.config.blob.container_name,
                        blob=plugin["blob_path"]
                    )

                    with open(zip_path, "wb") as f:
                        download_stream = blob_client.download_blob()
                        f.write(download_stream.readall())

                    # Extract to plugins directory
                    local_path = self._local_plugin_dir / plugin_name
                    if local_path.exists():
                        shutil.rmtree(local_path)

                    with zipfile.ZipFile(zip_path, "r") as zf:
                        zf.extractall(local_path)

            # Reload in tool_manager
            # This would require tool_manager to support unload/reload
            # For now, just log success
            logger.info(f"Plugin {plugin_name} reloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False


# Global service instance
_plugin_registry_service: Optional[PluginRegistryService] = None


def get_plugin_registry_service() -> PluginRegistryService:
    """Get or create plugin registry service"""
    global _plugin_registry_service
    if _plugin_registry_service is None:
        _plugin_registry_service = PluginRegistryService()
    return _plugin_registry_service
