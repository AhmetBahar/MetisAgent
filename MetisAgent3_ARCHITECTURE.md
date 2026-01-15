# MetisAgent3 - Production-Ready Architecture Blueprint

## 🎯 DESIGN PRINCIPLES

### **1. CLAUDE.md COMPLIANCE (MANDATORY)**
- **NO Quick Fixes**: Every solution must be architectural, not band-aid
- **NO Hard-coded Rules**: Pure LLM-driven decision making only
- **NO Command Injection**: All user inputs sanitized and validated
- **NO Print Debugging**: Structured logging only (structlog)
- **NO Spagetti Code**: Clear separation of concerns, SOLID principles
- **NO Comments Unless Asked**: Self-documenting code with type hints
- **Atomized Components**: Working parts never broken during development
- **Security First**: All credentials encrypted, no secrets in logs

### **2. CONTRACT-FIRST DEVELOPMENT**
- **Strong Data Contracts**: Pydantic models for all data exchange
- **API Versioning**: Backward compatibility guarantees
- **Schema Validation**: Runtime type checking
- **Documentation**: Auto-generated from schemas

### **3. FAULT-TOLERANT DESIGN**
- **Circuit Breakers**: Prevent cascading failures
- **Graceful Degradation**: System works even with tool failures
- **Retry Mechanisms**: Smart exponential backoff
- **Fallback Strategies**: Alternative execution paths

### **4. PLUGIN-FIRST ARCHITECTURE**
- **Hot-Pluggable Tools**: Add/remove tools without restart
- **Isolated Execution**: Tool failures don't crash system
- **Standardized Interfaces**: All tools implement same contract
- **Dynamic Discovery**: Auto-registration and capability detection

## 🏗️ CORE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│                      API GATEWAY & ROUTING                      │
├─────────────────────────────────────────────────────────────────┤
│                     WORKFLOW ENGINE CORE                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ PLAN GENERATOR  │ │ EXECUTOR ENGINE │ │ RESULT PROCESSOR│    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                        SERVICE LAYER                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ TOOL REGISTRY   │ │ GRAPH MEMORY    │ │ AUTH SERVICE    │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                         PLUGIN LAYER                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ MCP TOOLS       │ │ NATIVE TOOLS    │ │ EXTERNAL APIs   │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                       INFRASTRUCTURE                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ EVENT BUS       │ │ MONITORING      │ │ PERSISTENT STORAGE│   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 DATA CONTRACTS

### **Core Types**

```python
from enum import Enum
from typing import Generic, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# Base Types
class AgentResult(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time_ms: Optional[float] = None

class ToolCapability(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    examples: List[Dict[str, Any]] = []
    version: str = "1.0.0"

class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    capability_name: str
    input_data: Dict[str, Any]
    depends_on: List[str] = []
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 3
```

### **Domain Models**

```python
# Gmail Domain
class EmailAddress(BaseModel):
    email: str
    name: Optional[str] = None

class EmailMessage(BaseModel):
    id: str
    thread_id: str
    from_addr: EmailAddress
    to_addrs: List[EmailAddress]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    date: datetime
    snippet: str
    labels: List[str] = []

class EmailQuery(BaseModel):
    query: str = ""
    max_results: int = 10
    include_spam_trash: bool = False

# Visual Creation Domain  
class ImageGenRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"
    provider: str = "openai"
    style: Optional[str] = None

class GeneratedImage(BaseModel):
    id: str
    url: str
    local_path: Optional[str] = None
    prompt: str
    size: str
    provider: str
    created_at: datetime
    metadata: Dict[str, Any] = {}
```

## 🔧 PLUGIN SYSTEM DESIGN

### **Tool Interface Contract**

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """All tools must implement this interface"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier"""
        pass
    
    @property  
    @abstractmethod
    def version(self) -> str:
        """Tool version for compatibility"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        """List all capabilities this tool provides"""
        pass
    
    @abstractmethod
    async def execute(self, capability: str, input_data: Dict[str, Any]) -> AgentResult:
        """Execute a specific capability"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Return True if tool is healthy"""
        pass

