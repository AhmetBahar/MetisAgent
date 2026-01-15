# Adaptive Settings Cards Blueprint - MetisAgent3

## 📋 Overview

Bu blueprint, Settings ekranı için adaptive cards sistemi tasarlar. Kullanıcılar farklı tipteki ayarları (OAuth2, API Keys, User Mappings, Tool Configurations) dynamic card'lar ile yönetebilecek.

## 🎯 Problem Statement

**Mevcut Durum:**
```
Settings.js:
- Hard-coded tabs (General, API Keys, OAuth, Google Manual)
- Static form fields
- Tool-specific UI components
- Maintenance overhead per new tool/setting
```

**Sorunlar:**
- Her yeni tool için UI kod yazılması gerekiyor
- Settings kategorileri hard-coded
- Action'lar (OAuth2, mapping) ve value editing mixed
- Responsive olmayan static forms

## 🏗️ Solution Architecture

### Adaptive Cards System

**Card Types:**
1. **Action Cards** - OAuth2, tool registration, system actions
2. **Value Cards** - API keys, user preferences, configuration values
3. **Status Cards** - Connection status, health checks, monitoring  
4. **Composite Cards** - Complex multi-step configurations

### Card Schema

```json
{
  "card_id": "google_oauth2_card",
  "type": "action",
  "category": "authentication",
  "title": "Google OAuth2",
  "description": "Secure Google API access",
  "icon": "🔑",
  "status": "not_configured",
  "actions": [
    {
      "id": "authorize",
      "type": "primary",
      "label": "Google ile Yetkilendir",
      "tool_call": {
        "tool_name": "google_tool",
        "capability": "oauth2_management", 
        "action": "authorize"
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
    "tool_name": "google_tool",
    "capability": "oauth2_management",
    "action": "check_status"
  }
}
```

## 🔧 Implementation Plan

### 1. Settings Card Service

**Location:** `core/services/settings_card_service.py`

```python
class SettingsCardService:
    def __init__(self, tool_execution_service):
        self.tool_execution_service = tool_execution_service
        self.card_registry = {}
    
    async def get_user_cards(self, user_id: str) -> List[SettingsCard]:
        """Get all available settings cards for user"""
        
    async def execute_card_action(self, card_id: str, action_id: str, user_id: str, params: dict):
        """Execute card action via tool system"""
        
    async def refresh_card_data(self, card_id: str, user_id: str):
        """Refresh card data from data source"""
```

### 2. Card Registry System

**Dynamic Card Discovery:**
```python
# Cards can be defined by tools themselves
class GoogleTool:
    def get_settings_cards(self) -> List[SettingsCardSchema]:
        return [
            {
                "card_id": "google_oauth2",
                "type": "action",
                "title": "Google OAuth2",
                # ... card definition
            },
            {
                "card_id": "google_user_mapping", 
                "type": "value",
                "title": "Google Account Mapping",
                # ... mapping form
            }
        ]
```

### 3. Frontend Card Components

**React Card Components:**

```javascript
// ActionCard.js - OAuth2, registrations
const ActionCard = ({ card, onAction }) => {
    return (
        <div className={`settings-card action-card ${card.status}`}>
            <CardHeader icon={card.icon} title={card.title} status={card.status} />
            <CardContent description={card.description} />
            <CardActions actions={card.actions} onAction={onAction} />
        </div>
    );
};

// ValueCard.js - API keys, preferences  
const ValueCard = ({ card, onSave }) => {
    return (
        <div className="settings-card value-card">
            <CardHeader title={card.title} />
            <CardForm schema={card.form_schema} onSave={onSave} />
        </div>
    );
};

// StatusCard.js - Health, connections
const StatusCard = ({ card }) => {
    return (
        <div className="settings-card status-card">
            <CardHeader title={card.title} />
            <StatusDisplay status={card.status} metrics={card.metrics} />
        </div>
    );
};
```

### 4. Card Categories & Filtering

```javascript
const SettingsCardGrid = ({ cards, activeCategory }) => {
    const filteredCards = cards.filter(card => 
        activeCategory === 'all' || card.category === activeCategory
    );
    
    const groupedCards = groupBy(filteredCards, 'category');
    
    return (
        <div className="settings-grid">
            {Object.entries(groupedCards).map(([category, categoryCards]) => (
                <CardCategory key={category} title={category} cards={categoryCards} />
            ))}
        </div>
    );
};
```

## 🎨 Card Types & Examples

### Action Cards

**Google OAuth2 Card:**
```json
{
  "card_id": "google_oauth2",
  "type": "action",
  "category": "authentication",
  "title": "Google OAuth2",
  "description": "Gmail, Drive, Calendar erişimi",
  "icon": "🔑",
  "status": "not_configured",
  "actions": [
    {
      "id": "authorize",
      "type": "primary",
      "label": "Yetkilendir",
      "tool_call": {
        "tool_name": "google_tool",
        "capability": "oauth2_management",
        "action": "authorize"
      }
    },
    {
      "id": "revoke",
      "type": "danger", 
      "label": "İptal Et",
      "condition": "status === 'authorized'",
      "tool_call": {
        "tool_name": "google_tool", 
        "capability": "oauth2_management",
        "action": "revoke"
      }
    }
  ]
}
```

**Tool Registry Card:**
```json
{
  "card_id": "register_instagram_tool",
  "type": "action",
  "category": "tools",
  "title": "Instagram Tool",
  "description": "Social media automation",
  "icon": "📱",
  "status": "not_installed",
  "actions": [
    {
      "id": "install",
      "label": "Install Tool",
      "tool_call": {
        "tool_name": "tool_manager",
        "capability": "plugin_management", 
        "action": "install_plugin",
        "parameters": {"plugin_name": "instagram_tool"}
      }
    }
  ]
}
```

