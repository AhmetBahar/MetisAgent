# Tool Settings Cards Development Guide

## 📋 Overview

MetisAgent3'te her tool kendi settings card'larını tanımlayabilir. Bu sistem sayesinde:

- ✅ **Otomatik UI Oluşturma**: Tool'lar kendi settings interface'ini JSON ile tanımlar
- ✅ **Tutarlı UX**: Tüm tool'lar aynı card-based interface'i kullanır  
- ✅ **Dynamic Generation**: Card tanımı yoksa sistem otomatik standard card'lar oluşturur
- ✅ **Tool Isolation**: Her tool kendi card'larını bağımsız yönetir

## 🏗️ Settings Card Anatomy

### 1. Tool Directory Structure

```
plugins/your_tool/
├── your_tool.py
├── tool_config.json
└── settings_cards.json  # ← Settings cards definition
```

### 2. Settings Cards JSON Schema

```json
{
  "version": "1.0",
  "tool_name": "your_tool",
  "description": "Tool description for settings",
  "cards": [
    {
      "card_id": "unique_card_id",
      "type": "action|value|status",
      "category": "authentication|api_keys|tools|monitoring|preferences",
      "title": "Card Title",
      "description": "Card description", 
      "icon": "🔧",
      "order": 1,
      // Type-specific fields...
    }
  ]
}
```

## 🎯 Card Types

### 1. Action Cards

**Use Case**: OAuth2, tool installation, system actions

```json
{
  "card_id": "your_tool_oauth",
  "type": "action", 
  "category": "authentication",
  "title": "Your Tool OAuth",
  "description": "Authenticate with Your Tool API",
  "icon": "🔑",
  "order": 1,
  "status": "not_authorized",
  "actions": [
    {
      "id": "authorize",
      "type": "primary",
      "label": "Authorize",
      "tool_call": {
        "capability": "oauth2_management",
        "action": "authorize"
      }
    },
    {
      "id": "revoke", 
      "type": "danger",
      "label": "Revoke Access",
      "condition": "status === 'authorized'",
      "confirm_message": "Are you sure you want to revoke access?",
      "tool_call": {
        "capability": "oauth2_management", 
        "action": "revoke"
      }
    }
  ],
  "status_display": {
    "authorized": {
      "icon": "✅",
      "message": "Authorized",
      "color": "green"
    },
    "not_authorized": {
      "icon": "❌", 
      "message": "Not Authorized",
      "color": "red"
    }
  },
  "data_source": {
    "capability": "oauth2_management",
    "action": "check_status"
  }
}
```

### 2. Value Cards

**Use Case**: API keys, configuration values, preferences

```json
{
  "card_id": "your_tool_config",
  "type": "value",
  "category": "api_keys", 
  "title": "Your Tool Configuration",
  "description": "Configure API key and settings",
  "icon": "🔐",
  "order": 2,
  "form_schema": {
    "fields": [
      {
        "name": "api_key",
        "type": "password",
        "label": "API Key",
        "required": true,
        "placeholder": "Enter your API key...",
        "validation": {
          "min_length": 20,
          "pattern": "^sk-"
        }
      },
      {
        "name": "base_url",
        "type": "url", 
        "label": "Base URL",
        "required": false,
        "placeholder": "https://api.example.com"
      },
      {
        "name": "timeout",
        "type": "number",
        "label": "Timeout (seconds)",
        "required": false,
        "min": 1,
        "max": 300,
        "default": 30
      },
      {
        "name": "enabled",
        "type": "checkbox",
        "label": "Tool Enabled", 
        "required": false,
        "default": true
      }
    ]
  },
  "save_action": {
    "capability": "configuration",
    "action": "save_config"
  },
  "data_source": {
    "capability": "configuration",
    "action": "get_config"
  }
}
```

### 3. Status Cards

**Use Case**: Health checks, connection status, monitoring

```json
{
  "card_id": "your_tool_status",
  "type": "status",
  "category": "monitoring",
  "title": "Your Tool Status", 
  "description": "Health and connection status",
  "icon": "📊",
  "order": 3,
  "metrics": [
    {
      "name": "API Connection",
      "value": "Connected", 
      "status": "healthy",
      "icon": "🔗"
    },
    {
      "name": "Last Request",
      "value": "2 minutes ago",
      "status": "healthy", 
      "icon": "⏰"
    },
    {
      "name": "Rate Limit",
      "value": "85%",
      "status": "warning",
      "icon": "⚡"
    }
  ],
  "data_source": {
    "capability": "tool_health",
    "action": "get_health_status"
  }
}
```

## 🔧 Tool Capability Integration

### Required Tool Methods

Your tool must implement the capabilities referenced in cards:

```python
class YourTool:
    
    async def oauth2_management_authorize(self, context, **params):
        """Handle OAuth2 authorization"""
        # Implementation...
        return {"success": True, "redirect_url": "..."}
    
    async def oauth2_management_check_status(self, context, **params):
        """Check OAuth2 status"""
        # Implementation...
        return {"authenticated": True, "user_email": "..."}
    
    async def configuration_save_config(self, context, **params):
        """Save configuration"""
        # Implementation...
        return {"success": True}
    
    async def configuration_get_config(self, context, **params):
        """Get current configuration"""
        # Implementation...
        return {"api_key": "sk-...", "enabled": True}
    
    async def tool_health_get_health_status(self, context, **params):
        """Get tool health status"""
        # Implementation...
        return {
            "metrics": [
                {"name": "API Connection", "value": "Connected", "status": "healthy", "icon": "🔗"}
            ]
        }
```

