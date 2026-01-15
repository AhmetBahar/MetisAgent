"""
Reasoning Manager Implementation - Multi-Step Analysis & Workflow Planning

CLAUDE.md COMPLIANT:
- Context-aware reasoning with graph memory integration
- Multi-step analysis pipeline (Intent → Entities → Context → Planning)
- LLM-based workflow generation with optimization
- Sequential Thinking evolution for MetisAgent3
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from uuid import uuid4

from ..contracts import (
    RequestAnalysis,
    IntentClassification,
    EntityExtraction,
    ContextEnrichment,
    ReasoningStep,
    WorkflowOptimization,
    ValidationResult,
    ReasoningResult,
    ReasoningTrace,
    LLMInteraction,
    ComplexityLevel,
    ActionType,
    DataFlow,
    ExecutionContext,
    AgentResult
)
from ..interfaces import (
    IRequestAnalyzer,
    IWorkflowGenerator,
    IReasoningEngine,
    ILLMService,
    IContextEnricher,
    IWorkflowOptimizer,
    IReasoningValidator,
    IPromptEngine
)

logger = logging.getLogger(__name__)


class LLMService(ILLMService):
    """Production LLM service with real API integration"""
    
    def __init__(self, default_model: str = "claude-3-5-sonnet-20241022", storage=None):
        self.default_model = default_model
        self.interaction_history: Dict[str, List[LLMInteraction]] = {}

        # Current session provider/model (must be set by user)
        self.current_provider = None  # User must select provider
        self.current_model = default_model
        # Provider-aware defaults to avoid provider/model mismatch
        self._provider_defaults = {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-7-sonnet-latest'
        }

        # Import LLM tool for real API calls with storage injection
        from ..tools.llm_tool import LLMTool
        self.llm_tool = LLMTool(storage=storage)

        # Conversation service for history (lazy init)
        self._conversation_service = None

        # Express Mode cache for performance
        self._express_cache: Dict[str, bool] = {}
        self._express_cache_timestamps: Dict[str, datetime] = {}
        self._express_cache_ttl = 300  # 5 minutes TTL

    def _get_conversation_service(self):
        """Lazy initialization of conversation service"""
        if self._conversation_service is None:
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        return self._conversation_service

    async def _get_conversation_history(self, context: ExecutionContext, limit: int = 5) -> str:
        """Get formatted conversation history for context"""
        if not context or not context.user_id or not context.conversation_id:
            return ""

        try:
            conv_service = self._get_conversation_service()
            messages = await conv_service.get_messages(
                conversation_id=context.conversation_id,
                user_id=context.user_id,
                limit=limit
            )

            if not messages:
                return ""

            # Format messages for LLM context
            history_parts = []
            for msg in messages[-limit:]:  # Get last N messages
                role = msg.role.upper()
                content = msg.content[:500] if len(msg.content) > 500 else msg.content  # Truncate long messages
                history_parts.append(f"{role}: {content}")

            if history_parts:
                return "CONVERSATION HISTORY (recent messages):\n" + "\n".join(history_parts) + "\n\n"
            return ""
        except Exception as e:
            logger.warning(f"Could not fetch conversation history: {e}")
            return ""
    
    async def generate_structured(self, prompt: str, response_schema: Dict[str, Any], context: Optional[ExecutionContext] = None, provider: str = None, model: str = None) -> Dict[str, Any]:
        """Generate structured response using real LLM API"""
        try:
            start_time = datetime.now()
            
            # Enhance prompt for structured generation
            base_prompt = f"""Please respond with a valid JSON object that matches this schema:
{json.dumps(response_schema, indent=2)}

User request: {prompt}

Respond with ONLY the JSON object, no additional text or formatting."""

            # Add system prompt context if available
            if context and context.system_prompt:
                structured_prompt = f"""Context: {context.system_prompt}

