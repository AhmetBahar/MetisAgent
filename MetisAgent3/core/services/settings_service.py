"""
Settings Service - Advanced User Settings Management

CLAUDE.md COMPLIANT:
- EAV model based flexible settings system
- Category-based settings organization
- Validation and type checking
- Default values and constraints
- Settings templates and presets
- Bulk settings operations
- Settings migration support
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from ..storage.sqlite_storage import SQLiteUserStorage

logger = logging.getLogger(__name__)


class SettingType(str, Enum):
    """Supported setting value types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float" 
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    ENCRYPTED = "encrypted"


class SettingCategory(str, Enum):
    """Setting categories for organization"""
    GENERAL = "general"
    APPEARANCE = "appearance"
    PRIVACY = "privacy"
    NOTIFICATIONS = "notifications"
    INTEGRATIONS = "integrations"
    API_KEYS = "api_keys"
    OAUTH = "oauth"
    TOOLS = "tools"
    PERFORMANCE = "performance"
    ADVANCED = "advanced"


@dataclass
class SettingDefinition:
    """Definition of a setting with metadata"""
    key: str
    category: SettingCategory
    setting_type: SettingType
    default_value: Any
    description: str
    is_required: bool = False
    is_encrypted: bool = False
    is_readonly: bool = False
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    max_length: Optional[int] = None
    validation_pattern: Optional[str] = None
    depends_on: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass 
class UserSetting:
    """Individual user setting with metadata"""
    key: str
    value: Any
    setting_type: SettingType
    category: SettingCategory
    is_encrypted: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    user_id: str