## 🤖 Automatic Card Generation

Tool tanımlanmış card'ları yoksa, sistem otomatik standard card'lar oluşturur:

### Analysis Criteria

System tool'ınızı analiz ederek şunları belirler:

- **OAuth2 Capability**: `oauth`, `authorize`, `token` methodları varsa
- **API Key Requirement**: `api_key`, `secret`, `key` methodları varsa  
- **Configuration**: `config`, `setting`, `preference` methodları varsa
- **Health Check**: `health`, `status`, `ping`, `check` methodları varsa

### Generated Cards

1. **OAuth2 Card**: OAuth2 capability tespit edilirse
2. **API Key Card**: API key requirement tespit edilirse
3. **Configuration Card**: Config capability tespit edilirse  
4. **Status Card**: Health check capability tespit edilirse
5. **Management Card**: Tool yönetimi için (her zaman oluşturulur)

## 📚 Examples

### Minimal Example

**File**: `plugins/simple_tool/settings_cards.json`

```json
{
  "version": "1.0",
  "tool_name": "simple_tool",
  "cards": [
    {
      "card_id": "simple_config",
      "type": "value",
      "category": "tools", 
      "title": "Simple Tool Config",
      "description": "Basic configuration",
      "icon": "⚙️",
      "form_schema": {
        "fields": [
          {
            "name": "enabled",
            "type": "checkbox",
            "label": "Tool Enabled",
            "required": false,
            "default": true
          }
        ]
      },
      "save_action": {
        "capability": "configuration",
        "action": "update_config"
      }
    }
  ]
}
```

### Complex Example

**File**: `plugins/advanced_tool/settings_cards.json`

```json
{
  "version": "1.0",
  "tool_name": "advanced_tool", 
  "description": "Advanced tool with multiple integrations",
  "cards": [
    {
      "card_id": "oauth_integration",
      "type": "action",
      "category": "authentication",
      "title": "OAuth Integration", 
      "description": "Connect with external service",
      "icon": "🔐",
      "order": 1,
      "actions": [
        {"id": "authorize", "type": "primary", "label": "Connect", 
         "tool_call": {"capability": "oauth", "action": "authorize"}},
        {"id": "disconnect", "type": "danger", "label": "Disconnect",
         "condition": "status === 'connected'",
         "confirm_message": "Disconnect from service?",
         "tool_call": {"capability": "oauth", "action": "disconnect"}}
      ],
      "data_source": {"capability": "oauth", "action": "check_connection"}
    },
    {
      "card_id": "advanced_config", 
      "type": "value",
      "category": "preferences",
      "title": "Advanced Settings",
      "description": "Detailed configuration options",
      "icon": "⚙️", 
      "order": 2,
      "form_schema": {
        "fields": [
          {"name": "mode", "type": "select", "label": "Operation Mode",
           "required": true, "options": [
             {"value": "auto", "label": "Automatic"},
             {"value": "manual", "label": "Manual"},
             {"value": "hybrid", "label": "Hybrid"}
           ]},
          {"name": "batch_size", "type": "number", "label": "Batch Size",
           "required": false, "min": 1, "max": 1000, "default": 50},
          {"name": "description", "type": "textarea", "label": "Description", 
           "required": false, "placeholder": "Optional description..."}
        ]
      },
      "save_action": {"capability": "config", "action": "save_advanced"},
      "data_source": {"capability": "config", "action": "get_advanced"}
    },
    {
      "card_id": "system_monitoring",
      "type": "status", 
      "category": "monitoring",
      "title": "System Monitor",
      "description": "Real-time system metrics", 
      "icon": "📈",
      "order": 3,
      "data_source": {"capability": "monitoring", "action": "get_metrics"}
    }
  ]
}
```

## 🚀 Quick Start

1. **Create Settings Cards File**:
   ```bash
   touch plugins/your_tool/settings_cards.json
   ```

2. **Define Your Cards**:
   ```json
   {
     "version": "1.0",
     "tool_name": "your_tool",
     "cards": [/* your cards */]
   }
   ```

3. **Implement Tool Capabilities**:
   ```python
   async def capability_action(self, context, **params):
       # Your implementation
       return {"success": True, "data": {}}
   ```

4. **Restart Bridge Server** - Cards auto-discovered on startup

## 🔍 Debugging

### Logs to Watch

```bash
# Card discovery logs
INFO - 🔍 Card discovery service attached
INFO - 🃏 Auto-discovered and registered 5 cards from 2 tools

# Card validation logs  
ERROR - Tool your_tool card missing required fields: {'title'}
WARNING - Tool your_tool invalid settings cards file
```

### Common Issues

1. **Missing Required Fields**: Ensure all cards have required fields
2. **Invalid JSON**: Validate JSON syntax
3. **Tool Name Mismatch**: `tool_name` must match directory name
4. **Capability Not Found**: Tool must implement referenced capabilities

## 📋 Best Practices

1. **Card Organization**: Group related settings in categories
2. **Order Matters**: Use `order` field for logical flow  
3. **User-Friendly Labels**: Clear, descriptive titles and labels
4. **Validation**: Add proper form validation rules
5. **Status Feedback**: Provide clear status displays
6. **Error Handling**: Implement robust error handling in tool methods
7. **Documentation**: Document your capabilities and expected parameters

---

**Ready to create awesome tool settings? Start with a simple card and iterate! 🚀**