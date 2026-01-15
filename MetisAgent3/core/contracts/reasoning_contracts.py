"""
Reasoning Contracts - Reasoning Engine Data Models

CLAUDE.md COMPLIANT:
- Structured reasoning analysis contracts
- Intent classification and entity extraction
- Multi-step workflow planning types
- Context-aware decision making
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

from .base_types import AgentResult


class ComplexityLevel(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"          # Single tool, single step
    MODERATE = "moderate"      # Multiple tools, sequential steps
    COMPLEX = "complex"        # Multiple tools, parallel steps, dependencies
    EXPERT = "expert"          # Advanced reasoning, multi-domain knowledge


class ActionType(str, Enum):
    """Primary action types"""
    QUERY = "query"           # Information retrieval
    CREATE = "create"         # Content/resource creation
    MODIFY = "modify"         # Existing resource modification
    ANALYZE = "analyze"       # Data analysis and insights
    WORKFLOW = "workflow"     # Multi-step process execution
    INTERACT = "interact"     # External system interaction


class DataFlow(str, Enum):
    """Data flow patterns"""
    READ = "read"             # Read-only operations
    WRITE = "write"           # Write-only operations
    READ_WRITE = "read_write" # Read and write operations
    TRANSFORM = "transform"   # Data transformation operations


class IntentClassification(BaseModel):
    """Intent classification with reasoning"""
    primary_intent: str
    secondary_intents: List[str] = Field(default_factory=list)
    action_type: ActionType
    data_flow: DataFlow
    reasoning: str
    confidence: float
    extracted_keywords: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class EntityExtraction(BaseModel):
    """Extracted entities from user request"""
    entities: List[str]
    entity_types: Dict[str, str]  # entity -> type mapping
    relationships: List[Dict[str, str]] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)

    class Config:
        frozen = True


class ContextEnrichment(BaseModel):
    """Enriched context from graph memory"""
    conversation_context: List[Dict[str, Any]] = Field(default_factory=list)
    related_entities: Dict[str, Any] = Field(default_factory=dict)
    tool_preferences: Dict[str, Any] = Field(default_factory=dict)
    user_patterns: Dict[str, Any] = Field(default_factory=dict)
    temporal_context: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class RequestAnalysis(BaseModel):
    """Comprehensive analysis of user request"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    original_request: str
    intent: IntentClassification
    entities: EntityExtraction
    context: ContextEnrichment
    complexity: ComplexityLevel
    reasoning_path: List[str] = Field(default_factory=list)
    confidence_score: float
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    estimated_duration_seconds: Optional[float] = None

    class Config:
        frozen = True


class StepDependency(BaseModel):
    """Dependency between workflow steps"""
    step_id: str
    depends_on: str
    dependency_type: str  # "data", "order", "resource"
    required_output: Optional[str] = None
    optional: bool = False

    class Config:
        frozen = True


class ParameterMapping(BaseModel):
    """Parameter mapping between steps"""
    source_step: str
    source_field: str
    target_parameter: str
    transformation: Optional[str] = None  # JSON path or transformation rule
    default_value: Optional[Any] = None

    class Config:
        frozen = True


class ReasoningStep(BaseModel):
    """Individual reasoning step in workflow"""
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    tool_name: str
    capability: str
    input_parameters: Dict[str, Any] = Field(default_factory=dict)
    parameter_mappings: List[ParameterMapping] = Field(default_factory=list)
    dependencies: List[StepDependency] = Field(default_factory=list)
    expected_output: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)
    error_handling: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 60
    retry_count: int = 0
    parallel_group: Optional[str] = None
    reasoning: str
    confidence: float

    class Config:
        frozen = True


class OptimizationStrategy(BaseModel):
    """Workflow optimization strategy"""
    parallel_execution: bool = True
    resource_optimization: bool = True
    dependency_minimization: bool = True
    error_recovery: bool = True
    caching_strategy: str = "adaptive"
    priority_ordering: bool = False

    class Config:
        frozen = True


class WorkflowOptimization(BaseModel):
    """Workflow optimization analysis"""
    original_steps: List[ReasoningStep]
    optimized_steps: List[ReasoningStep]
    parallel_groups: Dict[str, List[str]] = Field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    estimated_time_savings: float = 0.0
    resource_efficiency_gain: float = 0.0
    optimization_reasoning: List[str] = Field(default_factory=list)
    strategy: OptimizationStrategy

    class Config:
        frozen = True


class ReasoningTrace(BaseModel):
    """Trace of reasoning process"""
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    user_request: str
    analysis_steps: List[str] = Field(default_factory=list)
    decision_points: List[Dict[str, Any]] = Field(default_factory=list)
    alternatives_considered: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_evolution: List[float] = Field(default_factory=list)
    reasoning_duration_ms: float = 0.0
    llm_interactions: int = 0

    class Config:
        frozen = True


class ValidationResult(BaseModel):
    """Validation result for workflow steps"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    validation_details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class ReasoningResult(BaseModel):
    """Result of reasoning process"""
    success: bool
    analysis: Optional[RequestAnalysis] = None
    steps: List[ReasoningStep] = Field(default_factory=list)
    optimization: Optional[WorkflowOptimization] = None
    validation: Optional[ValidationResult] = None
    reasoning_trace: Optional[ReasoningTrace] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class AdaptationContext(BaseModel):
    """Context for workflow adaptation"""
    current_execution_state: Dict[str, Any] = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    available_data: Dict[str, Any] = Field(default_factory=dict)
    resource_constraints: Dict[str, Any] = Field(default_factory=dict)
    time_constraints: Optional[float] = None
    user_feedback: Optional[str] = None

    class Config:
        frozen = True


class ReasoningPrompt(BaseModel):
    """Structured prompt for reasoning engine"""
    template_type: str
    user_request: str
    context_data: Dict[str, Any] = Field(default_factory=dict)
    tool_capabilities: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    response_schema: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class LLMInteraction(BaseModel):
    """LLM interaction record"""
    interaction_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    response: str
    model: str
    tokens_used: int
    latency_ms: float
    cost: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None

    class Config:
        frozen = True