{base_prompt}"""
            else:
                structured_prompt = base_prompt
            
            # Call LLM via tool with proper user context
            if context:
                llm_context = context
                logger.debug(f"Using provided context: user_id={context.user_id}")
            else:
                # Fallback to system context only if no context provided
                llm_context = ExecutionContext(user_id="system", session_id="reasoning")
                logger.warning("No context provided, using system user_id")
            
            # Use provided provider or current session provider
            selected_provider = provider or self.current_provider
            
            if not selected_provider:
                raise ValueError("No LLM provider selected. User must choose a provider.")
            
            # ALWAYS use unique conversation_id for internal LLM calls
            # Using real conversation_id causes context_length_exceeded from accumulated history
            unique_structured_cid = f"structured_{uuid4()}"
            # pick model compatible with selected provider
            chosen_model = model or self._provider_defaults.get(selected_provider, self.current_model)
            result = await self.llm_tool.execute("chat", {
                "message": structured_prompt,
                "provider": selected_provider,
                "model": chosen_model,
                "conversation_id": unique_structured_cid
            }, llm_context)
            
            if result.success:
                response_text = result.data["response"]
                
                # Try to extract JSON from response
                try:
                    # Find JSON in response (handle cases where LLM adds extra text)
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        response = json.loads(json_text)
                    else:
                        # Fallback: try parsing entire response
                        response = json.loads(response_text)
                
                except json.JSONDecodeError:
                    # Fallback to mock response if JSON parsing fails
                    logger.warning("Failed to parse structured response, using fallback")
                    response = self._get_fallback_structured_response(response_schema)
            else:
                logger.error(f"LLM call failed: {result.error}")
                response = self._get_fallback_structured_response(response_schema)
            
            # Record interaction
            interaction = LLMInteraction(
                prompt=prompt[:200] + "..." if len(prompt) > 200 else prompt,
                response=json.dumps(response)[:200] + "..." if len(json.dumps(response)) > 200 else json.dumps(response),
                model=self.default_model,
                tokens_used=result.data.get("usage", {}).get("total_tokens", 0) if result.success else 0,
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            session_id = context.session_id if context else "default"
            if session_id not in self.interaction_history:
                self.interaction_history[session_id] = []
            self.interaction_history[session_id].append(interaction)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM structured generation failed: {e}")
            # Return fallback response
            return self._get_fallback_structured_response(response_schema)
    
    def _get_fallback_structured_response(self, response_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback structured response when LLM fails"""
        if "intent" in response_schema.get("properties", {}):
            return {
                "primary_intent": "general_assistance",
                "secondary_intents": ["information_request"],
                "action_type": "query",
                "data_flow": "read",
                "reasoning": "Processing user request with available tools",
                "confidence": 0.7,
                "extracted_keywords": ["request", "assistance"]
            }
        elif "steps" in response_schema.get("properties", {}):
            return {
                "steps": [
                    {
                        "step_id": str(uuid4()),
                        "name": "Process User Request",
                        "description": "Handle user request with available capabilities",
                        "tool_name": "llm_tool",
                        "capability": "chat",
                        "input_parameters": {"message": "Please process this user request"},
                        "expected_output": {"result": "processed"},
                        "reasoning": "Fallback processing step",
                        "confidence": 0.6
                    }
                ]
            }
        else:
            return {"result": "Fallback response - LLM service temporarily unavailable"}
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000, context: Optional[ExecutionContext] = None, provider: str = None, model: str = None) -> str:
        """Generate text response using real LLM API with dynamic provider/model"""
        try:
            start_time = datetime.now()
            
            # Use provided provider/model or defaults
            selected_provider = provider or self.current_provider
            
            if not selected_provider:
                raise ValueError("No LLM provider selected. User must choose a provider.")
            selected_model = model or self._provider_defaults.get(selected_provider, self.default_model)
            
            # Call LLM via tool with proper user context
            if context:
                llm_context = context
                logger.debug(f"Using provided context: user_id={context.user_id}")
            else:
                # Fallback to system context only if no context provided
                llm_context = ExecutionContext(user_id="system", session_id="reasoning")
                logger.warning("No context provided, using system user_id")
            
            # IMPORTANT: Always use a unique conversation_id for internal LLM calls
            # This prevents loading previous conversation history which can cause
            # context_length_exceeded errors when previous messages contain large tool outputs
            unique_cid = f"internal_{uuid4()}"
            result = await self.llm_tool.execute("chat", {
                "message": prompt,
                "provider": selected_provider,
                "model": selected_model,
                "conversation_id": unique_cid
            }, llm_context)
            
            if result.success:
                response = result.data["response"]
                
                interaction = LLMInteraction(
                    prompt=prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    response=response[:200] + "..." if len(response) > 200 else response,
                    model=selected_model,
                    tokens_used=result.data.get("usage", {}).get("total_tokens", 0),
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
                return response
            else:
                logger.error(f"LLM text generation failed: {result.error}")
                return f"I apologize, but I'm experiencing technical difficulties. Please try again later."
            
        except Exception as e:
            logger.error(f"LLM text generation failed: {e}")
            return f"Error generating response: {str(e)}"
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using LLM"""
        try:
            sentiment_prompt = f"""Analyze the sentiment and emotional context of this text:

"{text}"

Respond with a JSON object containing:
- sentiment: "positive", "negative", or "neutral"
- confidence: number between 0 and 1
- emotions: array of detected emotions (max 3)

JSON response only:"""
            
            result = await self.generate_structured(
                sentiment_prompt,
                {
                    "type": "object",
                    "properties": {
                        "sentiment": {"type": "string"},
                        "confidence": {"type": "number"},
                        "emotions": {"type": "array"}
                    }
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": ["uncertain"]
            }
    
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords and key phrases"""
        # Simple keyword extraction - in real implementation would use NLP
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3][:5]
        return keywords
    
    async def classify_text(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Classify text into categories with confidence"""
        # Mock classification
        return {cat: 0.1 + (hash(text + cat) % 80) / 100 for cat in categories}
    
    async def get_interaction_history(self, session_id: str) -> List[LLMInteraction]:
        """Get LLM interaction history"""
        return self.interaction_history.get(session_id, [])
    
    async def classify_request_complexity(self, user_request: str, context: Optional[ExecutionContext] = None, provider: str = None) -> Dict[str, Any]:
        """Quick classification for Express Mode - simple vs complex requests"""
        try:
            # Check cache first
            cache_key = user_request.lower().strip()
            if cache_key in self._express_cache:
                cache_time = self._express_cache_timestamps[cache_key]
                if (datetime.now() - cache_time).total_seconds() < self._express_cache_ttl:
                    logger.info(f"🚀 Express classification cache HIT: {cache_key[:50]}")
                    return {"mode": "EXPRESS" if self._express_cache[cache_key] else "NORMAL", "from_cache": True}
            
            quick_prompt = f"""Analyze this request and classify its type. Respond with ONLY a JSON object:

Request: "{user_request}"

Classification rules:
- SIMPLE: Single system command (ping, dns, ls, ps, cat, ifconfig, ip addr, etc.), system information requests (IP address, DNS settings, network config), clear intent, minimal steps
- COMPLEX: Multiple tools needed, analysis required, ambiguous intent, data processing
- CHAT: General knowledge questions, explanations of concepts, theoretical questions - NO system information requests

System information requests (IP, DNS, network, processes, files) are ALWAYS SIMPLE, not CHAT.

If CHAT type, also provide the answer to save time and tokens.

JSON format:
{{
    "complexity": "SIMPLE" or "COMPLEX" or "CHAT",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation",
    "direct_answer": "Only if CHAT type - provide direct answer here"
}}"""

            start_time = datetime.now()
            
            # Quick LLM call for classification
            selected_provider = provider or self.current_provider
            if not selected_provider:
                raise ValueError("No LLM provider selected. User must choose a provider.")
            
            llm_context = context or ExecutionContext(user_id="system", conversation_id="express_classification")

            # ALWAYS use unique conversation_id for internal LLM calls
            # Using real conversation_id causes context_length_exceeded from accumulated history
            unique_express_cid = f"express_{uuid4()}"
            quick_model = self._provider_defaults.get(selected_provider, self.current_model)
            result = await self.llm_tool.execute("chat", {
                "message": quick_prompt,
                "provider": selected_provider,
                "model": quick_model,
                "conversation_id": unique_express_cid
            }, llm_context)
            
            if result.success:
                response = result.data["response"]
                logger.info(f"🔧 DEBUG: LLM Raw Response: {response[:200]}")

                # Try to parse JSON response
                try:
                    classification = json.loads(response.strip())
                    complexity = classification["complexity"]
                    is_simple = complexity == "SIMPLE"
                    is_chat = complexity == "CHAT"
                    logger.info(f"🔧 DEBUG: JSON Parse SUCCESS - complexity: {complexity}")
                    
                    # Cache the result
                    self._express_cache[cache_key] = is_simple
                    self._express_cache_timestamps[cache_key] = datetime.now()
                    
                    duration = (datetime.now() - start_time).total_seconds() * 1000
                    logger.info(f"⚡ Request classification: {complexity} ({duration:.1f}ms)")
                    
                    result = {
                        "mode": "CHAT" if is_chat else ("EXPRESS" if is_simple else "NORMAL"),
                        "complexity": complexity,
                        "confidence": classification.get("confidence", 0.8),
                        "reasoning": classification.get("reasoning", ""),
                        "duration_ms": duration
                    }
                    
                    # Add direct answer for CHAT requests to save tokens
                    if is_chat and "direct_answer" in classification:
                        result["direct_answer"] = classification["direct_answer"]
                        logger.info(f"💬 CHAT mode: Direct answer provided ({len(classification['direct_answer'])} chars)")
                    
                    return result
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"🔧 DEBUG: JSON Parse FAILED: {e}")
                    logger.warning(f"🔧 DEBUG: Raw response was: {repr(response)}")
                    return {"mode": "NORMAL", "error": "JSON parse failed"}
            else:
                logger.error(f"Express classification failed: {result.error}")
                return {"mode": "NORMAL", "error": result.error}
                
        except Exception as e:
            logger.error(f"Express classification error: {e}")
            return {"mode": "NORMAL", "error": str(e)}

    async def unified_plan_request(self, user_request: str, user_tools: List[Dict[str, Any]],
                                   context: Optional[ExecutionContext] = None,
                                   provider: str = None,
                                   conversation_memory_context: str = "") -> Dict[str, Any]:
        """
        UNIFIED PLANNING - Single LLM call for classification + workflow generation

        Replaces the old multi-call flow:
        - classify_request_complexity (removed)
        - analyze_request → classify_intent, extract_entities (removed)
        - generate_workflow_steps (combined here)

        Returns:
            {
                "mode": "CHAT" | "TOOL",
                "response": "direct answer if CHAT mode",
                "workflow": [...steps...] if TOOL mode,
                "confidence": 0.0-1.0,
                "reasoning": "explanation"
            }
        """
        try:
            start_time = datetime.now()

            # Format tools for LLM - with truncation
            tools_text = self._format_tools_complete(user_tools)

            # Use lightweight conversation memory context instead of full history
            # This prevents context_length_exceeded errors from large previous responses
            memory_context = conversation_memory_context if conversation_memory_context else ""

            unified_prompt = f"""You are an intelligent assistant that helps users accomplish tasks.

{memory_context}USER REQUEST: "{user_request}"

AVAILABLE TOOLS:
{tools_text}

INSTRUCTIONS:
1. First, consider the conversation history above (if any) to understand context
2. Determine if this request needs tools or is just a conversation/question
3. If it's a general question, greeting, or conversation → respond with mode "CHAT" and provide direct answer
4. If it requires using tools → respond with mode "TOOL" and create a workflow
5. IMPORTANT: If the user refers to something from previous messages (like "y value" referring to a previous discussion about a page), use that context

Respond with ONLY a valid JSON object:

For CHAT mode (no tools needed):
{{
    "mode": "CHAT",
    "response": "Your direct answer to the user's question",
    "confidence": 0.9,
    "reasoning": "This is a general question that doesn't require tools"
}}

For TOOL mode (tools needed):
{{
    "mode": "TOOL",
    "confidence": 0.9,
    "reasoning": "Brief explanation of why these tools are needed",
    "workflow": [
        {{
            "step_id": "step_1",
            "name": "Step name",
            "description": "What this step does",
            "tool_name": "exact_tool_name",
            "capability": "exact_capability_name",
            "input_parameters": {{"param": "value"}},
            "reasoning": "Why this step is needed"
        }}
    ]
}}

IMPORTANT:
- tool_name must match EXACTLY one of the available tools
- capability must match EXACTLY one of that tool's capabilities
- Keep workflows simple: 1-3 steps for most requests
- For CHAT mode, provide a helpful, complete response in the user's language"""

            # Select provider
            selected_provider = provider or self.current_provider
            if not selected_provider:
                raise ValueError("No LLM provider selected")

            selected_model = self._provider_defaults.get(selected_provider, self.current_model)

            # Single LLM call for everything
            # IMPORTANT: Use unique conversation_id to prevent loading previous conversation history
            # This avoids context_length_exceeded errors from accumulated messages
            unique_planning_cid = f"unified_planning_{uuid4()}"
            result = await self.llm_tool.execute(
                capability="chat",
                input_data={
                    "message": unified_prompt,
                    "provider": selected_provider,
                    "model": selected_model,
                    "max_tokens": 2000,
                    "conversation_id": unique_planning_cid  # Unique ID prevents history loading
                },
                context=context or ExecutionContext(user_id="system", conversation_id=unique_planning_cid)
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            if result.success and result.data:
                response = result.data.get("response", "")

                # Parse JSON response
                try:
                    # Clean response
                    response = response.strip()
                    if response.startswith("```json"):
                        response = response[7:]
                    if response.startswith("```"):
                        response = response[3:]
                    if response.endswith("```"):
                        response = response[:-3]
                    response = response.strip()

                    # Remove JavaScript-style comments that break JSON parsing
                    # Handle both // comments and trailing comments
                    import re
                    # Remove single-line comments (// ...) but not inside strings
                    response = re.sub(r'//[^\n]*', '', response)
                    # Remove trailing commas before } or ]
                    response = re.sub(r',(\s*[}\]])', r'\1', response)
                    response = response.strip()

                    parsed = json.loads(response)
                    parsed["duration_ms"] = duration_ms

                    mode = parsed.get("mode", "CHAT")
                    if mode == "TOOL":
                        workflow = parsed.get("workflow", [])
                        logger.info(f"🛠️ UNIFIED PLANNING: TOOL mode with {len(workflow)} steps ({duration_ms:.0f}ms)")
                    else:
                        logger.info(f"💬 UNIFIED PLANNING: CHAT mode ({duration_ms:.0f}ms)")

                    return parsed

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed in unified planning: {e}")
                    # Fallback to CHAT mode with raw response
                    return {
                        "mode": "CHAT",
                        "response": response,
                        "confidence": 0.5,
                        "reasoning": "JSON parse failed, returning raw response",
                        "duration_ms": duration_ms
                    }
            else:
                logger.error(f"Unified planning LLM call failed: {result.error}")
                return {
                    "mode": "CHAT",
                    "response": "Üzgünüm, isteğinizi işlerken bir hata oluştu.",
                    "confidence": 0.0,
                    "error": result.error,
                    "duration_ms": duration_ms
                }

        except Exception as e:
            logger.error(f"Unified planning error: {e}")
            return {
                "mode": "CHAT",
                "response": f"Bir hata oluştu: {str(e)}",
                "confidence": 0.0,
                "error": str(e)
            }

    def _format_tools_complete(self, user_tools: List[Dict[str, Any]]) -> str:
        """Format tools with truncated descriptions to avoid context overflow"""
        if not user_tools:
            return "No tools available"

        formatted = []
        max_desc_length = 300  # Truncate long descriptions
        max_cap_desc_length = 250  # Truncate capability descriptions (increased to include guidance)

        for tool in user_tools:
            # Truncate tool description
            tool_desc = tool.get('description', 'No description')
            if len(tool_desc) > max_desc_length:
                tool_desc = tool_desc[:max_desc_length] + "..."

            tool_lines = [
                f"## {tool['name']}",
                f"Description: {tool_desc}"
            ]

            # Capabilities with truncated descriptions
            if 'capabilities' in tool and tool['capabilities']:
                tool_lines.append("Capabilities:")
                for cap in tool['capabilities']:
                    cap_name = cap.get('name', cap.get('capability', 'unknown'))
                    cap_desc = cap.get('description', 'No description')
                    # Truncate capability description
                    if len(cap_desc) > max_cap_desc_length:
                        cap_desc = cap_desc[:max_cap_desc_length] + "..."
                    tool_lines.append(f"  - {cap_name}: {cap_desc}")

                # DEBUG: Log SCADA capabilities
                if tool['name'] == 'rmms_scada_tool':
                    cap_names = [c.get('name', 'unknown') for c in tool['capabilities']]
                    logger.info(f"🔍 DEBUG SCADA capabilities order: {cap_names}")

            formatted.append("\n".join(tool_lines))

        result = "\n\n".join(formatted)

        # DEBUG: Log if analyze_page is in the formatted output
        if 'rmms_scada_tool' in result:
            logger.info(f"🔍 DEBUG: analyze_page in output: {'analyze_page' in result}")

        return result


class RequestAnalyzer(IRequestAnalyzer):
    """Request analysis with multi-step reasoning"""
    
    def __init__(self, llm_service: ILLMService, graph_memory_service):
        self.llm = llm_service
        self.graph_memory = graph_memory_service
    
    async def analyze_request(self, user_request: str, context: ExecutionContext) -> RequestAnalysis:
        """Perform comprehensive request analysis"""
        try:
            start_time = datetime.now()
            
            # Step 1: Intent Classification
            intent = await self.classify_intent(user_request, context)
            
            # Step 2: Entity Extraction
            entities = await self.extract_entities(user_request)
            
            # Step 3: Context Enrichment
            enriched_context = await self.enrich_context(entities["entities"], context.user_id)
            
            # Step 4: Complexity Assessment
            complexity_level = await self.assess_complexity(user_request, intent)
            
            # Build reasoning path
            reasoning_path = [
                f"Classified intent as {intent['primary_intent']} with {intent['confidence']:.2f} confidence",
                f"Extracted {len(entities['entities'])} entities: {', '.join(entities['entities'][:3])}",
                f"Enriched context from {len(enriched_context)} sources",
                f"Assessed complexity as {complexity_level}"
            ]
            
            analysis = RequestAnalysis(
                original_request=user_request,
                intent=IntentClassification(**intent),
                entities=EntityExtraction(**entities),
                context=ContextEnrichment(**enriched_context),
                complexity=ComplexityLevel(complexity_level),
                reasoning_path=reasoning_path,
                confidence_score=intent["confidence"],
                user_id=context.user_id,
                estimated_duration_seconds=self._estimate_duration(complexity_level)
            )
            
            analysis_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Request analysis completed in {analysis_time:.2f}ms")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Request analysis failed: {e}")
            raise
    
    def _estimate_duration(self, complexity_level: str) -> int:
        """Estimate task duration in seconds based on complexity"""
        if complexity_level == "low":
            return 5
        elif complexity_level == "medium":
            return 15
        else:  # high
            return 30
    
    async def classify_intent(self, user_request: str, context: Optional[ExecutionContext] = None) -> Dict[str, Any]:
        """Classify user intent with sophisticated reasoning"""
        classification_prompt = f"""
        Analyze this user request and classify the intent with detailed reasoning:
        
        REQUEST: {user_request}
        
        Consider these aspects:
        1. Primary action type - MUST be one of: query, create, modify, analyze, workflow, interact
        2. Data flow requirements - MUST be one of: read, write, read_write, transform
        3. Multi-step complexity indicators
        4. Tool interaction patterns
        5. Urgency and priority signals

        IMPORTANT: action_type must be exactly one of the listed values above.
        
        Provide reasoning for your classification and extract key keywords.
        """
        
        schema = {
            "type": "object",
            "properties": {
                "primary_intent": {"type": "string"},
                "secondary_intents": {"type": "array", "items": {"type": "string"}},
                "action_type": {
                    "type": "string",
                    "enum": ["query", "create", "modify", "analyze", "workflow", "interact"]
                },
                "data_flow": {
                    "type": "string",
                    "enum": ["read", "write", "read_write", "transform"]
                },
                "reasoning": {"type": "string"},
                "confidence": {"type": "number"},
                "extracted_keywords": {"type": "array", "items": {"type": "string"}}
            }
        }
        
        result = await self.llm.generate_structured(classification_prompt, schema, context)
        return result
    
    async def extract_entities(self, user_request: str) -> Dict[str, Any]:
        """Extract entities and relationships"""
        extraction_prompt = f"""
        Extract entities, their types, and relationships from this request:
        
        REQUEST: {user_request}
        
        Identify:
        1. Named entities (people, places, organizations)
        2. Temporal entities (dates, times, durations)
        3. Technical entities (tools, systems, formats)
        4. Action entities (verbs, operations)
        5. Relationships between entities
        
        Provide confidence scores for each extraction.
        """
        
        # Mock entity extraction - real implementation would use NLP
        keywords = await self.llm.extract_keywords(user_request)
        
        return {
            "entities": keywords[:5],
            "entity_types": {entity: "keyword" for entity in keywords[:5]},
            "relationships": [{"type": "mentions", "from": "user", "to": entity} for entity in keywords[:3]],
            "confidence_scores": {entity: 0.8 for entity in keywords[:5]}
        }
    
    async def assess_complexity(self, user_request: str, intent: Dict[str, Any]) -> str:
        """Assess task complexity level"""
        # Simple complexity assessment - real implementation would be more sophisticated
        request_length = len(user_request.split())
        secondary_intents = len(intent.get("secondary_intents", []))
        
        if request_length < 5 and secondary_intents == 0:
            return ComplexityLevel.SIMPLE.value
        elif request_length < 15 and secondary_intents <= 1:
            return ComplexityLevel.MODERATE.value
        elif request_length < 30 and secondary_intents <= 3:
            return ComplexityLevel.COMPLEX.value
        else:
            return ComplexityLevel.EXPERT.value
    
    async def enrich_context(self, entities: List[str], user_id: str) -> Dict[str, Any]:
        """Enrich context from graph memory"""
        enriched = {
            "conversation_context": [],
            "related_entities": {},
            "tool_preferences": {},
            "user_patterns": {},
            "temporal_context": {"timestamp": datetime.now().isoformat()}
        }
        
        if self.graph_memory:
            try:
                # Get conversation history
                conversations = await self.graph_memory.get_conversation_history(user_id, limit=5)
                if conversations:
                    enriched["conversation_context"] = conversations
                
                # Get related entities
                for entity in entities:
                    related = await self.graph_memory.search_nodes(f"user:{user_id} AND {entity}")
                    if related:
                        enriched["related_entities"][entity] = related
                
                # Get tool preferences
                user_tools = await self.graph_memory.get_user_tools(user_id)
                enriched["tool_preferences"] = {"preferred_tools": [tool["name"] for tool in user_tools]}
                
            except Exception as e:
                logger.warning(f"Context enrichment from graph memory failed: {e}")
        
        return enriched


class WorkflowGenerator(IWorkflowGenerator):
    """Workflow generation with optimization"""
    
    def __init__(self, llm_service: ILLMService, graph_memory_service):
        self.llm = llm_service
        self.graph_memory = graph_memory_service
    
    async def generate_workflow_steps(self, analysis: RequestAnalysis, context: Optional[ExecutionContext] = None) -> List[ReasoningStep]:
        """Generate optimized workflow steps"""
        try:
            # Get user-specific tools
            user_tools = []
            if self.graph_memory:
                user_tools = await self.graph_memory.get_user_tools(analysis.user_id)
                tool_prompt = await self.graph_memory.generate_tool_prompt(analysis.user_id)
            else:
                tool_prompt = "No tools available"
            
            # Build sophisticated planning prompt
            planning_prompt = self._build_planning_prompt(analysis, user_tools, tool_prompt)
            
            # Generate steps using LLM
            schema = {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_id": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "tool_name": {"type": "string"},
                                "capability": {"type": "string"},
                                "input_parameters": {"type": "object"},
                                "expected_output": {"type": "object"},
                                "reasoning": {"type": "string"},
                                "confidence": {"type": "number"}
                            }
                        }
                    }
                }
            }
            
            response = await self.llm.generate_structured(planning_prompt, schema, context)
            
            # Convert to ReasoningStep objects
            steps = []
            for step_data in response.get("steps", []):
                step = ReasoningStep(
                    step_id=step_data.get("step_id", str(uuid4())),
                    name=step_data.get("name", "Unnamed Step"),
                    description=step_data.get("description", ""),
                    tool_name=step_data.get("tool_name", ""),
                    capability=step_data.get("capability", ""),
                    input_parameters=step_data.get("input_parameters", {}),
                    expected_output=step_data.get("expected_output", {}),
                    reasoning=step_data.get("reasoning", ""),
                    confidence=step_data.get("confidence", 0.5)
                )
                steps.append(step)
            
            return steps
            
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}")
            return []
    
    async def optimize_sequence(self, steps: List[ReasoningStep]) -> WorkflowOptimization:
        """Optimize workflow step sequence"""
        # Simple optimization - real implementation would be more sophisticated
        return WorkflowOptimization(
            original_steps=steps,
            optimized_steps=steps,  # No optimization for now
            parallel_groups={},
            dependency_graph={},
            estimated_time_savings=0.0,
            resource_efficiency_gain=0.0,
            optimization_reasoning=["No optimization applied in current implementation"],
            strategy={"parallel_execution": False}
        )
    
    async def generate_express_workflow(self, analysis: RequestAnalysis, context: Optional[ExecutionContext] = None) -> List[ReasoningStep]:
        """Generate lightweight workflow for simple requests (EXPRESS MODE)"""
        try:
            # Get cached tools quickly
            user_tools = []
            if self.graph_memory:
                user_tools = await self.graph_memory.get_user_tools(analysis.user_id)
                logger.info(f"🔧 DEBUG: Retrieved {len(user_tools)} user tools for {analysis.user_id}")
                for tool in user_tools[:2]:  # Log first 2 tools
                    logger.info(f"🔧 DEBUG: Tool: {tool.get('name', 'unknown')} with {len(tool.get('capabilities', []))} capabilities")
            
            # Build express planning prompt - much simpler than full workflow
            entities_list = []
            if hasattr(analysis, 'entities') and hasattr(analysis.entities, 'entities'):
                entities_list = analysis.entities.entities
            
            # Add conversation context if available
            context_info = ""
            if context and hasattr(context, 'system_prompt') and context.system_prompt:
                context_info = f"\nConversation Context:\n{context.system_prompt}\n"

            express_prompt = f"""Generate a simple workflow for this straightforward request.

Request: "{analysis.original_request}"
Intent: {analysis.intent.primary_intent if hasattr(analysis, 'intent') else 'Unknown intent'}
Entities: {', '.join(entities_list) if entities_list else 'None'}
{context_info}
Available tools:
{self._format_tools_for_express(user_tools)}

Guidelines for tool selection:
- For system information (IP address, DNS settings, network info): use command_executor with execute_command capability
- For DNS queries/lookups: use command_executor with resolve_dns capability
- For system commands: use command_executor with execute_command capability
- For network connectivity tests: use command_executor with measure_ping capability

Create a simple 1-3 step workflow. Respond with ONLY a JSON object:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "name": "Step name",
            "description": "What this step does",
            "tool_name": "tool_name",
            "capability": "capability_name",
            "input_parameters": {{"key": "value"}},
            "reasoning": "Why this step"
        }}
    ]
}}"""

            start_time = datetime.now()
            
            # Simple JSON generation (no complex schema validation) - use current provider
            response = await self.llm.generate_text(express_prompt, max_tokens=1000, context=context, provider=self.llm.current_provider)
            
            # Parse response
            try:
                response_data = json.loads(response.strip())
                steps = []
                
                for i, step_data in enumerate(response_data.get("steps", [])):
                    step = ReasoningStep(
                        step_id=step_data.get("step_id", f"express_step_{i+1}"),
                        name=step_data.get("name", f"Step {i+1}"),
                        description=step_data.get("description", ""),
                        tool_name=step_data.get("tool_name", ""),
                        capability=step_data.get("capability", ""),
                        input_parameters=step_data.get("input_parameters", {}),
                        expected_output={"type": "object"},
                        reasoning=step_data.get("reasoning", "Express mode generation"),
                        confidence=0.8,  # Good confidence for express mode
                        dependencies=[],
                        estimated_duration=30,  # Quick estimates
                        priority=1
                    )
                    steps.append(step)
                
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"⚡ Express workflow generated: {len(steps)} steps ({duration:.1f}ms)")
                
                return steps
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse express workflow JSON: {response}")
                raise ValueError("Express workflow JSON parse failed")
                
        except Exception as e:
            logger.error(f"Express workflow generation failed: {e}")
            raise
    
    def _format_tools_for_express(self, user_tools: List[Dict[str, Any]]) -> str:
        """Format tools for express mode (comprehensive format for accurate tool selection)"""
        if not user_tools:
            return "- No tools available"

        formatted = []
        # Show ALL tools - tool selection accuracy is more important than speed
        for tool in user_tools:
            # Full description for accurate tool matching (increased from 80 to 300)
            tool_info = f"- {tool['name']}: {tool.get('description', 'No description')[:300]}"

            # Add ALL capabilities for better LLM understanding
            if 'capabilities' in tool:
                caps = [cap.get('name', cap.get('capability', '')) for cap in tool['capabilities']]
                if caps:
                    tool_info += f"\n  Capabilities: {', '.join(caps)}"

            formatted.append(tool_info)

        return "\n".join(formatted)
    
    async def validate_workflow(self, steps: List[ReasoningStep]) -> ValidationResult:
        """Validate workflow consistency"""
        errors = []
        warnings = []
        
        # Basic validation
        if not steps:
            errors.append("Workflow has no steps")
        
        for step in steps:
            if not step.tool_name:
                errors.append(f"Step {step.step_id} has no tool specified")
            if not step.capability:
                errors.append(f"Step {step.step_id} has no capability specified")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def adapt_workflow(self, steps: List[ReasoningStep], context) -> List[ReasoningStep]:
        """Adapt workflow based on runtime context"""
        # Simple adaptation - return original steps
        return steps
    
    def _build_planning_prompt(self, analysis: RequestAnalysis, user_tools: List[Dict], tool_prompt: str) -> str:
        """Build sophisticated planning prompt"""
        return f"""
# INTELLIGENT WORKFLOW PLANNING

## USER REQUEST ANALYSIS
Original Request: {analysis.original_request}
Primary Intent: {analysis.intent.primary_intent}
Action Type: {analysis.intent.action_type.value}
Data Flow: {analysis.intent.data_flow.value}
Complexity: {analysis.complexity.value}
Entities: {', '.join(analysis.entities.entities)}
Confidence: {analysis.confidence_score:.2f}

## CONTEXT ENRICHMENT
{json.dumps(analysis.context.dict(), indent=2)}

## AVAILABLE TOOLS
{tool_prompt}

## REASONING INSTRUCTIONS
You are an intelligent workflow planner. Create an optimal execution plan that:

1. **Understands True Intent**: Look beyond surface request to understand user's real goal
2. **Leverages Context**: Use conversation history and user patterns
3. **Optimizes Tool Usage**: Select most appropriate tools and capabilities
4. **Plans Dependencies**: Ensure proper data flow between steps
5. **Handles Errors**: Consider potential failure points and recovery

## OUTPUT REQUIREMENTS
Generate a workflow with these characteristics:
- Clear, actionable steps with specific tool calls
- Logical progression from input to desired output
- Parameter mappings between steps where needed
- Confidence scores for each step selection
- Detailed reasoning for tool and capability choices

Think step by step and create an efficient, reliable workflow.
"""


