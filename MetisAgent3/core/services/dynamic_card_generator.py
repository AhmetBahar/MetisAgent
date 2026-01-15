"""
Dynamic Card Generator - MetisAgent3

Automatically generates standard settings cards for tools based on their capabilities and configurations.
Provides fallback cards when tools don't define their own settings_cards.json.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .settings_card_service import SettingsCard, CardType, ActionType

logger = logging.getLogger(__name__)

@dataclass
class ToolCapabilityInfo:
    """Tool capability analysis result"""
    tool_name: str
    has_auth: bool = False
    has_api_keys: bool = False
    has_oauth2: bool = False
    has_config: bool = False
    has_health_check: bool = False
    capabilities: List[str] = None
    config_fields: Dict[str, Any] = None

class DynamicCardGenerator:
    """Generates standard settings cards based on tool capabilities"""
    
    def __init__(self):
        self.capability_patterns = {
            'oauth2': ['oauth', 'authorize', 'token', 'google', 'microsoft'],
            'api_key': ['api_key', 'secret', 'key', 'token'],
            'auth': ['auth', 'login', 'credential', 'password'],
            'config': ['config', 'setting', 'preference'],
            'health': ['health', 'status', 'ping', 'check', 'monitor']
        }
    
    def analyze_tool_capabilities(self, tool_instance, tool_config: Optional[Dict] = None) -> ToolCapabilityInfo:
        """Analyze tool to determine its capabilities and requirements"""
        try:
            tool_name = getattr(tool_instance, 'name', tool_instance.__class__.__name__.lower())
            
            # Get tool methods and attributes
            tool_methods = [method for method in dir(tool_instance) if not method.startswith('_')]
            tool_docstring = getattr(tool_instance, '__doc__', '') or ''
            
            capability_info = ToolCapabilityInfo(
                tool_name=tool_name,
                capabilities=tool_methods
            )
            
            # Analyze for OAuth2 capability
            oauth2_indicators = any(
                any(pattern in method.lower() for pattern in self.capability_patterns['oauth2'])
                for method in tool_methods
            )
            capability_info.has_oauth2 = oauth2_indicators or 'oauth' in tool_docstring.lower()
            
            # Analyze for API key requirements
            api_key_indicators = any(
                any(pattern in method.lower() for pattern in self.capability_patterns['api_key'])
                for method in tool_methods
            )
            capability_info.has_api_keys = api_key_indicators or 'api' in tool_docstring.lower()
            
            # Analyze for general auth
            auth_indicators = any(
                any(pattern in method.lower() for pattern in self.capability_patterns['auth'])
                for method in tool_methods
            )
            capability_info.has_auth = auth_indicators or capability_info.has_oauth2
            
            # Analyze for configuration
            config_indicators = any(
                any(pattern in method.lower() for pattern in self.capability_patterns['config'])
                for method in tool_methods
            )
            capability_info.has_config = config_indicators or tool_config is not None
            
            # Analyze for health check
            health_indicators = any(
                any(pattern in method.lower() for pattern in self.capability_patterns['health'])
                for method in tool_methods
            )
            capability_info.has_health_check = health_indicators
            
            # Extract config fields from tool_config if available
            if tool_config:
                capability_info.config_fields = self._extract_config_fields(tool_config)
            
            logger.debug(f"Tool {tool_name} capability analysis: {capability_info}")
            return capability_info
            
        except Exception as e:
            logger.error(f"Failed to analyze tool capabilities: {e}")
            return ToolCapabilityInfo(tool_name=tool_name or "unknown")
    
    def _extract_config_fields(self, tool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration fields from tool config"""
        config_fields = {}
        
        # Common config patterns
        field_patterns = {
            'api_key': {'type': 'password', 'label': 'API Key', 'required': True},
            'api_secret': {'type': 'password', 'label': 'API Secret', 'required': True},
            'base_url': {'type': 'url', 'label': 'Base URL', 'required': False},
            'timeout': {'type': 'number', 'label': 'Timeout (seconds)', 'required': False},
            'enabled': {'type': 'checkbox', 'label': 'Tool Enabled', 'required': False},
            'debug': {'type': 'checkbox', 'label': 'Debug Mode', 'required': False}
        }
        
        for key, value in tool_config.items():
            if key in field_patterns:
                config_fields[key] = field_patterns[key]
            else:
                # Infer field type from value
                if isinstance(value, bool):
                    config_fields[key] = {'type': 'checkbox', 'label': key.title(), 'required': False}
                elif isinstance(value, (int, float)):
                    config_fields[key] = {'type': 'number', 'label': key.title(), 'required': False}
                elif 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
                    config_fields[key] = {'type': 'password', 'label': key.title(), 'required': True}
                elif 'url' in key.lower():
                    config_fields[key] = {'type': 'url', 'label': key.title(), 'required': False}
                else:
                    config_fields[key] = {'type': 'text', 'label': key.title(), 'required': False}
        
        return config_fields
    
    def generate_standard_cards(self, capability_info: ToolCapabilityInfo) -> List[SettingsCard]:
        """Generate standard settings cards based on tool capabilities"""
        cards = []
        
        try:
            tool_name = capability_info.tool_name
            
            # 1. OAuth2/Authentication Card
            if capability_info.has_oauth2:
                oauth2_card = self._create_oauth2_card(tool_name)
                if oauth2_card:
                    cards.append(oauth2_card)
            
            # 2. API Key Configuration Card
            elif capability_info.has_api_keys:
                api_key_card = self._create_api_key_card(tool_name, capability_info.config_fields)
                if api_key_card:
                    cards.append(api_key_card)
            
            # 3. General Configuration Card
            if capability_info.has_config:
                config_card = self._create_config_card(tool_name, capability_info.config_fields)
                if config_card:
                    cards.append(config_card)
            
            # 4. Tool Status/Health Card
            if capability_info.has_health_check:
                status_card = self._create_status_card(tool_name)
                if status_card:
                    cards.append(status_card)
            
            # 5. Tool Management Card (always included)
            management_card = self._create_tool_management_card(tool_name)
            if management_card:
                cards.append(management_card)
            
            logger.info(f"Generated {len(cards)} standard cards for tool: {tool_name}")
            return cards
            
        except Exception as e:
            logger.error(f"Failed to generate standard cards for {capability_info.tool_name}: {e}")
            return []
    
    def _create_oauth2_card(self, tool_name: str) -> Optional[SettingsCard]:
        """Create standard OAuth2 authentication card"""
        try:
            return SettingsCard(
                card_id=f"{tool_name}_oauth2",
                title=f"{tool_name.title()} OAuth2",
                description=f"{tool_name} için OAuth2 yetkilendirmesi",
                card_type=CardType.ACTION,
                category="authentication",
                icon="🔑",
                order=1,
                metadata={
                    'tool_name': tool_name,
                    'generated': True,
                    'actions': [
                        {
                            'id': 'authorize',
                            'type': ActionType.PRIMARY,
                            'label': 'Yetkilendir',
                            'tool_call': {
                                'capability': 'oauth2_management',
                                'action': 'authorize'
                            }
                        },
                        {
                            'id': 'revoke',
                            'type': ActionType.DANGER,
                            'label': 'Yetkilendirmeyi İptal Et',
                            'condition': 'status === "authorized"',
                            'confirm_message': f'{tool_name} yetkilendirmesini iptal etmek istediğinize emin misiniz?',
                            'tool_call': {
                                'capability': 'oauth2_management',
                                'action': 'revoke'
                            }
                        }
                    ],
                    'status_display': {
                        'authorized': {'icon': '✅', 'message': 'Yetkilendirildi', 'color': 'green'},
                        'not_authorized': {'icon': '❌', 'message': 'Yetkilendirilmedi', 'color': 'red'}
                    },
                    'data_source': {
                        'capability': 'oauth2_management',
                        'action': 'check_status'
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to create OAuth2 card for {tool_name}: {e}")
            return None
    
    def _create_api_key_card(self, tool_name: str, config_fields: Optional[Dict] = None) -> Optional[SettingsCard]:
        """Create standard API key configuration card"""
        try:
            # Default fields
            fields = [
                {
                    'name': 'api_key',
                    'type': 'password',
                    'label': 'API Key',
                    'required': True,
                    'placeholder': 'API key girin...'
                }
            ]
            
            # Add additional fields from config
            if config_fields:
                for field_name, field_config in config_fields.items():
                    if 'key' in field_name.lower():
                        fields.append({
                            'name': field_name,
                            'type': field_config.get('type', 'text'),
                            'label': field_config.get('label', field_name.title()),
                            'required': field_config.get('required', False),
                            'placeholder': f"{field_config.get('label', field_name)} girin..."
                        })
            
            return SettingsCard(
                card_id=f"{tool_name}_api_key",
                title=f"{tool_name.title()} API Key",
                description=f"{tool_name} için API key yapılandırması",
                card_type=CardType.VALUE,
                category="api_keys",
                icon="🔐",
                order=2,
                metadata={
                    'tool_name': tool_name,
                    'generated': True,
                    'form_schema': {'fields': fields},
                    'save_action': {
                        'capability': 'configuration',
                        'action': 'save_api_key'
                    },
                    'data_source': {
                        'capability': 'configuration',
                        'action': 'get_api_key'
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to create API key card for {tool_name}: {e}")
            return None
    
    def _create_config_card(self, tool_name: str, config_fields: Optional[Dict] = None) -> Optional[SettingsCard]:
        """Create standard configuration card"""
        try:
            fields = []
            
            if config_fields:
                for field_name, field_config in config_fields.items():
                    fields.append({
                        'name': field_name,
                        'type': field_config.get('type', 'text'),
                        'label': field_config.get('label', field_name.title()),
                        'required': field_config.get('required', False),
                        'placeholder': f"{field_config.get('label', field_name)} girin..."
                    })
            else:
                # Default config fields
                fields = [
                    {
                        'name': 'enabled',
                        'type': 'checkbox',
                        'label': 'Tool Aktif',
                        'required': False,
                        'default': True
                    },
                    {
                        'name': 'timeout',
                        'type': 'number',
                        'label': 'Timeout (saniye)',
                        'required': False,
                        'placeholder': '30',
                        'min': 1,
                        'max': 300
                    }
                ]
            
            return SettingsCard(
                card_id=f"{tool_name}_config",
                title=f"{tool_name.title()} Yapılandırma",
                description=f"{tool_name} ayarları ve yapılandırması",
                card_type=CardType.VALUE,
                category="tools",
                icon="⚙️",
                order=3,
                metadata={
                    'tool_name': tool_name,
                    'generated': True,
                    'form_schema': {'fields': fields},
                    'save_action': {
                        'capability': 'configuration',
                        'action': 'update_config'
                    },
                    'data_source': {
                        'capability': 'configuration',
                        'action': 'get_config'
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to create config card for {tool_name}: {e}")
            return None
    
    def _create_status_card(self, tool_name: str) -> Optional[SettingsCard]:
        """Create standard status/health card"""
        try:
            return SettingsCard(
                card_id=f"{tool_name}_status",
                title=f"{tool_name.title()} Durum",
                description=f"{tool_name} sağlık durumu ve bağlantı bilgileri",
                card_type=CardType.STATUS,
                category="monitoring",
                icon="📊",
                order=4,
                metadata={
                    'tool_name': tool_name,
                    'generated': True,
                    'metrics': [
                        {
                            'name': 'Bağlantı Durumu',
                            'value': 'Kontrol Ediliyor...',
                            'status': 'unknown',
                            'icon': '🔗'
                        },
                        {
                            'name': 'Son Kullanım',
                            'value': 'Bilinmiyor',
                            'status': 'unknown',
                            'icon': '⏰'
                        },
                        {
                            'name': 'Yapılandırma',
                            'value': 'Kontrol Ediliyor...',
                            'status': 'unknown',
                            'icon': '⚙️'
                        }
                    ],
                    'data_source': {
                        'capability': 'tool_health',
                        'action': 'get_health_status'
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to create status card for {tool_name}: {e}")
            return None
    
    def _create_tool_management_card(self, tool_name: str) -> Optional[SettingsCard]:
        """Create standard tool management card"""
        try:
            return SettingsCard(
                card_id=f"{tool_name}_management",
                title=f"{tool_name.title()} Yönetim",
                description=f"{tool_name} tool yükleme ve kaldırma işlemleri",
                card_type=CardType.ACTION,
                category="tools",
                icon="🔧",
                order=5,
                metadata={
                    'tool_name': tool_name,
                    'generated': True,
                    'actions': [
                        {
                            'id': 'reload',
                            'type': ActionType.SECONDARY,
                            'label': 'Tool\'ı Yeniden Yükle',
                            'tool_call': {
                                'capability': 'plugin_management',
                                'action': 'reload'
                            }
                        },
                        {
                            'id': 'disable',
                            'type': ActionType.SECONDARY,
                            'label': 'Tool\'ı Devre Dışı Bırak',
                            'condition': 'status === "enabled"',
                            'tool_call': {
                                'capability': 'plugin_management',
                                'action': 'disable'
                            }
                        },
                        {
                            'id': 'enable',
                            'type': ActionType.PRIMARY,
                            'label': 'Tool\'ı Etkinleştir',
                            'condition': 'status === "disabled"',
                            'tool_call': {
                                'capability': 'plugin_management',
                                'action': 'enable'
                            }
                        },
                        {
                            'id': 'uninstall',
                            'type': ActionType.DANGER,
                            'label': 'Tool\'ı Kaldır',
                            'confirm_message': f'{tool_name} tool\'ını kalıcı olarak kaldırmak istediğinize emin misiniz?',
                            'tool_call': {
                                'capability': 'plugin_management',
                                'action': 'uninstall'
                            }
                        }
                    ],
                    'data_source': {
                        'capability': 'plugin_management',
                        'action': 'get_tool_status'
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to create management card for {tool_name}: {e}")
            return None