class SettingsService:
    """Advanced settings management service"""
    
    def __init__(self, storage: Optional[SQLiteUserStorage] = None):
        self.storage = storage or SQLiteUserStorage()
        self.setting_definitions: Dict[str, SettingDefinition] = {}
        self._init_default_settings()
        logger.info("Settings service initialized")
    
    def _init_default_settings(self):
        """Initialize default setting definitions"""
        
        # General Settings
        self.register_setting(SettingDefinition(
            key="user_language",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.STRING,
            default_value="en",
            description="User interface language",
            choices=["en", "tr", "es", "fr", "de"],
            tags=["ui", "localization"]
        ))
        
        self.register_setting(SettingDefinition(
            key="timezone",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.STRING,
            default_value="UTC",
            description="User timezone for date/time display",
            tags=["time", "display"]
        ))
        
        self.register_setting(SettingDefinition(
            key="date_format",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.STRING,
            default_value="YYYY-MM-DD",
            description="Preferred date format",
            choices=["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "DD.MM.YYYY"],
            tags=["format", "display"]
        ))
        
        # Appearance Settings
        self.register_setting(SettingDefinition(
            key="theme",
            category=SettingCategory.APPEARANCE,
            setting_type=SettingType.STRING,
            default_value="light",
            description="UI theme preference",
            choices=["light", "dark", "auto"],
            tags=["ui", "theme"]
        ))
        
        self.register_setting(SettingDefinition(
            key="items_per_page",
            category=SettingCategory.APPEARANCE,
            setting_type=SettingType.INTEGER,
            default_value=20,
            description="Number of items to display per page",
            min_value=5,
            max_value=100,
            tags=["pagination", "display"]
        ))
        
        # API Keys (Encrypted)
        self.register_setting(SettingDefinition(
            key="openai_api_key",
            category=SettingCategory.API_KEYS,
            setting_type=SettingType.ENCRYPTED,
            default_value=None,
            description="OpenAI API Key",
            is_encrypted=True,
            tags=["api", "llm", "openai"]
        ))
        
        self.register_setting(SettingDefinition(
            key="anthropic_api_key",
            category=SettingCategory.API_KEYS,
            setting_type=SettingType.ENCRYPTED,
            default_value=None,
            description="Anthropic (Claude) API Key", 
            is_encrypted=True,
            tags=["api", "llm", "anthropic"]
        ))
        
        self.register_setting(SettingDefinition(
            key="google_api_key",
            category=SettingCategory.API_KEYS,
            setting_type=SettingType.ENCRYPTED,
            default_value=None,
            description="Google API Key",
            is_encrypted=True,
            tags=["api", "google"]
        ))
        
        # Privacy Settings
        self.register_setting(SettingDefinition(
            key="analytics_enabled",
            category=SettingCategory.PRIVACY,
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            description="Enable usage analytics",
            tags=["privacy", "analytics"]
        ))
        
        self.register_setting(SettingDefinition(
            key="data_retention_days",
            category=SettingCategory.PRIVACY,
            setting_type=SettingType.INTEGER,
            default_value=30,
            description="Days to retain conversation data",
            min_value=1,
            max_value=365,
            tags=["privacy", "retention"]
        ))
        
        # Notifications
        self.register_setting(SettingDefinition(
            key="notifications_enabled",
            category=SettingCategory.NOTIFICATIONS,
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            description="Enable notifications",
            tags=["notifications"]
        ))
        
        self.register_setting(SettingDefinition(
            key="notification_channels",
            category=SettingCategory.NOTIFICATIONS,
            setting_type=SettingType.LIST,
            default_value=["email", "in_app"],
            description="Enabled notification channels",
            choices=["email", "in_app", "sms", "push"],
            tags=["notifications", "channels"]
        ))
        
        # Tool Settings
        self.register_setting(SettingDefinition(
            key="default_llm_provider",
            category=SettingCategory.TOOLS,
            setting_type=SettingType.STRING,
            default_value="anthropic",
            description="Default LLM provider",
            choices=["openai", "anthropic"],
            tags=["llm", "tools"]
        ))
        
        self.register_setting(SettingDefinition(
            key="default_llm_model",
            category=SettingCategory.TOOLS,
            setting_type=SettingType.STRING,
            default_value="claude-3-5-sonnet-20241022",
            description="Default LLM model",
            tags=["llm", "model"]
        ))
        
        self.register_setting(SettingDefinition(
            key="max_tokens_per_request",
            category=SettingCategory.TOOLS,
            setting_type=SettingType.INTEGER,
            default_value=2000,
            description="Maximum tokens per LLM request",
            min_value=100,
            max_value=8000,
            tags=["llm", "limits"]
        ))
        
        # Performance Settings
        self.register_setting(SettingDefinition(
            key="cache_enabled",
            category=SettingCategory.PERFORMANCE,
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            description="Enable response caching",
            tags=["performance", "cache"]
        ))
        
        self.register_setting(SettingDefinition(
            key="concurrent_requests",
            category=SettingCategory.PERFORMANCE,
            setting_type=SettingType.INTEGER,
            default_value=3,
            description="Maximum concurrent API requests",
            min_value=1,
            max_value=10,
            tags=["performance", "concurrency"]
        ))
    
    def register_setting(self, definition: SettingDefinition):
        """Register a new setting definition"""
        self.setting_definitions[definition.key] = definition
        logger.debug(f"Registered setting: {definition.key}")
    
    def get_setting_definition(self, key: str) -> Optional[SettingDefinition]:
        """Get setting definition by key"""
        return self.setting_definitions.get(key)
    
    def get_setting_definitions_by_category(self, category: SettingCategory) -> Dict[str, SettingDefinition]:
        """Get all setting definitions in a category"""
        return {
            key: definition for key, definition in self.setting_definitions.items()
            if definition.category == category
        }
    
    async def get_user_setting(self, user_id: str, key: str) -> Any:
        """Get user setting value (returns default if not set)"""
        try:
            value = await self.storage.get_user_attribute(user_id, key)
            if value is not None:
                return self._deserialize_setting_value(key, value)
            
            # Return default value if not set
            definition = self.get_setting_definition(key)
            return definition.default_value if definition else None
            
        except Exception as e:
            logger.error(f"Failed to get setting {key} for user {user_id}: {e}")
            # Return default on error
            definition = self.get_setting_definition(key)
            return definition.default_value if definition else None
    
    async def set_user_setting(self, user_id: str, key: str, value: Any) -> bool:
        """Set user setting value with validation"""
        try:
            # Validate setting
            definition = self.get_setting_definition(key)
            if not definition:
                raise ValueError(f"Unknown setting: {key}")
            
            if definition.is_readonly:
                raise ValueError(f"Setting {key} is readonly")
            
            # Validate value
            validated_value = self._validate_setting_value(definition, value)
            serialized_value = self._serialize_setting_value(key, validated_value)
            
            # Store in database
            await self.storage.set_user_attribute(
                user_id=user_id,
                attribute_name=key,
                attribute_value=serialized_value,
                encrypt=definition.is_encrypted
            )
            
            logger.info(f"Set setting {key} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set setting {key} for user {user_id}: {e}")
            return False
    
    async def get_user_settings_by_category(
        self, 
        user_id: str, 
        category: SettingCategory,
        include_defaults: bool = True
    ) -> Dict[str, Any]:
        """Get all user settings in a category"""
        category_definitions = self.get_setting_definitions_by_category(category)
        settings = {}
        
        for key, definition in category_definitions.items():
            value = await self.get_user_setting(user_id, key)
            if value is not None or include_defaults:
                settings[key] = value
        
        return settings
    
    async def get_all_user_settings(self, user_id: str, include_defaults: bool = True) -> Dict[str, Any]:
        """Get all user settings grouped by category"""
        result = {}
        
        for category in SettingCategory:
            category_settings = await self.get_user_settings_by_category(
                user_id, category, include_defaults
            )
            if category_settings:
                result[category.value] = category_settings
        
        return result
    
    async def bulk_set_user_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, bool]:
        """Set multiple user settings in bulk"""
        results = {}
        
        for key, value in settings.items():
            results[key] = await self.set_user_setting(user_id, key, value)
        
        return results
    
    async def reset_user_setting(self, user_id: str, key: str) -> bool:
        """Reset user setting to default value"""
        try:
            definition = self.get_setting_definition(key)
            if not definition:
                return False
            
            if definition.default_value is None:
                # Delete the setting
                return await self.delete_user_setting(user_id, key)
            else:
                # Set to default value
                return await self.set_user_setting(user_id, key, definition.default_value)
                
        except Exception as e:
            logger.error(f"Failed to reset setting {key} for user {user_id}: {e}")
            return False
    
    async def delete_user_setting(self, user_id: str, key: str) -> bool:
        """Delete user setting"""
        try:
            # Note: Would need a delete method in SQLiteUserStorage
            # For now, set to None or empty value based on type
            definition = self.get_setting_definition(key)
            if definition and definition.setting_type == SettingType.BOOLEAN:
                return await self.set_user_setting(user_id, key, False)
            else:
                return await self.set_user_setting(user_id, key, None)
                
        except Exception as e:
            logger.error(f"Failed to delete setting {key} for user {user_id}: {e}")
            return False
    
    async def search_settings(self, query: str) -> List[SettingDefinition]:
        """Search setting definitions by key, description, or tags"""
        query_lower = query.lower()
        results = []
        
        for definition in self.setting_definitions.values():
            # Search in key
            if query_lower in definition.key.lower():
                results.append(definition)
                continue
            
            # Search in description
            if query_lower in definition.description.lower():
                results.append(definition)
                continue
            
            # Search in tags
            if definition.tags:
                for tag in definition.tags:
                    if query_lower in tag.lower():
                        results.append(definition)
                        break
        
        return results
    
    def _validate_setting_value(self, definition: SettingDefinition, value: Any) -> Any:
        """Validate setting value against definition constraints"""
        if value is None and definition.is_required:
            raise ValueError(f"Setting {definition.key} is required")
        
        if value is None:
            return None
        
        # Type validation
        if definition.setting_type == SettingType.STRING:
            if not isinstance(value, str):
                value = str(value)
            
            if definition.max_length and len(value) > definition.max_length:
                raise ValueError(f"Value too long (max {definition.max_length})")
            
            if definition.validation_pattern:
                import re
                if not re.match(definition.validation_pattern, value):
                    raise ValueError(f"Value doesn't match required pattern")
        
        elif definition.setting_type == SettingType.INTEGER:
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid integer value: {value}")
            
            if definition.min_value is not None and value < definition.min_value:
                raise ValueError(f"Value below minimum ({definition.min_value})")
            
            if definition.max_value is not None and value > definition.max_value:
                raise ValueError(f"Value above maximum ({definition.max_value})")
        
        elif definition.setting_type == SettingType.FLOAT:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid float value: {value}")
            
            if definition.min_value is not None and value < definition.min_value:
                raise ValueError(f"Value below minimum ({definition.min_value})")
            
            if definition.max_value is not None and value > definition.max_value:
                raise ValueError(f"Value above maximum ({definition.max_value})")
        
        elif definition.setting_type == SettingType.BOOLEAN:
            if not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    value = bool(value)
        
        elif definition.setting_type in [SettingType.JSON, SettingType.LIST]:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON value: {value}")
        
        # Choice validation
        if definition.choices and value not in definition.choices:
            raise ValueError(f"Value must be one of: {definition.choices}")
        
        return value
    
    def _serialize_setting_value(self, key: str, value: Any) -> str:
        """Serialize setting value for storage"""
        if value is None:
            return ""
        
        definition = self.get_setting_definition(key)
        if not definition:
            return str(value)
        
        if definition.setting_type in [SettingType.JSON, SettingType.LIST]:
            return json.dumps(value)
        elif definition.setting_type == SettingType.BOOLEAN:
            return "1" if value else "0"
        else:
            return str(value)
    
    def _deserialize_setting_value(self, key: str, value: str) -> Any:
        """Deserialize setting value from storage"""
        if not value:
            return None
        
        definition = self.get_setting_definition(key)
        if not definition:
            return value
        
        try:
            if definition.setting_type == SettingType.INTEGER:
                return int(value)
            elif definition.setting_type == SettingType.FLOAT:
                return float(value)
            elif definition.setting_type == SettingType.BOOLEAN:
                return value in ("1", "true", "True")
            elif definition.setting_type in [SettingType.JSON, SettingType.LIST]:
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to deserialize setting {key}: {e}")
            return definition.default_value
    
    async def export_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Export all user settings for backup/migration"""
        settings = await self.get_all_user_settings(user_id, include_defaults=False)
        return {
            "user_id": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "settings": settings
        }
    
    async def import_user_settings(self, user_id: str, settings_data: Dict[str, Any]) -> Dict[str, bool]:
        """Import user settings from backup/migration"""
        settings = settings_data.get("settings", {})
        results = {}
        
        for category, category_settings in settings.items():
            if isinstance(category_settings, dict):
                for key, value in category_settings.items():
                    results[key] = await self.set_user_setting(user_id, key, value)
        
        return results
    
    async def get_setting_schema(self, category: Optional[SettingCategory] = None) -> Dict[str, Any]:
        """Get settings schema for UI generation"""
        definitions = (
            self.get_setting_definitions_by_category(category) 
            if category else self.setting_definitions
        )
        
        schema = {
            "categories": {},
            "definitions": {}
        }
        
        for key, definition in definitions.items():
            schema["definitions"][key] = {
                "key": definition.key,
                "category": definition.category.value,
                "type": definition.setting_type.value,
                "default": definition.default_value,
                "description": definition.description,
                "required": definition.is_required,
                "readonly": definition.is_readonly,
                "encrypted": definition.is_encrypted,
                "choices": definition.choices,
                "min_value": definition.min_value,
                "max_value": definition.max_value,
                "max_length": definition.max_length,
                "validation_pattern": definition.validation_pattern,
                "tags": definition.tags
            }
            
            # Group by category
            cat_name = definition.category.value
            if cat_name not in schema["categories"]:
                schema["categories"][cat_name] = []
            schema["categories"][cat_name].append(key)
        
        return schema


# Settings Service Integration Helper
class SettingsIntegration:
    """Helper for integrating settings with other components"""
    
    def __init__(self, settings_service: SettingsService):
        self.settings = settings_service
    
    async def get_llm_config(self, user_id: str) -> Dict[str, Any]:
        """Get LLM configuration from user settings"""
        config = {}
        
        # Get API keys
        openai_key = await self.settings.get_user_setting(user_id, "openai_api_key")
        anthropic_key = await self.settings.get_user_setting(user_id, "anthropic_api_key")
        
        config["api_keys"] = {
            "openai": openai_key,
            "anthropic": anthropic_key
        }
        
        # Get defaults
        config["default_provider"] = await self.settings.get_user_setting(user_id, "default_llm_provider")
        config["default_model"] = await self.settings.get_user_setting(user_id, "default_llm_model")
        config["max_tokens"] = await self.settings.get_user_setting(user_id, "max_tokens_per_request")
        
        return config
    
    async def get_ui_config(self, user_id: str) -> Dict[str, Any]:
        """Get UI configuration from user settings"""
        config = {}
        
        # Appearance settings
        config["theme"] = await self.settings.get_user_setting(user_id, "theme")
        config["language"] = await self.settings.get_user_setting(user_id, "user_language")
        config["timezone"] = await self.settings.get_user_setting(user_id, "timezone")
        config["date_format"] = await self.settings.get_user_setting(user_id, "date_format")
        config["items_per_page"] = await self.settings.get_user_setting(user_id, "items_per_page")
        
        return config
    
    async def get_privacy_config(self, user_id: str) -> Dict[str, Any]:
        """Get privacy configuration from user settings"""
        config = {}
        
        config["analytics_enabled"] = await self.settings.get_user_setting(user_id, "analytics_enabled")
        config["data_retention_days"] = await self.settings.get_user_setting(user_id, "data_retention_days")
        
        return config