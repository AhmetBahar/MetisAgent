# Generic Tool Execution Blueprint - MetisAgent3

## 📋 Overview

Bu blueprint, MetisAgent3'te tool execution'ı için generic endpoint sistemi tasarlar. Şu anki yaklaşımda her tool capability için ayrı endpoint oluşturulması sürdürülebilir değildir.

## 🎯 Problem Statement

**Mevcut Durum:**
```
/api/settings/auth/google/login     - OAuth2 authorize
/api/settings/auth/status           - OAuth2 status check  
/api/settings/auth/logout           - OAuth2 revoke
/api/settings/auth/google/mapping   - User mapping (GET/POST/DELETE)
```

**Sorunlar:**
- Her tool capability için yeni endpoint gerekiyor
- Code duplication (async wrapper, context creation, error handling)  
- Maintenance overhead
- Bridge server şişiyor
- Tool-specific logic bridge'de karışıyor

## 🏗️ Solution Architecture

### Generic Tool Execution Endpoint

**Single Endpoint:**
```
POST /api/tools/execute
```

**Request Format:**
```json
{
  "tool_name": "google_tool",
  "capability": "oauth2_management", 
  "action": "authorize",
  "parameters": {
    "user_id": "test_user",
    "google_email": "user@gmail.com"
  }
}
```

**Response Format:**
```json
{
  "success": true,
  "tool_name": "google_tool",
  "capability": "oauth2_management",
  "action": "authorize", 
  "data": {
    "auth_url": "https://accounts.google.com/oauth/...",
    "message": "Authorization URL generated"
  },
  "execution_time": 1250
}
```

## 🔧 Implementation Plan

### 1. Generic Tool Executor Service

**Location:** `core/services/tool_execution_service.py`

```python
class ToolExecutionService:
    def __init__(self, tool_manager, user_manager):
        self.tool_manager = tool_manager
        self.user_manager = user_manager
    
    async def execute_tool_capability(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        """Generic tool capability execution"""
        
        # 1. Validate request
        # 2. Get tool instance
        # 3. Create execution context  
        # 4. Execute capability
        # 5. Format response
        # 6. Handle errors consistently
```

### 2. Bridge Server Integration

**Single Endpoint:**
```python
@app.route('/api/tools/execute', methods=['POST'])
def execute_tool_capability():
    """Generic tool execution endpoint"""
    try:
        data = request.get_json()
        
        # Create execution request
        tool_request = ToolExecutionRequest(
            tool_name=data.get('tool_name'),
            capability=data.get('capability'),
            action=data.get('action'),
            parameters=data.get('parameters', {}),
            user_id=get_current_user_id()
        )
        
        # Execute via service
        result = await bridge.tool_execution_service.execute_tool_capability(tool_request)
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

### 3. Frontend Integration

**Generic Tool Client:**
```javascript
class ToolClient {
    async executeToolCapability(toolName, capability, action, parameters = {}) {
        const response = await fetch('/api/tools/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                tool_name: toolName,
                capability: capability,
                action: action,
                parameters: parameters
            })
        });
        
        return await response.json();
    }
    
    // Specialized methods for common operations
    async googleOAuth2Authorize() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'authorize');
    }
    
    async setGoogleUserMapping(googleEmail, googleName) {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'set_user_mapping', {
            google_email: googleEmail,
            google_name: googleName
        });
    }
}
```

## 🔐 Security & Validation

### Request Validation
- Tool existence check
- Capability validation
- User authorization
- Parameter sanitization
- Rate limiting per tool/user

### Error Handling
```python
class ToolExecutionError(Exception):
    def __init__(self, tool_name, capability, action, error_message):
        self.tool_name = tool_name
        self.capability = capability  
        self.action = action
        self.error_message = error_message
```

## 📊 Benefits

### 1. Scalability
- ✅ Single endpoint for all tools
- ✅ No new endpoints per capability
- ✅ Consistent request/response format

### 2. Maintainability  
- ✅ Centralized error handling
- ✅ Consistent logging/monitoring
- ✅ Single place for authentication/authorization

### 3. Developer Experience
- ✅ Predictable API structure
- ✅ Easy to add new tools
- ✅ Frontend client simplification

### 4. Architecture Compliance
- ✅ Bridge server stays thin
- ✅ Business logic in tools
- ✅ Clean separation of concerns

## 🗂️ Migration Plan

### Phase 1: Core Implementation
1. Create `ToolExecutionService`
2. Add generic `/api/tools/execute` endpoint  
3. Create frontend `ToolClient`

### Phase 2: Google Tool Migration
1. Update Google Tool calls to use generic endpoint
2. Remove specific Google OAuth endpoints
3. Test OAuth2 flow end-to-end

### Phase 3: System-wide Adoption
1. Migrate other tool calls to generic endpoint
2. Remove old specific endpoints
3. Update documentation

### Phase 4: Enhancement
1. Add request/response caching
2. Implement tool execution analytics
3. Add advanced error handling/retry logic

## 🧪 Testing Strategy

### Unit Tests
- ToolExecutionService validation
- Error handling scenarios
- Parameter sanitization

### Integration Tests  
- End-to-end tool execution
- Authentication/authorization
- Error propagation

### Performance Tests
- Tool execution latency
- Concurrent execution handling
- Resource usage validation

## 📋 Example Usage Scenarios

### Google OAuth2 Authorization
```javascript
const result = await toolClient.executeToolCapability(
    'google_tool', 
    'oauth2_management', 
    'authorize'
);

if (result.success) {
    window.location.href = result.data.auth_url;
}
```

### User Mapping Management
```javascript
// Get mapping
const mapping = await toolClient.executeToolCapability(
    'google_tool',
    'oauth2_management', 
    'get_user_mapping'
);

// Set mapping  
const setResult = await toolClient.executeToolCapability(
    'google_tool',
    'oauth2_management',
    'set_user_mapping',
    { 
        google_email: 'user@gmail.com',
        google_name: 'John Doe' 
    }
);
```

### Gmail Operations
```javascript
const emails = await toolClient.executeToolCapability(
    'google_tool',
    'gmail_operations',
    'list',
    { max_results: 10 }
);
```

## 🎯 Success Criteria

- ✅ Single generic endpoint handling all tool executions
- ✅ Zero code duplication in bridge server  
- ✅ Consistent error handling across all tools
- ✅ Simplified frontend integration
- ✅ Backward compatibility during migration
- ✅ Improved system maintainability

## ⚠️ Risks & Mitigations

### Risk: Performance Impact
**Mitigation:** Add request caching and tool execution optimization

### Risk: Breaking Changes
**Mitigation:** Phased migration with backward compatibility

### Risk: Complex Error Handling
**Mitigation:** Standardized error response format with detailed context

---

**Author:** Claude Code Assistant  
**Date:** 2025-08-18  
**Status:** Draft - Ready for Implementation  
**Priority:** High