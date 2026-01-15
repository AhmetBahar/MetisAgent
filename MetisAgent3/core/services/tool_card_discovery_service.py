"""
Tool Card Discovery Service - MetisAgent3

Automatically discovers and loads settings cards from tool directories.
Each tool can define its settings cards in a settings_cards.json file.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .settings_card_service import SettingsCard, CardType, ActionType
from .dynamic_card_generator import DynamicCardGenerator

logger = logging.getLogger(__name__)

@dataclass
class ToolCardDefinition:
    """Tool card definition from JSON"""
    tool_name: str
    version: str
    description: str
    cards: List[Dict[str, Any]]

class ToolCardValidator:
    """Validates tool settings cards schema"""
    
    REQUIRED_CARD_FIELDS = {'card_id', 'type', 'category', 'title', 'description', 'icon'}
    VALID_CARD_TYPES = {'action', 'value', 'status'}
    VALID_CATEGORIES = {'authentication', 'api_keys', 'tools', 'preferences', 'monitoring'}
    
    def validate_card_schema(self, card_data: Dict[str, Any], tool_name: str) -> bool:
        """Validate individual card schema"""
        try:
            # Check required fields
            missing_fields = self.REQUIRED_CARD_FIELDS - card_data.keys()
            if missing_fields:
                logger.error(f"Tool {tool_name} card missing required fields: {missing_fields}")
                return False
            
            # Validate card type
            if card_data['type'] not in self.VALID_CARD_TYPES:
                logger.error(f"Tool {tool_name} invalid card type: {card_data['type']}")
                return False
            
            # Validate category
            if card_data['category'] not in self.VALID_CATEGORIES:
                logger.warning(f"Tool {tool_name} unknown category: {card_data['category']}")
            
            # Type-specific validation
            if card_data['type'] == 'action':
                return self._validate_action_card(card_data, tool_name)
            elif card_data['type'] == 'value':
                return self._validate_value_card(card_data, tool_name)
            elif card_data['type'] == 'status':
                return self._validate_status_card(card_data, tool_name)
                
            return True
            
        except Exception as e:
            logger.error(f"Tool {tool_name} card validation error: {e}")
            return False
    
    def _validate_action_card(self, card_data: Dict[str, Any], tool_name: str) -> bool:
        """Validate action card specific fields"""
        if 'actions' not in card_data or not isinstance(card_data['actions'], list):
            logger.error(f"Tool {tool_name} action card missing actions array")
            return False
        
        for action in card_data['actions']:
            if not isinstance(action, dict) or 'id' not in action or 'tool_call' not in action:
                logger.error(f"Tool {tool_name} invalid action format")
                return False
                
            tool_call = action['tool_call']
            if 'capability' not in tool_call or 'action' not in tool_call:
                logger.error(f"Tool {tool_name} invalid tool_call format")
                return False
        
        return True
    
    def _validate_value_card(self, card_data: Dict[str, Any], tool_name: str) -> bool:
        """Validate value card specific fields"""
        if 'form_schema' not in card_data:
            logger.error(f"Tool {tool_name} value card missing form_schema")
            return False
        
        form_schema = card_data['form_schema']
        if 'fields' not in form_schema or not isinstance(form_schema['fields'], list):
            logger.error(f"Tool {tool_name} value card invalid form_schema")
            return False
        
        return True
    
    def _validate_status_card(self, card_data: Dict[str, Any], tool_name: str) -> bool:
        """Validate status card specific fields"""
        if 'metrics' in card_data:
            if not isinstance(card_data['metrics'], list):
                logger.error(f"Tool {tool_name} status card invalid metrics format")
                return False
        
        return True
    
    def validate_tool_cards_file(self, cards_file_path: str, tool_name: str) -> bool:
        """Validate entire tool cards file"""
        try:
            with open(cards_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required top-level fields
            required_fields = {'version', 'tool_name', 'cards'}
            missing_fields = required_fields - data.keys()
            if missing_fields:
                logger.error(f"Tool {tool_name} cards file missing: {missing_fields}")
                return False
            
            # Validate tool name matches
            if data['tool_name'] != tool_name:
                logger.error(f"Tool name mismatch: expected {tool_name}, got {data['tool_name']}")
                return False
            
            # Validate each card
            for card in data['cards']:
                if not self.validate_card_schema(card, tool_name):
                    return False
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Tool {tool_name} cards file JSON error: {e}")
            return False
        except Exception as e:
            logger.error(f"Tool {tool_name} cards file validation error: {e}")
            return False


class ToolCardDiscoveryService:
    """Discovers and loads settings cards from tool directories"""
    
    def __init__(self):
        self.validator = ToolCardValidator()
        self.card_generator = DynamicCardGenerator()
        self.discovered_cards: Dict[str, List[SettingsCard]] = {}
    
    async def discover_tool_cards(self, tool_path: str, tool_name: str, tool_instance=None, tool_config: Optional[Dict] = None) -> List[SettingsCard]:
        """Discover settings cards from tool directory"""
        try:
            tool_dir = Path(tool_path)
            cards_file = tool_dir / "settings_cards.json"
            
            if not cards_file.exists():
                logger.debug(f"No settings cards file found for tool: {tool_name}")
                # Generate standard cards if tool instance is provided
                if tool_instance:
                    logger.info(f"Generating standard cards for tool: {tool_name}")
                    capability_info = self.card_generator.analyze_tool_capabilities(tool_instance, tool_config)
                    standard_cards = self.card_generator.generate_standard_cards(capability_info)
                    self.discovered_cards[tool_name] = standard_cards
                    return standard_cards
                return []
            
            # Validate file first
            if not self.validator.validate_tool_cards_file(str(cards_file), tool_name):
                logger.warning(f"Invalid settings cards file for tool: {tool_name}")
                # Fallback to standard cards if validation fails and tool instance is provided
                if tool_instance:
                    logger.info(f"Falling back to standard cards for tool: {tool_name}")
                    capability_info = self.card_generator.analyze_tool_capabilities(tool_instance, tool_config)
                    standard_cards = self.card_generator.generate_standard_cards(capability_info)
                    self.discovered_cards[tool_name] = standard_cards
                    return standard_cards
                return []
            
            # Load and parse cards
            with open(cards_file, 'r', encoding='utf-8') as f:
                card_definition_data = json.load(f)
            
            tool_definition = ToolCardDefinition(
                tool_name=card_definition_data['tool_name'],
                version=card_definition_data['version'],
                description=card_definition_data.get('description', ''),
                cards=card_definition_data['cards']
            )
            
            # Convert to SettingsCard objects
            settings_cards = []
            for card_data in tool_definition.cards:
                settings_card = self._create_settings_card_from_json(card_data, tool_name)
                if settings_card:
                    settings_cards.append(settings_card)
            
            self.discovered_cards[tool_name] = settings_cards
            logger.info(f"Discovered {len(settings_cards)} cards for tool: {tool_name}")
            
            return settings_cards
            
        except Exception as e:
            logger.error(f"Failed to discover cards for tool {tool_name}: {e}")
            return []
    
    def _create_settings_card_from_json(self, card_data: Dict[str, Any], tool_name: str) -> Optional[SettingsCard]:
        """Create SettingsCard from JSON data"""
        try:
            # Map string type to CardType enum
            card_type_map = {
                'action': CardType.ACTION,
                'value': CardType.VALUE,
                'status': CardType.STATUS
            }
            
            card_type = card_type_map.get(card_data['type'])
            if not card_type:
                logger.error(f"Invalid card type for tool {tool_name}: {card_data['type']}")
                return None
            
            # Extract actions for action cards
            actions = []
            if card_type == CardType.ACTION and 'actions' in card_data:
                for action_data in card_data['actions']:
                    action_type_map = {
                        'primary': ActionType.PRIMARY,
                        'secondary': ActionType.SECONDARY,
                        'danger': ActionType.DANGER
                    }
                    action_type = action_type_map.get(action_data.get('type', 'primary'), ActionType.PRIMARY)
                    
                    # Add tool_name to tool_call
                    tool_call = action_data['tool_call'].copy()
                    tool_call['tool_name'] = tool_name
                    
                    actions.append({
                        'id': action_data['id'],
                        'type': action_type,
                        'label': action_data['label'],
                        'tool_call': tool_call,
                        'condition': action_data.get('condition'),
                        'confirm_message': action_data.get('confirm_message')
                    })
            
            # Create SettingsCard
            settings_card = SettingsCard(
                card_id=f"{tool_name}_{card_data['card_id']}",  # Prefix with tool name for uniqueness
                title=card_data['title'],
                description=card_data['description'],
                type=card_type,
                category=card_data['category'],
                icon=card_data['icon'],
                order=card_data.get('order', 999),
                metadata={
                    'tool_name': tool_name,
                    'original_card_id': card_data['card_id'],
                    'data_source': self._add_tool_name_to_action(card_data.get('data_source'), tool_name),
                    'form_schema': card_data.get('form_schema'),
                    'save_action': self._add_tool_name_to_action(card_data.get('save_action'), tool_name),
                    'metrics': card_data.get('metrics'),
                    'status_display': card_data.get('status_display'),
                    'actions': actions if actions else None
                }
            )
            
            return settings_card
            
        except Exception as e:
            logger.error(f"Failed to create settings card from JSON for tool {tool_name}: {e}")
            return None
    
    def _add_tool_name_to_action(self, action_dict: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """Add tool_name to action/data_source dict"""
        if not action_dict:
            return action_dict
        
        action_copy = action_dict.copy()
        action_copy['tool_name'] = tool_name
        return action_copy
    
    def get_discovered_cards(self, tool_name: Optional[str] = None) -> Dict[str, List[SettingsCard]]:
        """Get discovered cards, optionally filtered by tool name"""
        if tool_name:
            return {tool_name: self.discovered_cards.get(tool_name, [])}
        return self.discovered_cards.copy()
    
    async def discover_all_tool_cards(self, plugins_directory: str, tool_manager=None) -> Dict[str, List[SettingsCard]]:
        """Discover cards from all tools in plugins directory"""
        plugins_path = Path(plugins_directory)
        if not plugins_path.exists():
            logger.warning(f"Plugins directory not found: {plugins_directory}")
            return {}
        
        all_discovered_cards = {}
        
        # Scan for tool directories
        for tool_dir in plugins_path.iterdir():
            if tool_dir.is_dir() and not tool_dir.name.startswith('.'):
                tool_name = tool_dir.name
                
                # Get tool instance and config if tool_manager is provided
                tool_instance = None
                tool_config = None
                if tool_manager and hasattr(tool_manager, 'tools'):
                    tool_instance = tool_manager.tools.get(tool_name)
                    if hasattr(tool_manager, 'get_tool_config'):
                        tool_config = tool_manager.get_tool_config(tool_name)
                
                cards = await self.discover_tool_cards(str(tool_dir), tool_name, tool_instance, tool_config)
                if cards:
                    all_discovered_cards[tool_name] = cards
        
        logger.info(f"Discovered cards from {len(all_discovered_cards)} tools")
        return all_discovered_cards
    
    def get_card_template_for_tool(self, tool_name: str) -> Dict[str, Any]:
        """Generate a template settings cards file for new tools"""
        return {
            "version": "1.0",
            "tool_name": tool_name,
            "description": f"{tool_name} settings and configuration",
            "cards": [
                {
                    "card_id": f"{tool_name}_config",
                    "type": "value",
                    "category": "tools",
                    "title": f"{tool_name.title()} Configuration",
                    "description": f"Configure {tool_name} settings",
                    "icon": "⚙️",
                    "order": 1,
                    "form_schema": {
                        "fields": [
                            {
                                "name": "enabled",
                                "type": "checkbox",
                                "label": "Tool Enabled",
                                "required": False,
                                "default": True
                            }
                        ]
                    },
                    "save_action": {
                        "capability": "tool_management",
                        "action": "update_config"
                    },
                    "data_source": {
                        "capability": "tool_management",
                        "action": "get_config"
                    }
                }
            ]
        }