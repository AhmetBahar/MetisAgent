"""
Core Interfaces Module - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Abstract interfaces for all major components
- Strong contracts with type safety
- Extensible plugin architecture
- No implementation details in interfaces
"""

from .tool_interface import IToolManager, IToolExecutor, IToolHealth
from .workflow_interface import IWorkflowPlanner, IWorkflowExecutor, IWorkflowValidator
from .memory_interface import IMemoryService, IGraphService, IConversationService
from .user_interface import IUserManager, IAuthService, IPermissionService
from .event_interface import IEventBus, IEventHandler, IEventStore
from .reasoning_interface import (
    IRequestAnalyzer, IWorkflowGenerator, IReasoningEngine, ILLMService,
    IContextEnricher, IWorkflowOptimizer, IReasoningValidator, IPromptEngine
)

__all__ = [
    # Tool Interfaces
    "IToolManager",
    "IToolExecutor", 
    "IToolHealth",
    
    # Workflow Interfaces
    "IWorkflowPlanner",
    "IWorkflowExecutor",
    "IWorkflowValidator",
    
    # Memory Interfaces
    "IMemoryService",
    "IGraphService",
    "IConversationService",
    
    # User Interfaces
    "IUserManager",
    "IAuthService",
    "IPermissionService",
    
    # Event Interfaces
    "IEventBus",
    "IEventHandler",
    "IEventStore",
    
    # Reasoning Interfaces
    "IRequestAnalyzer",
    "IWorkflowGenerator", 
    "IReasoningEngine",
    "ILLMService",
    "IContextEnricher",
    "IWorkflowOptimizer",
    "IReasoningValidator",
    "IPromptEngine"
]