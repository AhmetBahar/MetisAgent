"""
Settings Manager - User bilgileri ve OAuth2 credentials yönetimi (MCP Tool)
ChromaDB'den user_storage'e geçiş ile güncellenmiş versiyon
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class SettingsManagerTool(MCPTool):
    """Kullanıcı ayarları ve OAuth2 credentials yönetimi"""
    
    def __init__(self):
        """Settings Manager MCP Tool başlatır"""
        super().__init__(
            name="settings_manager",
            description="User settings and OAuth2 credentials management",
            version="2.0.0"
        )
        
        # Import user_storage here to avoid circular imports
        from .user_storage import get_user_storage
        self.storage = get_user_storage()
        
        # Register capabilities
        self.add_capability("user_settings")
        self.add_capability("api_key_management")
        self.add_capability("oauth2_credentials")
        self.add_capability("user_mapping")
        self.add_capability("profile_management")
        
        # Register actions
        self.register_action(
            "get_user_setting",
            self._get_user_setting,
            required_params=["user_id", "setting_key"],
            optional_params=["default_value"]
        )
        
        self.register_action(
            "set_user_setting", 
            self._set_user_setting,
            required_params=["user_id", "setting_key", "setting_value"],
            optional_params=["encrypt"]
        )
        
        self.register_action(
            "get_api_key",
            self._get_api_key,
            required_params=["user_id", "service"],
            optional_params=[]
        )
        
        self.register_action(
            "set_api_key",
            self._set_api_key,
            required_params=["user_id", "service", "api_key"],
            optional_params=[]
        )
        
        self.register_action(
            "get_oauth2_credentials",
            self._get_oauth2_credentials,
            required_params=["user_id"],
            optional_params=["provider"]
        )
        
        self.register_action(
            "set_oauth2_credentials",
            self._set_oauth2_credentials,
            required_params=["user_id", "provider", "credentials"],
            optional_params=[]
        )
        
        self.register_action(
            "get_user_mapping",
            self._get_user_mapping,
            required_params=["user_id", "provider"],
            optional_params=[]
        )
        
        self.register_action(
            "set_user_mapping",
            self._set_user_mapping,
            required_params=["user_id", "provider", "external_id"],
            optional_params=[]
        )
        
        self.register_action(
            "get_all_users",
            self._get_all_users,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "get_user_profile",
            self._get_user_profile,
            required_params=["user_id"],
            optional_params=[]
        )
        
        self.register_action(
            "set_user_profile",
            self._set_user_profile,
            required_params=["user_id", "profile_data"],
            optional_params=[]
        )
        
        self.register_action(
            "get_google_client_credentials",
            self._get_google_client_credentials,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "set_google_client_credentials",
            self._set_google_client_credentials,
            required_params=["client_id", "client_secret"],
            optional_params=[]
        )
        
        self.register_action(
            "get_user_property",
            self._get_user_property,
            required_params=["user_id", "property_name"],
            optional_params=[]
        )
        
        self.register_action(
            "set_user_property",
            self._set_user_property,
            required_params=["user_id", "property_name", "value"],
            optional_params=[]
        )
        
        self.register_action(
            "delete_user_property",
            self._delete_user_property,
            required_params=["user_id", "property_name"],
            optional_params=[]
        )
        
        logger.info("Settings Manager MCP Tool initialized with user_storage backend")
    
    def _get_user_setting(self, user_id: str, setting_key: str, default_value: Any = None) -> MCPToolResult:
        """Kullanıcı ayarını al"""
        try:
            value = self.storage.get_property(user_id, setting_key, default_value)
            return MCPToolResult(
                success=True,
                data={"setting_key": setting_key, "value": value},
                metadata={"user_id": user_id}
            )
        except Exception as e:
            logger.error(f"Error getting user setting {setting_key} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                data={"setting_key": setting_key, "default_value": default_value},
                metadata={"user_id": user_id}
            )
    
    def _set_user_setting(self, user_id: str, setting_key: str, setting_value: Any, encrypt: bool = False) -> MCPToolResult:
        """Kullanıcı ayarını kaydet"""
        try:
            property_type = 'json' if isinstance(setting_value, (dict, list)) else 'string'
            
            result = self.storage.set_property(
                user_id=user_id,
                property_name=setting_key,
                property_value=setting_value,
                property_type=property_type,
                encrypt=encrypt
            )
            
            if result:
                logger.info(f"User setting {setting_key} saved for {user_id}")
                return MCPToolResult(
                    success=True,
                    data={"setting_key": setting_key, "saved": True},
                    metadata={"user_id": user_id, "encrypted": encrypt}
                )
            
            return MCPToolResult(
                success=False,
                error="Failed to save setting",
                metadata={"user_id": user_id, "setting_key": setting_key}
            )
            
        except Exception as e:
            logger.error(f"Error setting user setting {setting_key} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "setting_key": setting_key}
            )
    
    def _get_api_key(self, user_id: str, service: str) -> MCPToolResult:
        """API key al"""
        try:
            setting_key = f"api_key_{service}"
            api_key_data = self.storage.get_property(user_id, setting_key)
            
            api_key = None
            if isinstance(api_key_data, dict):
                api_key = api_key_data.get('api_key') or api_key_data.get('key')
            elif isinstance(api_key_data, str):
                api_key = api_key_data
                
            return MCPToolResult(
                success=True,
                data={"service": service, "api_key": api_key, "has_key": bool(api_key)},
                metadata={"user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Error getting API key {service} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "service": service}
            )
    
    def _set_api_key(self, user_id: str, service: str, api_key: str) -> MCPToolResult:
        """API key kaydet"""
        try:
            setting_key = f"api_key_{service}"
            api_key_data = {
                'api_key': api_key,
                'service': service,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.storage.set_property(
                user_id=user_id,
                property_name=setting_key,
                property_value=api_key_data,
                property_type='json',
                encrypt=True
            )
            
            return MCPToolResult(
                success=result,
                data={"service": service, "saved": result},
                metadata={"user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Error setting API key {service} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "service": service}
            )
    
    def _get_oauth2_credentials(self, user_id: str, provider: str = 'google') -> MCPToolResult:
        """OAuth2 credentials al"""
        try:
            # OAuth token'ını user_storage'dan al
            oauth_token = self.storage.get_oauth_token(user_id, provider)
            if oauth_token:
                return MCPToolResult(
                    success=True,
                    data={"provider": provider, "credentials": oauth_token},
                    metadata={"user_id": user_id, "source": "oauth_token"}
                )
            
            # Fallback: settings'den al
            setting_key = f"oauth2_{provider}"
            credentials = self.storage.get_property(user_id, setting_key)
            
            return MCPToolResult(
                success=bool(credentials),
                data={"provider": provider, "credentials": credentials},
                metadata={"user_id": user_id, "source": "settings"}
            )
            
        except Exception as e:
            logger.error(f"Error getting OAuth2 credentials {provider} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "provider": provider}
            )
    
    def _set_oauth2_credentials(self, user_id: str, provider: str, credentials: Dict) -> MCPToolResult:
        """OAuth2 credentials kaydet"""
        try:
            result = self.storage.set_oauth_token(user_id, provider, credentials)
            
            if result:
                logger.info(f"OAuth2 credentials {provider} saved for {user_id}")
                return MCPToolResult(
                    success=True,
                    data={"provider": provider, "saved": True},
                    metadata={"user_id": user_id}
                )
            
            return MCPToolResult(
                success=False,
                error="Failed to save OAuth2 credentials",
                metadata={"user_id": user_id, "provider": provider}
            )
            
        except Exception as e:
            logger.error(f"Error setting OAuth2 credentials {provider} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "provider": provider}
            )
    
    def _get_user_mapping(self, user_id: str, provider: str) -> MCPToolResult:
        """User mapping al"""
        try:
            mapping = self.storage.get_user_mapping(user_id, provider)
            return MCPToolResult(
                success=True,
                data={"user_id": user_id, "provider": provider, "external_id": mapping},
                metadata={"has_mapping": bool(mapping)}
            )
        except Exception as e:
            logger.error(f"Error getting user mapping {provider} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "provider": provider}
            )
    
    def _set_user_mapping(self, user_id: str, provider: str, external_id: str) -> MCPToolResult:
        """User mapping kaydet"""
        try:
            result = self.storage.set_user_mapping(user_id, provider, external_id)
            
            if result:
                logger.info(f"User mapping {provider} saved: {user_id} -> {external_id}")
                return MCPToolResult(
                    success=True,
                    data={"user_id": user_id, "provider": provider, "external_id": external_id},
                    metadata={"saved": True}
                )
            
            return MCPToolResult(
                success=False,
                error="Failed to save user mapping",
                metadata={"user_id": user_id, "provider": provider}
            )
            
        except Exception as e:
            logger.error(f"Error setting user mapping {provider} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "provider": provider}
            )
    
    def _get_all_users(self) -> MCPToolResult:
        """Tüm kullanıcı ID'lerini al"""
        try:
            users = self.storage.list_users()
            return MCPToolResult(
                success=True,
                data={"users": users, "user_count": len(users)},
                metadata={"source": "user_storage"}
            )
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                data={"users": [], "user_count": 0}
            )
    
    def _get_user_profile(self, user_id: str) -> MCPToolResult:
        """Kullanıcı profil bilgilerini al"""
        try:
            profile = self.storage.get_user_profile(user_id)
            return MCPToolResult(
                success=True,
                data={"user_id": user_id, "profile": profile},
                metadata={"has_profile": bool(profile)}
            )
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id}
            )
    
    def _set_user_profile(self, user_id: str, profile_data: Dict) -> MCPToolResult:
        """Kullanıcı profil bilgilerini kaydet"""
        try:
            result = self.storage.set_user_profile(user_id, profile_data)
            
            if result:
                logger.info(f"User profile saved for {user_id}")
                return MCPToolResult(
                    success=True,
                    data={"user_id": user_id, "profile_saved": True},
                    metadata={"profile_keys": list(profile_data.keys()) if profile_data else []}
                )
            
            return MCPToolResult(
                success=False,
                error="Failed to save user profile",
                metadata={"user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Error setting user profile for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id}
            )
    
    def _get_google_client_credentials(self) -> MCPToolResult:
        """Google OAuth2 client credentials al"""
        try:
            # Önce database'den al
            admin_settings = self.storage.get_property('system', 'google_oauth_client', {})
            logger.info(f"Google credentials from SQLite: {bool(admin_settings)}")
            
            if admin_settings and admin_settings.get('client_id') and admin_settings.get('client_secret'):
                return MCPToolResult(
                    success=True,
                    data=admin_settings,
                    metadata={"source": "database"}
                )
            
            # Environment variables'dan al
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
            logger.info(f"Google credentials from ENV: client_id={bool(client_id)}, client_secret={bool(client_secret)}")
            
            if (client_id and client_secret and 
                not client_id.startswith('your-') and 
                not client_secret.startswith('your-')):
                credentials = {
                    'client_id': client_id,
                    'client_secret': client_secret
                }
                return MCPToolResult(
                    success=True,
                    data=credentials,
                    metadata={"source": "environment"}
                )
            
            # Son fallback: environment variables required
            credentials = {
                'client_id': os.getenv("GOOGLE_CLIENT_ID", ""),
                'client_secret': os.getenv("GOOGLE_CLIENT_SECRET", "")
            }
            
            return MCPToolResult(
                success=True,
                data=credentials,
                metadata={"source": "hardcoded"}
            )
            
        except Exception as e:
            logger.error(f"Error getting Google client credentials: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"source": "error"}
            )
    
    def _set_google_client_credentials(self, client_id: str, client_secret: str) -> MCPToolResult:
        """Google OAuth2 client credentials kaydet"""
        try:
            credentials = {
                'client_id': client_id,
                'client_secret': client_secret,
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.storage.set_property(
                user_id='system',
                property_name='google_oauth_client',
                property_value=credentials,
                property_type='json',
                encrypt=True
            )
            
            return MCPToolResult(
                success=result,
                data={"saved": result, "client_id": client_id},
                metadata={"encrypted": True}
            )
            
        except Exception as e:
            logger.error(f"Error setting Google client credentials: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"client_id": client_id}
            )

    # Legacy compatibility methods
    def get_user_setting(self, user_id: str, setting_key: str, default_value: Any = None) -> Any:
        """Legacy compatibility method"""
        result = self._get_user_setting(user_id, setting_key, default_value)
        return result.data.get("value") if result.success else default_value
        
    def get_google_credentials(self, user_id: str) -> Optional[Dict]:
        """Legacy compatibility - get Google OAuth2 credentials"""
        result = self._get_oauth2_credentials(user_id, "google")
        return result.data.get("credentials") if result.success else None
    
    # Additional legacy compatibility methods
    def get_oauth2_credentials(self, user_id: str, provider: str = 'google'):
        """Legacy method - wrapper around MCP action"""
        result = self._get_oauth2_credentials(user_id, provider)
        return result.data.get('credentials') if result.success else None
    
    def get_user_mapping(self, user_id: str, provider: str):
        """Legacy method - wrapper around MCP action"""
        result = self._get_user_mapping(user_id, provider)
        return result.data.get('external_id') if result.success else None
    
    def set_oauth2_credentials(self, user_id: str, provider: str, credentials):
        """Legacy method - wrapper around MCP action"""
        result = self._set_oauth2_credentials(user_id, provider, credentials)
        return result.success
    
    def set_user_mapping(self, user_id: str, provider: str, mapping):
        """Legacy method - wrapper around MCP action"""
        result = self._set_user_mapping(user_id, provider, mapping)
        return result.success
    
    def get_google_client_credentials(self):
        """Legacy method - wrapper around MCP action"""
        result = self._get_google_client_credentials()
        return result.data if result.success else None
    
    def get_user_property(self, user_id: str, property_name: str):
        """Legacy method - direct storage access for compatibility"""
        try:
            return self.storage.get_property(user_id, property_name)
        except Exception as e:
            logger.error(f"Error getting user property {property_name} for {user_id}: {e}")
            return None
    
    def set_user_property(self, user_id: str, property_name: str, value):
        """Legacy method - direct storage access for compatibility"""
        try:
            self.storage.set_property(user_id, property_name, value)
            return True
        except Exception as e:
            logger.error(f"Error setting user property {property_name} for {user_id}: {e}")
            return False
    
    def delete_user_property(self, user_id: str, property_name: str):
        """Legacy method - direct storage access for compatibility"""
        try:
            self.storage.delete_property(user_id, property_name)
            return True
        except Exception as e:
            logger.error(f"Error deleting user property {property_name} for {user_id}: {e}")
            return False
    
    def get_all_users(self):
        """Legacy method - wrapper around MCP action"""
        result = self._get_all_users()
        return result.data.get('users', []) if result.success else []
    
    def get_user_profile(self, user_id: str):
        """Legacy method - wrapper around MCP action"""
        result = self._get_user_profile(user_id)
        return result.data.get('profile') if result.success else None
    
    def set_user_profile(self, user_id: str, profile_data):
        """Legacy method - wrapper around MCP action"""  
        result = self._set_user_profile(user_id, profile_data)
        return result.success
    
    def _get_user_property(self, user_id: str, property_name: str) -> MCPToolResult:
        """Get user property from storage"""
        try:
            value = self.storage.get_property(user_id, property_name)
            return MCPToolResult(
                success=True,
                data={'value': value},
                metadata={'user_id': user_id, 'property_name': property_name}
            )
        except Exception as e:
            logger.error(f"Error getting user property {property_name} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={'user_id': user_id, 'property_name': property_name}
            )
    
    def _set_user_property(self, user_id: str, property_name: str, value: Any) -> MCPToolResult:
        """Set user property in storage"""
        try:
            self.storage.set_property(user_id, property_name, value)
            return MCPToolResult(
                success=True,
                data={'set': True},
                metadata={'user_id': user_id, 'property_name': property_name}
            )
        except Exception as e:
            logger.error(f"Error setting user property {property_name} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={'user_id': user_id, 'property_name': property_name}
            )
    
    def _delete_user_property(self, user_id: str, property_name: str) -> MCPToolResult:
        """Delete user property from storage"""
        try:
            self.storage.delete_property(user_id, property_name)
            return MCPToolResult(
                success=True,
                data={'deleted': True},
                metadata={'user_id': user_id, 'property_name': property_name}
            )
        except Exception as e:
            logger.error(f"Error deleting user property {property_name} for {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={'user_id': user_id, 'property_name': property_name}
            )

def register_tool(registry):
    """Register Settings Manager tool with the registry"""
    try:
        tool = SettingsManagerTool()
        registry.register_tool(tool)
        logger.info("Settings Manager MCP tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register Settings Manager tool: {e}")
        return False

# Global settings manager instance - legacy compatibility
_settings_manager = None

def get_settings_manager():
    """Legacy compatibility function"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManagerTool()
    return _settings_manager

def reset_settings_manager():
    """Settings manager instance'ını sıfırla"""
    global _settings_manager
    _settings_manager = None

# Export the instance for backward compatibility
settings_manager = get_settings_manager()