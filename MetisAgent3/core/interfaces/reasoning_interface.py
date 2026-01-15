"""
Reasoning System Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract reasoning contracts
- Multi-step analysis interfaces
- Context-aware planning abstractions
- LLM integration interfaces
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..contracts import (
    RequestAnalysis,
    ReasoningStep,
    WorkflowOptimization,
    ValidationResult,
    ReasoningResult,
    AdaptationContext,
    ReasoningTrace,
    LLMInteraction,
    ExecutionContext
)


class IRequestAnalyzer(ABC):
    """Abstract interface for request analysis"""
    
    @abstractmethod
    async def analyze_request(self, user_request: str, context: ExecutionContext) -> RequestAnalysis:
        """Perform deep analysis of user request"""
        pass
    
    @abstractmethod
    async def classify_intent(self, user_request: str) -> Dict[str, Any]:
        """Classify user intent with reasoning"""
        pass
    
    @abstractmethod
    async def extract_entities(self, user_request: str) -> Dict[str, Any]:
        """Extract entities and relationships"""
        pass
    
    @abstractmethod
    async def assess_complexity(self, user_request: str, intent: Dict[str, Any]) -> str:
        """Assess task complexity level"""
        pass
    
    @abstractmethod
    async def enrich_context(self, entities: List[str], user_id: str) -> Dict[str, Any]:
        """Enrich context from graph memory"""
        pass


class IWorkflowGenerator(ABC):
    """Abstract interface for workflow generation"""
    
    @abstractmethod
    async def generate_workflow_steps(self, analysis: RequestAnalysis) -> List[ReasoningStep]:
        """Generate workflow steps from analysis"""
        pass
    
    @abstractmethod
    async def optimize_sequence(self, steps: List[ReasoningStep]) -> WorkflowOptimization:
        """Optimize step execution order"""
        pass
    
    @abstractmethod
    async def validate_workflow(self, steps: List[ReasoningStep]) -> ValidationResult:
        """Validate workflow consistency"""
        pass
    
    @abstractmethod
    async def adapt_workflow(self, steps: List[ReasoningStep], context: AdaptationContext) -> List[ReasoningStep]:
        """Adapt workflow based on runtime context"""
        pass


class IReasoningEngine(ABC):
    """Abstract interface for reasoning engine"""
    
    @abstractmethod
    async def reason_about_request(self, user_request: str, context: ExecutionContext) -> ReasoningResult:
        """Complete reasoning process for user request"""
        pass
    
    @abstractmethod
    async def explain_reasoning(self, reasoning_result: ReasoningResult) -> str:
        """Generate human-readable reasoning explanation"""
        pass
    
    @abstractmethod
    async def get_reasoning_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Get detailed reasoning trace"""
        pass
    
    @abstractmethod
    async def evaluate_alternatives(self, analysis: RequestAnalysis) -> List[Dict[str, Any]]:
        """Evaluate alternative approaches"""
        pass