### Value Cards

**API Key Management:**
```json
{
  "card_id": "openai_api_key",
  "type": "value",
  "category": "api_keys",
  "title": "OpenAI API Key",
  "description": "ChatGPT ve DALL-E erişimi",
  "icon": "🤖",
  "form_schema": {
    "fields": [
      {
        "name": "api_key",
        "type": "password",
        "label": "API Key",
        "required": true,
        "placeholder": "sk-..."
      }
    ]
  },
  "save_action": {
    "tool_name": "settings_manager",
    "capability": "api_key_management",
    "action": "save_api_key",
    "parameters": {
      "service": "openai"
    }
  }
}
```

**User Preferences:**
```json
{
  "card_id": "user_preferences",
  "type": "value",
  "category": "general",
  "title": "Kullanıcı Tercihleri",
  "form_schema": {
    "fields": [
      {
        "name": "theme",
        "type": "select", 
        "label": "Tema",
        "options": [
          {"value": "light", "label": "Açık"},
          {"value": "dark", "label": "Koyu"}
        ]
      },
      {
        "name": "language",
        "type": "select",
        "label": "Dil",
        "options": [
          {"value": "tr", "label": "Türkçe"},
          {"value": "en", "label": "English"}
        ]
      }
    ]
  }
}
```

### Status Cards

**System Health Card:**
```json
{
  "card_id": "system_health",
  "type": "status", 
  "category": "system",
  "title": "System Health",
  "icon": "⚡",
  "metrics": [
    {
      "name": "Tools Loaded",
      "value": "5",
      "status": "healthy"
    },
    {
      "name": "Active Connections",
      "value": "3", 
      "status": "healthy"
    },
    {
      "name": "Memory Usage",
      "value": "45%",
      "status": "warning"
    }
  ],
  "data_source": {
    "tool_name": "system_monitor",
    "capability": "health_check",
    "action": "get_system_status"
  }
}
```

## 📱 Responsive Design

### Grid Layout
```css
.settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
    padding: 20px;
}

@media (max-width: 768px) {
    .settings-grid {
        grid-template-columns: 1fr;
        padding: 10px;
    }
}
```

### Card Animations
```css
.settings-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.settings-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}
```

## 🔐 Security & Validation

### Card Action Validation
```python
async def validate_card_action(self, card_id: str, action_id: str, user_id: str):
    """Validate user permission for card action"""
    
    # Check user permissions
    if not await self.check_user_permission(user_id, card_id, action_id):
        raise PermissionError(f"User {user_id} not allowed to execute {action_id}")
    
    # Check card/action exists
    card = self.get_card(card_id)
    if not card or not card.has_action(action_id):
        raise ValueError(f"Invalid card action: {card_id}.{action_id}")
    
    return True
```

### Input Sanitization
```python
def sanitize_card_input(self, form_data: dict, schema: dict) -> dict:
    """Sanitize and validate card form input"""
    
    sanitized = {}
    for field in schema.get('fields', []):
        field_name = field['name']
        if field_name in form_data:
            value = form_data[field_name]
            
            # Type validation
            if field['type'] == 'password' and len(value) < 8:
                raise ValueError(f"Password too short for {field_name}")
                
            sanitized[field_name] = value
    
    return sanitized
```

## 🚀 Implementation Phases

### Phase 1: Core Infrastructure
1. SettingsCardService implementation
2. Card schema definitions  
3. Backend card registry
4. Basic card components (Action, Value, Status)

### Phase 2: Tool Integration
1. Google Tool cards migration
2. API Key management cards
3. User preference cards
4. Tool registry cards

### Phase 3: Advanced Features  
1. Conditional actions
2. Card dependencies
3. Bulk operations
4. Card templates

### Phase 4: Enhancement
1. Card analytics
2. User customization
3. Card sharing
4. Advanced validation

## 🧪 Testing Strategy

### Unit Tests
```python
def test_action_card_execution():
    # Test OAuth2 card authorization
    # Test tool registration card
    # Test permission validation

def test_value_card_validation():
    # Test API key format validation
    # Test required field validation
    # Test data sanitization
```

### Integration Tests
```python  
def test_card_tool_integration():
    # Test card actions call correct tools
    # Test data sources refresh correctly
    # Test error handling
```

### UI Tests
```javascript
describe('Settings Cards', () => {
    it('should render action cards correctly', () => {
        // Test card rendering
        // Test action buttons
        // Test status display
    });
    
    it('should handle form submission', () => {
        // Test value card forms
        // Test validation
        // Test save operations
    });
});
```

## 🎯 Success Criteria

- ✅ Dynamic card system supporting all setting types
- ✅ Tool-agnostic card definitions
- ✅ Responsive mobile-friendly design
- ✅ Consistent user experience across card types
- ✅ Easy addition of new tools/settings
- ✅ Proper validation and security
- ✅ Smooth animations and interactions

## 📊 Example Usage Scenarios

### Adding New Tool Settings
```python
# Tool developer just needs to implement get_settings_cards()
class NewTool:
    def get_settings_cards(self):
        return [
            {
                "card_id": "new_tool_config",
                "type": "value", 
                "title": "New Tool Settings",
                # ... card definition
            }
        ]
```

### User Experience
```
User opens Settings → 
  Sees categorized cards → 
    Click "Google OAuth2" action card →
      Redirected to Google → 
        Returns authorized →
          Card status updates to ✅
```

---

**Author:** Claude Code Assistant  
**Date:** 2025-08-18  
**Status:** Draft - Ready for Implementation  
**Priority:** Medium-High  
**Dependencies:** Generic Tool Execution System