class MCPTool(BaseTool):
    """MCP-based tool implementation"""
    
    def __init__(self, mcp_server_path: str):
        self.server_path = mcp_server_path
        self.process = None
    
    async def start_server(self):
        """Start MCP server process"""
        pass
    
    async def call_mcp(self, method: str, params: Dict) -> Dict:
        """Make JSON-RPC call to MCP server"""
        pass

class NativeTool(BaseTool):
    """Python-native tool implementation"""
    
    def __init__(self):
        self.capabilities_registry = {}
    
    def register_capability(self, name: str, func: callable, schema: ToolCapability):
        """Register a new capability"""
        self.capabilities_registry[name] = (func, schema)
```

### **Dynamic Tool Loading**

```python
class ToolManager:
    """Manages plugin lifecycle"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_health: Dict[str, bool] = {}
    
    async def load_tool(self, tool_path: str) -> bool:
        """Dynamically load a tool"""
        try:
            # Auto-detect tool type (MCP/Native/External)
            tool = await self._instantiate_tool(tool_path)
            
            # Validate capabilities
            capabilities = tool.get_capabilities()
            self._validate_capabilities(capabilities)
            
            # Health check
            if not tool.health_check():
                raise Exception(f"Tool {tool.name} failed health check")
            
            self.tools[tool.name] = tool
            self.tool_health[tool.name] = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load tool {tool_path}: {e}")
            return False
    
    async def execute_capability(self, tool_name: str, capability: str, input_data: Dict) -> AgentResult:
        """Execute tool capability with circuit breaker"""
        
        if not self.tool_health.get(tool_name, False):
            return AgentResult(success=False, error=f"Tool {tool_name} is unhealthy")
        
        try:
            tool = self.tools[tool_name]
            result = await tool.execute(capability, input_data)
            
            # Update health status based on result
            self.tool_health[tool_name] = result.success
            return result
            
        except Exception as e:
            self.tool_health[tool_name] = False
            return AgentResult(success=False, error=str(e))
```

## 🧠 REASONING ENGINE & WORKFLOW INTELLIGENCE

### **Multi-Step Reasoning Architecture**

The reasoning engine provides intelligent analysis and planning capabilities, evolved from MetisAgent2's Sequential Thinking system.

```python
class ReasoningEngine:
    """Multi-step reasoning and complex problem analysis"""
    
    def __init__(self, llm_service: LLMService, graph_memory: GraphMemoryService):
        self.llm = llm_service
        self.graph_memory = graph_memory
        self.reasoning_context = {}
    
    async def analyze_request(self, user_request: str, context: ExecutionContext) -> RequestAnalysis:
        """Deep analysis of user request with context"""
        
        # Step 1: Intent Classification
        intent = await self._classify_intent(user_request)
        
        # Step 2: Entity Extraction
        entities = await self._extract_entities(user_request)
        
        # Step 3: Context Enrichment from Graph Memory
        enriched_context = await self._enrich_context(entities, context.user_id)
        
        # Step 4: Complexity Assessment
        complexity = await self._assess_complexity(user_request, intent)
        
        return RequestAnalysis(
            intent=intent,
            entities=entities,
            context=enriched_context,
            complexity=complexity,
            reasoning_path=self._get_reasoning_trace()
        )
    
    async def generate_workflow_steps(self, analysis: RequestAnalysis) -> List[WorkflowStep]:
        """Generate optimized workflow steps from analysis"""
        
        # Get user-specific tool capabilities from graph memory
        user_tools = await self.graph_memory.get_user_tools(analysis.user_id)
        tool_prompt = await self.graph_memory.generate_tool_prompt(analysis.user_id)
        
        # Multi-step reasoning for workflow planning
        reasoning_prompt = self._build_reasoning_prompt(analysis, user_tools, tool_prompt)
        
        # LLM-based step generation with reasoning
        steps_response = await self.llm.generate_structured(
            prompt=reasoning_prompt,
            response_schema=WorkflowStepsSchema
        )
        
        # Validate and optimize steps
        validated_steps = await self._validate_steps(steps_response.steps, user_tools)
        optimized_steps = await self._optimize_sequence(validated_steps)
        
        return optimized_steps
    
    async def optimize_sequence(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Optimize step execution order and dependencies"""
        
        # Dependency analysis
        dependencies = await self._analyze_dependencies(steps)
        
        # Parallel execution opportunities
        parallel_groups = await self._identify_parallel_steps(steps, dependencies)
        
        # Resource optimization
        resource_optimized = await self._optimize_resources(parallel_groups)
        
        return resource_optimized
    
    async def _classify_intent(self, user_request: str) -> IntentClassification:
        """Classify user intent with reasoning"""
        
        classification_prompt = f"""
        Analyze this user request and classify the intent:
        
        REQUEST: {user_request}
        
        Consider:
        1. Primary action type (query, creation, modification, analysis)
        2. Data flow requirements (read, write, transform)
        3. Multi-step complexity indicators
        4. Tool interaction patterns
        
        Provide reasoning for your classification.
        """
        
        response = await self.llm.generate_structured(
            prompt=classification_prompt,
            response_schema=IntentClassificationSchema
        )
        
        return response
    
    async def _enrich_context(self, entities: List[str], user_id: str) -> Dict[str, Any]:
        """Enrich context from graph memory and conversation history"""
        
        enriched = {}
        
        # Get related entities from graph memory
        for entity in entities:
            related_info = await self.graph_memory.search_nodes(
                f"user:{user_id} AND entity:{entity}"
            )
            if related_info:
                enriched[entity] = related_info
        
        # Get conversation context
        recent_conversations = await self.graph_memory.get_conversation_history(user_id, limit=5)
        enriched["conversation_context"] = recent_conversations
        
        # Get tool usage patterns
        tool_usage = await self.graph_memory.get_user_tool_usage(user_id)
        enriched["tool_preferences"] = tool_usage
        
        return enriched

