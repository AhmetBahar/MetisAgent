"""
LLM Tool - Simplified chat interface with multiple LLM providers
"""

import os
import json
import logging
from typing import List, Dict, Optional, Generator
from datetime import datetime
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult
# Import user storage (SQLite-based)
from .user_storage import get_user_storage

logger = logging.getLogger(__name__)

class LLMTool(MCPTool):
    """Simplified LLM tool for chat interactions"""
    
    def __init__(self):
        super().__init__(
            name="llm_tool",
            description="Chat with various LLM providers (OpenAI, Anthropic)",
            version="2.0.0"
        )
        
        # Register capabilities
        self.add_capability("text_generation")
        self.add_capability("chat_completion")
        self.add_capability("multi_provider_support")
        self.add_capability("conversation_management")
        
        # Register actions
        self.register_action(
            "chat",
            self._chat,
            required_params=["message"],
            optional_params=["provider", "model", "system_prompt", "conversation_id"]
        )
        
        self.register_action(
            "get_providers",
            self._get_providers,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "get_models",
            self._get_models,
            required_params=["provider"],
            optional_params=[]
        )
        
        self.register_action(
            "get_conversation",
            self._get_conversation,
            required_params=["conversation_id"],
            optional_params=[]
        )
        
        self.register_action(
            "clear_conversation",
            self._clear_conversation,
            required_params=["conversation_id"],
            optional_params=[]
        )
        
        self.register_action(
            "get_user_conversations",
            self._get_user_conversations,
            required_params=["user_id"],
            optional_params=[]
        )
        
        self.register_action(
            "create_user_conversation",
            self._create_user_conversation,
            required_params=["user_id", "conversation_name"],
            optional_params=["conversation_id"]
        )
        
        self.register_action(
            "store_memory",
            self._store_memory,
            required_params=["content"],
            optional_params=["category", "tags", "user_id"]
        )
        
        # Provider configurations
        self.providers = {
            "openai": {
                "name": "OpenAI",
                "api_key_env": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "default_model": "gpt-4o-mini"
            },
            "anthropic": {
                "name": "Anthropic",
                "api_key_env": "ANTHROPIC_API_KEY", 
                "base_url": "https://api.anthropic.com/v1",
                "models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
                "default_model": "claude-3-sonnet-20240229"
            }
        }
        
        # Multi-user conversation storage - now with ChromaDB persistence
        # Format: {conversation_id: [messages]}
        self.conversations: Dict[str, List[Dict]] = {}
        # Format: {user_id: {conversation_id: conversation_name}}
        self.user_conversations: Dict[str, Dict[str, str]] = {}
        
        # Initialize database for conversation persistence  
        try:
            from app.database import db_manager
            self.db = db_manager
            # Skip ChromaDB conversation loading for SQLite compatibility
            logger.info("Database manager loaded, using JSON fallback for conversations")
        except Exception as e:
            logger.warning(f"Could not load conversation database: {e}")
            self.db = None
        
        # Initialize JSON file persistence as fallback
        self.conversation_storage_dir = os.path.join(os.getcwd(), "conversation_storage")
        os.makedirs(self.conversation_storage_dir, exist_ok=True)
        
        # Load conversations from JSON if database failed
        if not self.db:
            self._load_conversations_from_json()
        
    def detect_user_intent(self, user_message: str) -> str:
        """Detect user intent from request"""
        message_lower = user_message.lower()
        
        # Gmail-specific intent detection
        if any(word in message_lower for word in ['gönderen', 'sender', 'kimden', 'from', 'gönderenini']):
            return 'sender_request'
        elif any(word in message_lower for word in ['konu', 'subject', 'başlık', 'konusu']):
            return 'subject_request'
        elif any(word in message_lower for word in ['ek', 'attachment', 'dosya', 'ekler']):
            return 'attachment_request'
        elif any(word in message_lower for word in ['tarih', 'date', 'ne zaman']):
            return 'date_request'
        else:
            return 'general_request'
    
    def enhance_system_prompt_with_intent(self, original_prompt: str, user_intent: str = None) -> str:
        """Enhance system prompt based on detected user intent"""
        intent_instructions = {
            'sender_request': """
CRITICAL INTENT: User asked specifically for SENDER information.
- Focus ONLY on 'from' field
- Lead response with sender information
- Format: "📧 Gönderen: {sender_email}"
- Do NOT include subject or other fields unless specifically asked
""",
            'subject_request': """
CRITICAL INTENT: User asked specifically for SUBJECT information.
- Focus ONLY on 'subject' field
- Lead response with subject information  
- Format: "📝 Konu: {subject_text}"
- Do NOT include sender or other fields unless specifically asked
""",
            'attachment_request': """
CRITICAL INTENT: User asked specifically for ATTACHMENT information.
- Focus ONLY on attachment status and files
- Format: "📎 Ek dosya: {attachment_status}"
- Do NOT include subject or sender unless specifically asked
""",
            'date_request': """
CRITICAL INTENT: User asked specifically for DATE information.
- Focus ONLY on date/time information
- Format: "📅 Tarih: {date_info}"
- Do NOT include subject or sender unless specifically asked
""",
            'general_request': """
GENERAL REQUEST: Provide comprehensive email information.
"""
        }
        
        intent_instruction = intent_instructions.get(user_intent, intent_instructions['general_request'])
        return f"{original_prompt}\n\n{intent_instruction}"

    def _chat(self, message, provider: str = "openai", model: Optional[str] = None,
              system_prompt: Optional[str] = None, conversation_id: str = "default", 
              enable_tools: bool = True, user_id: str = "default", requires_decision: bool = False,
              decision_title: str = None, decision_description: str = None, 
              decision_options: List = None, **kwargs) -> MCPToolResult:
        """Send a chat message to an LLM provider"""
        try:
            # Normalize message parameter (handle dict format from workflows)
            if isinstance(message, dict):
                if 'content' in message:
                    message = message['content']
                elif 'text' in message:
                    message = message['text']
                else:
                    message = str(message)
            elif not isinstance(message, str):
                message = str(message)
                
            # Detect user intent for better response generation
            user_intent = self.detect_user_intent(message)
            logger.info(f"INTENT DETECTION: '{message}' -> '{user_intent}'")
            
            # Validate provider
            if provider not in self.providers:
                return MCPToolResult(
                    success=False,
                    error=f"Provider '{provider}' not supported. Available: {list(self.providers.keys())}"
                )
            
            provider_config = self.providers[provider]
            
            # Check API key from SQLite database first, then fallback to environment
            api_key = None
            try:
                # Try to get API key from SQLite user storage
                storage = get_user_storage()
                api_key_data = storage.get_api_key(user_id, provider)
                if api_key_data:
                    # Handle both dict and string formats
                    if isinstance(api_key_data, dict):
                        api_key = api_key_data.get('api_key')
                    else:
                        api_key = api_key_data
                    
                    if api_key:
                        logger.info(f"Using API key from SQLite storage for {provider}")
            except Exception as e:
                logger.warning(f"Could not get API key from SQLite storage: {e}")
            
            # Fallback to environment variable
            if not api_key:
                api_key = os.getenv(provider_config["api_key_env"])
                if api_key:
                    logger.info(f"Using API key from environment for {provider}")
            
            if not api_key:
                return MCPToolResult(
                    success=False,
                    error=f"API key not found. Please add {provider} API key in Settings or set {provider_config['api_key_env']} environment variable"
                )
            
            # Use default model if not specified
            if not model:
                model = provider_config["default_model"]
            
            # Get or create conversation
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            conversation = self.conversations[conversation_id]
            
            # Add system prompt if provided and conversation is empty
            if system_prompt and len(conversation) == 0:
                # Enhance system prompt with intent awareness
                enhanced_prompt = self.enhance_system_prompt_with_intent(system_prompt, user_intent)
                conversation.append({
                    "role": "system",
                    "content": enhanced_prompt,
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif len(conversation) == 0 and enable_tools:
                # Enhanced system prompt with dynamic tools and intent awareness
                enhanced_system_prompt = self._get_enhanced_system_prompt()
                intent_aware_prompt = self.enhance_system_prompt_with_intent(enhanced_system_prompt, user_intent)
                conversation.append({
                    "role": "system",
                    "content": intent_aware_prompt,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Add user message
            conversation.append({
                "role": "user", 
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Make API call based on provider
            if provider == "openai":
                response = self._call_openai(api_key, provider_config["base_url"], model, conversation)
            elif provider == "anthropic":
                response = self._call_anthropic(api_key, provider_config["base_url"], model, conversation)
            else:
                return MCPToolResult(success=False, error=f"Provider '{provider}' not implemented")
            
            if response["success"]:
                # Add assistant response to conversation
                conversation.append({
                    "role": "assistant",
                    "content": response["content"],
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Save conversation to database after each interaction
                if self.db:
                    self._save_conversation_to_db(conversation_id, user_id)
                else:
                    self._save_conversation_to_json(conversation_id, user_id)
                
                result_data = {
                    "response": response["content"],
                    "provider": provider,
                    "model": model,
                    "conversation_id": conversation_id,
                    "message_count": len(conversation)
                }
                
                # Add decision data if this is a decision step
                if requires_decision and decision_options:
                    result_data.update({
                        "requires_decision": True,
                        "decision_title": decision_title or "Please choose an option:",
                        "decision_description": decision_description or "",
                        "decision_options": decision_options
                    })
                
                return MCPToolResult(success=True, data=result_data)
            else:
                return MCPToolResult(success=False, error=response["error"])
                
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _call_openai(self, api_key: str, base_url: str, model: str, conversation: List[Dict]) -> Dict:
        """Call OpenAI API with conditional Structured Outputs"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Convert conversation format for OpenAI
            messages = []
            for msg in conversation:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Check if system prompt or user message explicitly requests JSON-only workflow responses
            system_message = ""
            user_message_content = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                elif msg["role"] == "user":
                    user_message_content = msg["content"]
                    
            all_content = system_message + " " + user_message_content
            is_json_workflow_request = (
                "ONLY returns JSON" in all_content or 
                "Do NOT call tools" in all_content or
                "workflow planner that ONLY returns JSON" in all_content
            )
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # Only enable structured outputs if NOT explicitly requesting JSON workflow
            if not is_json_workflow_request:
                # Detect if this is a Gmail request that needs tool calling
                user_message = messages[-1]["content"].lower() if messages else ""
                needs_gmail_tool = self._detect_gmail_request(user_message)
                
                # Add Gmail tool with strict schema if needed (with fail-safe)
                if needs_gmail_tool:
                    try:
                        payload["tools"] = self._get_gmail_tools_schema()
                        payload["tool_choice"] = "required"  # Force tool usage
                        logger.info(f"STRUCTURED OUTPUTS: Gmail tool enabled with strict schema for: {user_message}")
                    except Exception as e:
                        logger.error(f"FAIL-SAFE: Gmail tool schema failed, continuing without tools: {e}")
                        # Continue without tools instead of crashing
            else:
                logger.info(f"JSON WORKFLOW MODE: Skipping structured outputs due to explicit JSON-only request")
            
            try:
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
            except Exception as e:
                logger.error(f"FAIL-SAFE: OpenAI API request failed: {e}")
                return {"response": "Error: Unable to connect to OpenAI API", "error": str(e)}
            
            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]
                
                # Handle tool calls from structured outputs
                if "tool_calls" in message and message["tool_calls"]:
                    tool_calls = message["tool_calls"]
                    logger.info(f"TOOL CALLS DETECTED: {len(tool_calls)} tools called")
                    
                    # Format response to include tool calls
                    formatted_response = {
                        "response": message.get("content", "Executing Gmail operation..."),
                        "tool_calls": []
                    }
                    
                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        formatted_response["tool_calls"].append({
                            "tool": "gmail_helper",
                            "action": function.get("name", "send_email"),
                            "params": json.loads(function.get("arguments", "{}"))
                        })
                    
                    return {"success": True, "content": json.dumps(formatted_response)}
                else:
                    content = message.get("content", "")
                    return {"success": True, "content": content}
            else:
                error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                logger.error(f"FAIL-SAFE: {error_msg}")
                # Return a fallback response instead of failing completely
                return {
                    "response": f"I encountered an API error (status {response.status_code}). The system will continue with fallback processing.",
                    "error": error_msg,
                    "fallback": True
                }
                
        except Exception as e:
            error_msg = f"OpenAI API call failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _call_anthropic(self, api_key: str, base_url: str, model: str, conversation: List[Dict]) -> Dict:
        """Call Anthropic API"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Convert conversation format for Anthropic
            messages = []
            system_prompt = None
            
            for msg in conversation:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{base_url}/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                return {"success": True, "content": content}
            else:
                error_msg = f"Anthropic API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Anthropic API call failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _get_providers(self, **kwargs) -> MCPToolResult:
        """Get available LLM providers"""
        try:
            providers_info = []
            for provider_id, config in self.providers.items():
                api_key = os.getenv(config["api_key_env"])
                providers_info.append({
                    "id": provider_id,
                    "name": config["name"],
                    "available": api_key is not None,
                    "models": config["models"],
                    "default_model": config["default_model"]
                })
            
            return MCPToolResult(success=True, data={"providers": providers_info})
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_models(self, provider: str, **kwargs) -> MCPToolResult:
        """Get available models for a provider"""
        try:
            if provider not in self.providers:
                return MCPToolResult(
                    success=False,
                    error=f"Provider '{provider}' not found"
                )
            
            config = self.providers[provider]
            return MCPToolResult(
                success=True,
                data={
                    "provider": provider,
                    "models": config["models"],
                    "default_model": config["default_model"]
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_conversation(self, conversation_id: str, **kwargs) -> MCPToolResult:
        """Get conversation history"""
        try:
            if conversation_id not in self.conversations:
                return MCPToolResult(
                    success=False,
                    error=f"Conversation '{conversation_id}' not found"
                )
            
            return MCPToolResult(
                success=True,
                data={
                    "conversation_id": conversation_id,
                    "messages": self.conversations[conversation_id],
                    "message_count": len(self.conversations[conversation_id])
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _clear_conversation(self, conversation_id: str, **kwargs) -> MCPToolResult:
        """Clear conversation history"""
        try:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
            
            return MCPToolResult(
                success=True,
                data={"message": f"Conversation '{conversation_id}' cleared"}
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_user_conversations(self, user_id: str, **kwargs) -> MCPToolResult:
        """Get all conversations for a user"""
        try:
            user_convs = self.user_conversations.get(user_id, {})
            conversations = []
            
            for conv_id, conv_name in user_convs.items():
                message_count = len(self.conversations.get(conv_id, []))
                conversations.append({
                    "conversation_id": conv_id,
                    "name": conv_name,
                    "message_count": message_count,
                    "last_activity": self._get_last_activity(conv_id)
                })
            
            return MCPToolResult(
                success=True,
                data={
                    "user_id": user_id,
                    "conversations": conversations,
                    "total_conversations": len(conversations)
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _create_user_conversation(self, user_id: str, conversation_name: str, 
                                 conversation_id: str = None, **kwargs) -> MCPToolResult:
        """Create a new conversation for a user"""
        try:
            if not conversation_id:
                import uuid
                conversation_id = f"{user_id}_{str(uuid.uuid4())[:8]}"
            
            # Initialize user conversations if needed
            if user_id not in self.user_conversations:
                self.user_conversations[user_id] = {}
            
            # Add conversation
            self.user_conversations[user_id][conversation_id] = conversation_name
            
            # Initialize empty conversation
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            return MCPToolResult(
                success=True,
                data={
                    "conversation_id": conversation_id,
                    "name": conversation_name,
                    "user_id": user_id
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_last_activity(self, conversation_id: str) -> Optional[str]:
        """Get last activity timestamp for a conversation"""
        messages = self.conversations.get(conversation_id, [])
        if messages:
            return messages[-1].get('timestamp')
        return None
    
    def _store_memory(self, content: str, category: str = "general", 
                     tags: List[str] = None, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Store memory using memory manager (proxy method)"""
        try:
            # This would be handled by the tool coordinator
            # For now, return a success response
            return MCPToolResult(
                success=True,
                data={
                    "message": "Memory storage request sent to memory_manager",
                    "content": content,
                    "category": category,
                    "tags": tags or [],
                    "user_id": user_id
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def update_dynamic_tools_in_prompt(self, dynamic_tools_info: list):
        """Update system prompt to include dynamic tools"""
        try:
            # This will be called by tool_manager when tools are added/removed
            # For now, we store the dynamic tools info to use in future conversations
            self._dynamic_tools_info = dynamic_tools_info
            logger.info(f"LLM tool updated with {len(dynamic_tools_info)} dynamic tools")
        except Exception as e:
            logger.error(f"Error updating dynamic tools in LLM prompt: {str(e)}")
    
    def _get_enhanced_system_prompt(self):
        """Get system prompt enhanced with dynamic tools"""
        base_prompt = """You are a helpful AI assistant with access to system tools. 

CRITICAL: When users ask questions that require system commands, you MUST respond with ONLY JSON format.

MANDATORY JSON FORMAT for tool usage:
{
  "response": "Brief explanation of what you're doing",
  "tool_calls": [
    {
      "tool": "command_executor",
      "action": "execute", 
      "params": {"command": "appropriate_command"}
    }
  ]
}

EXAMPLES:
User: "How long has my computer been on?" 
Response: {"response": "I'll check your system uptime", "tool_calls": [{"tool": "command_executor", "action": "execute", "params": {"command": "uptime"}}]}

User: "What directory am I in?"
Response: {"response": "I'll check your current directory", "tool_calls": [{"tool": "command_executor", "action": "execute", "params": {"command": "pwd"}}]}

User: "List files"
Response: {"response": "I'll list the files in this directory", "tool_calls": [{"tool": "command_executor", "action": "execute", "params": {"command": "ls -la"}}]}

User: "Bilgisayarım kaç saattir açık?"
Response: {"response": "Bilgisayarınızın ne kadar süredir açık olduğunu kontrol ediyorum", "tool_calls": [{"tool": "command_executor", "action": "execute", "params": {"command": "uptime"}}]}

User: "Klasör listesi"
Response: {"response": "Bu dizindeki klasörleri listeliyorum", "tool_calls": [{"tool": "command_executor", "action": "execute", "params": {"command": "ls -la"}}]}
User: "Send email to john@test.com"
Response: {"response": "I'll send the email for you", "tool_calls": [{"tool": "gmail_helper", "action": "send_email", "params": {"recipient": "john@test.com", "subject": "MetisAgent Email", "body": "Email sent via MetisAgent"}}]}
User: "ahmet@test.com adresine email gönder"
Response: {"response": "Size email gönderiyorum", "tool_calls": [{"tool": "gmail_helper", "action": "send_email", "params": {"recipient": "ahmet@test.com", "subject": "MetisAgent Email", "body": "MetisAgent üzerinden gönderilen mesaj"}}]}

CONVERSATION RULES:
- For regular chat (no tools needed): Respond naturally and conversationally
- For tool requests: Use JSON format with tool calls
- For tool result analysis: Provide clear, helpful summaries

ANALYSIS EXAMPLES (only when tools were executed):
- Ping results: "Bağlantı mükemmel çalışıyor! Google'a başarıyla ulaşabiliyoruz, tüm paketler alındı ve ortalama yanıt süresi 35ms."
- Directory listing: "Bu klasörde toplam 12 öğe var - 3 klasör ve 9 dosya bulunuyor."
- File content: "Dosya başarıyla okundu. İçinde 25 satır metin var."
- DNS config: "DNS ayarlarınız Google DNS (8.8.8.8) kullanıyor."
- Current directory: "Şu anda /home/ahmet/MetisAgent/MetisAgent2 klasöründeyiz."

MEMORY MANAGEMENT:
- Store important information automatically using memory_manager
- Remember user preferences, important facts, and context
- Retrieve relevant memories to provide better assistance

GMAIL API USAGE:
When users ask about Gmail emails (subject, sender, content), you MUST make TWO sequential tool calls:
1. First: gmail_list_messages to get message ID
2. Second: gmail_get_message to get message details and extract subject

CRITICAL: When user asks for email subject, do NOT stop after getting message list. 
You MUST immediately get message details to find the subject.

GMAIL EXAMPLES:
User: "gmail inbox son gelen mailin konusu nedir"
Step 1: {"response": "Gmail'deki son mesajı kontrol ediyorum", "tool_calls": [{"tool": "google_oauth2_manager", "action": "gmail_list_messages", "params": {"max_results": 1}}]}
Step 2: After getting message ID, IMMEDIATELY call: {"response": "Mesaj detaylarını alıp subject'i çıkarıyorum", "tool_calls": [{"tool": "google_oauth2_manager", "action": "gmail_get_message", "params": {"message_id": "ACTUAL_MESSAGE_ID"}}]}

CRITICAL USER MAPPING:
- DO NOT include user_id in Gmail tool calls - tool will auto-detect current user
- Tool automatically maps system user to their configured Google account
- Let the tool handle user identification and mapping internally

NEVER ask user permission between these steps - execute both automatically!

MEMORY EXAMPLES:
User: "Remember that I prefer dark mode"
Response: {"response": "I'll remember your preference for dark mode", "tool_calls": [{"tool": "memory_manager", "action": "store_memory", "params": {"content": "User prefers dark mode interface", "category": "preferences", "tags": ["ui", "preference"]}}]}

User: "What do you remember about me?"
Response: {"response": "Let me check what I remember about you", "tool_calls": [{"tool": "memory_manager", "action": "retrieve_memories", "params": {"limit": 10}}]}

TOOL LISTING EXAMPLES:
User: "hangi araçlar kullanılabilir durumda?"
Response: {"response": "I'll show you the available tools", "tool_calls": [{"tool": "registry", "action": "list_tools", "params": {}}]}

User: "hangi tool'lar var şu anda"
Response: {"response": "I'll list the current tools", "tool_calls": [{"tool": "registry", "action": "list_tools", "params": {}}]}

User: "what tools are available?"
Response: {"response": "I'll list the available tools", "tool_calls": [{"tool": "registry", "action": "list_tools", "params": {}}]}

MEMORY CATEGORIES:
- "preferences": User preferences and settings
- "facts": Important facts about the user
- "projects": Current projects and work
- "skills": User's skills and expertise
- "general": General information

""" + self._generate_tools_documentation() + """

TOOL MANAGEMENT EXAMPLES:
User: "install website fetcher tool"
Response: {"response": "I'll install the website fetcher tool", "tool_calls": [{"tool": "tool_manager", "action": "install_tool", "params": {"source": "path_or_repo"}}]}

User: "remove calculator tool"
Response: {"response": "I'll remove the calculator tool", "tool_calls": [{"tool": "tool_manager", "action": "remove_tool", "params": {"target_tool": "calculator"}}]}

User: "list installed tools"
Response: {"response": "I'll show you the installed tools", "tool_calls": [{"tool": "tool_manager", "action": "list_installed_tools", "params": {}}]}"""

        # Add dynamic tools if available
        if hasattr(self, '_dynamic_tools_info') and self._dynamic_tools_info:
            base_prompt += "\n\nDYNAMIC TOOLS (RUNTIME LOADED):\n"
            for tool_info in self._dynamic_tools_info:
                base_prompt += tool_info + "\n"
            
            base_prompt += "\nIMPORTANT: Always prefer dynamic tools when available for their specific tasks!"
        
        base_prompt += "\n\nCRITICAL: Always provide clear, definitive answers when interpreting results."
        
        return base_prompt
    
    def _detect_gmail_request(self, user_message: str) -> bool:
        """Detect if user message requires Gmail tool calling"""
        # Çok dilli tetikleyici sözlük (TR + EN)
        gmail_triggers = [
            # Turkish triggers
            'gönder', 'ile gönder', 'gmail üzerinden', 'postala',
            'email gönder', 'mail gönder', 'mesaj gönder',
            'görseli gönder', 'resmi gönder', 'ekli gönder',
            # English triggers  
            'send email', 'send mail', 'email to', 'mail to',
            'send via gmail', 'through gmail', 'using gmail',
            'send image', 'send picture', 'send attachment'
        ]
        
        return any(trigger in user_message for trigger in gmail_triggers)
    
    def _get_gmail_tools_schema(self) -> list:
        """Get Gmail tools with strict schema for Structured Outputs"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send a basic email via Gmail",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {
                                "type": "string",
                                "format": "email",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string", 
                                "description": "Email body content"
                            }
                        },
                        "required": ["recipient", "subject", "body"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email_with_attachment",
                    "description": "Send an email via Gmail with file attachment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {
                                "type": "string",
                                "format": "email",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string", 
                                "description": "Email body content"
                            },
                            "attachment_path": {
                                "type": "string",
                                "description": "Path to attachment file"
                            }
                        },
                        "required": ["recipient", "subject", "body", "attachment_path"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "send_email_with_attachment",
                    "description": "Send email with attachment using Gmail API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {
                                "type": "string",
                                "format": "email",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body content"
                            },
                            "attachment_path": {
                                "type": "string", 
                                "description": "Path to attachment file"
                            }
                        },
                        "required": ["recipient", "subject", "body", "attachment_path"],
                        "additionalProperties": False
                    },
                    "strict": True  # Structured Outputs enforcement
                }
            }
        ]
    
    def _generate_tools_documentation(self) -> str:
        """Generate dynamic tool documentation from registry"""
        try:
            from app.mcp_core import registry
            import json
            
            all_tools = registry.list_tools()
            if not all_tools:
                return "Available tools: None (registry empty)"
            
            tools_doc = "Available tools:\n"
            
            for tool in all_tools:
                if not tool.get('is_enabled', True):
                    continue
                    
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', 'No description')
                actions = tool.get('actions', {})
                
                tools_doc += f"- {tool_name}: {tool_desc}\n"
                
                # Add action documentation
                for action_name, action_info in actions.items():
                    required_params = action_info.get('required_params', [])
                    optional_params = action_info.get('optional_params', [])
                    
                    # Build example JSON
                    example_params = {}
                    for param in required_params:
                        if param == 'command':
                            example_params[param] = "ping -c 4 google.com"
                        elif param == 'prompt':
                            example_params[param] = "description or theme"
                        elif param == 'message_id':
                            example_params[param] = "email_id"
                        elif param == 'user_id':
                            example_params[param] = "user_identifier"
                        else:
                            example_params[param] = f"<{param}_value>"
                    
                    # Add some common optional parameters for examples
                    if 'max_results' in optional_params:
                        example_params['max_results'] = 10
                    elif 'query' in optional_params and tool_name == 'gmail_helper':
                        example_params['query'] = "search terms"
                    
                    example_json = json.dumps({
                        "tool": tool_name,
                        "action": action_name,
                        "params": example_params
                    })
                    
                    param_info = ""
                    if required_params:
                        param_info += f" (required: {', '.join(required_params)})"
                    if optional_params:
                        param_info += f" (optional: {', '.join(optional_params)})"
                    
                    tools_doc += f"  - {action_name}{param_info}: {example_json}\n"
            
            return tools_doc
            
        except Exception as e:
            logger.error(f"Error generating tools documentation: {e}")
            return "Available tools: Error loading tool information from registry"
    
    def health_check(self) -> MCPToolResult:
        """Check LLM tool health"""
        try:
            # Check if at least one provider is configured
            available_providers = []
            for provider_id, config in self.providers.items():
                api_key = os.getenv(config["api_key_env"])
                if api_key:
                    available_providers.append(provider_id)
            
            if available_providers:
                return MCPToolResult(
                    success=True,
                    data={
                        "status": "healthy",
                        "available_providers": available_providers,
                        "total_providers": len(self.providers),
                        "active_conversations": len(self.conversations)
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="No LLM providers configured (missing API keys)"
                )
                
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_conversation_collection(self):
        """Get or create conversation collection - SQLite compatibility"""
        try:
            if not self.db:
                return None
            
            # SQLite DatabaseManager doesn't have client attribute
            # Return None to use JSON fallback storage
            logger.info("No conversation database available - starting fresh")
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation collection: {e}")
            return None
    
    def _save_conversation_to_db(self, conversation_id: str, user_id: str = "default"):
        """Save conversation to ChromaDB"""
        try:
            collection = self._get_conversation_collection()
            if not collection or conversation_id not in self.conversations:
                return
            
            conversation_data = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "last_updated": datetime.now().isoformat(),
                "message_count": len(self.conversations[conversation_id])
            }
            
            # Try to get existing conversation first
            try:
                existing = collection.get(ids=[conversation_id])
                if existing["ids"]:
                    # Update existing
                    collection.delete(ids=[conversation_id])
            except:
                pass
            
            # Add/Update conversation
            collection.add(
                ids=[conversation_id],
                metadatas=[conversation_data],
                documents=[json.dumps(self.conversations[conversation_id])]
            )
            
            logger.debug(f"Saved conversation {conversation_id} to database")
            
        except Exception as e:
            logger.error(f"Error saving conversation to database: {e}")
    
    def _load_conversations_from_db(self, limit: int = 50):
        """Load recent conversations from ChromaDB on startup"""
        try:
            collection = self._get_conversation_collection()
            if not collection:
                logger.info("No conversation database available - starting fresh")
                return
            
            # Get all conversations
            results = collection.get(limit=limit)
            
            if not results["ids"]:
                logger.info("No previous conversations found in database")
                return
            
            loaded_count = 0
            for i, (conv_id, document, metadata) in enumerate(zip(
                results["ids"], results["documents"], results["metadatas"]
            )):
                try:
                    # Load conversation messages
                    messages = json.loads(document)
                    self.conversations[conv_id] = messages
                    
                    # Load user conversation mapping
                    user_id = metadata.get("user_id", "default")
                    if user_id not in self.user_conversations:
                        self.user_conversations[user_id] = {}
                    
                    # Generate conversation name from first user message or use ID
                    conv_name = f"Conversation {conv_id[:8]}"
                    if messages:
                        for msg in messages:
                            if msg.get("role") == "user":
                                # Use first 50 chars of first user message as name
                                conv_name = msg.get("content", "")[:50]
                                if len(conv_name) == 50:
                                    conv_name += "..."
                                break
                    
                    self.user_conversations[user_id][conv_id] = conv_name
                    loaded_count += 1
                    
                except Exception as msg_error:
                    logger.warning(f"Could not load conversation {conv_id}: {msg_error}")
                    continue
            
            logger.info(f"Loaded {loaded_count} conversations from database")
            
        except Exception as e:
            logger.error(f"Error loading conversations from database: {e}")
    
    def _save_conversation_to_json(self, conversation_id: str, user_id: str = "default"):
        """Save conversation to JSON file as fallback"""
        try:
            # Create user-specific file
            json_file = os.path.join(self.conversation_storage_dir, f"conversations_{user_id}.json")
            
            # Load existing data
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"conversations": {}, "user_conversations": {}}
            
            # Update conversation data
            if conversation_id in self.conversations:
                data["conversations"][conversation_id] = {
                    "messages": self.conversations[conversation_id],
                    "last_updated": datetime.now().isoformat(),
                    "message_count": len(self.conversations[conversation_id])
                }
            
            # Update user conversation mapping
            if user_id in self.user_conversations:
                data["user_conversations"] = self.user_conversations[user_id]
            
            # Save to file
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved conversation {conversation_id} to JSON file")
            
        except Exception as e:
            logger.error(f"Error saving conversation to JSON: {e}")
    
    def _load_conversations_from_json(self, limit: int = 50):
        """Load conversations from JSON files"""
        try:
            # Get all user conversation files
            json_files = [f for f in os.listdir(self.conversation_storage_dir) if f.startswith("conversations_") and f.endswith(".json")]
            
            loaded_count = 0
            for json_file in json_files:
                try:
                    # Extract user_id from filename
                    user_id = json_file.replace("conversations_", "").replace(".json", "")
                    
                    file_path = os.path.join(self.conversation_storage_dir, json_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Load conversations
                    conversations = data.get("conversations", {})
                    for conv_id, conv_data in list(conversations.items())[:limit]:
                        self.conversations[conv_id] = conv_data.get("messages", [])
                        loaded_count += 1
                    
                    # Load user conversation mapping
                    user_convs = data.get("user_conversations", {})
                    if user_convs:
                        if user_id not in self.user_conversations:
                            self.user_conversations[user_id] = {}
                        self.user_conversations[user_id].update(user_convs)
                    
                except Exception as file_error:
                    logger.warning(f"Could not load conversation file {json_file}: {file_error}")
                    continue
            
            logger.info(f"Loaded {loaded_count} conversations from JSON files")
            
        except Exception as e:
            logger.error(f"Error loading conversations from JSON: {e}")

def register_tool(registry):
    """Register the LLM tool with the registry"""
    tool = LLMTool()
    return registry.register_tool(tool)