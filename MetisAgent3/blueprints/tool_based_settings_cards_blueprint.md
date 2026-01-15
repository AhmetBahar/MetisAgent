# Tool-Based Settings Cards Blueprint - MetisAgent3

## 📋 Overview

Bu blueprint, her tool'ın kendi settings card'larını tanımladığı ve yönettiği bir sistem tasarlar. Tool'lar `settings_cards.json` dosyasında kendi card'larını define eder.

## 🎯 Problem Statement

**Current Approach:**
```python
# Central registration in bridge_server.py
settings_card_service.register_card(create_google_oauth2_card())
settings_card_service.register_card(create_google_user_mapping_card())
```

**Issues:**
- Tool'ların card tanımları merkezi bir yerde hard-coded
- Yeni tool eklediğinde bridge server değişmeli
- Tool'lar kendi UI'larını yönetemez
- Card definitions tool'dan ayrı

## 🏗️ Solution Architecture

### Tool-Based Card Storage

**File Structure:**
```
plugins/google_tool/
├── google_tool.py
├── google_tool_legacy.py
├── tool_config.json
└── settings_cards.json     # ← New card definitions
```

**Settings Cards JSON Schema:**
```json
{
  "version": "1.0",
  "tool_name": "google_tool",
  "cards": [
    {
      "card_id": "google_oauth2",
      "type": "action",
      "category": "authentication",
      "title": "Google OAuth2",
      "description": "Gmail, Drive, Calendar API erişimi",
      "icon": "🔑",
      "order": 1,
      "actions": [
        {
          "id": "authorize",
          "type": "primary",
          "label": "Google ile Yetkilendir",
          "tool_call": {
            "capability": "oauth2_management",
            "action": "authorize"
          }
        }
      ],
      "data_source": {
        "capability": "oauth2_management",
        "action": "check_status"
      }
    }
  ]
}
```

### Dynamic Card Discovery

**Card Discovery Service:**
```python
class ToolCardDiscoveryService:
    async def discover_tool_cards(self, tool_path: str) -> List[SettingsCard]:
        """Discover settings cards from tool directory"""
        
        cards_file = Path(tool_path) / "settings_cards.json"
        if not cards_file.exists():
            return []
        
        with open(cards_file, 'r') as f:
            card_data = json.load(f)
        
        return [self._create_card_from_json(card) for card in card_data['cards']]
```

## 🔧 Implementation Plan

### 1. Tool Card Schema Validator

**Location:** `core/services/tool_card_validator.py`

```python
class ToolCardValidator:
    def validate_card_schema(self, card_data: dict) -> bool:
        """Validate card schema against specification"""
        
    def validate_tool_calls(self, card_data: dict, tool_name: str) -> bool:
        """Validate that tool calls reference valid capabilities"""
```

### 2. Enhanced Settings Card Service

**Auto-Discovery Integration:**
```python
class SettingsCardService:
    async def discover_and_register_tool_cards(self):
        """Auto-discover cards from all loaded tools"""
        
        for tool_name, tool_instance in self.tool_manager.tools.items():
            try:
                # Get tool directory
                tool_path = self._get_tool_path(tool_instance)
                
                # Discover cards
                cards = await self.card_discovery.discover_tool_cards(tool_path)
                
                # Register discovered cards
                for card in cards:
                    self.register_card(card)
                    
            except Exception as e:
                logger.warning(f"Failed to load cards for {tool_name}: {e}")
```

### 3. Google Tool Settings Cards

**File:** `plugins/google_tool/settings_cards.json`

```json
{
  "version": "1.0",
  "tool_name": "google_tool",
  "description": "Google Workspace integration settings",
  "cards": [
    {
      "card_id": "google_oauth2",
      "type": "action",
      "category": "authentication", 
      "title": "Google OAuth2",
      "description": "Gmail, Drive, Calendar API erişimi için OAuth2 yetkilendirmesi",
      "icon": "🔑",
      "order": 1,
      "status": "not_authorized",
      "actions": [
        {
          "id": "authorize",
          "type": "primary",
          "label": "Google ile Yetkilendir",
          "tool_call": {
            "capability": "oauth2_management",
            "action": "authorize"
          }
        },
        {
          "id": "revoke",
          "type": "danger",
          "label": "Yetkilendirmeyi İptal Et",
          "condition": "status === 'authorized'",
          "confirm_message": "Google OAuth2 yetkilendirmesini iptal etmek istediğinize emin misiniz?",
          "tool_call": {
            "capability": "oauth2_management",
            "action": "revoke"
          }
        }
      ],
      "status_display": {
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
      "data_source": {
        "capability": "oauth2_management",
        "action": "check_status"
      }
    },
    {
      "card_id": "google_user_mapping",
      "type": "value",
      "category": "authentication",
      "title": "Google Hesap Eşleme",
      "description": "MetisAgent hesabınızı Google hesabınızla eşleştirin",
      "icon": "🔗",
      "order": 2,
      "form_schema": {
        "fields": [
          {
            "name": "google_email",
            "type": "email",
            "label": "Google Email",
            "required": true,
            "placeholder": "user@gmail.com",
            "validation": {
              "pattern": "@gmail\\.com$"
            }
          },
          {
            "name": "google_name",
            "type": "text",
            "label": "Google İsim",
            "required": false,
            "placeholder": "John Doe"
          }
        ]
      },
      "save_action": {
        "capability": "oauth2_management",
        "action": "set_user_mapping"
      },
      "data_source": {
        "capability": "oauth2_management",
        "action": "get_user_mapping"
      }
    }
  ]
}
```

