#!/usr/bin/env python3
"""
Environment Configuration Manager
Centralized configuration management for MetisAgent2
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """Centralized environment configuration manager"""
    
    def __init__(self):
        self._load_env_file()
        self._validate_required_vars()
        
    def _load_env_file(self):
        """Load .env file if it exists"""
        env_file = Path('.env')
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info("Loaded environment variables from .env file")
            except ImportError:
                logger.warning("python-dotenv not installed. Using system environment variables only.")
        else:
            logger.warning(".env file not found. Using system environment variables only.")
    
    def _validate_required_vars(self):
        """Validate that required environment variables are set"""
        required_vars = [
            'OPENAI_API_KEY',
            'GOOGLE_CLIENT_ID', 
            'GOOGLE_CLIENT_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not self.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.info("Please copy .env.example to .env and fill in the required values")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with optional default"""
        return os.getenv(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = self.get(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable"""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default
    
    def get_list(self, key: str, separator: str = ',', default: list = None) -> list:
        """Get list environment variable"""
        if default is None:
            default = []
        
        value = self.get(key)
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @property
    def api_keys(self) -> Dict[str, str]:
        """Get all API keys"""
        return {
            'openai': self.get('OPENAI_API_KEY'),
            'anthropic': self.get('ANTHROPIC_API_KEY'),
            'huggingface': self.get('HUGGINGFACE_API_KEY')
        }
    
    @property
    def google_oauth(self) -> Dict[str, str]:
        """Get Google OAuth configuration"""
        return {
            'client_id': self.get('GOOGLE_CLIENT_ID'),
            'client_secret': self.get('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': self.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/oauth2/google/callback')
        }
    
    @property
    def server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        return {
            'host': self.get('FLASK_HOST', '0.0.0.0'),
            'port': self.get_int('FLASK_PORT', 5001),
            'debug': self.get_bool('FLASK_DEBUG', False),
            'base_url': self.get('BASE_URL', 'http://localhost:5001')
        }
    
    @property
    def storage_paths(self) -> Dict[str, str]:
        """Get storage paths configuration"""
        return {
            'metis_data': self.get('METIS_DATA_PATH', './metis_json_storage'),
            'oauth_tokens': self.get('OAUTH_TOKENS_PATH', './oauth_tokens'),
            'generated_images': self.get('GENERATED_IMAGES_PATH', './generated_images'),
            'conversation_storage': self.get('CONVERSATION_STORAGE_PATH', './conversation_storage'),
            'graph_memory': self.get('GRAPH_MEMORY_PATH', './graph_memory_storage')
        }
    
    @property
    def security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            'session_secret_key': self.get('SESSION_SECRET_KEY', 'dev-only-change-in-production'),
            'session_timeout_minutes': self.get_int('SESSION_TIMEOUT_MINUTES', 60),
            'encryption_key': self.get('ENCRYPTION_KEY')
        }
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': self.get('LOG_LEVEL', 'INFO'),
            'file': self.get('LOG_FILE', './app.log')
        }
    
    @property
    def feature_flags(self) -> Dict[str, bool]:
        """Get feature flags"""
        return {
            'workflow_orchestration': self.get_bool('ENABLE_WORKFLOW_ORCHESTRATION', True),
            'sequential_thinking': self.get_bool('ENABLE_SEQUENTIAL_THINKING', True),
            'graph_memory': self.get_bool('ENABLE_GRAPH_MEMORY', True),
            'visual_creation': self.get_bool('ENABLE_VISUAL_CREATION', True),
            'debug_routes': self.get_bool('ENABLE_DEBUG_ROUTES', False),
            'thought_logging': not self.get_bool('DISABLE_THOUGHT_LOGGING', False)
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.get_bool('FLASK_DEBUG', False)
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.is_development()
    
    def validate_api_key(self, service: str) -> bool:
        """Validate that an API key is available for a service"""
        api_key = self.api_keys.get(service.lower())
        return bool(api_key and api_key != f'your_{service}_api_key_here')
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get configuration without sensitive data (for logging/debugging)"""
        return {
            'server': {
                'host': self.server_config['host'],
                'port': self.server_config['port'],
                'debug': self.server_config['debug']
            },
            'storage_paths': self.storage_paths,
            'feature_flags': self.feature_flags,
            'api_keys_available': {
                service: self.validate_api_key(service) 
                for service in ['openai', 'anthropic', 'huggingface']
            },
            'google_oauth_configured': bool(self.google_oauth['client_id'])
        }

# Global configuration instance
config = EnvironmentConfig()

# Convenience functions
def get_api_key(service: str) -> Optional[str]:
    """Get API key for a service"""
    return config.api_keys.get(service.lower())

def is_api_available(service: str) -> bool:
    """Check if API key is available for a service"""
    return config.validate_api_key(service)

def get_storage_path(path_type: str) -> str:
    """Get storage path for a type"""
    return config.storage_paths.get(path_type, './')

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled"""
    return config.feature_flags.get(feature, False)

# Export main config object
__all__ = ['config', 'EnvironmentConfig', 'get_api_key', 'is_api_available', 'get_storage_path', 'is_feature_enabled']