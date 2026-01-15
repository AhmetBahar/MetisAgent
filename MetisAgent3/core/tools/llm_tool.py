"""
LLM Tool - Production-Ready Multi-Provider LLM Integration

CLAUDE.md COMPLIANT:
- Multi-provider LLM support (OpenAI, Anthropic)
- Encrypted API key management from SQLite storage
- Conversation management with persistence
- Structured response generation
- Intent-aware system prompts
"""

import asyncio
import json
import logging
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from ..contracts.base_types import AgentResult, ExecutionContext, HealthStatus
from ..contracts.tool_contracts import BaseTool, ToolMetadata, ToolConfiguration, ToolType
from ..storage.sqlite_storage import SQLiteUserStorage
from ..services.conversation_service import ConversationService, LLMConversationIntegration

logger = logging.getLogger(__name__)


class LLMTool(BaseTool):
    """Production-ready LLM tool with multi-provider support"""
    
    def __init__(self, metadata: Optional[ToolMetadata] = None, config: Optional[ToolConfiguration] = None, storage: Optional[SQLiteUserStorage] = None):
        # Create default metadata and config if not provided (for backward compatibility)
        if metadata is None:
            metadata = ToolMetadata(
                name="llm_tool",
                description="Multi-provider LLM chat interface with conversation management", 
                version="3.0.0",
                tool_type=ToolType.INTERNAL,
                capabilities=[],
                author="MetisAgent3"
            )
        if config is None:
            config = ToolConfiguration(
                tool_name="llm_tool",
                enabled=True,
                config={
                    "timeout": 30.0,
                    "max_retries": 3,
                    "health_check_interval": 60
                }
            )
        
        super().__init__(metadata, config)
        
        self.storage = storage or SQLiteUserStorage()
        
        # Initialize conversation service
        self.conversation_service = ConversationService()
        self.conversation_integration = LLMConversationIntegration(self.conversation_service)
        
        # Provider configurations
        self.providers = {
            "openai": {
                "name": "OpenAI",
                "api_key_name": "api_key_openai",
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "default_model": "gpt-4o-mini"
            },
            "anthropic": {
                "name": "Anthropic", 
                "api_key_name": "anthropic_api_key",
                "base_url": "https://api.anthropic.com/v1",
                "models": ["claude-3-7-sonnet-latest", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
                "default_model": "claude-3-7-sonnet-latest"
            }
        }
        
        # Conversation storage
        self.conversations: Dict[str, List[Dict]] = {}
        
        # Register capabilities
        self.capabilities = {
            "text_generation": "Generate text responses using LLMs",
            "chat_completion": "Multi-turn conversation support",
            "multi_provider": f"Support for {len(self.providers)} LLM providers",
            "conversation_management": "SQLite-based persistent conversation storage",
            "conversation_search": "Full-text search in conversation history",
            "context_retrieval": "Smart context retrieval from conversation history",
            "structured_generation": "JSON-structured response generation",
            "intent_detection": "Context-aware prompt enhancement"
        }
        
        logger.info(f"LLM Tool initialized with {len(self.providers)} providers")
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute LLM tool capabilities"""
        try:
            if capability in ["chat", "generate_response"]:
                return await self._chat(input_data, context)
            elif capability == "get_providers":
                return await self._get_providers()
            elif capability == "get_models":
                return await self._get_models(input_data)
            elif capability == "get_conversation":
                return await self._get_conversation_persistent(input_data, context)
            elif capability == "list_conversations":
                return await self._list_conversations_persistent(input_data, context)
            elif capability == "search_conversations":
                return await self._search_conversations(input_data, context)
            elif capability == "delete_conversation":
                return await self._delete_conversation_persistent(input_data, context)
            elif capability == "clear_conversation":
                return await self._clear_conversation(input_data)  # Keep legacy method
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown capability: {capability}",
                    metadata={"available_capabilities": list(self.capabilities.keys())}
                )
                
        except Exception as e:
            logger.error(f"LLM tool execution failed: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _chat(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Send chat message to LLM provider"""
        try:
            # Extract parameters - handle both "message" and "messages" formats
            messages = input_data.get("messages")
            message = input_data.get("message", "")
            provider = input_data.get("provider", "openai")
            model = input_data.get("model")
            system_prompt = input_data.get("system_prompt")
            conversation_id = input_data.get("conversation_id", "default")
            user_id = context.user_id or "default"
            
            # Handle messages format (preferred)
            if messages and isinstance(messages, list) and len(messages) > 0:
                # Use last message as the user message
                last_message = messages[-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    message = last_message["content"]
                
                # Extract system prompt from messages if present
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("role") == "system":
                        system_prompt = msg.get("content")
                        break
            
            # Parameter validation
            if not message:
                return AgentResult(success=False, error="Message is required")
            
            if provider not in self.providers:
                return AgentResult(
                    success=False,
                    error=f"Provider '{provider}' not supported. Available: {list(self.providers.keys())}"
                )
            
            provider_config = self.providers[provider]
            
            # Get API key from encrypted storage
            api_key = await self._get_api_key(user_id, provider)
            if not api_key:
                return AgentResult(
                    success=False,
                    error=f"API key not found for {provider}. Please configure API key in user settings."
                )
            
            # Use default model if not specified
            if not model:
                model = provider_config["default_model"]
            
            # Get or create conversation in SQLite
            persistent_conversation = await self.conversation_service.get_conversation(
                conversation_id, user_id
            )
            
            new_thread = False
            if not persistent_conversation:
                # Create new conversation using provided conversation_id to preserve UI threading
                title = f"{provider.title()} Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await self.conversation_integration.start_conversation(
                    user_id=user_id,
                    title=title,
                    initial_message=message,
                    provider=provider,
                    model=model,
                    conversation_id=conversation_id
                )
                new_thread = True
                conversation = [{"role": "user", "content": message}]
            else:
                # Get existing conversation context
                conversation = await self.conversation_service.get_conversation_context_for_llm(
                    conversation_id, user_id, max_tokens=4000
                )
            
            # Add system prompt if provided (even when conversation has history) to reinforce context
            if system_prompt:
                enhanced_prompt = self._enhance_system_prompt_with_intent(system_prompt, message)
                conversation = ([{
                    "role": "system",
                    "content": enhanced_prompt,
                    "timestamp": datetime.utcnow().isoformat()
                }] + conversation)
            elif len(conversation) == 0:
                # Default system prompt
                default_prompt = self._get_default_system_prompt()
                enhanced_prompt = self._enhance_system_prompt_with_intent(default_prompt, message)
                conversation.append({
                    "role": "system", 
                    "content": enhanced_prompt,
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
                response = await self._call_openai(api_key, provider_config, model, conversation)
            elif provider == "anthropic":
                response = await self._call_anthropic(api_key, provider_config, model, conversation)
            else:
                return AgentResult(success=False, error=f"Provider '{provider}' not implemented")
            
            if response["success"]:
                # Save to SQLite persistent storage
                if persistent_conversation:
                    # Continue existing conversation
                    await self.conversation_integration.continue_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        user_message=message,
                        assistant_response=response["content"],
                        provider=provider,
                        model=model,
                        usage=response.get("usage", {})
                    )
                elif new_thread:
                    # We already stored initial user message in start_conversation; add assistant reply now
                    try:
                        await self.conversation_service.add_message(
                            conversation_id=conversation_id,
                            user_id=user_id,
                            role="assistant",
                            content=response["content"],
                            metadata={
                                "provider": provider,
                                "model": model,
                                "usage": response.get("usage", {})
                            },
                            token_count=response.get("usage", {}).get("completion_tokens", 0)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant reply for new thread: {e}")
                
                # Update legacy in-memory storage (for backward compatibility)
                conversation_key = f"{user_id}:{conversation_id}"
                if conversation_key not in self.conversations:
                    self.conversations[conversation_key] = []
                
                self.conversations[conversation_key].append({
                    "role": "assistant",
                    "content": response["content"],
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return AgentResult(
                    success=True,
                    data={
                        "response": response["content"],
                        "provider": provider,
                        "model": model,
                        "conversation_id": conversation_id,
                        "message_count": len(conversation) + 1,
                        "usage": response.get("usage", {})
                    },
                    metadata={
                        "persistent": True,
                        "response_time": response.get("response_time", 0)
                    }
                )
            else:
                return AgentResult(success=False, error=response["error"])
                
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _get_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get API key from encrypted storage via settings service"""
        try:
            from ..services.settings_service import SettingsService
            settings_service = SettingsService()
            
            api_key_name = self.providers[provider]['api_key_name']
            api_key_data = await settings_service.get_user_setting(user_id, api_key_name)
            
            if api_key_data:
                # Handle both dict and string formats
                if isinstance(api_key_data, dict):
                    return api_key_data.get('api_key')
                return api_key_data
            
            # Fallback to environment variable
            env_key = f"{provider.upper()}_API_KEY"
            return os.getenv(env_key)
            
        except Exception as e:
            logger.warning(f"Failed to get API key for {provider}: {e}")
            return None
    
    async def _call_openai(self, api_key: str, provider_config: Dict, model: str, conversation: List[Dict]) -> Dict:
        """Call OpenAI API"""
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
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            start_time = datetime.now()
            response = requests.post(
                f"{provider_config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "content": content,
                    "usage": data.get("usage", {}),
                    "response_time": response_time
                }
            else:
                error_detail = response.text
                logger.error(f"OpenAI API error: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "error": f"OpenAI API error: {response.status_code} - {error_detail}"
                }
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _call_anthropic(self, api_key: str, provider_config: Dict, model: str, conversation: List[Dict]) -> Dict:
        """Call Anthropic API"""
        try:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Convert conversation format for Anthropic
            messages = []
            system_message = ""
            
            for msg in conversation:
                if msg["role"] == "system":
                    system_message = msg["content"]
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
            
            if system_message:
                payload["system"] = system_message
            
            start_time = datetime.now()
            response = requests.post(
                f"{provider_config['base_url']}/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                
                return {
                    "success": True,
                    "content": content,
                    "usage": data.get("usage", {}),
                    "response_time": response_time
                }
            else:
                # Try graceful fallback on model_not_found
                error_detail = response.text
                try:
                    err = response.json().get('error', {})
                except Exception:
                    err = {}
                if response.status_code in (400, 404) and isinstance(err, dict) and 'model' in (err.get('message', '').lower()):
                    fallback_models = provider_config.get('models', [])
                    for fb in fallback_models:
                        if fb == model:
                            continue
                        logger.warning(f"Anthropic model '{model}' not available, retrying with '{fb}'")
                        payload['model'] = fb
                        response_fb = requests.post(
                            f"{provider_config['base_url']}/messages",
                            headers=headers,
                            json=payload,
                            timeout=30
                        )
                        if response_fb.status_code == 200:
                            data = response_fb.json()
                            content = data["content"][0]["text"]
                            return {
                                "success": True,
                                "content": content,
                                "usage": data.get("usage", {}),
                                "response_time": 0
                            }
                logger.error(f"Anthropic API error: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "error": f"Anthropic API error: {response.status_code} - {error_detail}"
                }
                
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhance_system_prompt_with_intent(self, original_prompt: str, user_message: str) -> str:
        """Enhance system prompt based on detected user intent"""
        intent = self._detect_user_intent(user_message)
        
        intent_instructions = {
            'email_sender': """
CRITICAL INTENT: User asked specifically for EMAIL SENDER information.
- Focus ONLY on 'from' field
- Lead response with sender information
- Format: "📧 Gönderen: {sender_email}"
- Do NOT include subject or other fields unless specifically asked
""",
            'email_subject': """
CRITICAL INTENT: User asked specifically for EMAIL SUBJECT information.
- Focus ONLY on 'subject' field
- Lead response with subject information  
- Format: "📝 Konu: {subject_text}"
- Do NOT include sender or other fields unless specifically asked
""",
            'visual_generation': """
CRITICAL INTENT: User wants to generate VISUAL/IMAGE content.
- Focus on creative visual generation
- Extract key themes and concepts
- Provide detailed visual descriptions
""",
            'data_extraction': """
CRITICAL INTENT: User wants to extract specific DATA.
- Focus on accurate data retrieval
- Provide structured information
- Be precise and concise
""",
            'general': """
GENERAL REQUEST: Provide comprehensive assistance.
"""
        }
        
        intent_instruction = intent_instructions.get(intent, intent_instructions['general'])
        return f"{original_prompt}\n\n{intent_instruction}"
    
    def _detect_user_intent(self, user_message: str) -> str:
        """Detect user intent from message"""
        message_lower = user_message.lower()
        
        # Email-specific intents
        if any(word in message_lower for word in ['gönderen', 'sender', 'kimden', 'from']):
            return 'email_sender'
        elif any(word in message_lower for word in ['konu', 'subject', 'başlık']):
            return 'email_subject'
        elif any(word in message_lower for word in ['görsel', 'visual', 'resim', 'image', 'üret', 'oluştur']):
            return 'visual_generation'
        elif any(word in message_lower for word in ['çıkar', 'extract', 'getir', 'al', 'listele']):
            return 'data_extraction'
        else:
            return 'general'
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return """You are a helpful AI assistant integrated with MetisAgent3. You have access to various tools and can help with:

- Email management and analysis
- Visual content generation
- Data processing and extraction
- General conversation and assistance

Be concise, accurate, and helpful. When working with structured data, provide clear and organized responses."""
    
    async def _save_conversation(self, conversation_key: str, user_id: str, conversation_id: str):
        """Save conversation to persistent storage"""
        try:
            conversation_data = {
                'messages': self.conversations[conversation_key],
                'user_id': user_id,
                'conversation_id': conversation_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Store in user attributes with conversation key
            attr_name = f"conversation_{conversation_id}"
            await self.storage.set_user_attribute(
                user_id, attr_name, conversation_data, encrypt=False
            )
            
            logger.info(f"Saved conversation {conversation_id} for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save conversation: {e}")
    
    async def _get_providers(self) -> AgentResult:
        """Get available LLM providers"""
        try:
            provider_info = {}
            for provider_id, config in self.providers.items():
                provider_info[provider_id] = {
                    "name": config["name"],
                    "models": config["models"],
                    "default_model": config["default_model"]
                }
            
            return AgentResult(
                success=True,
                data={
                    "providers": provider_info,
                    "total_providers": len(self.providers)
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _get_models(self, input_data: Dict[str, Any]) -> AgentResult:
        """Get available models for a provider"""
        try:
            provider = input_data.get("provider")
            if not provider:
                return AgentResult(success=False, error="Provider is required")
            
            if provider not in self.providers:
                return AgentResult(
                    success=False,
                    error=f"Provider '{provider}' not supported"
                )
            
            config = self.providers[provider]
            return AgentResult(
                success=True,
                data={
                    "provider": provider,
                    "models": config["models"],
                    "default_model": config["default_model"]
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _get_conversation(self, input_data: Dict[str, Any]) -> AgentResult:
        """Get conversation history"""
        try:
            conversation_id = input_data.get("conversation_id", "default")
            user_id = input_data.get("user_id", "default")
            
            conversation_key = f"{user_id}:{conversation_id}"
            conversation = self.conversations.get(conversation_key, [])
            
            return AgentResult(
                success=True,
                data={
                    "conversation_id": conversation_id,
                    "messages": conversation,
                    "message_count": len(conversation)
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _clear_conversation(self, input_data: Dict[str, Any]) -> AgentResult:
        """Clear conversation history"""
        try:
            conversation_id = input_data.get("conversation_id", "default")
            user_id = input_data.get("user_id", "default")
            
            conversation_key = f"{user_id}:{conversation_id}"
            if conversation_key in self.conversations:
                del self.conversations[conversation_key]
            
            # Remove from persistent storage
            attr_name = f"conversation_{conversation_id}"
            # Note: Would need a delete_user_attribute method in storage
            
            return AgentResult(
                success=True,
                data={"conversation_id": conversation_id, "cleared": True}
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """List all conversations for a user"""
        conversations = []
        try:
            # Get conversations from memory
            for key, messages in self.conversations.items():
                if key.startswith(f"{user_id}:"):
                    conversation_id = key.split(":", 1)[1]
                    conversations.append({
                        "conversation_id": conversation_id,
                        "messages": messages,
                        "message_count": len(messages)
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            # Check storage connection
            if not self.storage:
                return HealthStatus.UNHEALTHY
            
            # Check provider configurations
            if not self.providers:
                return HealthStatus.UNHEALTHY
                
            return HealthStatus.HEALTHY
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus.UNHEALTHY
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        
        try:
            if capability in ["chat", "generate_response"]:
                if "messages" not in input_data:
                    errors.append("messages parameter is required")
                elif not isinstance(input_data["messages"], list):
                    errors.append("messages must be a list")
                elif not input_data["messages"]:
                    errors.append("messages cannot be empty")
                
                if "model" in input_data:
                    model = input_data["model"]
                    valid_models = []
                    for provider_config in self.providers.values():
                        valid_models.extend(provider_config["models"])
                    
                    if model not in valid_models:
                        errors.append(f"Invalid model: {model}. Valid models: {valid_models}")
            
            elif capability == "get_models":
                if "provider" not in input_data:
                    errors.append("provider parameter is required")
                elif input_data["provider"] not in self.providers:
                    errors.append(f"Invalid provider: {input_data['provider']}. Valid providers: {list(self.providers.keys())}")
            
            elif capability in ["get_conversation", "clear_conversation"]:
                if "user_id" not in input_data:
                    errors.append("user_id parameter is required")
            
            elif capability not in ["get_providers"]:
                errors.append(f"Unknown capability: {capability}")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    async def _get_conversation_persistent(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Get persistent conversation from SQLite"""
        try:
            conversation_id = input_data.get("conversation_id")
            if not conversation_id:
                return AgentResult(success=False, error="conversation_id is required")
            
            user_id = context.user_id
            conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
            
            if not conversation:
                return AgentResult(success=False, error="Conversation not found")
            
            messages = await self.conversation_service.get_messages(conversation_id, user_id)
            
            return AgentResult(
                success=True,
                data={
                    "conversation": {
                        "id": conversation.id,
                        "title": conversation.title,
                        "summary": conversation.summary,
                        "total_messages": conversation.total_messages,
                        "total_tokens": conversation.total_tokens,
                        "created_at": conversation.first_message_at.isoformat(),
                        "updated_at": conversation.last_message_at.isoformat(),
                        "tags": conversation.tags
                    },
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "token_count": msg.token_count
                        } for msg in messages
                    ]
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _list_conversations_persistent(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """List user's persistent conversations"""
        try:
            limit = input_data.get("limit", 50)
            offset = input_data.get("offset", 0)
            sort_by = input_data.get("sort_by", "last_message_at")
            
            user_id = context.user_id
            conversations = await self.conversation_service.list_conversations(
                user_id=user_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by
            )
            
            return AgentResult(
                success=True,
                data={
                    "conversations": [
                        {
                            "id": conv.id,
                            "title": conv.title,
                            "summary": conv.summary,
                            "total_messages": conv.total_messages,
                            "total_tokens": conv.total_tokens,
                            "created_at": conv.first_message_at.isoformat(),
                            "updated_at": conv.last_message_at.isoformat(),
                            "tags": conv.tags
                        } for conv in conversations
                    ],
                    "total": len(conversations),
                    "limit": limit,
                    "offset": offset
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _search_conversations(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Search in user's conversation history"""
        try:
            query = input_data.get("query", "")
            if not query:
                return AgentResult(success=False, error="query is required")
            
            limit = input_data.get("limit", 20)
            include_context = input_data.get("include_context", True)
            
            user_id = context.user_id
            results = await self.conversation_service.search_conversations(
                user_id=user_id,
                query=query,
                limit=limit,
                include_context=include_context
            )
            
            return AgentResult(
                success=True,
                data={
                    "results": [
                        {
                            "conversation_id": result.conversation_id,
                            "message_id": result.message_id,
                            "role": result.role,
                            "content_snippet": result.content_snippet,
                            "relevance_score": result.relevance_score,
                            "created_at": result.created_at.isoformat(),
                            "context_before": result.context_before,
                            "context_after": result.context_after
                        } for result in results
                    ],
                    "query": query,
                    "total_results": len(results)
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _delete_conversation_persistent(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Delete persistent conversation"""
        try:
            conversation_id = input_data.get("conversation_id")
            if not conversation_id:
                return AgentResult(success=False, error="conversation_id is required")
            
            user_id = context.user_id
            deleted = await self.conversation_service.delete_conversation(conversation_id, user_id)
            
            if deleted:
                return AgentResult(
                    success=True,
                    data={"conversation_id": conversation_id, "deleted": True}
                )
            else:
                return AgentResult(success=False, error="Conversation not found or already deleted")
                
        except Exception as e:
            return AgentResult(success=False, error=str(e))
