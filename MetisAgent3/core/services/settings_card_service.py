#!/usr/bin/env python3
"""
Settings Card Service - Dynamic Settings Management

CLAUDE.md COMPLIANT:
- Adaptive card system for settings management
- Tool-agnostic card definitions  
- Action and value card support
- Consistent user experience
- Enhanced with tool card discovery and dynamic generation
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .tool_execution_service import ToolExecutionService, ToolExecutionRequest
from ..contracts.base_types import ExecutionContext

logger = logging.getLogger(__name__)


class CardType(str, Enum):
    """Settings card types"""
    ACTION = "action"       # OAuth2, registrations, system actions
    VALUE = "value"         # API keys, preferences, configuration
    STATUS = "status"       # Health checks, connection status
    COMPOSITE = "composite" # Complex multi-step configurations


class ActionType(str, Enum):
    """Card action types"""
    PRIMARY = "primary"     # Main action (authorize, save)
    SECONDARY = "secondary" # Secondary action (test, refresh)
    DANGER = "danger"       # Destructive action (delete, revoke)


@dataclass
class CardAction:
    """Card action definition"""
    id: str
    type: ActionType
    label: str
    tool_call: Dict[str, Any]
    condition: Optional[str] = None  # JavaScript-like condition
    confirm_message: Optional[str] = None
    parameters: Dict[str, Any] = None


@dataclass
class FormField:
    """Form field definition for value cards"""
    name: str
    type: str  # text, password, select, checkbox, number
    label: str
    required: bool = False
    placeholder: Optional[str] = None
    options: List[Dict[str, str]] = None  # For select fields
    validation: Dict[str, Any] = None


@dataclass
class StatusMetric:
    """Status metric for status cards"""
    name: str
    value: str
    status: str  # healthy, warning, error
    icon: Optional[str] = None


@dataclass
class SettingsCard:
    """Settings card definition"""
    card_id: str
    type: CardType
    category: str
    title: str
    description: str
    icon: str
    status: str = "unknown"
    
    # Action card fields
    actions: List[CardAction] = None
    status_display: Dict[str, Dict[str, str]] = None
    
    # Value card fields  
    form_schema: Dict[str, Any] = None
    save_action: Dict[str, Any] = None
    current_values: Dict[str, Any] = None
    
    # Status card fields
    metrics: List[StatusMetric] = None
    
    # Data source for refreshing
    data_source: Dict[str, Any] = None
    
    # Metadata
    order: int = 0
    enabled: bool = True
    requires_permission: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class SettingsCardService:
    """Service for managing adaptive settings cards with tool discovery"""
    
    def __init__(self, tool_execution_service: ToolExecutionService):
        self.tool_execution_service = tool_execution_service
        self.card_registry: Dict[str, SettingsCard] = {}
        self.card_discovery_service = None  # Will be set by orchestrator
        self.category_order = {
            "authentication": 1,
            "api_keys": 2, 
            "tools": 3,
            "monitoring": 4,
            "preferences": 5,
            "general": 6,
            "system": 7
        }
        logger.info("🃏 Settings Card Service initialized")
    
    def register_card(self, card: SettingsCard) -> None:
        """Register a settings card"""
        self.card_registry[card.card_id] = card
        logger.info(f"📋 Registered settings card: {card.card_id}")
    
    def register_cards(self, cards: List[SettingsCard]) -> None:
        """Register multiple settings cards"""
        for card in cards:
            self.register_card(card)
    
    def set_card_discovery_service(self, discovery_service) -> None:
        """Set card discovery service (injected by orchestrator)"""
        self.card_discovery_service = discovery_service
        logger.info("🔍 Card discovery service attached")
    
    async def discover_and_register_tool_cards(self, plugins_directory: str, tool_manager=None) -> None:
        """Auto-discover and register cards from all tools"""
        if not self.card_discovery_service:
            logger.warning("Card discovery service not available")
            return
        
        try:
            # Discover cards from all tools
            all_tool_cards = await self.card_discovery_service.discover_all_tool_cards(
                plugins_directory, tool_manager
            )
            
            # Register all discovered cards
            total_cards = 0
            for tool_name, cards in all_tool_cards.items():
                for card in cards:
                    self.register_card(card)
                    total_cards += 1
            
            logger.info(f"🃏 Auto-discovered and registered {total_cards} cards from {len(all_tool_cards)} tools")
            
        except Exception as e:
            logger.error(f"Failed to discover and register tool cards: {e}")
    
    def clear_registry(self) -> None:
        """Clear all registered cards (useful for testing)"""
        self.card_registry.clear()
        logger.info("🗑️ Card registry cleared")
    
    async def get_user_cards(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available settings cards for user
        
        Args:
            user_id: User ID
            category: Optional category filter
            
        Returns:
            List of card dictionaries with refreshed data
        """
        try:
            # Filter cards by category if specified
            cards = list(self.card_registry.values())
            if category and category != 'all':
                cards = [card for card in cards if card.category == category]
            
            # Filter by permissions (future implementation)
            # cards = [card for card in cards if self._check_user_permission(user_id, card)]
            
            # Refresh card data
            refreshed_cards = []
            for card in cards:
                try:
                    refreshed_card = await self._refresh_card_data(card, user_id)
                    refreshed_cards.append(refreshed_card.to_dict())
                except Exception as e:
                    logger.warning(f"Failed to refresh card {card.card_id}: {e}")
                    # Include card with original data
                    refreshed_cards.append(card.to_dict())
            
            # Sort by category and order
            refreshed_cards.sort(key=lambda c: (
                self.category_order.get(c['category'], 999),
                c.get('order', 0)
            ))
            
            return refreshed_cards
            
        except Exception as e:
            logger.error(f"Failed to get user cards: {e}")
            return []
    
    async def execute_card_action(self, 
                                  card_id: str, 
                                  action_id: str, 
                                  user_id: str, 
                                  parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a card action
        
        Args:
            card_id: Card ID
            action_id: Action ID within card
            user_id: User ID
            parameters: Optional action parameters
            
        Returns:
            Action execution result
        """
        try:
            # Get card
            card = self.card_registry.get(card_id)
            if not card:
                return {"success": False, "error": f"Card not found: {card_id}"}
            
            # Find action in metadata
            action = None
            actions_list = card.metadata.get('actions') if card.metadata else None
            if actions_list:
                for a in actions_list:
                    if a.get('id') == action_id:
                        action = a
                        break
            
            if not action:
                return {"success": False, "error": f"Action not found: {action_id}"}
            
            # Prepare tool execution request
            tool_call = action['tool_call'].copy()
            if parameters:
                tool_call_params = tool_call.get('parameters', {})
                tool_call_params.update(parameters)
                tool_call['parameters'] = tool_call_params
            
            # Add action parameters if specified
            action_parameters = action.get('parameters')
            if action_parameters:
                tool_call_params = tool_call.get('parameters', {})
                tool_call_params.update(action_parameters)
                tool_call['parameters'] = tool_call_params
            
            # Get tool_name from tool_call or from card metadata
            tool_name = tool_call.get('tool_name') or card.metadata.get('tool_name')
            if not tool_name:
                return {"success": False, "error": f"No tool_name found for action {action_id} in card {card_id}"}
            
            request = ToolExecutionRequest(
                tool_name=tool_name,
                capability=tool_call['capability'],
                action=tool_call['action'], 
                parameters=tool_call.get('parameters', {}),
                user_id=user_id
            )
            
            # Execute via tool execution service
            result = await self.tool_execution_service.execute_tool_capability(request)
            
            logger.info(f"🎬 Executed card action {card_id}.{action_id}: {result.success}")
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Card action execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_card_values(self, 
                               card_id: str, 
                               values: Dict[str, Any], 
                               user_id: str) -> Dict[str, Any]:
        """
        Save card form values
        
        Args:
            card_id: Card ID
            values: Form values
            user_id: User ID
            
        Returns:
            Save operation result
        """
        try:
            # Get card
            card = self.card_registry.get(card_id)
            save_action = card.metadata.get('save_action') if card and card.metadata else None
            if not card or not save_action:
                return {"success": False, "error": f"Card or save action not found: {card_id}"}
            
            # Validate form values
            if card.form_schema:
                validation_error = self._validate_form_values(values, card.form_schema)
                if validation_error:
                    return {"success": False, "error": validation_error}
            
            # Prepare save request
            save_action_copy = save_action.copy()
            save_params = save_action_copy.get('parameters', {})
            save_params.update(values)
            save_action_copy['parameters'] = save_params
            
            # Get tool_name from save_action or from card metadata
            tool_name = save_action_copy.get('tool_name') or card.metadata.get('tool_name')
            if not tool_name:
                return {"success": False, "error": f"No tool_name found for card {card_id} save action"}
            
            request = ToolExecutionRequest(
                tool_name=tool_name,
                capability=save_action_copy['capability'],
                action=save_action_copy['action'],
                parameters=save_params,
                user_id=user_id
            )
            
            # Execute save
            result = await self.tool_execution_service.execute_tool_capability(request)
            
            logger.info(f"💾 Saved card values {card_id}: {result.success}")
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Card values save failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _refresh_card_data(self, card: SettingsCard, user_id: str) -> SettingsCard:
        """Refresh card data from data source"""
        data_source = card.metadata.get('data_source') if card.metadata else None
        if not data_source:
            return card
        
        try:
            # Execute data source to get current data
            # Get tool_name from data_source or from card metadata
            tool_name = data_source.get('tool_name') or card.metadata.get('tool_name')
            if not tool_name:
                logger.warning(f"No tool_name found for card {card.card_id} data source")
                return card
            
            request = ToolExecutionRequest(
                tool_name=tool_name,
                capability=data_source['capability'],
                action=data_source['action'],
                parameters=data_source.get('parameters', {}),
                user_id=user_id
            )
            
            result = await self.tool_execution_service.execute_tool_capability(request)
            
            if result.success:
                # Update card with fresh data
                updated_card = SettingsCard(**card.to_dict())
                
                # Update status based on result
                if 'authenticated' in result.data:
                    updated_card.status = 'authorized' if result.data['authenticated'] else 'not_authorized'
                elif 'status' in result.data:
                    updated_card.status = result.data['status']
                
                # Update current values for value cards
                if card.type == CardType.VALUE and result.data:
                    # Handle nested mapping data structure
                    if 'mapping' in result.data and result.data['mapping']:
                        updated_card.current_values = result.data['mapping']
                    else:
                        updated_card.current_values = result.data
                
                # Update metrics for status cards
                if card.type == CardType.STATUS and 'metrics' in result.data:
                    updated_card.metrics = [
                        StatusMetric(**metric) for metric in result.data['metrics']
                    ]
                    # Update overall card status based on metrics
                    if 'overall_status' in result.data:
                        updated_card.status = result.data['overall_status']
                
                return updated_card
                
        except Exception as e:
            logger.warning(f"Failed to refresh card data for {card.card_id}: {e}")
        
        return card
    
    def _validate_form_values(self, values: Dict[str, Any], form_schema: Dict[str, Any]) -> Optional[str]:
        """Validate form values against schema"""
        try:
            fields = form_schema.get('fields', [])
            
            for field in fields:
                field_name = field['name']
                
                # Required field validation
                if field.get('required', False) and not values.get(field_name):
                    return f"Field '{field['label']}' is required"
                
                # Type validation
                if field_name in values:
                    value = values[field_name]
                    field_type = field['type']
                    
                    if field_type == 'password' and len(str(value)) < 8:
                        return f"Password must be at least 8 characters"
                    
                    if field_type == 'email' and '@' not in str(value):
                        return f"Invalid email format for '{field['label']}'"
                    
                    # Custom validation
                    if field.get('validation'):
                        validation = field['validation']
                        if 'min_length' in validation and len(str(value)) < validation['min_length']:
                            return f"'{field['label']}' must be at least {validation['min_length']} characters"
                        
                        # Pattern validation (regex)
                        if 'pattern' in validation:
                            import re
                            pattern = validation['pattern']
                            if not re.search(pattern, str(value)):
                                if field_type == 'email':
                                    return f"'{field['label']}' must be a valid Gmail address"
                                else:
                                    return f"'{field['label']}' does not match required format"
            
            return None
            
        except Exception as e:
            return f"Validation error: {str(e)}"
    
    def get_card_categories(self) -> List[Dict[str, Any]]:
        """Get available card categories"""
        categories = set(card.category for card in self.card_registry.values())
        
        return [
            {
                "id": "all",
                "name": "Tümü",
                "icon": "📋",
                "order": 0
            }
        ] + [
            {
                "id": category,
                "name": category.replace('_', ' ').title(),
                "icon": self._get_category_icon(category),
                "order": self.category_order.get(category, 999)
            }
            for category in sorted(categories, key=lambda c: self.category_order.get(c, 999))
        ]
    
    def _get_category_icon(self, category: str) -> str:
        """Get icon for category"""
        icons = {
            "authentication": "🔐",
            "api_keys": "🔑",
            "tools": "🔧",
            "general": "⚙️", 
            "system": "💻"
        }
        return icons.get(category, "📁")


def create_google_oauth2_card() -> SettingsCard:
    """Create Google OAuth2 action card"""
    return SettingsCard(
        card_id="google_oauth2",
        type=CardType.ACTION,
        category="authentication",
        title="Google OAuth2",
        description="Gmail, Drive, Calendar API erişimi",
        icon="🔑",
        status="not_authorized",
        actions=[
            CardAction(
                id="authorize",
                type=ActionType.PRIMARY,
                label="Google ile Yetkilendir",
                tool_call={
                    "tool_name": "google_tool",
                    "capability": "oauth2_management",
                    "action": "authorize"
                }
            ),
            CardAction(
                id="revoke",
                type=ActionType.DANGER,
                label="Yetkilendirmeyi İptal Et",
                tool_call={
                    "tool_name": "google_tool", 
                    "capability": "oauth2_management",
                    "action": "revoke"
                },
                condition="status === 'authorized'",
                confirm_message="Google OAuth2 yetkilendirmesini iptal etmek istediğinize emin misiniz?"
            )
        ],
        status_display={
            "authorized": {
                "icon": "✅",
                "message": "Yetkilendirildi",
                "color": "green"
            },
            "not_authorized": {
                "icon": "❌",
                "message": "Yetkilendirilmedi", 
                "color": "red"
            }
        },
        data_source={
            "tool_name": "google_tool",
            "capability": "oauth2_management",
            "action": "check_status"
        },
        order=1
    )


def create_google_user_mapping_card() -> SettingsCard:
    """Create Google user mapping value card"""
    return SettingsCard(
        card_id="google_user_mapping",
        type=CardType.VALUE,
        category="authentication",
        title="Google Hesap Eşleme",
        description="MetisAgent hesabınızı Google hesabınızla eşleştirin",
        icon="🔗",
        form_schema={
            "fields": [
                FormField(
                    name="google_email",
                    type="email",
                    label="Google Email",
                    required=True,
                    placeholder="user@gmail.com",
                    validation={"pattern": "@gmail\\.com$"}
                ).__dict__,
                FormField(
                    name="google_name",
                    type="text", 
                    label="Google İsim",
                    required=False,
                    placeholder="John Doe"
                ).__dict__
            ]
        },
        save_action={
            "tool_name": "google_tool",
            "capability": "oauth2_management", 
            "action": "set_user_mapping"
        },
        data_source={
            "tool_name": "google_tool",
            "capability": "oauth2_management",
            "action": "get_user_mapping"
        },
        order=2
    )