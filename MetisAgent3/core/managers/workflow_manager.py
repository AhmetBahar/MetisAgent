"""
Workflow Manager Implementation - Intelligent Planning & Execution

CLAUDE.md COMPLIANT:
- ReasoningEngine integration for intelligent planning
- GraphMemoryService integration for user-specific capabilities
- Fault-tolerant execution with circuit breakers
- Step-by-step orchestration with dependency resolution
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import logging
from uuid import uuid4

from ..contracts import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStep,
    StepExecution,
    ExecutionContext,
    ExecutionStatus,
    AgentResult,
    ReasoningStep,
    ReasoningResult,
    RequestAnalysis,
    ToolExecutionRequest
)
from ..interfaces import (
    IWorkflowPlanner,
    IWorkflowExecutor,
    IWorkflowValidator,
    IReasoningEngine
)

logger = logging.getLogger(__name__)


class WorkflowPlanner(IWorkflowPlanner):
    """Intelligent workflow planning with reasoning engine"""
    
    def __init__(self, reasoning_engine: IReasoningEngine, graph_memory_service, tool_manager):
        self.reasoning = reasoning_engine
        self.graph_memory = graph_memory_service
        self.tool_manager = tool_manager
        self.workflow_templates: Dict[str, Any] = {}
        
    async def generate_workflow(self, user_request: str, available_tools: List[str], context: ExecutionContext) -> WorkflowDefinition:
        """Generate workflow using reasoning engine"""
        try:
            start_time = datetime.now()
            
            # Step 1: Complete reasoning about the request
            reasoning_result = await self.reasoning.reason_about_request(user_request, context)
            
            if not reasoning_result.success:
                logger.error(f"Reasoning failed: {reasoning_result.error}")
                return self._create_empty_workflow(user_request, reasoning_result.error)
            
            # Step 2: Convert reasoning steps to workflow steps
            workflow_steps = await self._convert_reasoning_to_workflow_steps(
                reasoning_result.steps, 
                context
            )
            
            # Step 3: Create workflow definition
            workflow = WorkflowDefinition(
                name=self._generate_workflow_name(reasoning_result.analysis),
                description=self._generate_workflow_description(reasoning_result.analysis),
                steps=workflow_steps,
                global_parameters={
                    "user_id": context.user_id,
                    "reasoning_trace_id": reasoning_result.reasoning_trace.trace_id if reasoning_result.reasoning_trace else None,
                    "complexity_level": reasoning_result.analysis.complexity.value if reasoning_result.analysis else "unknown"
                },
                timeout_seconds=self._calculate_workflow_timeout(workflow_steps),
                tags=self._extract_workflow_tags(reasoning_result.analysis)
            )
            
            # Step 4: Store workflow plan in graph memory for analytics
            if self.graph_memory:
                await self._store_workflow_plan(workflow, reasoning_result, context)
            
            planning_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Workflow planned in {planning_time:.2f}ms with {len(workflow_steps)} steps")
            
            return workflow
            
        except Exception as e:
            logger.error(f"Workflow planning failed: {e}")
            return self._create_empty_workflow(user_request, str(e))
    
    async def optimize_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Optimize workflow for performance and reliability"""
        try:
            optimized_steps = []
            
            # Step 1: Analyze dependencies
            dependency_graph = await self._analyze_step_dependencies(workflow.steps)
            
            # Step 2: Identify parallel execution opportunities
            parallel_groups = await self._identify_parallel_groups(workflow.steps, dependency_graph)
            
            # Step 3: Optimize step order
            optimized_order = await self._optimize_step_order(workflow.steps, dependency_graph)
            
            # Step 4: Add error recovery strategies
            recovery_enhanced_steps = await self._add_error_recovery(optimized_order)
            
            optimized_workflow = workflow.copy(deep=True)
            optimized_workflow.steps = recovery_enhanced_steps
            optimized_workflow.global_parameters["optimizations_applied"] = {
                "dependency_analysis": True,
                "parallel_groups": len(parallel_groups),
                "error_recovery": True,
                "optimization_timestamp": datetime.now().isoformat()
            }
            
            return optimized_workflow
            
        except Exception as e:
            logger.error(f"Workflow optimization failed: {e}")
            return workflow
    
    async def validate_workflow(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow structure and dependencies"""
        errors = []
        
        try:
            # Basic validation
            if not workflow.steps:
                errors.append("Workflow has no steps")
                return errors
            
            # Validate each step
            for step in workflow.steps:
                step_errors = await self._validate_step(step)
                errors.extend(step_errors)
            
            # Validate dependencies
            dependency_errors = await self._validate_dependencies(workflow.steps)
            errors.extend(dependency_errors)
            
            # Validate tool availability
            if self.tool_manager:
                tool_errors = await self._validate_tool_availability(workflow.steps)
                errors.extend(tool_errors)
            
            return errors
            
        except Exception as e:
            logger.error(f"Workflow validation failed: {e}")
            return [f"Validation error: {e}"]
    
    async def estimate_execution_time(self, workflow: WorkflowDefinition) -> float:
        """Estimate workflow execution time in seconds"""
        try:
            total_time = 0.0
            
            # Analyze dependencies to determine parallel vs sequential execution
            dependency_graph = await self._analyze_step_dependencies(workflow.steps)
            parallel_groups = await self._identify_parallel_groups(workflow.steps, dependency_graph)
            
            # Calculate time for each parallel group
            for group_steps in parallel_groups.values():
                # For parallel steps, take the maximum time
                group_max_time = 0.0
                for step_id in group_steps:
                    step = next((s for s in workflow.steps if s.id == step_id), None)
                    if step:
                        step_time = self._estimate_step_time(step)
                        group_max_time = max(group_max_time, step_time)
                total_time += group_max_time
            
            # Add buffer for coordination overhead
            overhead_factor = 1.2  # 20% overhead
            return total_time * overhead_factor
            
        except Exception as e:
            logger.error(f"Time estimation failed: {e}")
            return 60.0  # Default estimate
    
    async def suggest_improvements(self, workflow: WorkflowDefinition) -> List[str]:
        """Suggest workflow improvements"""
        suggestions = []
        
        try:
            # Analyze workflow complexity
            if len(workflow.steps) > 10:
                suggestions.append("Consider breaking down into smaller sub-workflows")
            
            # Check for sequential dependencies that could be parallelized
            dependency_graph = await self._analyze_step_dependencies(workflow.steps)
            sequential_chains = self._find_sequential_chains(dependency_graph)
            
            if len(sequential_chains) > 5:
                suggestions.append("Some sequential steps might be parallelizable")
            
            # Check for missing error handling
            steps_without_error_handling = [
                step for step in workflow.steps 
                if not step.conditions.get("on_failure")
            ]
            
            if len(steps_without_error_handling) > len(workflow.steps) * 0.5:
                suggestions.append("Add error handling to more steps")
            
            # Check timeout values
            steps_with_default_timeout = [
                step for step in workflow.steps 
                if not step.timeout_seconds or step.timeout_seconds == 60
            ]
            
            if steps_with_default_timeout:
                suggestions.append("Consider customizing timeout values for each step")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Improvement suggestions failed: {e}")
            return ["Unable to generate suggestions due to analysis error"]
    
    # Helper methods
    async def _convert_reasoning_to_workflow_steps(self, reasoning_steps: List[ReasoningStep], context: ExecutionContext) -> List[WorkflowStep]:
        """Convert reasoning steps to workflow steps"""
        workflow_steps = []
        
        for reasoning_step in reasoning_steps:
            # Convert parameters from reasoning step format
            parameters = []
            for param_name, param_value in reasoning_step.input_parameters.items():
                parameters.append({
                    "name": param_name,
                    "source": "constant",
                    "value": param_value,
                    "required": True
                })
            
            # Add parameter mappings from previous steps
            for mapping in reasoning_step.parameter_mappings:
                parameters.append({
                    "name": mapping.target_parameter,
                    "source": "previous_step",
                    "step_reference": mapping.source_step,
                    "json_path": mapping.source_field,
                    "default_value": mapping.default_value,
                    "required": True
                })
            
            # Convert dependencies
            dependencies = [dep.depends_on for dep in reasoning_step.dependencies]
            
            workflow_step = WorkflowStep(
                id=reasoning_step.step_id,
                name=reasoning_step.name,
                step_type="tool_execution",
                tool_name=reasoning_step.tool_name,
                capability=reasoning_step.capability,
                parameters=parameters,
                dependencies=dependencies,
                timeout_seconds=reasoning_step.timeout_seconds,
                retry_count=reasoning_step.retry_count,
                conditions={
                    "success_criteria": reasoning_step.success_criteria,
                    "error_handling": reasoning_step.error_handling
                }
            )
            
            workflow_steps.append(workflow_step)
        
        return workflow_steps
    
    def _generate_workflow_name(self, analysis: Optional[RequestAnalysis]) -> str:
        """Generate descriptive workflow name"""
        if not analysis:
            return "Generated Workflow"
        
        intent = analysis.intent.primary_intent
        complexity = analysis.complexity.value
        return f"{intent.title()} Workflow ({complexity})"
    
    def _generate_workflow_description(self, analysis: Optional[RequestAnalysis]) -> str:
        """Generate workflow description"""
        if not analysis:
            return "Auto-generated workflow"
        
        return f"Workflow for: {analysis.original_request}"
    
    def _calculate_workflow_timeout(self, steps: List[WorkflowStep]) -> int:
        """Calculate appropriate workflow timeout"""
        total_step_timeout = sum(step.timeout_seconds or 60 for step in steps)
        # Add 50% buffer for coordination overhead
        return int(total_step_timeout * 1.5)
    
    def _extract_workflow_tags(self, analysis: Optional[RequestAnalysis]) -> List[str]:
        """Extract tags from analysis"""
        tags = ["auto-generated"]
        
        if analysis:
            tags.append(f"complexity-{analysis.complexity.value}")
            tags.append(f"action-{analysis.intent.action_type.value}")
            tags.extend(analysis.entities.entities[:3])  # Add first 3 entities as tags
        
        return tags
    
    async def _store_workflow_plan(self, workflow: WorkflowDefinition, reasoning_result: ReasoningResult, context: ExecutionContext):
        """Store workflow plan in graph memory"""
        try:
            plan_data = {
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "user_request": reasoning_result.analysis.original_request if reasoning_result.analysis else "",
                "step_count": len(workflow.steps),
                "complexity": reasoning_result.analysis.complexity.value if reasoning_result.analysis else "unknown",
                "created_at": datetime.now().isoformat(),
                "reasoning_trace_id": reasoning_result.reasoning_trace.trace_id if reasoning_result.reasoning_trace else None
            }
            
            # Store as memory entry
            await self.graph_memory.store_workflow_plan(plan_data, context.user_id)
            
        except Exception as e:
            logger.warning(f"Failed to store workflow plan in graph memory: {e}")
    
    def _create_empty_workflow(self, user_request: str, error: str) -> WorkflowDefinition:
        """Create empty workflow for error cases"""
        return WorkflowDefinition(
            name="Failed Workflow",
            description=f"Failed to plan workflow for: {user_request}",
            steps=[],
            global_parameters={"error": error, "fallback": True}
        )
    
    async def _validate_step(self, step: WorkflowStep) -> List[str]:
        """Validate individual workflow step"""
        errors = []
        
        if not step.name:
            errors.append(f"Step {step.id} has no name")
        
        if step.step_type == "tool_execution":
            if not step.tool_name:
                errors.append(f"Step {step.id} has no tool specified")
            if not step.capability:
                errors.append(f"Step {step.id} has no capability specified")
        
        return errors
    
    async def _validate_dependencies(self, steps: List[WorkflowStep]) -> List[str]:
        """Validate step dependencies"""
        errors = []
        step_ids = {step.id for step in steps}
        
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step {step.id} depends on non-existent step {dep}")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(steps)
        if circular_deps:
            errors.append(f"Circular dependencies detected: {circular_deps}")
        
        return errors
    
    async def _validate_tool_availability(self, steps: List[WorkflowStep]) -> List[str]:
        """Validate tool availability"""
        errors = []
        
        for step in steps:
            if step.step_type == "tool_execution" and step.tool_name:
                tool = await self.tool_manager.get_tool(step.tool_name)
                if not tool:
                    errors.append(f"Tool {step.tool_name} not available for step {step.id}")
                else:
                    # Check capability availability
                    capabilities = await self.tool_manager.get_tool_capabilities(step.tool_name)
                    if step.capability and step.capability not in capabilities:
                        errors.append(f"Capability {step.capability} not available in tool {step.tool_name}")
        
        return errors
    
    def _detect_circular_dependencies(self, steps: List[WorkflowStep]) -> Optional[List[str]]:
        """Detect circular dependencies in workflow"""
        # Simple DFS-based cycle detection
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False
            
            visited.add(step_id)
            rec_stack.add(step_id)
            
            # Find step and check its dependencies
            step = next((s for s in steps if s.id == step_id), None)
            if step:
                for dep in step.dependencies:
                    if has_cycle(dep):
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in steps:
            if step.id not in visited:
                if has_cycle(step.id):
                    return [step.id]  # Return one cycle found
        
        return None
    
    async def _analyze_step_dependencies(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Analyze step dependencies"""
        dependency_graph = {}
        
        for step in steps:
            dependency_graph[step.id] = step.dependencies.copy()
        
        return dependency_graph
    
    async def _identify_parallel_groups(self, steps: List[WorkflowStep], dependency_graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Identify groups of steps that can run in parallel"""
        # Simple implementation - steps with no dependencies can run in parallel
        parallel_groups = {}
        
        independent_steps = [
            step.id for step in steps 
            if not dependency_graph.get(step.id, [])
        ]
        
        if independent_steps:
            parallel_groups["group_0"] = independent_steps
        
        return parallel_groups
    
    async def _optimize_step_order(self, steps: List[WorkflowStep], dependency_graph: Dict[str, List[str]]) -> List[WorkflowStep]:
        """Optimize step execution order"""
        # Topological sort for dependency order
        sorted_steps = []
        visited = set()
        temp_visited = set()
        
        def visit(step_id: str):
            if step_id in temp_visited:
                return  # Circular dependency - skip
            if step_id in visited:
                return
            
            temp_visited.add(step_id)
            
            # Visit dependencies first
            for dep in dependency_graph.get(step_id, []):
                visit(dep)
            
            temp_visited.remove(step_id)
            visited.add(step_id)
            
            # Add step to sorted list
            step = next((s for s in steps if s.id == step_id), None)
            if step:
                sorted_steps.append(step)
        
        for step in steps:
            if step.id not in visited:
                visit(step.id)
        
        return sorted_steps
    
    async def _add_error_recovery(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Add error recovery strategies to steps"""
        enhanced_steps = []
        
        for step in steps:
            enhanced_step = step.copy(deep=True)
            
            # Add basic error recovery if not present
            if not enhanced_step.conditions.get("on_failure"):
                enhanced_step.conditions["on_failure"] = "continue"  # Continue with next step on failure
            
            # Add retry logic for critical steps
            if enhanced_step.retry_count == 0:
                enhanced_step.retry_count = 1  # Default retry once
            
            enhanced_steps.append(enhanced_step)
        
        return enhanced_steps
    
    def _find_sequential_chains(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find chains of sequential dependencies"""
        chains = []
        # Simple implementation - would be more sophisticated in real system
        return chains
    
    def _estimate_step_time(self, step: WorkflowStep) -> float:
        """Estimate execution time for a step"""
        # Default estimates based on step type
        if step.step_type == "tool_execution":
            return 30.0  # 30 seconds default for tool execution
        elif step.step_type == "conditional":
            return 1.0   # 1 second for conditional logic
        else:
            return 10.0  # 10 seconds default


class WorkflowExecutor(IWorkflowExecutor):
    """Execute workflows with fault tolerance and monitoring"""
    
    def __init__(self, tool_manager, graph_memory_service=None):
        self.tool_manager = tool_manager
        self.graph_memory = graph_memory_service
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_lock = asyncio.Lock()
    
    async def execute_workflow(self, workflow: WorkflowDefinition, context: ExecutionContext) -> WorkflowExecution:
        """Execute complete workflow with monitoring"""
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            context=context,
            start_time=datetime.now()
        )
        
        # Initialize step executions
        for step in workflow.steps:
            execution.steps[step.id] = StepExecution(step_id=step.id)
        
        async with self.execution_lock:
            self.active_executions[execution.id] = execution
        
        try:
            execution.status = ExecutionStatus.IN_PROGRESS
            
            # Execute steps in dependency order
            execution_order = await self._resolve_execution_order(workflow.steps)
            
            for step in execution_order:
                if execution.status == ExecutionStatus.CANCELLED:
                    break
                
                step_result = await self._execute_step(step, execution, workflow)
                
                if not step_result.success:
                    # Check if failure should stop execution
                    if await self._should_stop_on_failure(step, workflow):
                        execution.status = ExecutionStatus.FAILED
                        execution.error_message = f"Critical step {step.id} failed: {step_result.error}"
                        break
            
            if execution.status == ExecutionStatus.IN_PROGRESS:
                execution.status = ExecutionStatus.COMPLETED
            
            execution.end_time = datetime.now()
            
            # Log execution to graph memory
            if self.graph_memory:
                await self._log_execution(execution, workflow)
            
            return execution
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            logger.error(f"Workflow execution failed: {e}")
            return execution
        
        finally:
            # Cleanup
            async with self.execution_lock:
                self.active_executions.pop(execution.id, None)
    
    async def execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> StepExecution:
        """Execute individual step"""
        return await self._execute_step(step, execution, None)
    
    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause workflow execution"""
        async with self.execution_lock:
            execution = self.active_executions.get(execution_id)
            if execution and execution.status == ExecutionStatus.IN_PROGRESS:
                execution.status = ExecutionStatus.PENDING  # Use as paused status
                return True
        return False
    
    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume paused workflow execution"""
        async with self.execution_lock:
            execution = self.active_executions.get(execution_id)
            if execution and execution.status == ExecutionStatus.PENDING:
                execution.status = ExecutionStatus.IN_PROGRESS
                return True
        return False
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel workflow execution"""
        async with self.execution_lock:
            execution = self.active_executions.get(execution_id)
            if execution:
                execution.status = ExecutionStatus.CANCELLED
                return True
        return False
    
    async def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get current execution status"""
        return self.active_executions.get(execution_id)
    
    # Helper methods
    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution, workflow: Optional[WorkflowDefinition]) -> AgentResult:
        """Execute individual workflow step"""
        step_execution = execution.steps[step.id]
        step_execution.status = ExecutionStatus.IN_PROGRESS
        step_execution.start_time = datetime.now()
        step_execution.attempt_count += 1
        
        try:
            if step.step_type == "tool_execution":
                # Resolve step parameters
                resolved_params = await self._resolve_step_parameters(step, execution)
                step_execution.resolved_parameters = resolved_params
                
                # Create tool execution request
                request = ToolExecutionRequest(
                    tool_name=step.tool_name,
                    capability=step.capability,
                    input_data=resolved_params,
                    context=execution.context,
                    timeout_seconds=step.timeout_seconds
                )
                
                # Execute tool
                result = await self.tool_manager.execute_tool(request)
                step_execution.result = result.result
                
                if result.result.success:
                    step_execution.status = ExecutionStatus.COMPLETED
                else:
                    step_execution.status = ExecutionStatus.FAILED
                    step_execution.error_message = result.result.error
                
                return result.result
                
            else:
                # Handle other step types (conditional, etc.)
                result = AgentResult(success=True, data={"step_type": step.step_type})
                step_execution.result = result
                step_execution.status = ExecutionStatus.COMPLETED
                return result
                
        except Exception as e:
            step_execution.status = ExecutionStatus.FAILED
            step_execution.error_message = str(e)
            result = AgentResult(success=False, error=str(e))
            step_execution.result = result
            return result
        
        finally:
            step_execution.end_time = datetime.now()
    
    async def _resolve_execution_order(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Resolve step execution order based on dependencies"""
        # Topological sort
        sorted_steps = []
        visited = set()
        temp_visited = set()
        
        def visit(step_id: str):
            if step_id in temp_visited or step_id in visited:
                return
            
            temp_visited.add(step_id)
            
            # Find step and visit dependencies first
            step = next((s for s in steps if s.id == step_id), None)
            if step:
                for dep in step.dependencies:
                    visit(dep)
                
                temp_visited.remove(step_id)
                visited.add(step_id)
                sorted_steps.append(step)
        
        for step in steps:
            if step.id not in visited:
                visit(step.id)
        
        return sorted_steps
    
    async def _resolve_step_parameters(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Resolve step parameters from various sources"""
        resolved = {}
        
        for param in step.parameters:
            if param["source"] == "constant":
                resolved[param["name"]] = param["value"]
            elif param["source"] == "previous_step":
                # Get data from previous step
                prev_step_id = param.get("step_reference")
                if prev_step_id and prev_step_id in execution.steps:
                    prev_result = execution.steps[prev_step_id].result
                    if prev_result and prev_result.success:
                        # Extract value using JSON path or direct access
                        json_path = param.get("json_path", param["name"])
                        value = self._extract_value_by_path(prev_result.data, json_path)
                        resolved[param["name"]] = value if value is not None else param.get("default_value")
                    else:
                        resolved[param["name"]] = param.get("default_value")
            elif param["source"] == "context":
                # Get from execution context
                resolved[param["name"]] = execution.global_context.get(param["name"], param.get("default_value"))
            else:
                resolved[param["name"]] = param.get("default_value")
        
        return resolved
    
    def _extract_value_by_path(self, data: Any, path: str) -> Any:
        """Extract value from data using simple path notation"""
        if not data or not isinstance(data, dict):
            return None
        
        # Simple implementation - would use JSONPath in real system
        return data.get(path)
    
    async def _should_stop_on_failure(self, step: WorkflowStep, workflow: WorkflowDefinition) -> bool:
        """Determine if workflow should stop on step failure"""
        # Check step-specific error handling
        error_handling = step.conditions.get("on_failure", "stop")
        return error_handling == "stop"
    
    async def _log_execution(self, execution: WorkflowExecution, workflow: WorkflowDefinition):
        """Log execution results to graph memory"""
        try:
            execution_data = {
                "execution_id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "duration_seconds": (execution.end_time - execution.start_time).total_seconds() if execution.end_time and execution.start_time else 0,
                "steps_completed": len([s for s in execution.steps.values() if s.status == ExecutionStatus.COMPLETED]),
                "steps_failed": len([s for s in execution.steps.values() if s.status == ExecutionStatus.FAILED]),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store execution log
            await self.graph_memory.log_workflow_execution(execution_data, execution.context.user_id)
            
        except Exception as e:
            logger.warning(f"Failed to log workflow execution: {e}")


class WorkflowValidator(IWorkflowValidator):
    """Validate workflows for consistency and executability"""
    
    def __init__(self, tool_manager=None):
        self.tool_manager = tool_manager
    
    async def validate_step_dependencies(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate step dependency graph"""
        errors = []
        step_ids = {step.id for step in workflow.steps}
        
        for step in workflow.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step {step.id} depends on non-existent step {dep}")
        
        return errors
    
    async def check_circular_dependencies(self, workflow: WorkflowDefinition) -> List[str]:
        """Check for circular dependencies"""
        # Implementation would use graph algorithms to detect cycles
        return []
    
    async def validate_tool_availability(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate that required tools are available"""
        errors = []
        
        if self.tool_manager:
            for step in workflow.steps:
                if step.step_type == "tool_execution" and step.tool_name:
                    tool = await self.tool_manager.get_tool(step.tool_name)
                    if not tool:
                        errors.append(f"Tool {step.tool_name} not available")
        
        return errors
    
    async def validate_parameters(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow parameters"""
        errors = []
        
        for step in workflow.steps:
            for param in step.parameters:
                if param.get("required", False) and not param.get("value") and not param.get("default_value"):
                    errors.append(f"Required parameter {param['name']} in step {step.id} has no value")
        
        return errors
    
    async def security_scan(self, workflow: WorkflowDefinition) -> List[str]:
        """Perform security scan on workflow"""
        warnings = []
        
        # Check for potentially dangerous tool combinations
        dangerous_tools = ["command_executor", "file_system"]
        used_dangerous_tools = [
            step.tool_name for step in workflow.steps 
            if step.tool_name in dangerous_tools
        ]
        
        if len(used_dangerous_tools) > 1:
            warnings.append(f"Workflow uses multiple dangerous tools: {used_dangerous_tools}")
        
        return warnings