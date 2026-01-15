# MetisAgent2

Simplified MCP Tool-based Flask Application with React Frontend

## Overview

MetisAgent2 is a streamlined version of the MetisAgent project, focusing on a clean MCP (Model Context Protocol) tool architecture with essential features for AI-powered system interactions.

## Features

### Backend (Flask)
- **MCP Tool Architecture**: Modular tool system with registration and management
- **Command Executor**: Secure, platform-independent command execution
- **LLM Integration**: OpenAI and Anthropic API support with conversation management
- **RESTful API**: Clean endpoints for frontend communication
- **Security**: Input validation and dangerous command filtering

### Frontend (React)
- **Chat Interface**: Real-time chat with multiple LLM providers
- **Command Interface**: Safe command execution with validation
- **Tools Management**: View and interact with available tools
- **Provider Management**: Switch between different LLM providers

## Quick Start

### Backend Setup

1. **Install Dependencies**
```bash
cd MetisAgent2
pip install -r requirements.txt
```

2. **Environment Setup**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the Server**
```bash
python app.py
```

The backend will start on `http://localhost:5000`

### Frontend Setup

1. **Install Dependencies**
```bash
cd MetisAgent2-Frontend
npm install
```

2. **Start Development Server**
```bash
npm start
```

The frontend will start on `http://localhost:3000`

## API Endpoints

### Core Endpoints
- `GET /api/health` - Health check
- `GET /api/tools` - List available tools
- `POST /api/tools/{tool_name}/execute` - Execute tool actions

### Simplified Endpoints
- `POST /api/chat` - Chat with LLM
- `POST /api/execute` - Execute commands
- `POST /api/validate-command` - Validate command safety
- `GET /api/providers` - Get LLM providers

## Configuration

### Required Environment Variables
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Optional Configuration
```
FLASK_ENV=development
FLASK_DEBUG=true
```

## Architecture

### MCP Tool System
- **MCPTool**: Base class for all tools
- **MCPToolRegistry**: Central registry for tool management
- **MCPToolResult**: Standardized result format

### Security Features
- Command validation and filtering
- Dangerous command blocking
- Input sanitization
- Timeout protection

## Development

### Adding New Tools
1. Create tool class inheriting from `MCPTool`
2. Register actions and capabilities
3. Add to registry in `tools/__init__.py`
4. Implement registration function

### Frontend Development
- React components in `src/components/`
- API service in `src/services/apiService.js`
- Styling in CSS files

## Testing

### Backend Testing
```bash
# Health check
curl http://localhost:5000/api/health

# List tools
curl http://localhost:5000/api/tools

# Test command execution
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "echo hello"}'
```

### Frontend Testing
1. Start both backend and frontend
2. Test chat interface with configured LLM providers
3. Test command execution with safe commands
4. Verify tools interface shows available tools

## Next Steps

1. **Add More Tools**: File manager, system info, etc.
2. **Streaming Support**: Real-time chat streaming
3. **Authentication**: User authentication and authorization
4. **Persistence**: Database storage for conversations
5. **Monitoring**: Logging and metrics

## Troubleshooting

### Common Issues
- **Connection Failed**: Check if backend is running on port 5000
- **API Key Errors**: Verify environment variables are set
- **Command Blocked**: Check command against security filters
- **Tool Not Found**: Ensure tool is registered in registry

### Development Tips
- Use browser dev tools to check API calls
- Check Flask logs for backend errors
- Verify CORS settings if having connection issues
- Test API endpoints directly with curl first