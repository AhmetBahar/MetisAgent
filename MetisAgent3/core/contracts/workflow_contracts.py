"""
Workflow Contracts - Workflow System Data Models

CLAUDE.md COMPLIANT:
- Immutable workflow definitions
- Strong type safety for step execution
- Generic parameter system
- Clear dependency tracking
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

from .base_types import AgentResult, ExecutionContext, ExecutionStatus, Priority


class WorkflowStepType(str, Enum):
    """Types of workflow steps"""
    TOOL_EXECUTION = "tool_execution"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    LOOP = "loop"
    HUMAN_INPUT = "human_input"


class ParameterSource(str, Enum):
    """Source of parameter values"""
    USER_INPUT = "user_input"
    PREVIOUS_STEP = "previous_step"
    CONSTANT = "constant"
    CONTEXT = "context"
    COMPUTED = "computed"


class WorkflowParameter(BaseModel):
    """Parameter definition for workflow steps"""
    name: str
    source: ParameterSource
    value: Optional[Any] = None
    step_reference: Optional[str] = None
    json_path: Optional[str] = None
    default_value: Optional[Any] = None
    required: bool = True

    class Config:
        frozen = True


class WorkflowStep(BaseModel):
    """Individual step in a workflow"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    step_type: WorkflowStepType
    tool_name: Optional[str] = None
    capability: Optional[str] = None
    parameters: List[WorkflowParameter] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    timeout_seconds: Optional[int] = None
    priority: Priority = Priority.MEDIUM

    class Config:
        frozen = True


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    version: str = "1.0.0"
    steps: List[WorkflowStep]
    global_parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class StepExecution(BaseModel):
    """Execution state of a workflow step"""
    step_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[AgentResult] = None
    resolved_parameters: Dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    error_message: Optional[str] = None

    class Config:
        frozen = False


class WorkflowExecution(BaseModel):
    """Execution state of an entire workflow"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    context: ExecutionContext
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    steps: Dict[str, StepExecution] = Field(default_factory=dict)
    global_context: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    def get_step_execution(self, step_id: str) -> Optional[StepExecution]:
        """Get execution state for a specific step"""
        return self.steps.get(step_id)

    def update_step_status(self, step_id: str, status: ExecutionStatus, result: Optional[AgentResult] = None):
        """Update the status of a step"""
        if step_id not in self.steps:
            return
        
        step_exec = self.steps[step_id]
        step_exec.status = status
        
        if status == ExecutionStatus.IN_PROGRESS and not step_exec.start_time:
            step_exec.start_time = datetime.now()
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
            step_exec.end_time = datetime.now()
            if result:
                step_exec.result = result

    class Config:
        frozen = False


class WorkflowTemplate(BaseModel):
    """Reusable workflow template"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    category: str
    template_definition: WorkflowDefinition
    required_tools: List[str]
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def instantiate(self, parameters: Dict[str, Any], context: ExecutionContext) -> WorkflowExecution:
        """Create a workflow execution from this template"""
        workflow_exec = WorkflowExecution(
            workflow_id=self.template_definition.id,
            context=context
        )
        
        # Initialize step executions
        for step in self.template_definition.steps:
            workflow_exec.steps[step.id] = StepExecution(step_id=step.id)
        
        # Apply template parameters
        workflow_exec.global_context.update(parameters)
        
        return workflow_exec

    class Config:
        frozen = True