class RequestAnalysis(BaseModel):
    """Structured analysis of user request"""
    intent: IntentClassification
    entities: List[str]
    context: Dict[str, Any]
    complexity: ComplexityLevel
    reasoning_path: List[str]
    confidence_score: float


class IntentClassification(BaseModel):
    """Intent classification with reasoning"""
    primary_intent: str
    secondary_intents: List[str]
    action_type: str  # query, create, modify, analyze, workflow
    data_flow: str   # read, write, read_write, transform
    reasoning: str
    confidence: float


class ComplexityLevel(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"          # Single tool, single step
    MODERATE = "moderate"      # Multiple tools, sequential steps
    COMPLEX = "complex"        # Multiple tools, parallel steps, dependencies
    EXPERT = "expert"          # Advanced reasoning, multi-domain knowledge
```

### **Intelligent Workflow Planning**

```python
class WorkflowPlanner:
    """Intelligent workflow planning with reasoning engine"""
    
    def __init__(self, reasoning_engine: ReasoningEngine, graph_memory: GraphMemoryService):
        self.reasoning = reasoning_engine
        self.graph_memory = graph_memory
    
    async def create_plan(self, user_request: str, context: ExecutionContext) -> WorkflowPlan:
        """Create intelligent workflow plan"""
        
        # Step 1: Deep request analysis
        analysis = await self.reasoning.analyze_request(user_request, context)
        
        # Step 2: Generate workflow steps with reasoning
        steps = await self.reasoning.generate_workflow_steps(analysis)
        
        # Step 3: Optimize execution sequence
        optimized_steps = await self.reasoning.optimize_sequence(steps)
        
        # Step 4: Create workflow plan with metadata
        plan = WorkflowPlan(
            id=str(uuid4()),
            name=self._generate_plan_name(analysis),
            description=self._generate_plan_description(analysis),
            steps=optimized_steps,
            analysis=analysis,
            estimated_duration=self._estimate_duration(optimized_steps),
            resource_requirements=self._calculate_resources(optimized_steps)
        )
        
        # Step 5: Store plan in graph memory for future reference
        await self.graph_memory.store_workflow_plan(plan, context.user_id)
        
        return plan
    
    async def adapt_plan(self, plan: WorkflowPlan, execution_context: Dict[str, Any]) -> WorkflowPlan:
        """Adapt plan based on runtime context"""
        
        # Analyze current execution state
        current_state = await self._analyze_execution_state(execution_context)
        
        # Re-reason about remaining steps
        remaining_steps = [step for step in plan.steps if step.status == StepStatus.PENDING]
        adapted_steps = await self.reasoning.re_evaluate_steps(remaining_steps, current_state)
        
        # Create adapted plan
        adapted_plan = plan.copy(deep=True)
        adapted_plan.steps = [
            step for step in plan.steps if step.status != StepStatus.PENDING
        ] + adapted_steps
        
        return adapted_plan
```

### **Sequential Thinking Evolution**

MetisAgent3's reasoning engine evolves from MetisAgent2's Sequential Thinking system:

**MetisAgent2 Sequential Thinking:**
- MCP-based reasoning server
- Basic workflow planning
- Tool matching and sequencing

**MetisAgent3 Reasoning Engine:**
- Integrated reasoning with graph memory
- Context-aware analysis
- Multi-dimensional optimization
- Adaptive planning capabilities

```python
# Migration from Sequential Thinking to Reasoning Engine
class SequentialThinkingAdapter:
    """Adapter for migrating from MetisAgent2 Sequential Thinking"""
    
    def __init__(self, reasoning_engine: ReasoningEngine):
        self.reasoning = reasoning_engine
        
    async def plan_workflow(self, user_request: str, available_tools: List[str], user_id: str) -> Dict:
        """Legacy compatibility method"""
        
        context = ExecutionContext(user_id=user_id)
        analysis = await self.reasoning.analyze_request(user_request, context)
        steps = await self.reasoning.generate_workflow_steps(analysis)
        
        # Convert to legacy format for backward compatibility
        return {
            "success": True,
            "steps": [self._convert_step_to_legacy(step) for step in steps],
            "metadata": {
                "analysis": analysis.dict(),
                "reasoning_path": analysis.reasoning_path
            }
        }
```

### **Reasoning Prompt Engineering**

The reasoning engine uses sophisticated prompting for intelligent analysis:

```python
def _build_reasoning_prompt(self, analysis: RequestAnalysis, user_tools: List[Dict], tool_prompt: str) -> str:
    """Build sophisticated reasoning prompt"""
    
    return f"""
# INTELLIGENT WORKFLOW PLANNING

## USER REQUEST ANALYSIS
Request: {analysis.intent.primary_intent}
Entities: {', '.join(analysis.entities)}
Complexity: {analysis.complexity.value}
Context: {json.dumps(analysis.context, indent=2)}

## AVAILABLE TOOLS
{tool_prompt}

## REASONING INSTRUCTIONS
You are an intelligent workflow planner. Analyze the request deeply and create an optimal execution plan.

### Step 1: REASONING PROCESS
- Understand the user's true intent beyond surface request
- Identify required data flows and transformations
- Consider context from previous interactions
- Evaluate tool capabilities and limitations

### Step 2: WORKFLOW DESIGN
- Break down complex tasks into logical steps
- Identify dependencies between steps
- Optimize for parallel execution where possible
- Plan error handling and fallback strategies

### Step 3: OUTPUT FORMAT
Provide a structured workflow with:
- Clear step descriptions and reasoning
- Tool selections with justification
- Parameter mappings between steps
- Success criteria for each step

Think step by step and explain your reasoning for each decision.
"""
```

**Key Features of Reasoning Engine:**

1. **Context-Aware Analysis**: Uses graph memory for enriched context
2. **Multi-Dimensional Planning**: Intent, entities, complexity, dependencies
3. **Adaptive Intelligence**: Plans adapt based on execution context
4. **Backward Compatibility**: Sequential Thinking adapter for migration
5. **Sophisticated Prompting**: Engineered prompts for optimal LLM reasoning

## 🔄 WORKFLOW EXECUTION ENGINE

class WorkflowExecutor:
    """Executes workflow plans with fault tolerance and LLM-based reasoning"""
    
    def __init__(self, tool_manager: ToolManager, reasoning_engine: ReasoningEngine):
        self.tool_manager = tool_manager
        self.reasoning_engine = reasoning_engine
        self.execution_context = {}
    
    async def execute_plan(self, plan: WorkflowPlan) -> WorkflowResult:
        """Execute plan with dependency resolution and SEQUENTIAL REASONED EXECUTION"""
        
        results = {}
        failed_steps = []
        
        # Topological sort for dependency order
        execution_order = self._resolve_dependencies(plan.steps)
        
        for step in execution_order:
            try:
                # Resolve input parameters from previous steps
                resolved_input = await self._resolve_step_input(step, results)
                
                # Execute step with LLM-based reasoning and recovery
                result = await self._execute_step_with_reasoning(step, resolved_input, results)
                
                results[step.id] = result
                
                if not result.success:
                    failed_steps.append(step)
                    
                    # Check if this failure should stop execution
                    if self._is_critical_failure(step, plan):
                        break
                        
            except Exception as e:
                failed_steps.append(step)
                results[step.id] = AgentResult(success=False, error=str(e))
        
        return WorkflowResult(
            success=len(failed_steps) == 0,
            step_results=results,
            failed_steps=failed_steps,
            execution_summary=self._generate_summary(results)
        )
    
    async def _execute_step_with_reasoning(self, step: WorkflowStep, input_data: Dict[str, Any], 
                                          previous_results: Dict[str, AgentResult]) -> AgentResult:
        """Execute step with LLM reasoning for failure recovery (CRITICAL ENHANCEMENT)"""
        
        max_reasoning_attempts = 3
        attempt = 0
        last_error = None
        
        while attempt < max_reasoning_attempts:
            try:
                # Try executing the step
                result = await self._execute_single_step(step, input_data)
                
                if result.success:
                    return result
                
                # STEP FAILED - Apply LLM reasoning for remedy
                last_error = result.error
                
                if attempt < max_reasoning_attempts - 1:  # Don't reason on last attempt
                    remedy_result = await self._apply_llm_remedy(
                        step=step,
                        failure_error=result.error,
                        failure_data=result.data,
                        previous_results=previous_results,
                        attempt_number=attempt + 1
                    )
                    
                    if remedy_result.success:
                        # LLM provided a remedy - update step and retry
                        step = remedy_result.data.get("updated_step", step)
                        input_data = remedy_result.data.get("updated_input", input_data)
                        logger.info(f"🧠 LLM Remedy Applied: {remedy_result.data.get('remedy_description')}")
                    else:
                        logger.warning(f"🚨 LLM Remedy Failed: {remedy_result.error}")
                
                attempt += 1
                
            except Exception as e:
                last_error = str(e)
                attempt += 1
        
        # All attempts failed
        return AgentResult(
            success=False,
            error=f"Step failed after {max_reasoning_attempts} reasoning attempts. Last error: {last_error}",
            metadata={"max_attempts_reached": True, "reasoning_attempts": max_reasoning_attempts}
        )
    
    async def _apply_llm_remedy(self, step: WorkflowStep, failure_error: str, 
                               failure_data: Any, previous_results: Dict[str, AgentResult],
                               attempt_number: int) -> AgentResult:
        """Use LLM to analyze failure and provide remedy (CORE INNOVATION)"""
        
        # Build context for LLM reasoning
        remedy_prompt = f"""
STEP FAILURE ANALYSIS & REMEDY

**Failed Step:**
- Tool: {step.tool_name}
- Capability: {step.capability_name}
- Input: {step.input_data}
- Error: {failure_error}
- Failure Data: {failure_data}

**Previous Results Context:**
{self._format_previous_results(previous_results)}

**Attempt Number:** {attempt_number}/3

**TASK:** Analyze the failure and provide a specific remedy to fix the step.

**COMMON FAILURE PATTERNS:**
1. **File/Directory Not Found**: Correct paths, check alternatives
2. **Permission Issues**: Adjust permissions or alternative approach  
3. **Parameter Mismatch**: Fix parameter format or values
4. **Timeout Issues**: Increase timeout or optimize command
5. **Command Syntax**: Fix command syntax for target platform

**REQUIRED OUTPUT:**
1. **Root Cause Analysis**: Why did this specific step fail?
2. **Remedy Strategy**: What specific changes will fix it?
3. **Updated Step**: Modified step parameters
4. **Confidence Level**: How likely is this remedy to succeed (0-1)?

Respond with structured JSON containing the remedy.
"""

        try:
            # Use reasoning engine to analyze and provide remedy
            remedy_response = await self.reasoning_engine.generate_structured_response(
                prompt=remedy_prompt,
                response_schema=StepRemedySchema,
                context_data={
                    "failed_step": step.dict(),
                    "previous_results": previous_results,
                    "attempt_number": attempt_number
                }
            )
            
            if remedy_response.success and remedy_response.data.confidence_level > 0.6:
                return AgentResult(
                    success=True,
                    data={
                        "remedy_description": remedy_response.data.remedy_strategy,
                        "updated_step": remedy_response.data.updated_step,
                        "updated_input": remedy_response.data.updated_input,
                        "confidence": remedy_response.data.confidence_level,
                        "root_cause": remedy_response.data.root_cause_analysis
                    }
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"LLM remedy confidence too low: {remedy_response.data.confidence_level if remedy_response.success else 'Failed to generate remedy'}"
                )
                
        except Exception as e:
            return AgentResult(success=False, error=f"LLM remedy generation failed: {str(e)}")
        
    def _format_previous_results(self, results: Dict[str, AgentResult]) -> str:
        """Format previous results for LLM context"""
        if not results:
            return "No previous results available."
        
        formatted = []
        for step_id, result in results.items():
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            formatted.append(f"Step {step_id}: {status}")
            if result.data:
                formatted.append(f"  Data: {str(result.data)[:200]}...")
            if result.error:
                formatted.append(f"  Error: {result.error}")
        
        return "\n".join(formatted)


class StepRemedySchema(BaseModel):
    """Schema for LLM remedy responses"""
    root_cause_analysis: str = Field(description="Analysis of why the step failed")
    remedy_strategy: str = Field(description="Specific strategy to fix the failure")
    updated_step: Optional[Dict[str, Any]] = Field(description="Modified step parameters if needed")
    updated_input: Optional[Dict[str, Any]] = Field(description="Modified input data if needed")
    confidence_level: float = Field(description="Confidence in remedy success (0.0-1.0)", ge=0.0, le=1.0)
    alternative_approaches: List[str] = Field(default_factory=list, description="Alternative approaches if primary remedy fails")
```

## 💾 GRAPH MEMORY ARCHITECTURE

### **Memory Service Design**

```python
class GraphMemoryService:
    """Persistent graph-based memory with MCP integration"""
    
    def __init__(self, mcp_server_path: str):
        self.mcp_server = MCPServer(mcp_server_path)
        self.local_cache = {}
    
    async def store_entity(self, entity: Entity) -> bool:
        """Store entity in graph memory"""
        try:
            result = await self.mcp_server.call("create_entities", {
                "entities": [entity.to_dict()]
            })
            return result.success
        except Exception:
            # Fallback to local storage
            return self._store_locally(entity)
    
    async def create_relation(self, from_entity: str, to_entity: str, relation_type: str) -> bool:
        """Create relationship between entities"""
        pass
    
    async def query_graph(self, query: str) -> List[Entity]:
        """Query graph using natural language"""
        pass

class ContextManager:
    """Manages conversation context and memory"""
    
    def __init__(self, memory_service: GraphMemoryService):
        self.memory = memory_service
        self.active_contexts = {}
    
    async def get_context(self, user_id: str, conversation_id: str) -> ConversationContext:
        """Get conversation context with memory"""
        
        # Check cache first
        cache_key = f"{user_id}:{conversation_id}"
        if cache_key in self.active_contexts:
            return self.active_contexts[cache_key]
        
        # Load from memory
        context = await self._load_context_from_memory(user_id, conversation_id)
        self.active_contexts[cache_key] = context
        return context
    
    async def update_context(self, context: ConversationContext, workflow_result: WorkflowResult):
        """Update context with workflow results"""
        
        # Extract important entities and relationships
        entities = self._extract_entities_from_result(workflow_result)
        
        for entity in entities:
            await self.memory.store_entity(entity)
        
        # Update conversation history
        context.add_workflow_result(workflow_result)
```

## 🔄 EVENT-DRIVEN ARCHITECTURE

### **Event System**

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Event:
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    correlation_id: str

class EventHandler(Protocol):
    async def handle(self, event: Event) -> None:
        """Handle an event"""
        ...

class EventBus:
    """Central event bus for system communication"""
    
    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = {}
    
    def subscribe(self, event_type: str, handler: EventHandler):
        """Subscribe to events"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        handlers = self.handlers.get(event.type, [])
        
        # Execute all handlers concurrently
        tasks = [handler.handle(event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

# Event Types
class WorkflowEvents:
    STARTED = "workflow.started"
    STEP_COMPLETED = "workflow.step.completed"
    STEP_FAILED = "workflow.step.failed"
    COMPLETED = "workflow.completed"
    FAILED = "workflow.failed"

class ToolEvents:
    LOADED = "tool.loaded"
    UNLOADED = "tool.unloaded"
    HEALTH_CHANGED = "tool.health_changed"
    CAPABILITY_ADDED = "tool.capability_added"
```

## 📊 MONITORING & OBSERVABILITY

### **Structured Logging**

```python
import structlog
from opentelemetry import trace, metrics

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]
)

class ObservabilityService:
    """Centralized observability"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        
        # Metrics
        self.workflow_duration = self.meter.create_histogram(
            "workflow_duration_seconds",
            description="Workflow execution time"
        )
        
        self.tool_calls = self.meter.create_counter(
            "tool_calls_total",
            description="Total tool calls"
        )
    
    async def trace_workflow(self, workflow_id: str, func: callable):
        """Trace workflow execution"""
        with self.tracer.start_as_current_span("workflow") as span:
            span.set_attribute("workflow.id", workflow_id)
            
            start_time = time.time()
            try:
                result = await func()
                span.set_attribute("workflow.success", result.success)
                return result
            finally:
                duration = time.time() - start_time
                self.workflow_duration.record(duration)
```

## 🧪 TESTING STRATEGY

### **Test Architecture**

```python
# Unit Tests
class TestGmailTool:
    async def test_list_emails_success(self):
        tool = GmailTool()
        result = await tool.execute("list_emails", {"max_results": 5})
        
        assert result.success
        assert isinstance(result.data, List[EmailMessage])
        assert len(result.data) <= 5

# Integration Tests  
class TestWorkflowExecution:
    async def test_gmail_to_visual_workflow(self):
        planner = WorkflowPlanner(tool_manager, llm_service)
        executor = WorkflowExecutor(tool_manager)
        
        plan = await planner.create_plan("Get latest email and create a visual")
        result = await executor.execute_plan(plan)
        
        assert result.success
        assert "email_data" in result.step_results
        assert "generated_image" in result.step_results

# Contract Tests
class TestToolContracts:
    def test_all_tools_implement_interface(self):
        for tool_name, tool in tool_manager.tools.items():
            assert isinstance(tool, BaseTool)
            assert len(tool.get_capabilities()) > 0
            assert tool.health_check() in [True, False]
```

## 🚫 CLAUDE.md ENFORCEMENT MECHANISMS

### **Automated Compliance Checking**
```python
class CLAUDEmdEnforcer:
    """Automated CLAUDE.md compliance checking"""
    
    def __init__(self):
        self.violations = []
    
    def check_code_quality(self, codebase_path: str) -> List[Violation]:
        """Check for CLAUDE.md violations"""
        violations = []
        
        # Check 1: No print() statements
        violations.extend(self._check_no_print_statements(codebase_path))
        
        # Check 2: No hard-coded keywords/rules  
        violations.extend(self._check_no_hardcoded_rules(codebase_path))
        
        # Check 3: All functions have type hints
        violations.extend(self._check_type_hints(codebase_path))
        
        # Check 4: No command injection patterns
        violations.extend(self._check_command_injection(codebase_path))
        
        # Check 5: Structured logging only
        violations.extend(self._check_structured_logging(codebase_path))
        
        return violations
    
    def _check_no_hardcoded_rules(self, path: str) -> List[Violation]:
        """Detect hard-coded decision patterns"""
        forbidden_patterns = [
            r'if.*"instagram".*in.*lower\(\)',  # Hard-coded keyword matching
            r'if.*"gmail".*in.*request',        # Direct string matching
            r'keyword.*in.*user_request',       # Keyword-based routing
        ]
        # Implementation...

class DevelopmentGuard:
    """Runtime CLAUDE.md compliance guard"""
    
    @staticmethod
    def validate_llm_decision(decision: Dict, context: str) -> bool:
        """Ensure LLM made the decision, not hard-coded rules"""
        
        if 'hard_coded' in decision.get('metadata', {}):
            raise CLAUDEmdViolation(f"Hard-coded decision detected in {context}")
        
        if not decision.get('llm_reasoning'):
            raise CLAUDEmdViolation(f"Missing LLM reasoning in {context}")
        
        return True
    
    @staticmethod  
    def secure_command_execution(command: str, user_input: str) -> str:
        """CLAUDE.md: Prevent command injection"""
        
        # Whitelist allowed commands only
        allowed_commands = ["ls", "pwd", "whoami"]
        
        base_cmd = command.split()[0]
        if base_cmd not in allowed_commands:
            raise SecurityViolation(f"Command {base_cmd} not allowed")
        
        # Sanitize user input
        sanitized_input = re.sub(r'[;&|`$]', '', user_input)
        
        return f"{command} {sanitized_input}"
```

### **Pre-commit Hooks**
```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: claude-md-enforcer
        name: CLAUDE.md Compliance Check
        entry: python tools/claude_enforcer.py
        language: python
        always_run: true
        pass_filenames: false
        
      - id: no-print-statements  
        name: No print() allowed
        entry: grep -rn "print(" --include="*.py" src/
        language: system
        pass_filenames: false
```

## 📦 PROJECT STRUCTURE

```
MetisAgent3/
├── core/
│   ├── contracts/          # Data contracts and schemas
│   ├── engine/            # Workflow engine
│   ├── memory/            # Graph memory service
│   ├── tools/             # Tool management
│   └── events/            # Event system
├── plugins/
│   ├── mcp_tools/         # MCP-based tools
│   ├── native_tools/      # Python native tools
│   └── external_apis/     # API integrations
├── services/
│   ├── auth/              # Authentication
│   ├── monitoring/        # Observability
│   └── storage/           # Persistence
├── api/
│   ├── rest/              # REST API
│   ├── websocket/         # WebSocket handlers
│   └── graphql/           # GraphQL endpoint (future)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── deployment/
    ├── docker/
    ├── kubernetes/
    └── monitoring/
```

## 🚀 MIGRATION STRATEGY

### **Phase 1: Foundation (Week 1-2)**
1. **Core Contracts**: Define all data models
2. **Base Tool Interface**: Implement BaseTool abstract class
3. **Tool Manager**: Dynamic loading and health checking
4. **Event Bus**: Basic pub/sub system

### **Phase 2: Engine (Week 3-4)**
1. **Workflow Planner**: LLM-based plan generation
2. **Workflow Executor**: Fault-tolerant execution
3. **Graph Memory**: MCP integration + fallback
4. **Basic Monitoring**: Structured logging

### **Phase 3: Migration (Week 5)**
1. **Tool Porting**: Convert existing tools to new interface
2. **Data Migration**: Move existing data to new format
3. **Testing**: Comprehensive test suite
4. **Performance Optimization**: Profiling and optimization

### **Phase 4: Production (Week 6)**
1. **Monitoring Setup**: Metrics, alerts, dashboards
2. **Documentation**: API docs, deployment guides
3. **Security Review**: Authentication, authorization
4. **Load Testing**: Performance validation

## ✅ SUCCESS CRITERIA

### **Reliability**
- [ ] 99.9% uptime during normal operations
- [ ] Graceful degradation when tools fail
- [ ] No cascading failures from single tool issues

### **Maintainability** 
- [ ] Add new tool in <2 hours
- [ ] Zero-downtime deployments
- [ ] Automated testing coverage >90%

### **Performance**
- [ ] <500ms response time for simple workflows
- [ ] <2s response time for complex workflows
- [ ] Handle 100+ concurrent users

### **Developer Experience**
- [ ] Type-safe API contracts
- [ ] Auto-generated documentation
- [ ] Hot-reload development environment

---

**🎯 THIS IS OUR NORTH STAR**

Every line of code in MetisAgent3 will be measured against this architecture. No shortcuts, no quick fixes - only production-ready, enterprise-grade software.

Ready to build the future? 🚀