class ILLMService(ABC):
    """Abstract interface for LLM service"""
    
    @abstractmethod
    async def generate_structured(self, prompt: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured response with schema"""
        pass
    
    @abstractmethod
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text response"""
        pass
    
    @abstractmethod
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment and emotional context"""
        pass
    
    @abstractmethod
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords and key phrases"""
        pass
    
    @abstractmethod
    async def classify_text(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Classify text into categories with confidence"""
        pass
    
    @abstractmethod
    async def get_interaction_history(self, session_id: str) -> List[LLMInteraction]:
        """Get LLM interaction history"""
        pass


class IContextEnricher(ABC):
    """Abstract interface for context enrichment"""
    
    @abstractmethod
    async def enrich_with_conversation_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Enrich with conversation history"""
        pass
    
    @abstractmethod
    async def enrich_with_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Enrich with user preferences and patterns"""
        pass
    
    @abstractmethod
    async def enrich_with_tool_usage(self, user_id: str) -> Dict[str, Any]:
        """Enrich with tool usage patterns"""
        pass
    
    @abstractmethod
    async def enrich_with_temporal_context(self, timestamp: datetime) -> Dict[str, Any]:
        """Enrich with temporal context (time, season, etc.)"""
        pass
    
    @abstractmethod
    async def enrich_with_related_entities(self, entities: List[str], user_id: str) -> Dict[str, Any]:
        """Enrich with related entities from graph memory"""
        pass


class IWorkflowOptimizer(ABC):
    """Abstract interface for workflow optimization"""
    
    @abstractmethod
    async def analyze_dependencies(self, steps: List[ReasoningStep]) -> Dict[str, List[str]]:
        """Analyze step dependencies"""
        pass
    
    @abstractmethod
    async def identify_parallel_steps(self, steps: List[ReasoningStep]) -> Dict[str, List[str]]:
        """Identify steps that can run in parallel"""
        pass
    
    @abstractmethod
    async def optimize_resource_usage(self, steps: List[ReasoningStep]) -> List[ReasoningStep]:
        """Optimize resource usage patterns"""
        pass
    
    @abstractmethod
    async def minimize_execution_time(self, steps: List[ReasoningStep]) -> List[ReasoningStep]:
        """Minimize total execution time"""
        pass
    
    @abstractmethod
    async def add_error_recovery(self, steps: List[ReasoningStep]) -> List[ReasoningStep]:
        """Add error recovery strategies"""
        pass


class IReasoningValidator(ABC):
    """Abstract interface for reasoning validation"""
    
    @abstractmethod
    async def validate_analysis(self, analysis: RequestAnalysis) -> ValidationResult:
        """Validate request analysis"""
        pass
    
    @abstractmethod
    async def validate_steps(self, steps: List[ReasoningStep]) -> ValidationResult:
        """Validate workflow steps"""
        pass
    
    @abstractmethod
    async def validate_dependencies(self, steps: List[ReasoningStep]) -> ValidationResult:
        """Validate step dependencies"""
        pass
    
    @abstractmethod
    async def validate_tool_availability(self, steps: List[ReasoningStep], user_id: str) -> ValidationResult:
        """Validate tool availability for user"""
        pass
    
    @abstractmethod
    async def validate_parameter_flow(self, steps: List[ReasoningStep]) -> ValidationResult:
        """Validate parameter flow between steps"""
        pass


class IPromptEngine(ABC):
    """Abstract interface for prompt generation"""
    
    @abstractmethod
    async def build_analysis_prompt(self, user_request: str, context: Dict[str, Any]) -> str:
        """Build prompt for request analysis"""
        pass
    
    @abstractmethod
    async def build_planning_prompt(self, analysis: RequestAnalysis, tools: List[Dict[str, Any]]) -> str:
        """Build prompt for workflow planning"""
        pass
    
    @abstractmethod
    async def build_optimization_prompt(self, steps: List[ReasoningStep]) -> str:
        """Build prompt for workflow optimization"""
        pass
    
    @abstractmethod
    async def build_explanation_prompt(self, reasoning_result: ReasoningResult) -> str:
        """Build prompt for reasoning explanation"""
        pass
    
    @abstractmethod
    async def get_prompt_templates(self) -> Dict[str, str]:
        """Get available prompt templates"""
        pass


class IReasoningMetrics(ABC):
    """Abstract interface for reasoning metrics"""
    
    @abstractmethod
    async def track_analysis_time(self, analysis: RequestAnalysis, duration_ms: float) -> None:
        """Track analysis performance"""
        pass
    
    @abstractmethod
    async def track_generation_time(self, steps: List[ReasoningStep], duration_ms: float) -> None:
        """Track workflow generation performance"""
        pass
    
    @abstractmethod
    async def track_optimization_impact(self, original: List[ReasoningStep], optimized: List[ReasoningStep]) -> None:
        """Track optimization effectiveness"""
        pass
    
    @abstractmethod
    async def track_llm_usage(self, interaction: LLMInteraction) -> None:
        """Track LLM usage and costs"""
        pass
    
    @abstractmethod
    async def get_reasoning_analytics(self, user_id: str, time_range: str) -> Dict[str, Any]:
        """Get reasoning analytics for user"""
        pass