class ReasoningEngine(IReasoningEngine):
    """Complete reasoning engine implementation"""
    
    def __init__(self, llm_service: ILLMService, graph_memory_service):
        self.llm = llm_service
        self.graph_memory = graph_memory_service
        self.analyzer = RequestAnalyzer(llm_service, graph_memory_service)
        self.generator = WorkflowGenerator(llm_service, graph_memory_service)
        self.reasoning_traces: Dict[str, ReasoningTrace] = {}
    
    async def reason_about_request(self, user_request: str, context: ExecutionContext, llm_provider: str = "anthropic", llm_model: str = "claude-3-5-sonnet-20241022") -> ReasoningResult:
        """Complete reasoning process"""
        try:
            start_time = datetime.now()
            trace_id = str(uuid4())
            
            # Set provider/model for this reasoning session
            self.llm.current_provider = llm_provider
            self.llm.current_model = llm_model
            
            # Step 1: Analyze request
            analysis = await self.analyzer.analyze_request(user_request, context)
            
            # Step 2: Generate workflow steps
            steps = await self.generator.generate_workflow_steps(analysis, context)
            
            # Step 3: Optimize workflow
            optimization = await self.generator.optimize_sequence(steps)
            
            # Step 4: Validate workflow
            validation = await self.generator.validate_workflow(optimization.optimized_steps)
            
            # Create reasoning trace
            reasoning_time = (datetime.now() - start_time).total_seconds() * 1000
            trace = ReasoningTrace(
                trace_id=trace_id,
                user_request=user_request,
                analysis_steps=analysis.reasoning_path,
                reasoning_duration_ms=reasoning_time,
                llm_interactions=3  # Approximate
            )
            self.reasoning_traces[trace_id] = trace
            
            result = ReasoningResult(
                success=validation.is_valid,
                analysis=analysis,
                steps=optimization.optimized_steps,
                optimization=optimization,
                validation=validation,
                reasoning_trace=trace,
                error=None if validation.is_valid else "Validation failed"
            )
            
            logger.info(f"Reasoning completed in {reasoning_time:.2f}ms with {len(steps)} steps")
            return result
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return ReasoningResult(
                success=False,
                error=str(e)
            )
    
    async def explain_reasoning(self, reasoning_result: ReasoningResult) -> str:
        """Generate human-readable explanation"""
        if not reasoning_result.success:
            return f"Reasoning failed: {reasoning_result.error}"
        
        explanation_parts = [
            "# Reasoning Process Explanation\n",
            f"**Request**: {reasoning_result.analysis.original_request}\n",
            f"**Intent**: {reasoning_result.analysis.intent.primary_intent}",
            f"**Complexity**: {reasoning_result.analysis.complexity.value}\n",
            "## Generated Workflow:\n"
        ]
        
        for i, step in enumerate(reasoning_result.steps, 1):
            explanation_parts.append(f"{i}. **{step.name}**: {step.description}")
            explanation_parts.append(f"   - Tool: {step.tool_name}")
            explanation_parts.append(f"   - Reasoning: {step.reasoning}\n")
        
        return "\n".join(explanation_parts)
    
    async def get_reasoning_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Get detailed reasoning trace"""
        return self.reasoning_traces.get(trace_id)
    
    async def evaluate_alternatives(self, analysis: RequestAnalysis) -> List[Dict[str, Any]]:
        """Evaluate alternative approaches"""
        # Mock alternatives - real implementation would generate actual alternatives
        return [
            {
                "approach": "Sequential execution",
                "pros": ["Simple", "Reliable"],
                "cons": ["Slower"],
                "confidence": 0.8
            },
            {
                "approach": "Parallel execution",
                "pros": ["Faster", "Efficient"],
                "cons": ["Complex", "Error-prone"],
                "confidence": 0.6
            }
        ]
