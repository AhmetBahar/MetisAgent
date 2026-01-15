# Google Tool Plugin

Complete Google Workspace integration for MetisAgent3 with event-driven automation.

## 🎯 Features

### Core Google Services
- **Gmail Operations** - Send, read, list emails with attachments
- **Calendar Management** - Create, update, delete events
- **Drive Operations** - Upload, download, share files
- **OAuth2 Authentication** - Secure token management

### 🚀 Event-Driven Automation
- **Email Triggers** - Execute workflows when emails arrive
- **Calendar Triggers** - Run workflows before events start
- **Drive Triggers** - Respond to file changes
- **Background Monitoring** - Continuous event detection

## 📦 Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Register the plugin:
```bash
python register_plugin.py
```

3. Configure OAuth2 credentials in MetisAgent3 settings.

## 🔐 OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail, Calendar, and Drive APIs
4. Create OAuth2 credentials (Web application)
5. Add redirect URI: `http://localhost:5001/oauth2/google/callback`
6. Configure client_id and client_secret in tool settings

## 🎮 Usage Examples

### Gmail Operations
```python
# List latest emails
{
  "capability": "gmail_operations",
  "input_data": {
    "action": "list",
    "params": {"max_results": 10}
  }
}

# Send email
{
  "capability": "gmail_operations", 
  "input_data": {
    "action": "send",
    "params": {
      "to": "recipient@example.com",
      "subject": "Test Email",
      "body": "Hello from MetisAgent3!"
    }
  }
}
```

### Calendar Operations
```python
# Create event
{
  "capability": "calendar_operations",
  "input_data": {
    "action": "create_event",
    "params": {
      "title": "Meeting",
      "start_time": "2025-08-11T14:00:00",
      "end_time": "2025-08-11T15:00:00"
    }
  }
}
```

### Drive Operations
```python
# Upload file
{
  "capability": "drive_operations",
  "input_data": {
    "action": "upload_file", 
    "params": {
      "file_path": "/path/to/file.pdf",
      "public": false
    }
  }
}
```

### Event Management
```python
# Create email trigger
{
  "capability": "event_management",
  "input_data": {
    "action": "create_email_trigger",
    "params": {
      "workflow_name": "urgent_email_handler",
      "subject_contains": "urgent",
      "enabled": true
    }
  }
}

# Create calendar trigger
{
  "capability": "event_management",
  "input_data": {
    "action": "create_calendar_trigger",
    "params": {
      "workflow_name": "meeting_reminder",
      "event_title_contains": "meeting",
      "minutes_before": 15
    }
  }
}
```

## 🔧 Configuration

### Required Settings
- `client_id` - Google OAuth2 Client ID
- `client_secret` - Google OAuth2 Client Secret  
- `redirect_uri` - OAuth2 callback URL (default: localhost:5001)

### Optional Settings
- `scopes` - Google API scopes (customizable)
- `rate_limits` - API call limits per user

## 📊 Capabilities

| Capability | Description | Actions |
|------------|-------------|---------|
| `oauth2_management` | Authentication | authorize, check_status, revoke |
| `gmail_operations` | Email management | list, read, send, send_with_attachment |
| `calendar_operations` | Calendar management | list_events, create_event, update_event, delete_event |
| `drive_operations` | File management | list_files, upload_file, download_file, share_file |
| `event_management` | Workflow automation | create_email_trigger, create_calendar_trigger, start_monitoring |

## 🎪 Event-Driven Workflows

### Email Events
- Trigger workflows when specific emails arrive
- Filter by sender, subject, or content
- Perfect for customer support automation

### Calendar Events  
- Execute workflows before meetings start
- Send reminders or prepare materials
- Automate meeting room setups

### Drive Events
- Process files when uploaded
- Backup important documents
- Collaborate on shared files

## 🛡️ Security

- **Encrypted Token Storage** - All OAuth2 tokens encrypted at rest
- **User Isolation** - Each user's credentials stored separately
- **Scope Limitation** - Request only necessary permissions
- **Auto Token Refresh** - Handles token expiration automatically

## 📝 Architecture

```
GoogleTool
├── OAuth2Manager - Handles authentication
├── Handlers/
│   ├── GmailHandler - Gmail API operations
│   ├── CalendarHandler - Calendar API operations  
│   └── DriveHandler - Drive API operations
├── EventHandler - Background event monitoring
└── EventHandlerAPI - Event trigger management
```

## 🚨 Claude.md Compliance

This plugin follows all CLAUDE.md rules:
- ✅ No hardcoded workflows or regex patterns
- ✅ SQLite-based encrypted storage
- ✅ Fault-tolerant error handling
- ✅ User-isolated credential management
- ✅ LLM-driven flexible automation
- ✅ Proper architectural design

## 🎯 Use Cases

1. **Email Automation** - Auto-respond to customer emails
2. **Meeting Management** - Schedule and prepare for meetings
3. **Document Workflow** - Process uploaded files automatically
4. **Notification Systems** - Send alerts based on calendar events
5. **Data Backup** - Automatically backup important files
6. **Customer Support** - Route urgent emails to appropriate workflows

## 🔄 Background Monitoring

The event handler runs continuously in the background:
- Checks Gmail for new messages every 60 seconds
- Monitors calendar for upcoming events
- Watches Drive for file changes
- Triggers configured workflows automatically

Start monitoring:
```python
{
  "capability": "event_management",
  "input_data": {
    "action": "start_monitoring"
  }
}
```

## 🎉 Success Stories

With this plugin, you can create powerful automations like:
- **"Email to Visual"** - Generate images based on email content
- **"Meeting Prep Bot"** - Prepare materials before meetings
- **"Smart File Processing"** - Auto-analyze uploaded documents
- **"Customer Alert System"** - Instant notifications for VIP customers

---

**🚀 Ready to supercharge your Google Workspace with AI automation!**