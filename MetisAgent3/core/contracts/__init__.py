"""
Core Contracts Module - Production-Ready Data Types

CLAUDE.md COMPLIANT:
- Strong type safety with Pydantic
- No hard-coded values
- Self-documenting with type hints
- Immutable data structures where appropriate
"""

from .base_types import (
    ExecutionStatus,
    Priority,
    AgentResult,
    ValidationError,
    ExecutionContext,
    HealthStatus,
    ResourceUsage,
    LogEntry
)

from .tool_contracts import (
    ToolType,
    CapabilityType,
    ToolCapability,
    ToolMetadata,
    ToolConfiguration,
    ToolExecutionRequest,
    ToolExecutionResult,
    BaseTool,
    ToolRegistry
)

from .workflow_contracts import (
    WorkflowStepType,
    ParameterSource,
    WorkflowParameter,
    WorkflowStep,
    WorkflowDefinition,
    StepExecution,
    WorkflowExecution,
    WorkflowTemplate
)

from .user_contracts import (
    UserRole,
    AuthProvider,
    PermissionLevel,
    UserProfile,
    AuthenticationSession,
    UserPermission,
    UserToolAccess,
    UserPreferences,
    ConversationContext,
    UserActivity,
    UserQuota
)

from .memory_contracts import (
    MemoryType,
    EntityType,
    RelationType,
    MemoryEntry,
    GraphEntity,
    GraphRelationship,
    ConversationMemory,
    MemoryQuery,
    MemorySearchResult,
    GraphQuery,
    GraphSearchResult,
    MemoryInsight
)

from .reasoning_contracts import (
    ComplexityLevel,
    ActionType,
    DataFlow,
    IntentClassification,
    EntityExtraction,
    ContextEnrichment,
    RequestAnalysis,
    StepDependency,
    ParameterMapping,
    ReasoningStep,
    WorkflowOptimization,
    ReasoningTrace,
    ValidationResult,
    ReasoningResult,
    AdaptationContext,
    LLMInteraction
)

__all__ = [
    # Base Types
    "ExecutionStatus",
    "Priority", 
    "AgentResult",
    "ValidationError",
    "ExecutionContext",
    "HealthStatus",
    "ResourceUsage",
    "LogEntry",
    
    # Tool Contracts
    "ToolType",
    "CapabilityType",
    "ToolCapability", 
    "ToolMetadata",
    "ToolConfiguration",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "BaseTool",
    "ToolRegistry",
    
    # Workflow Contracts
    "WorkflowStepType",
    "ParameterSource",
    "WorkflowParameter",
    "WorkflowStep",
    "WorkflowDefinition", 
    "StepExecution",
    "WorkflowExecution",
    "WorkflowTemplate",
    
    # User Contracts
    "UserRole",
    "AuthProvider",
    "PermissionLevel",
    "UserProfile",
    "AuthenticationSession",
    "UserPermission",
    "UserToolAccess",
    "UserPreferences",
    "ConversationContext",
    "UserActivity",
    "UserQuota",
    
    # Memory Contracts
    "MemoryType",
    "EntityType",
    "RelationType",
    "MemoryEntry",
    "GraphEntity",
    "GraphRelationship",
    "ConversationMemory",
    "MemoryQuery",
    "MemorySearchResult",
    "GraphQuery",
    "GraphSearchResult",
    "MemoryInsight",
    
    # Reasoning Contracts
    "ComplexityLevel",
    "ActionType",
    "DataFlow",
    "IntentClassification",
    "EntityExtraction",
    "ContextEnrichment",
    "RequestAnalysis",
    "StepDependency",
    "ParameterMapping",
    "ReasoningStep",
    "WorkflowOptimization",
    "ReasoningTrace",
    "ValidationResult",
    "ReasoningResult",
    "AdaptationContext",
    "LLMInteraction"
]