### 4. Tool Template Generator

**Location:** `tools/create_tool_cards.py`

```python
def create_tool_cards_template(tool_name: str) -> dict:
    """Generate settings cards template for new tools"""
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
                "form_schema": {
                    "fields": [
                        {
                            "name": "enabled",
                            "type": "checkbox",
                            "label": "Tool Enabled",
                            "required": false
                        }
                    ]
                },
                "save_action": {
                    "capability": "tool_management",
                    "action": "update_config"
                }
            }
        ]
    }
```

## 🔧 Enhanced Tool Integration

### Tool Interface Extension

```python
class BaseTool:
    def get_settings_cards_path(self) -> Optional[str]:
        """Return path to settings cards JSON file"""
        tool_dir = Path(self.__class__.__module__).parent
        cards_file = tool_dir / "settings_cards.json"
        return str(cards_file) if cards_file.exists() else None
    
    def validate_settings_cards(self) -> bool:
        """Validate tool's settings cards schema"""
        cards_path = self.get_settings_cards_path()
        if not cards_path:
            return True  # No cards to validate
            
        validator = ToolCardValidator()
        return validator.validate_cards_file(cards_path, self.get_name())
```

### Discovery Integration

```python
# In application_orchestrator.py
async def _discover_and_load_tools(self):
    """Discover tools and their settings cards"""
    
    # Existing tool discovery...
    
    # Discover and register settings cards
    await self.settings_card_service.discover_and_register_tool_cards()
```

## 📋 Card Types Examples

### API Key Management Card

**File:** `plugins/openai_tool/settings_cards.json`

```json
{
  "version": "1.0",
  "tool_name": "openai_tool",
  "cards": [
    {
      "card_id": "openai_api_key",
      "type": "value",
      "category": "api_keys",
      "title": "OpenAI API Key",
      "description": "ChatGPT ve DALL-E erişimi için API key",
      "icon": "🤖",
      "order": 1,
      "form_schema": {
        "fields": [
          {
            "name": "api_key",
            "type": "password",
            "label": "API Key",
            "required": true,
            "placeholder": "sk-...",
            "validation": {
              "min_length": 20,
              "pattern": "^sk-"
            }
          },
          {
            "name": "model",
            "type": "select",
            "label": "Default Model",
            "required": false,
            "options": [
              {"value": "gpt-4", "label": "GPT-4"},
              {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"}
            ]
          }
        ]
      },
      "save_action": {
        "capability": "configuration",
        "action": "save_api_key"
      }
    }
  ]
}
```

### Tool Registry Card

**File:** `plugins/instagram_tool/settings_cards.json`

```json
{
  "version": "1.0", 
  "tool_name": "instagram_tool",
  "cards": [
    {
      "card_id": "instagram_tool_registry",
      "type": "action",
      "category": "tools",
      "title": "Instagram Tool",
      "description": "Social media automation and posting",
      "icon": "📱",
      "status": "not_installed",
      "actions": [
        {
          "id": "install",
          "type": "primary",
          "label": "Tool'ı Yükle",
          "condition": "status === 'not_installed'",
          "tool_call": {
            "capability": "plugin_management",
            "action": "install"
          }
        },
        {
          "id": "uninstall", 
          "type": "danger",
          "label": "Tool'ı Kaldır",
          "condition": "status === 'installed'",
          "confirm_message": "Instagram Tool'ı kaldırmak istediğinize emin misiniz?",
          "tool_call": {
            "capability": "plugin_management",
            "action": "uninstall"
          }
        }
      ],
      "data_source": {
        "capability": "plugin_management", 
        "action": "check_status"
      }
    }
  ]
}
```

## 🔄 Migration Strategy

### Phase 1: Infrastructure
1. Create ToolCardDiscoveryService
2. Enhance SettingsCardService with discovery
3. Add card schema validator

### Phase 2: Google Tool Migration
1. Create `plugins/google_tool/settings_cards.json`
2. Remove hard-coded card creation from bridge server
3. Test discovery and registration

### Phase 3: System Integration  
1. Integrate discovery with orchestrator
2. Add tool template generator
3. Create documentation for tool developers

### Phase 4: Enhancement
1. Hot-reload for card changes
2. Card version management
3. Multi-language card support

## 🧪 Testing Strategy

### Unit Tests
```python
def test_card_discovery():
    # Test JSON file discovery
    # Test card validation
    # Test malformed card handling

def test_card_registration():
    # Test automatic registration
    # Test duplicate card handling
    # Test tool isolation
```

### Integration Tests
```python
def test_end_to_end_card_flow():
    # Tool loads → Cards discovered → UI renders → Actions work
```

## 🎯 Benefits

### For Tool Developers
- ✅ Self-contained card definitions
- ✅ No central registration needed
- ✅ Easy to version and maintain
- ✅ Template generator for quick start

### For System
- ✅ Automatic card discovery
- ✅ Tool isolation
- ✅ Hot-reload capabilities
- ✅ Consistent validation

### For Users
- ✅ Unified settings experience
- ✅ Tool-specific configurations
- ✅ Dynamic UI updates
- ✅ Consistent interactions

---

**Author:** Claude Code Assistant  
**Date:** 2025-08-18  
**Status:** Ready for Implementation  
**Priority:** High  
**Dependencies:** Adaptive Settings Cards System