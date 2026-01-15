"""
Workflow System Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract workflow contracts
- LLM-based planning interface
- No hard-coded workflow logic
- Extensible execution engine
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime

from ..contracts import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowTemplate,
    WorkflowStep,
    StepExecution,
    ExecutionContext,
    AgentResult
)


class IWorkflowPlanner(ABC):
    """Abstract interface for workflow planning"""
    
    @abstractmethod
    async def generate_workflow(self, user_request: str, available_tools: List[str], context: ExecutionContext) -> WorkflowDefinition:
        """Generate workflow from user request using LLM"""
        pass
    
    @abstractmethod
    async def optimize_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Optimize workflow for performance"""
        pass
    
    @abstractmethod
    async def validate_workflow(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow structure and dependencies"""
        pass
    
    @abstractmethod
    async def estimate_execution_time(self, workflow: WorkflowDefinition) -> float:
        """Estimate workflow execution time in seconds"""
        pass
    
    @abstractmethod
    async def suggest_improvements(self, workflow: WorkflowDefinition) -> List[str]:
        """Suggest workflow improvements"""
        pass


class IWorkflowExecutor(ABC):
    """Abstract interface for workflow execution"""
    
    @abstractmethod
    async def execute_workflow(self, workflow: WorkflowDefinition, context: ExecutionContext) -> WorkflowExecution:
        """Execute a complete workflow"""
        pass
    
    @abstractmethod
    async def execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> StepExecution:
        """Execute a single workflow step"""
        pass
    
    @abstractmethod
    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause workflow execution"""
        pass
    
    @abstractmethod
    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume paused workflow execution"""
        pass
    
    @abstractmethod
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel workflow execution"""
        pass
    
    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get current execution status"""
        pass


class IWorkflowValidator(ABC):
    """Abstract interface for workflow validation"""
    
    @abstractmethod
    async def validate_step_dependencies(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate step dependency graph"""
        pass
    
    @abstractmethod
    async def check_circular_dependencies(self, workflow: WorkflowDefinition) -> List[str]:
        """Check for circular dependencies"""
        pass
    
    @abstractmethod
    async def validate_tool_availability(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate that required tools are available"""
        pass
    
    @abstractmethod
    async def validate_parameters(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow parameters"""
        pass
    
    @abstractmethod
    async def security_scan(self, workflow: WorkflowDefinition) -> List[str]:
        """Perform security scan on workflow"""
        pass


class IWorkflowTemplate(ABC):
    """Abstract interface for workflow templates"""
    
    @abstractmethod
    async def save_template(self, template: WorkflowTemplate) -> str:
        """Save workflow as reusable template"""
        pass
    
    @abstractmethod
    async def load_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Load workflow template by ID"""
        pass
    
    @abstractmethod
    async def list_templates(self, category: Optional[str] = None) -> List[WorkflowTemplate]:
        """List available workflow templates"""
        pass
    
    @abstractmethod
    async def delete_template(self, template_id: str) -> bool:
        """Delete workflow template"""
        pass
    
    @abstractmethod
    async def instantiate_template(self, template_id: str, parameters: Dict[str, Any], context: ExecutionContext) -> WorkflowDefinition:
        """Create workflow instance from template"""
        pass


class IWorkflowMonitor(ABC):
    """Abstract interface for workflow monitoring"""
    
    @abstractmethod
    async def monitor_execution(self, execution_id: str) -> AsyncIterator[WorkflowExecution]:
        """Monitor workflow execution progress"""
        pass
    
    @abstractmethod
    async def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get execution performance metrics"""
        pass
    
    @abstractmethod
    async def get_execution_logs(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get execution logs"""
        pass
    
    @abstractmethod
    async def alert_on_failure(self, execution_id: str, alert_config: Dict[str, Any]) -> None:
        """Set up failure alerting"""
        pass


class IWorkflowScheduler(ABC):
    """Abstract interface for workflow scheduling"""
    
    @abstractmethod
    async def schedule_workflow(self, workflow: WorkflowDefinition, schedule: str, context: ExecutionContext) -> str:
        """Schedule workflow for future execution"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_workflow(self, schedule_id: str) -> bool:
        """Cancel scheduled workflow"""
        pass
    
    @abstractmethod
    async def list_scheduled_workflows(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List scheduled workflows"""
        pass
    
    @abstractmethod
    async def update_schedule(self, schedule_id: str, new_schedule: str) -> bool:
        """Update workflow schedule"""
        pass


class IWorkflowAnalytics(ABC):
    """Abstract interface for workflow analytics"""
    
    @abstractmethod
    async def analyze_performance(self, workflow_ids: List[str]) -> Dict[str, Any]:
        """Analyze workflow performance patterns"""
        pass
    
    @abstractmethod
    async def identify_bottlenecks(self, workflow_id: str) -> List[str]:
        """Identify performance bottlenecks"""
        pass
    
    @abstractmethod
    async def suggest_optimizations(self, workflow_id: str) -> List[str]:
        """Suggest workflow optimizations"""
        pass
    
    @abstractmethod
    async def usage_statistics(self, time_range: str) -> Dict[str, Any]:
        """Get workflow usage statistics"""
        pass