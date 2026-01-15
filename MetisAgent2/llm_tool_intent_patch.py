
# ADD TO LLMTool class in tools/llm_tool.py

def detect_user_intent(self, user_message: str) -> str:
    """Detect user intent from request"""
    message_lower = user_message.lower()
    
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

# MODIFY _chat method to detect intent and pass to tools
def _chat(self, message: str, provider: str = "openai", model: Optional[str] = None,
          system_prompt: Optional[str] = None, conversation_id: str = "default", 
          enable_tools: bool = True, user_id: str = "default", **kwargs) -> MCPToolResult:
    
    # Detect user intent
    user_intent = self.detect_user_intent(message)
    logger.info(f"INTENT DETECTION: '{message}' -> '{user_intent}'")
    
    # Enhance system prompt based on intent
    if system_prompt:
        system_prompt = self.enhance_system_prompt_with_intent(system_prompt, user_intent)
    elif enable_tools:
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        system_prompt = self.enhance_system_prompt_with_intent(enhanced_system_prompt, user_intent)
    
    # ... rest of existing _chat method ...

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
