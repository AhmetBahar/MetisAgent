"""
Workflow Orchestration Engine - LLM-driven multi-step task execution
"""

import json
import logging
import uuid
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from .mcp_core import registry, MCPToolResult
from .utils.llm_eval import summarize_for_llm
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Usage patterns removed for simplicity

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_APPROVAL = "requires_approval"

@dataclass
class WorkflowStep:
    """Workflow'daki bir adım"""
    id: str
    title: str
    description: str
    tool_name: str
    action_name: str
    params: Dict[str, Any]
    status: StepStatus
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration: Optional[int] = None  # seconds
    dependencies: List[str] = None  # Other step IDs this depends on
    requires_user_input: Optional[bool] = False  # Step needs user interaction
    conflict_info: Optional[Dict] = None  # Tool conflict data
    original_request: Optional[str] = None  # Original user request

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class WorkflowPlan:
    """Workflow execution plan"""
    id: str
    title: str
    description: str
    user_id: str
    conversation_id: str
    status: WorkflowStatus
    steps: List[WorkflowStep]
    created_at: str
    updated_at: str
    estimated_total_duration: Optional[int] = None
    current_step_index: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class WorkflowOrchestrator:
    """LLM-driven workflow orchestration engine"""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowPlan] = {}
        self.workflow_history: List[WorkflowPlan] = []
        self.max_planning_iterations = 3
        self.max_step_duration = 300  # 5 minutes per step
        self._tool_cache = {}  # Cache for available tools
        self._last_registry_update = None
        self.workflow_eval_cache = {}  # Cache for LLM evaluation results
        self.cache_max_size = 100
        self.cache_ttl = 3600  # 1 hour
        self._execution_locks = {}  # Prevent parallel execution of same workflow
        self.step_results = {}  # Store step execution results for context passing
        
        # Initialize unified planner (workflow-first approach)
        self.unified_planner = None  # Will be initialized when registry is available
    
    def clear_workflow_cache(self):
        """Clear all workflow caches to force fresh execution"""
        self.active_workflows.clear()
        self.step_results.clear()
        self.workflow_eval_cache.clear()
        self._execution_locks.clear()
        logger.info("WORKFLOW CACHE CLEARED - All caches reset for fresh execution")
        
        # WebSocket integration for real-time updates
        self.websocket_manager = None
    
    def initialize_planner(self, registry):
        """Initialize using Sequential Thinking MCP as primary planner"""  
        self.registry = registry
        logger.info("Sequential Thinking MCP initialized as primary workflow planner")
    
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager reference"""
        self.websocket_manager = websocket_manager
        
    def _broadcast_workflow_update(self, user_id: str, workflow: WorkflowPlan):
        """Broadcast workflow update via WebSocket"""
        if self.websocket_manager:
            try:
                workflow_data = self._serialize_workflow(workflow)
                self.websocket_manager.broadcast_workflow_update(user_id, workflow_data)
            except Exception as e:
                logger.error(f"Failed to broadcast workflow update: {e}")
    
    def _broadcast_step_update(self, user_id: str, workflow_id: str, step: WorkflowStep):
        """Broadcast individual step update via WebSocket"""
        if self.websocket_manager:
            try:
                step_data = {
                    'id': step.id,
                    'title': step.title,
                    'description': step.description,
                    'status': step.status.value,
                    'tool_name': step.tool_name,
                    'action_name': step.action_name,
                    'started_at': step.started_at,
                    'completed_at': step.completed_at,
                    'error': step.error
                }
                self.websocket_manager.broadcast_workflow_step_update(user_id, workflow_id, step_data)
            except Exception as e:
                logger.error(f"Failed to broadcast step update: {e}")
    
    def _broadcast_workflow_started(self, user_id: str, workflow: WorkflowPlan):
        """Broadcast workflow started event"""
        if self.websocket_manager:
            try:
                workflow_data = self._serialize_workflow(workflow)
                self.websocket_manager.broadcast_workflow_started(user_id, workflow_data)
            except Exception as e:
                logger.error(f"Failed to broadcast workflow started: {e}")
    
    def _broadcast_workflow_completed(self, user_id: str, workflow_id: str, status: str):
        """Broadcast workflow completed event"""
        if self.websocket_manager:
            try:
                self.websocket_manager.broadcast_workflow_completed(user_id, workflow_id, status)
            except Exception as e:
                logger.error(f"Failed to broadcast workflow completed: {e}")
    
    def _clean_base64_from_data(self, data: Any) -> Any:
        """Remove base64 image data to prevent LLM context overflow"""
        if not data:
            return data
        
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if key in ['base64_image', 'b64_json', 'base64_data']:
                    # Replace with reference
                    if isinstance(value, str) and len(value) > 100:
                        cleaned[key] = f"[BASE64_IMAGE_DATA_REMOVED_{len(value)}_CHARS]"
                    else:
                        cleaned[key] = value
                elif isinstance(value, (dict, list)):
                    cleaned[key] = self._clean_base64_from_data(value)
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, list):
            return [self._clean_base64_from_data(item) for item in data]
        else:
            return data
    
    def _serialize_workflow(self, workflow: WorkflowPlan) -> Dict[str, Any]:
        """Serialize workflow for WebSocket transmission"""
        return {
            'workflow_id': workflow.id,
            'title': workflow.title,
            'description': workflow.description,
            'status': workflow.status.value,
            'user_id': workflow.user_id,
            'steps': [{
                'id': step.id,
                'title': step.title,
                'description': step.description,
                'status': step.status.value,
                'tool_name': step.tool_name,
                'action_name': step.action_name,
                'started_at': step.started_at,
                'completed_at': step.completed_at,
                'error': step.error
            } for step in workflow.steps],
            'total_steps': len(workflow.steps),
            'completed_steps': len([s for s in workflow.steps if s.status == StepStatus.COMPLETED]),
            'progress_percentage': (len([s for s in workflow.steps if s.status == StepStatus.COMPLETED]) / len(workflow.steps)) * 100 if workflow.steps else 0,
            'created_at': workflow.created_at,
            'updated_at': datetime.now().isoformat()
        }
    
    def refresh_tool_cache(self):
        """Tool cache'ini yenile (tool_manager'dan sonra çağrılır)"""
        try:
            self._tool_cache = {}
            self._last_registry_update = datetime.now()
            logger.info("Tool cache refreshed - dynamic tools updated")
        except Exception as e:
            logger.error(f"Error refreshing tool cache: {e}")
    
    def get_available_tools(self):
        """Cache'lenmiş veya fresh tool listesi döner"""
        try:
            # Fresh registry data al
            available_tools = registry.list_tools()
            
            # Cache'i güncelle
            current_time = datetime.now()
            if (not self._last_registry_update or 
                (current_time - self._last_registry_update).seconds > 10):
                self._tool_cache = {tool['name']: tool for tool in available_tools}
                self._last_registry_update = current_time
                
            return available_tools
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return []
        
    def create_workflow_from_user_input(self, user_input: str, user_id: str, 
                                      conversation_id: str) -> WorkflowPlan:
        """Create workflow using ONLY Sequential Thinking MCP - no unified planner"""
        try:
            logger.info(f"Creating workflow using ONLY Sequential Thinking MCP for: {user_input}")
            
            # Use ONLY Sequential Thinking MCP directly - bypass unified planner
            sequential_tool = self.registry.get_tool('sequential_thinking')
            if sequential_tool:
                logger.info(f"Sequential Thinking tool found, calling plan_workflow")
                
                # Debug: Write to file to confirm orchestrator is calling sequential thinking
                with open("/tmp/orchestrator_debug.txt", "w") as f:
                    f.write(f"ORCHESTRATOR: Calling Sequential Thinking with: {user_input}\n")
                    f.write(f"Time: {__import__('datetime').datetime.now()}\n")
                    f.write(f"Sequential tool exists: {sequential_tool is not None}\n")
                
                # Call plan_workflow directly 
                planning_result = sequential_tool.execute_action(
                    'plan_workflow',
                    user_request=user_input,
                    user_id=user_id or 'anonymous'
                )
                
                # Debug planning result data immediately (no logger)
                with open("/tmp/planning_result_debug.txt", "w") as f:
                    f.write(f"Planning Result Success: {planning_result.success}\n")
                    f.write(f"Planning Result Data: {planning_result.data}\n")
                    f.write(f"Planning Result Error: {planning_result.error}\n")
                
                if planning_result.success and planning_result.data:
                    workflow = self._convert_sequential_to_workflow(planning_result.data, user_id, conversation_id)
                    self.active_workflows[workflow.id] = workflow
                    logger.info(f"Sequential Thinking workflow created: {workflow.title} ({len(workflow.steps)} steps)")
                    return workflow
                else:
                    logger.warning(f"Sequential Thinking plan_workflow failed: {planning_result.error}")
            
            # Create simple fallback workflow
            logger.info("Creating simple fallback workflow")
            return self._create_simple_fallback_workflow(user_input, user_id, conversation_id)
            
        except Exception as e:
            logger.error(f"Sequential Thinking MCP failed: {e}")
            # Create simple fallback workflow
            return self._create_simple_fallback_workflow(user_input, user_id, conversation_id)
    
    def _convert_sequential_to_workflow(self, sequential_data, user_id: str, conversation_id: str) -> WorkflowPlan:
        """Convert Sequential Thinking MCP data to WorkflowPlan"""
        workflow_id = str(uuid.uuid4())
        
        # Convert steps from Sequential Thinking format
        workflow_steps = []
        steps = sequential_data.get('steps', [])
        
        for i, step_data in enumerate(steps):
            workflow_step = WorkflowStep(
                id=step_data.get('id', f"step_{i+1}"),
                title=step_data.get('title', f"Step {i+1}"),
                description=step_data.get('description', f"Execute step {i+1}"),
                tool_name=step_data.get('tool_name', 'command_executor'),
                action_name=step_data.get('action_name', 'execute'),
                params=step_data.get('parameters', step_data.get('params', {})),
                dependencies=step_data.get('dependencies', []),
                status=StepStatus.PENDING,
                requires_user_input=step_data.get('requires_user_input', False),
                conflict_info=step_data.get('conflict_info'),
                original_request=step_data.get('original_request')
            )
            workflow_steps.append(workflow_step)
        
        # Create workflow
        workflow = WorkflowPlan(
            id=workflow_id,
            title=sequential_data.get('title', 'Sequential Thinking Workflow'),
            description=sequential_data.get('description', 'Generated by Sequential Thinking MCP'),
            steps=workflow_steps,
            user_id=user_id,
            conversation_id=conversation_id,
            status=WorkflowStatus.PLANNING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            metadata={
                'planner_used': 'Sequential Thinking MCP',
                'input_complexity': sequential_data.get('complexity', 'unknown')
            }
        )
        
        logger.info(f"Converted Sequential Thinking data to workflow: {len(workflow_steps)} steps")
        return workflow
    
    def _create_simple_fallback_workflow(self, user_input: str, user_id: str, conversation_id: str) -> WorkflowPlan:
        """Create a simple fallback workflow with CONFLICT DETECTION"""
        workflow_id = str(uuid.uuid4())
        
        # CONFLICT DETECTION - Instagram tools
        if "instagram" in user_input.lower():
            # Return conflict resolution workflow
            workflow_step = WorkflowStep(
                id="step0",
                title="Instagram Tool Selection Required", 
                description="Multiple tools can handle Instagram requests. Please choose:",
                tool_name="user_clarification",
                action_name="request_clarification",
                params={
                    "request": user_input,
                    "options": [
                        {"tool_name": "Instagram Tool", "description": "Direct Instagram automation - login, post, story"},
                        {"tool_name": "Social Media Workflow", "description": "Advanced social media campaign workflow management"}
                    ],
                    "user_id": user_id,
                    "context": {"conflict_type": "instagram"}
                },
                dependencies=[],
                status=StepStatus.PENDING,
                requires_user_input=True,
                conflict_info={"type": "instagram_tools"},
                original_request=user_input
            )
        else:
            # Default simple workflow
            workflow_step = WorkflowStep(
                id="step0",
                title="Simple Command Execution",
                description=f"Process user request: {user_input}",
                tool_name="command_executor",
                action_name="execute",
                params={"command": f"echo 'Processing: {user_input[:50]}'"},
                dependencies=[],
                status=StepStatus.PENDING
            )
        
        workflow = WorkflowPlan(
            id=workflow_id,
            title="Simple Fallback Workflow",
            description="Basic workflow without complex planning",
            steps=[workflow_step],
            user_id=user_id,
            conversation_id=conversation_id,
            status=WorkflowStatus.PLANNING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            metadata={
                'planner_used': 'Simple Fallback',
                'no_llm': True
            }
        )
        
        logger.info(f"Created simple fallback workflow: {workflow_id}")
        return workflow
    
    def _convert_planner_plan_to_workflow(self, planner_plan, user_id: str, conversation_id: str) -> WorkflowPlan:
        """Convert PlannerPolicy plan to WorkflowPlan"""
        workflow_id = str(uuid.uuid4())
        
        # Convert steps
        workflow_steps = []
        for i, step in enumerate(planner_plan.steps):
            workflow_step = WorkflowStep(
                id=f"step{i}",
                title=f"Step {i+1}: {step.tool_name}.{step.action_name}",
                description=f"Execute {step.action_name} on {step.tool_name}",
                tool_name=step.tool_name,
                action_name=step.action_name,
                params=step.params,
                dependencies=[],
                status=StepStatus.PENDING
            )
            workflow_steps.append(workflow_step)
        
        # Create workflow
        workflow = WorkflowPlan(
            id=workflow_id,
            title=planner_plan.title,
            description=f"Generated by {planner_plan.planner_used}",
            steps=workflow_steps,
            status=WorkflowStatus.PLANNING,
            user_id=user_id,
            conversation_id=conversation_id,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            metadata={
                'plan_type': planner_plan.plan_type.value,
                'planner_used': planner_plan.planner_used,
                'estimated_duration': planner_plan.estimated_total_duration
            }
        )
        
        return workflow
    
    def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Workflow'u execute et - SEQUENTIAL EXECUTION WITH LOCKING"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Clear step results for this workflow execution
        self.step_results = {}
        
        # EXECUTION LOCK - Prevent parallel execution
        if workflow_id in self._execution_locks:
            logger.warning(f"WORKFLOW LOCK - {workflow_id} is already executing, returning cached result")
            return {
                'workflow_id': workflow_id,
                'steps_executed': [],
                'total_duration': 0,
                'success': False,
                'error': 'Workflow already executing'
            }
        
        # Acquire lock
        self._execution_locks[workflow_id] = datetime.now()
        logger.info(f"WORKFLOW LOCK - Acquired execution lock for {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.now().isoformat()
        
        # Broadcast workflow started
        self._broadcast_workflow_started(workflow.user_id, workflow)
        
        # Create workflow todos for better visibility
        self._create_workflow_todos(workflow)
        
        execution_log = {
            'workflow_id': workflow_id,
            'steps_executed': [],
            'total_duration': 0,
            'success': True,
            'error': None
        }
        
        try:
            # Execute steps starting from current index - STRICT SEQUENTIAL
            logger.info(f"WORKFLOW SEQUENTIAL - Starting execution. Current index: {workflow.current_step_index}, Total steps: {len(workflow.steps)}")
            
            while workflow.current_step_index < len(workflow.steps):
                step_index = workflow.current_step_index
                step = workflow.steps[step_index]
                
                logger.info(f"WORKFLOW SEQUENTIAL - EXECUTING STEP {step_index}: {step.title}")
                logger.info(f"WORKFLOW SEQUENTIAL - Before execution - Index: {workflow.current_step_index}")
                
                # Update todo status to in_progress
                self._update_workflow_todo_status(workflow, step_index, 'in_progress')
                
                # STRICT DEPENDENCY CHECK
                if not self._check_dependencies_strict(step, workflow):
                    logger.error(f"WORKFLOW SEQUENTIAL - DEPENDENCY FAILED for step {step_index}: {step.title}")
                    step.status = StepStatus.FAILED
                    step.error = "Dependencies not met"
                    execution_log['success'] = False
                    # Move to next step even on dependency failure
                    workflow.current_step_index += 1
                    continue
                
                # Execute step - SINGLE THREADED
                step_result = self._execute_step(step, workflow)
                execution_log['steps_executed'].append(step_result)
                
                # GMAIL EXPLICIT LOGGING: Track Gmail tool results
                correlation_id = getattr(workflow, 'correlation_id', 'unknown')
                if 'gmail' in step.tool_name.lower() or 'oauth2' in step.tool_name.lower():
                    gmail_data = step_result.get('result', {}).get('data', {})
                    logger.info(f"GMAIL_STEP_EXECUTED", extra={
                        "correlation_id": correlation_id,
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                        "tool": step.tool_name,
                        "action": step.action_name,
                        "success": step_result.get('success'),
                        "has_gmail_data": bool(gmail_data),
                        "gmail_data_type": type(gmail_data).__name__,
                        "gmail_data_size": len(str(gmail_data)) if gmail_data else 0,
                        "gmail_data_keys": list(gmail_data.keys()) if isinstance(gmail_data, dict) else []
                    })
                
                # DEBUG: Log step result
                logger.info(f"WORKFLOW SEQUENTIAL - COMPLETED STEP {step_index}: {step.title}")
                logger.info(f"WORKFLOW SEQUENTIAL - Step Result Success: {step_result.get('success')}")
                logger.info(f"WORKFLOW SEQUENTIAL - After execution - Index: {workflow.current_step_index}")
                
                # Update todo status based on step result
                todo_status = 'completed' if step_result.get('success') else 'failed'
                self._update_workflow_todo_status(workflow, step_index, todo_status)
                
                # SEQUENTIAL UPDATE - Move to next step FIRST
                workflow.current_step_index += 1
                workflow.updated_at = datetime.now().isoformat()
                logger.info(f"WORKFLOW SEQUENTIAL - INDEX UPDATED to: {workflow.current_step_index}")
                
                # LLM evaluation after each step (SMART EVALUATION) - AFTER index update
                if step_result['success']:
                    evaluation = self._evaluate_step_completion(step, workflow)
                    
                    # Check if workflow needs modification (controlled)
                    if evaluation.get('modify_workflow') and evaluation.get('safe_to_modify', True):
                        modification_result = self._modify_workflow(workflow, evaluation)
                        if modification_result:
                            logger.info(f"Workflow {workflow_id} modified based on LLM evaluation")
                            # Continue from current position after modification - index already updated
                            continue
                
                # Check if workflow should continue
                if not step_result['success'] and step_result.get('critical', True):
                    logger.info(f"WORKFLOW SEQUENTIAL - BREAKING due to failed critical step {step_index}")
                    workflow.status = WorkflowStatus.FAILED
                    execution_log['success'] = False
                    execution_log['error'] = step_result.get('error')
                    
                    # Broadcast workflow failure
                    self._broadcast_workflow_completed(workflow.user_id, workflow.id, workflow.status.value)
                    break
                
                logger.info(f"WORKFLOW SEQUENTIAL - READY FOR NEXT ITERATION. Index: {workflow.current_step_index}, Total: {len(workflow.steps)}")
            
            # Final workflow status - only complete if meaningful progress made
            if workflow.status == WorkflowStatus.RUNNING:
                completed_steps = len([s for s in workflow.steps if s.status == StepStatus.COMPLETED])
                total_steps = len(workflow.steps)
                
                if workflow.current_step_index >= total_steps:
                    if completed_steps == total_steps:
                        workflow.status = WorkflowStatus.COMPLETED  
                        logger.info(f"WORKFLOW COMPLETED - ALL {completed_steps}/{total_steps} steps successful")
                    elif completed_steps > 0:
                        workflow.status = WorkflowStatus.FAILED
                        logger.info(f"WORKFLOW PARTIALLY FAILED - Only {completed_steps}/{total_steps} steps completed")
                    else:
                        workflow.status = WorkflowStatus.FAILED
                        logger.info(f"WORKFLOW FAILED - No steps completed successfully")
                else:
                    # Workflow stopped early but not failed - keep running status
                    logger.info(f"WORKFLOW PAUSED - At step {workflow.current_step_index}/{total_steps}, {completed_steps} completed")
                    return execution_log  # Return without completion broadcast
                
                # CORRELATION TRACKING: Aggregate final results
                final_results = []
                total_data_size = 0
                for step in workflow.steps:
                    if step.result:
                        step_data_size = len(str(step.result.get('data', '')))
                        total_data_size += step_data_size
                        final_results.append({
                            'step_id': step.id,
                            'tool': step.tool_name,
                            'action': step.action_name,
                            'has_data': bool(step.result.get('data')),
                            'data_size': step_data_size
                        })
                
                correlation_id = getattr(execution_log, 'correlation_id', 'unknown')
                logger.info(f"WORKFLOW_COMPLETED", extra={
                    "workflow_id": workflow_id,
                    "correlation_id": correlation_id,
                    "total_steps": len(workflow.steps),
                    "successful_steps": len([s for s in workflow.steps if s.status == StepStatus.COMPLETED]),
                    "total_data_size": total_data_size,
                    "final_results_summary": final_results,
                    "has_final_data": total_data_size > 0
                })
                
                # Broadcast workflow completion
                self._broadcast_workflow_completed(workflow.user_id, workflow.id, workflow.status.value)
            
            return execution_log
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            execution_log['success'] = False
            execution_log['error'] = str(e)
            logger.error(f"Workflow execution failed: {str(e)}")
            
            # Broadcast workflow exception failure
            self._broadcast_workflow_completed(workflow.user_id, workflow_id, workflow.status.value)
            return execution_log
        finally:
            # Release lock
            if workflow_id in self._execution_locks:
                del self._execution_locks[workflow_id]
                logger.info(f"WORKFLOW LOCK - Released execution lock for {workflow_id}")
    
    def _create_workflow_todos(self, workflow):
        """Create todo items for workflow steps"""
        try:
            from tools.internal.todo_manager import get_todo_tool
            
            todo_tool = get_todo_tool()
            todos_data = []
            
            for i, step in enumerate(workflow.steps, 1):
                status = 'pending'
                if i <= workflow.current_step_index:
                    status = 'completed'
                elif i == workflow.current_step_index + 1:
                    status = 'in_progress'
                
                todos_data.append({
                    'id': f"workflow_{workflow.id}_step_{i}",
                    'content': f"Step {i}: {step.title}",
                    'status': status,
                    'priority': 'medium',
                    'workflow_id': workflow.id,
                    'step_id': step.id
                })
            
            result = todo_tool.todo_create(workflow.user_id, todos_data, workflow.id)
            
            if result.get('success'):
                logger.info(f"Created {len(todos_data)} workflow todos for {workflow.id}")
            else:
                logger.error(f"Failed to create workflow todos: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error creating workflow todos: {e}")
    
    def _update_workflow_todo_status(self, workflow, step_index: int, status: str):
        """Update workflow todo status"""
        try:
            from tools.internal.todo_manager import get_todo_tool
            
            todo_tool = get_todo_tool()
            todo_id = f"workflow_{workflow.id}_step_{step_index + 1}"
            
            result = todo_tool.todo_update_status(workflow.user_id, todo_id, status, workflow.id)
            
            if result.get('success'):
                logger.debug(f"Updated workflow todo {todo_id} to {status}")
            else:
                logger.error(f"Failed to update workflow todo: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error updating workflow todo: {e}")
    
    def _check_dependencies_strict(self, step: WorkflowStep, workflow: WorkflowPlan) -> bool:
        """STRICT adım dependencies kontrolü - sequential execution için"""
        
        # Get current step index
        current_step_index = next((i for i, s in enumerate(workflow.steps) if s.id == step.id), -1)
        
        if current_step_index == -1:
            logger.error(f"DEPENDENCY CHECK - Step {step.title} not found in workflow")
            return False
        
        # STRICT RULE: Previous steps must be completed
        for i in range(current_step_index):
            prev_step = workflow.steps[i]
            if prev_step.status != StepStatus.COMPLETED:
                logger.error(f"DEPENDENCY CHECK - Previous step {i} ({prev_step.title}) not completed: {prev_step.status}")
                return False
        
        # Check explicit dependencies
        if step.dependencies:
            for dep_id in step.dependencies:
                dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
                if not dep_step:
                    logger.error(f"DEPENDENCY CHECK - Dependency step {dep_id} not found")
                    return False
                if dep_step.status != StepStatus.COMPLETED:
                    logger.error(f"DEPENDENCY CHECK - Dependency step {dep_step.title} not completed: {dep_step.status}")
                    return False
        
        logger.info(f"DEPENDENCY CHECK - All dependencies met for step {current_step_index}: {step.title}")
        return True
    
    def _check_dependencies(self, step: WorkflowStep, workflow: WorkflowPlan) -> bool:
        """Adım dependencies kontrolü (legacy)"""
        if not step.dependencies:
            return True
        
        for dep_id in step.dependencies:
            dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False
        
        return True
    
    def _execute_step(self, step: WorkflowStep, workflow: WorkflowPlan) -> Dict[str, Any]:
        """Tek bir adımı execute et"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        # Broadcast step started via WebSocket
        self._broadcast_step_update(workflow.user_id, workflow.id, step)
        
        start_time = datetime.now()
        
        try:
            # Check if step requires user input (conflict resolution)
            if step.requires_user_input:
                logger.info(f"CONFLICT RESOLUTION - Step requires user input: {step.title}")
                
                # Execute user clarification tool to get options
                result = registry.execute_tool_action(
                    step.tool_name,
                    step.action_name, 
                    **step.params
                )
                
                # Set step to awaiting user response
                step.status = StepStatus.PENDING  # Keep as pending until user responds
                
                # Return special response indicating user input needed
                return {
                    'success': False,  # Don't mark workflow as complete
                    'requires_user_input': True,
                    'clarification_data': result.data if hasattr(result, 'data') else result,
                    'conflict_info': step.conflict_info,
                    'original_request': step.original_request,
                    'step_id': step.id,
                    'awaiting_user_response': True,
                    'workflow_paused': True
                }
            
            # Parameters'ı resolve et (previous step results)
            # **CHATGPT FIX**: Check if resolve_params returns early exit for display steps
            param_result = self._resolve_step_params(step, workflow)
            
            # If resolve_params returned a complete step result (display step fix), return it immediately
            if isinstance(param_result, dict) and param_result.get('workflow_display_method') == 'direct_transfer':
                logger.info(f"CHATGPT FIX - Early exit from _execute_step for display step: {step.title}")
                return param_result
            
            # Otherwise, param_result should be the resolved_params dict
            resolved_params = param_result
            
            # Tool action'ı execute et
            # Get effective user_id for tool coordinator
            effective_user_id = workflow.user_id
            if effective_user_id == 'anonymous':
                effective_user_id = '2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef'
            
            # Handle internal actions
            if step.tool_name == "__internal__":
                from .tool_coordinator import run_internal_action
                # Build context from previous steps
                step_context = {}
                for prev_step in workflow.steps:
                    if prev_step.result and prev_step.id != step.id:
                        step_context[prev_step.id] = prev_step.result
                
                result_dict = run_internal_action(step.action_name, resolved_params, step_context)
                from .mcp_core import MCPToolResult
                result = MCPToolResult(
                    success=result_dict['success'],
                    data=result_dict.get('data'),
                    error=result_dict.get('error')
                )
            
            # Handle gmail_get_message with multiple IDs
            elif step.tool_name == "google_oauth2_manager" and step.action_name == "gmail_get_message":
                # Check if we need to get multiple messages
                if "message_ids_from" in resolved_params:
                    src_step = resolved_params.get("message_ids_from", "step_1")
                    # Find source step result
                    source_result = None
                    for prev_step in workflow.steps:
                        if prev_step.id == src_step and prev_step.result:
                            source_result = prev_step.result
                            break
                    
                    if source_result:
                        # Extract message IDs
                        messages_data = source_result.get("data", {}).get("messages", {})
                        message_list = messages_data.get("messages", [])
                        
                        # Get details for each message
                        from .tool_coordinator import coordinator
                        messages_full = []
                        for msg in message_list:
                            msg_id = msg.get("id")
                            if msg_id:
                                tool_call = {
                                    'tool': step.tool_name,
                                    'action': step.action_name,
                                    'params': {"message_id": msg_id, "format": "metadata"}
                                }
                                msg_result = coordinator._execute_tool_call(tool_call, user_id=effective_user_id)
                                if msg_result.get('success'):
                                    messages_full.append(msg_result['data'])
                        
                        from .mcp_core import MCPToolResult
                        result = MCPToolResult(
                            success=True,
                            data={"messages": messages_full}
                        )
                    else:
                        from .mcp_core import MCPToolResult
                        result = MCPToolResult(success=False, error="Source step result not found")
                else:
                    # Single message call
                    from .tool_coordinator import coordinator
                    tool_call = {
                        'tool': step.tool_name,
                        'action': step.action_name,
                        'params': resolved_params
                    }
                    result_dict = coordinator._execute_tool_call(tool_call, user_id=effective_user_id)
                    from .mcp_core import MCPToolResult
                    result = MCPToolResult(
                        success=result_dict['success'],
                        data=result_dict.get('data'),
                        error=result_dict.get('error'),
                        metadata=result_dict.get('metadata')
                    )
            
            # Execute with user context for OAuth2 and Gmail tools
            elif step.tool_name in ['google_oauth2_manager', 'gmail_helper']:
                from .tool_coordinator import coordinator
                tool_call = {
                    'tool': step.tool_name,
                    'action': step.action_name,
                    'params': resolved_params
                }
                result_dict = coordinator._execute_tool_call(tool_call, user_id=effective_user_id)
                
                # Convert to MCPToolResult format
                from .mcp_core import MCPToolResult
                result = MCPToolResult(
                    success=result_dict['success'],
                    data=result_dict.get('data'),
                    error=result_dict.get('error'),
                    metadata=result_dict.get('metadata')
                )
            else:
                # Regular tool execution
                result = registry.execute_tool_action(
                    step.tool_name,
                    step.action_name,
                    **resolved_params
                )
            
            # Clean base64 data from result before storing, except for visual creator display steps
            is_visual_display_step = (
                step.tool_name == "simple_visual_creator" and 
                step.action_name == "load_and_display_image"
            )
            
            if is_visual_display_step:
                # Preserve image data for display steps
                cleaned_data = result.data
                logger.info(f"WORKFLOW IMAGE FIX - Preserving image data for display step: {step.title}")
            else:
                # Clean base64 data for other steps to prevent context overflow
                cleaned_data = self._clean_base64_from_data(result.data) if result.data else None
            
            # Sonuçları kaydet
            step.result = {
                'success': result.success,
                'data': cleaned_data,
                'error': result.error,
                'metadata': result.metadata
            }
            
            # Store result in step_results for context passing
            self.step_results[step.id] = step.result
            
            if result.success:
                step.status = StepStatus.COMPLETED
            else:
                step.status = StepStatus.FAILED
                step.error = result.error
            
            step.completed_at = datetime.now().isoformat()
            
            # Log tool operation to graph memory
            try:
                from tool_capability_manager import log_user_tool_operation
                log_user_tool_operation(
                    user_id=workflow.user_id,
                    tool_name=step.tool_name,
                    action_name=step.action_name,
                    result_data={
                        'success': result.success,
                        'error': result.error,
                        'step_id': step.id,
                        'workflow_id': workflow.id
                    },
                    parameters=resolved_params
                )
                logger.info(f"TOOL OPERATION LOGGED: {step.tool_name}.{step.action_name} for user {workflow.user_id}")
            except Exception as e:
                logger.warning(f"Failed to log tool operation: {e}")
            
            # Broadcast step completion via WebSocket
            self._broadcast_step_update(workflow.user_id, workflow.id, step)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'step_id': step.id,
                'success': result.success,
                'duration': duration,
                'result': step.result,
                'error': step.error
            }
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now().isoformat()
            
            # Broadcast step failure via WebSocket  
            self._broadcast_step_update(workflow.user_id, workflow.id, step)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'step_id': step.id,
                'success': False,
                'duration': duration,
                'error': str(e)
            }
    
    def _resolve_step_params(self, step: WorkflowStep, workflow: WorkflowPlan) -> Dict[str, Any]:
        """Step parameters'ını resolve et"""
        
        # Write debug to file for _resolve_step_params entry
        try:
            with open("/home/ahmet/MetisAgent/MetisAgent2/resolve_params_debug.txt", "w") as f:
                f.write(f"_resolve_step_params CALLED\n")
                f.write(f"Step: {step.title}\n")
                f.write(f"Tool: {step.tool_name}\n")
                f.write(f"Action: {step.action_name}\n")
                f.write(f"Step params: {step.params}\n")
        except Exception as e:
            logger.error(f"Debug file write error: {e}")
        
        resolved_params = step.params.copy()
        
        # DEBUG: Log original parameters
        logger.info(f"PARAM DEBUG - Original params for {step.tool_name}: {resolved_params}")
        
        # Clean base64 data from parameters to prevent LLM context overflow
        resolved_params = self._clean_base64_from_data(resolved_params)
        
        # LLM tool parameter fixes - MOVED UP for broader coverage
        if step.tool_name == "llm_tool":
            logger.info(f"LLM TOOL DEBUG - Processing step: '{step.title}' | Description: '{step.description}'")
            
            # Check for use_extracted_subjects parameter - PRIMARY DETECTION METHOD
            if resolved_params.get('use_extracted_subjects') == True:
                logger.info(f"LLM TOOL DEBUG - Detected use_extracted_subjects=True parameter")
                
                # Extract Gmail subjects from workflow
                gmail_subjects = self._extract_gmail_subjects_from_workflow(workflow)
                logger.info(f"GMAIL SUBJECT DEBUG - Found {len(gmail_subjects)} subjects via use_extracted_subjects")
                
                if gmail_subjects:
                    # Inject extracted subjects into the LLM message
                    original_message = resolved_params.get('message', 'Gmail subject bilgilerini göster')
                    subjects_text = "\n".join([f"• {subject}" for subject in gmail_subjects])
                    
                    # Create enhanced message with extracted subjects
                    enhanced_message = f"{original_message}\n\nÇıkarılan Gmail Konuları:\n{subjects_text}"
                    
                    resolved_params = {
                        "message": enhanced_message,
                        "conversation_id": workflow.conversation_id,
                        "enable_tools": False
                    }
                    
                    # Remove the use_extracted_subjects parameter as it's not a valid LLM tool param
                    resolved_params.pop('use_extracted_subjects', None)
                    
                    logger.info(f"GMAIL SUBJECT FIX - Injected {len(gmail_subjects)} subjects into LLM message via use_extracted_subjects")
                else:
                    # No subjects found, provide fallback
                    original_message = resolved_params.get('message', 'Gmail subject bilgilerini göster')
                    resolved_params = {
                        "message": f"{original_message}\n\nDikkat: Önceki adımlardan Gmail subject bilgileri çıkarılamadı.",
                        "conversation_id": workflow.conversation_id,
                        "enable_tools": False
                    }
                    resolved_params.pop('use_extracted_subjects', None)
                    logger.info("GMAIL SUBJECT FIX - No subjects found, using fallback via use_extracted_subjects")
            
            # Fallback: Special Gmail subject workflow detection (legacy detection)
            elif (("subject" in step.title.lower() or "subject" in step.description.lower() or 
                   "gmail" in workflow.title.lower() or "email" in workflow.title.lower()) and
                  ("display" in step.title.lower() or "show" in step.title.lower() or "present" in step.title.lower() or 
                   "display" in step.description.lower() or "present" in step.description.lower())):
                
                # This is likely a Gmail subject display step 
                gmail_subjects = self._extract_gmail_subjects_from_workflow(workflow)
                logger.info(f"GMAIL SUBJECT DEBUG - Detected Gmail workflow display step (legacy), found {len(gmail_subjects)} subjects")
                
                if gmail_subjects:
                    # Convert to a direct response instead of using LLM
                    subjects_text = "\n".join([f"• {subject}" for subject in gmail_subjects])
                    resolved_params = {
                        "message": f"Son 3 Gmail Konusu:\n\n{subjects_text}",
                        "conversation_id": workflow.conversation_id,
                        "enable_tools": False
                    }
                    logger.info(f"GMAIL SUBJECT FIX - Converted display step to show subjects (legacy): {len(gmail_subjects)} found")
                else:
                    # Fallback: provide basic parameters for LLM tool with extracted data attempt
                    all_workflow_data = self._extract_all_data_from_workflow(workflow)
                    resolved_params = {
                        "message": f"Gmail workflow tamamlandı. Önceki adımlardan veriler alındı ama subject extract edilemedi. Raw data: {str(all_workflow_data)[:500]}...",
                        "conversation_id": workflow.conversation_id,
                        "enable_tools": False
                    }
                    logger.info("GMAIL SUBJECT FIX - No subjects found, using fallback with workflow data (legacy)")
            else:
                # General LLM tool parameter handling
                # Ensure required parameters are present
                if "message" not in resolved_params:
                    # If no message, create from step description/title
                    base_message = step.description or step.title or "Process workflow step"
                    
                    # Add context from previous steps for better processing
                    context_info = []
                    for dep_id in step.dependencies:
                        if dep_id in self.step_results:
                            dep_result = self.step_results[dep_id]
                            if dep_result.get('success') and dep_result.get('data'):
                                # Add relevant context from previous step
                                context_info.append(f"Previous step data: {dep_result['data']}")
                    
                    if context_info:
                        resolved_params["message"] = f"{base_message}\n\nContext from previous steps:\n" + "\n".join(context_info)
                    else:
                        resolved_params["message"] = base_message
                
                # Always ensure conversation_id is present
                if "conversation_id" not in resolved_params:
                    resolved_params["conversation_id"] = workflow.conversation_id
                
                # Ensure user_id is present for LLM tool
                if "user_id" not in resolved_params:
                    resolved_params["user_id"] = workflow.user_id
                
                # Ensure conversation_name is present (LLM tool requires this)
                if "conversation_name" not in resolved_params:
                    resolved_params["conversation_name"] = f"workflow_{workflow.id}"
                
                # Default enable_tools to False unless specified
                if "enable_tools" not in resolved_params:
                    resolved_params["enable_tools"] = False
                    
                # Remove any unexpected parameters that might cause "source" errors
                allowed_llm_params = {"message", "conversation_id", "user_id", "conversation_name", "enable_tools", "max_tokens", "temperature"}
                resolved_params = {k: v for k, v in resolved_params.items() if k in allowed_llm_params}
                
                logger.info(f"LLM TOOL FIX - General parameter cleaning: {resolved_params}")
        
        # Sequential thinking tool parameter fixes
        elif step.tool_name == "sequential_thinking":
            if step.action_name == "break_down_task":
                # Map 'task' parameter to 'task_description' which is required
                if "task" in resolved_params and "task_description" not in resolved_params:
                    resolved_params["task_description"] = resolved_params.pop("task")
                    logger.info(f"SEQUENTIAL FIX - Mapped 'task' to 'task_description': {resolved_params['task_description']}")
                
                # Add context from previous steps if available
                if "response" in resolved_params and resolved_params["response"] == "from_previous_step":
                    context_data = []
                    for dep_id in step.dependencies:
                        if dep_id in self.step_results:
                            dep_result = self.step_results[dep_id]
                            if dep_result.get('success') and dep_result.get('data'):
                                context_data.append(str(dep_result['data']))
                    
                    if context_data:
                        resolved_params["context"] = "\n".join(context_data)
                        logger.info(f"SEQUENTIAL FIX - Added context from previous steps")
                    
                    # Remove the invalid 'response' parameter
                    resolved_params.pop("response", None)
                
                # Ensure user_id is present
                if "user_id" not in resolved_params:
                    resolved_params["user_id"] = workflow.user_id
                
                logger.info(f"SEQUENTIAL FIX - Final parameters: {resolved_params}")
        
        # Tool-specific parameter mapping fixes
        elif step.tool_name == "simple_visual_creator":
            logger.info(f"PARAM DEBUG - Visual creator step parameters: {resolved_params}")
            
            # Check if this is a display step (step title/description contains "display")
            is_display_step = any(keyword in step.title.lower() or keyword in step.description.lower() 
                                for keyword in ['display', 'show', 'load'])
            
            # **CRITICAL DEBUG**: Log display step detection
            logger.info(f"DISPLAY STEP DEBUG - Step: '{step.title}' | Tool: {step.tool_name} | Action: {step.action_name}")
            logger.info(f"DISPLAY STEP DEBUG - Keywords check: {[(kw, kw in step.title.lower() or kw in step.description.lower()) for kw in ['display', 'show', 'load']]}")
            logger.info(f"DISPLAY STEP DEBUG - is_display_step: {is_display_step}")
            
            # Display step için image_path parameter'ını set et ve image_source'u temizle
            if is_display_step:
                logger.info("DISPLAY STEP - Setting up image_path parameter from previous steps")
                
                # Completely clear the resolved_params for display steps and rebuild properly
                image_path_found = None
                
                # Find image path from previous steps
                for prev_step_id in reversed(list(self.step_results.keys())):
                    prev_result = self.step_results[prev_step_id]
                    if prev_result.get('success') and prev_result.get('data'):
                        prev_data = prev_result['data']
                        # Check for saved image path in different possible locations
                        if 'saved_path' in prev_data:
                            image_path_found = prev_data['saved_path']
                            break
                        elif 'successful_generations' in prev_data and prev_data['successful_generations']:
                            first_gen = prev_data['successful_generations'][0]
                            if 'data' in first_gen and 'saved_path' in first_gen['data']:
                                image_path_found = first_gen['data']['saved_path']
                                break
                
                if image_path_found:
                    # Clear all params and set only what's needed - display method only accepts image_path
                    resolved_params = {
                        'image_path': image_path_found
                    }
                    logger.info(f"DISPLAY STEP - Set clean params: {resolved_params}")
                else:
                    logger.error("DISPLAY STEP - No image path found in previous steps!")
                    resolved_params = {'image_path': ''}
            
            # Normal parameter processing continues
            # Map common parameter names to correct ones for generation steps  
            if "source" in resolved_params and "prompt" not in resolved_params:
                resolved_params["prompt"] = resolved_params.pop("source")
                logger.info(f"Mapped 'source' to 'prompt' for visual creator: {resolved_params['prompt']}")
            elif "description" in resolved_params and "prompt" not in resolved_params:
                resolved_params["prompt"] = resolved_params.pop("description") 
                logger.info(f"Mapped 'description' to 'prompt' for visual creator: {resolved_params['prompt']}")
            elif "text" in resolved_params and "prompt" not in resolved_params:
                resolved_params["prompt"] = resolved_params.pop("text")
                logger.info(f"Mapped 'text' to 'prompt' for visual creator: {resolved_params['prompt']}")
            
            # Also check for missing prompt entirely and add from step description if needed
            # BUT NOT for display steps - they use image_path, not prompt
            if "prompt" not in resolved_params and not is_display_step:
                # Extract prompt from step description or title
                prompt_text = step.description or step.title or "generate image"
                resolved_params["prompt"] = prompt_text
                logger.info(f"Added missing prompt from step description: {prompt_text}")
                
            logger.info(f"PARAM DEBUG - Final visual creator params: {resolved_params}")
        
        elif step.tool_name == "gmail_helper":
            # Gmail parameter corrections - reverse mapping: to → recipient
            if "to" in resolved_params and "recipient" not in resolved_params:
                resolved_params["recipient"] = resolved_params.pop("to")
            if "email_subject" in resolved_params and "subject" not in resolved_params:
                resolved_params["subject"] = resolved_params.pop("email_subject")
            
            # Auto-inject message_id for get_email_details from previous steps
            if step.action_name == "get_email_details" and ("message_id" not in resolved_params or resolved_params.get("message_id") == "to_be_extracted"):
                # Find previous step with message data
                for prev_step in reversed(workflow.steps):
                    if (prev_step.status == StepStatus.COMPLETED and 
                        prev_step.result and prev_step.result.get('success') and
                        prev_step.tool_name == "gmail_helper"):
                        
                        data = prev_step.result.get('data', {})
                        # Check if previous step has message with id
                        if 'message' in data and isinstance(data['message'], dict):
                            message_id = data['message'].get('id')
                            if message_id:
                                resolved_params['message_id'] = message_id
                                logger.info(f"Auto-injected message_id from previous Gmail step: {message_id}")
                                break
                        # Also check messages list format
                        elif 'messages' in data:
                            messages = data['messages']
                            if isinstance(messages, dict) and messages:
                                first_message = list(messages.values())[0]
                                if isinstance(first_message, dict) and 'id' in first_message:
                                    resolved_params['message_id'] = first_message['id']
                                    logger.info(f"Auto-injected message_id from messages dict: {first_message['id']}")
                                    break
                            elif isinstance(messages, list) and messages:
                                if 'id' in messages[0]:
                                    resolved_params['message_id'] = messages[0]['id']
                                    logger.info(f"Auto-injected message_id from messages list: {messages[0]['id']}")
                                    break
        
        elif step.tool_name == "google_oauth2_manager":
            # Google OAuth2 Manager Gmail operations
            if step.action_name in ["gmail_get_message", "get_email_details"] and "message_id" not in resolved_params:
                # Auto-inject message_id from previous Gmail list step
                for prev_step in reversed(workflow.steps):
                    if (prev_step.status == StepStatus.COMPLETED and 
                        prev_step.result and 
                        prev_step.tool_name in ["google_oauth2_manager", "gmail_helper"]):
                        
                        data = prev_step.result.get('data', {})
                        messages = data.get('messages', {}).get('messages', [])
                        if messages:
                            resolved_params['message_id'] = messages[0].get('id')
                            logger.info(f"Auto-injected message_id from previous Gmail step: {resolved_params['message_id']}")
                            break
            
            # Gmail subject workflow special handling - auto-resolve to multiple message IDs
            elif (step.action_name == "gmail_get_message" and 
                  ("subject" in step.title.lower() or "subject" in step.description.lower())):
                # This is likely a Gmail subject extraction step
                message_ids = []
                for prev_step in reversed(workflow.steps):
                    if (prev_step.status == StepStatus.COMPLETED and 
                        prev_step.result and 
                        prev_step.tool_name in ["google_oauth2_manager", "gmail_helper"]):
                        
                        data = prev_step.result.get('data', {})
                        messages = data.get('messages', {}).get('messages', [])
                        # Get all message IDs for subject extraction
                        message_ids = [msg.get('id') for msg in messages if msg.get('id')]
                        break
                
                if message_ids:
                    # Store message IDs for batch processing
                    resolved_params['message_ids'] = message_ids
                    resolved_params['message_id'] = message_ids[0]  # Primary message ID
                    logger.info(f"Auto-injected {len(message_ids)} message IDs for subject extraction")
        
        # Auto-add user_id for Gmail and Google OAuth2 tools
        elif step.tool_name in ['gmail_helper', 'google_oauth2_manager'] and 'user_id' not in resolved_params:
            try:
                from tools.settings_manager import settings_manager
                
                # If workflow user is anonymous, use the known authenticated user
                target_user_id = workflow.user_id
                if target_user_id == 'anonymous':
                    target_user_id = '2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef'  # Known authenticated user
                    logger.info(f"Using fallback user_id for anonymous: {target_user_id}")
                
                google_credentials = settings_manager.get_google_credentials(target_user_id)
                if google_credentials and google_credentials.get('email'):
                    resolved_params['user_id'] = google_credentials['email']
                    logger.info(f"Auto-added user_id for {step.tool_name}: {google_credentials['email']}")
                else:
                    logger.warning(f"No Google credentials found for user {target_user_id}")
                    resolved_params['user_id'] = target_user_id  # Use workflow user_id as fallback
            except Exception as e:
                logger.error(f"Error auto-adding user_id: {e}")
                resolved_params['user_id'] = workflow.user_id  # Final fallback
        
        # Also handle legacy 'auto' user_id parameter
        elif 'user_id' in resolved_params and resolved_params['user_id'] == 'auto':
            # Get actual Gmail account from workflow user
            try:
                from tools.settings_manager import settings_manager
                
                # If workflow user is anonymous, use the known authenticated user
                target_user_id = workflow.user_id
                if target_user_id == 'anonymous':
                    target_user_id = '2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef'  # Known authenticated user
                    logger.info(f"Using fallback user_id for anonymous: {target_user_id}")
                
                google_credentials = settings_manager.get_google_credentials(target_user_id)
                if google_credentials and google_credentials.get('email'):
                    resolved_params['user_id'] = google_credentials['email']
                    logger.info(f"Resolved user_id from 'auto' to {google_credentials['email']}")
                else:
                    logger.warning(f"No Google credentials found for user {target_user_id}")
                    # Keep 'auto' and let tool_coordinator handle it
            except Exception as e:
                logger.error(f"Error resolving user_id: {e}")
        
        # Social Media Workflow special handling - auto-inject campaign_id
        elif step.tool_name == "social_media_workflow":
            if step.action_name == "add_campaign_asset" and "campaign_id" not in resolved_params:
                # Auto-inject campaign_id from previous create_campaign step
                for prev_step in reversed(workflow.steps):
                    if (prev_step.status == StepStatus.COMPLETED and 
                        prev_step.result and 
                        prev_step.tool_name == "social_media_workflow" and
                        "create_campaign" in prev_step.action_name):
                        
                        data = prev_step.result.get('data', {})
                        if 'campaign_id' in data:
                            resolved_params['campaign_id'] = data['campaign_id']
                            logger.info(f"Auto-injected campaign_id from previous step: {resolved_params['campaign_id']}")
                            break
            
            elif step.action_name == "submit_for_approval" and "campaign_id" not in resolved_params:
                # Auto-inject campaign_id from previous step
                for prev_step in reversed(workflow.steps):
                    if (prev_step.status == StepStatus.COMPLETED and 
                        prev_step.result and 
                        prev_step.tool_name == "social_media_workflow"):
                        
                        data = prev_step.result.get('data', {})
                        if 'campaign_id' in data:
                            resolved_params['campaign_id'] = data['campaign_id']
                            logger.info(f"Auto-injected campaign_id for approval: {resolved_params['campaign_id']}")
                            break
            
            elif step.action_name == "execute_workflow_step":
                # Auto-inject campaign_id from create_campaign step
                if "campaign_id" not in resolved_params or resolved_params.get("campaign_id") == "from_previous_step":
                    for prev_step in reversed(workflow.steps):
                        if (prev_step.status == StepStatus.COMPLETED and 
                            prev_step.result and 
                            prev_step.tool_name == "social_media_workflow" and
                            "create_campaign" in prev_step.action_name):
                            
                            data = prev_step.result.get('data', {})
                            if 'campaign_id' in data:
                                resolved_params['campaign_id'] = data['campaign_id']
                                logger.info(f"Auto-injected campaign_id for workflow step: {resolved_params['campaign_id']}")
                                break
                
                # Set step_name dynamically based on workflow progress
                if "step_name" not in resolved_params or resolved_params["step_name"] == "briefing":
                    # Determine which step to execute next based on completed steps
                    step_sequence = ["briefing", "creative_ideation", "content_creation", "sharing_content", 
                                   "visual_production", "approval", "scheduling", "monitoring"]
                    
                    completed_steps = set()
                    for prev_step in workflow.steps:
                        if (prev_step.status == StepStatus.COMPLETED and 
                            prev_step.tool_name == "social_media_workflow" and
                            prev_step.action_name == "execute_workflow_step"):
                            # Try to extract step_name from previous executions
                            prev_data = prev_step.result.get('data', {})
                            if 'step_name' in prev_data:
                                completed_steps.add(prev_data['step_name'])
                    
                    # Find next step to execute
                    next_step = "briefing"  # Default
                    for step_name in step_sequence:
                        if step_name not in completed_steps:
                            next_step = step_name
                            break
                    
                    resolved_params['step_name'] = next_step
                    logger.info(f"Set next workflow step: {next_step} (completed: {list(completed_steps)})")

        # Resolve from_previous_step parameters
        for key, value in resolved_params.items():
            if isinstance(value, str):
                if value.startswith('from_previous_step'):
                    # Previous step'den değer al
                    resolved_value = self._extract_value_from_previous_steps(value, workflow)
                    if resolved_value is not None:
                        resolved_params[key] = resolved_value
                elif '{' in value and '}' in value:
                    # Handle placeholder replacements like {subject_from_step2}
                    resolved_params[key] = self._resolve_placeholders(value, workflow)
                    logger.info(f"PLACEHOLDER FIX - Resolved '{value}' to '{resolved_params[key]}'")
                    
        
        # Write debug about what we're returning
        try:
            with open("/home/ahmet/MetisAgent/MetisAgent2/resolve_return_debug.txt", "w") as f:
                f.write(f"_resolve_step_params RETURNING:\n")
                f.write(f"Type: {type(resolved_params)}\n")
                f.write(f"Value: {resolved_params}\n")
                if isinstance(resolved_params, dict):
                    f.write(f"Has workflow_display_method: {'workflow_display_method' in resolved_params}\n")
                    f.write(f"workflow_display_method value: {resolved_params.get('workflow_display_method')}\n")
                f.write(f"ERROR: This should not happen for display steps!\n")
        except Exception as e:
            logger.error(f"Resolve return debug error: {e}")
        
        return resolved_params
    
    def _resolve_placeholders(self, text: str, workflow: WorkflowPlan) -> str:
        """Resolve placeholders like {subject_from_step2} in text"""
        import re
        
        # Find all placeholders in format {variable_name}
        placeholders = re.findall(r'\{([^}]+)\}', text)
        
        for placeholder in placeholders:
            replacement = None
            
            # Handle step-specific references like subject_from_step2
            if '_from_step' in placeholder:
                parts = placeholder.split('_from_step')
                if len(parts) == 2:
                    var_name = parts[0]  # e.g., "subject"
                    step_ref = parts[1]  # e.g., "2"
                    
                    # Find the referenced step
                    step_id = f"step{step_ref}" if step_ref.isdigit() else step_ref
                    
                    for step in workflow.steps:
                        if step.id == step_id and step.result and step.result.get('success'):
                            step_data = step.result.get('data', {})
                            
                            # Look for the variable in step data
                            if var_name in step_data:
                                replacement = str(step_data[var_name])
                            elif 'extracted_subjects' in step_data and var_name == 'subject':
                                # Special case for Gmail subjects
                                subjects = step_data['extracted_subjects']
                                if isinstance(subjects, list) and len(subjects) > 1:
                                    replacement = subjects[1]  # Second subject
                            elif isinstance(step_data, str) and var_name == 'subject':
                                # If step data is a string, use it as subject
                                replacement = step_data
                            break
            
            # Replace the placeholder if we found a value
            if replacement:
                text = text.replace(f'{{{placeholder}}}', replacement)
                logger.info(f"PLACEHOLDER - Replaced {{{placeholder}}} with: {replacement}")
            else:
                logger.warning(f"PLACEHOLDER - Could not resolve {{{placeholder}}}")
        
        return text
    
    def _extract_gmail_subjects_from_workflow(self, workflow: WorkflowPlan) -> List[str]:
        """Extract Gmail subjects from previous workflow steps"""
        subjects = []
        
        try:
            # Look through completed steps for Gmail data
            for step in workflow.steps:
                if (step.status == StepStatus.COMPLETED and 
                    step.result and 
                    step.result.get('success') and 
                    step.result.get('data')):
                    
                    data = step.result['data']
                    
                    # Check for Gmail helper results with messages
                    if isinstance(data, dict):
                        # Check for auto-extracted subjects from Gmail list operation
                        if 'extracted_subjects' in data:
                            extracted = data['extracted_subjects']
                            if isinstance(extracted, list):
                                for subject in extracted:
                                    if subject and subject not in subjects:
                                        subjects.append(subject)
                                        logger.info(f"GMAIL EXTRACT - Found auto-extracted subject: {subject}")
                        
                        # Check for Gmail API metadata format (single message)
                        elif 'message' in data and isinstance(data['message'], dict):
                            message = data['message']
                            subject = self._extract_subject_from_gmail_message(message)
                            if subject and subject not in subjects:
                                subjects.append(subject)
                                logger.info(f"GMAIL EXTRACT - Found subject from message: {subject}")
                        
                        # Look for messages in various formats (message list)
                        messages_data = None
                        
                        if 'messages' in data:
                            if isinstance(data['messages'], dict) and 'messages' in data['messages']:
                                messages_data = data['messages']['messages']
                            elif isinstance(data['messages'], list):
                                messages_data = data['messages']
                        elif 'data' in data and isinstance(data['data'], dict) and 'messages' in data['data']:
                            messages_data = data['data']['messages']
                        
                        # Extract subjects from message list
                        if messages_data and isinstance(messages_data, list):
                            for msg in messages_data[:3]:  # Take first 3
                                if isinstance(msg, dict):
                                    # Try direct subject field first (older format)
                                    subject = msg.get('subject', '').strip()
                                    if not subject:
                                        # Try Gmail API metadata format
                                        subject = self._extract_subject_from_gmail_message(msg)
                                    
                                    if subject and subject not in subjects:
                                        subjects.append(subject)
                                        logger.info(f"GMAIL EXTRACT - Found subject from message list: {subject}")
                                        
                        # Also check for direct subject in data
                        elif 'subject' in data:
                            subject = data['subject'].strip()
                            if subject and subject not in subjects:
                                subjects.append(subject)
                                logger.info(f"GMAIL EXTRACT - Found direct subject: {subject}")
            
            logger.info(f"GMAIL EXTRACT - Found {len(subjects)} subjects total: {subjects}")
            return subjects[:3]  # Return max 3 subjects
            
        except Exception as e:
            logger.error(f"Error extracting Gmail subjects: {e}")
            return []
    
    def _extract_subject_from_gmail_message(self, message: Dict) -> str:
        """Extract subject from a Gmail API message object (metadata format)"""
        try:
            # Check for Gmail API metadata format: message.payload.headers
            if 'payload' in message and 'headers' in message['payload']:
                headers = message['payload']['headers']
                for header in headers:
                    if header.get('name') == 'Subject':
                        return header.get('value', '').strip()
            
            # Fallback: check for direct subject field
            return message.get('subject', '').strip()
            
        except Exception as e:
            logger.error(f"Error extracting subject from message: {e}")
            return ''
    
    def _extract_all_data_from_workflow(self, workflow: WorkflowPlan) -> Dict:
        """Extract all data from completed workflow steps for debugging"""
        all_data = {}
        
        try:
            for i, step in enumerate(workflow.steps):
                if (step.status == StepStatus.COMPLETED and 
                    step.result and 
                    step.result.get('success') and 
                    step.result.get('data')):
                    
                    step_key = f"step_{i+1}_{step.tool_name}"
                    all_data[step_key] = step.result['data']
                    
            return all_data
            
        except Exception as e:
            logger.error(f"Error extracting all workflow data: {e}")
            return {}
    
    def _extract_value_from_previous_steps(self, instruction: str, workflow: WorkflowPlan) -> Any:
        """Previous step'lerden değer extract et"""
        try:
            # "from_previous_step.messages[0].id" gibi formatlar
            if instruction == "from_previous_step":
                # Son completed step'in sonucunu al
                for step in reversed(workflow.steps):
                    if step.status == StepStatus.COMPLETED and step.result:
                        return step.result.get('data')
            
            # Daha specific extraction logic
            if instruction.startswith("from_previous_step."):
                path = instruction.replace("from_previous_step.", "")
                for step in reversed(workflow.steps):
                    if step.status == StepStatus.COMPLETED and step.result:
                        data = step.result.get('data', {})
                        
                        # Simple path navigation
                        if path == "messages[0].id":
                            messages = data.get('messages', {}).get('messages', [])
                            if messages:
                                return messages[0].get('id')
                        elif path == "id":
                            return data.get('id')
                        elif path == "message_id":
                            return data.get('message_id')
                        
                        # Try direct attribute access
                        try:
                            keys = path.split('.')
                            current = data
                            for key in keys:
                                if '[' in key and ']' in key:
                                    # Array access like messages[0]
                                    array_name = key.split('[')[0]
                                    index = int(key.split('[')[1].split(']')[0])
                                    current = current.get(array_name, [])[index]
                                else:
                                    current = current.get(key)
                            return current
                        except:
                            continue
            
            logger.warning(f"Could not extract value from instruction: {instruction}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting value from previous steps: {e}")
            return None
    
    def _filter_relevant_examples(self, user_input: str, usage_examples: List[Dict]) -> List[Dict]:
        """Kullanıcı input'una göre ilgili örnekleri filtrele"""
        try:
            user_input_lower = user_input.lower()
            relevant_examples = []
            
            for example in usage_examples:
                workflow = example['workflow']
                
                # User request examples'ı kontrol et
                for request_example in workflow.user_request_examples:
                    if self._is_intent_match(user_input_lower, request_example.lower()):
                        relevant_examples.append(example)
                        break
                
                # Tool name match
                if example['tool_name'] in user_input_lower:
                    relevant_examples.append(example)
                
            # En fazla 5 örnek döndür
            return relevant_examples[:5]
            
        except Exception as e:
            logger.error(f"Error filtering relevant examples: {e}")
            return []
    
    def _is_intent_match(self, user_input: str, example_request: str) -> bool:
        """İki text arasında intent benzerliği kontrol et"""
        try:
            # Basit keyword matching
            user_keywords = set(user_input.split())
            example_keywords = set(example_request.split())
            
            # Common keywords ratio
            common_keywords = user_keywords.intersection(example_keywords)
            if len(common_keywords) >= 2:  # En az 2 ortak kelime
                return True
            
            # Specific intent keywords
            intent_keywords = {
                'login': ['giriş', 'login', 'oturum', 'gir'],
                'upload': ['yükle', 'upload', 'paylaş', 'share'],
                'install': ['yükle', 'install', 'kur', 'ekle'],
                'send': ['gönder', 'send', 'yolla'],
                'get': ['getir', 'get', 'al', 'bilgi']
            }
            
            for intent, keywords in intent_keywords.items():
                user_has_intent = any(keyword in user_input for keyword in keywords)
                example_has_intent = any(keyword in example_request for keyword in keywords)
                
                if user_has_intent and example_has_intent:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in intent matching: {e}")
            return False
    
    def _format_usage_examples(self, relevant_examples: List[Dict]) -> str:
        """Usage examples'ları formatted string olarak döndür"""
        try:
            if not relevant_examples:
                return "No relevant usage examples found for this request."
            
            formatted_examples = []
            
            for example in relevant_examples:
                workflow = example['workflow']
                tool_name = example['tool_name']
                
                example_text = f"""
EXAMPLE: {workflow.title} ({tool_name})
Description: {workflow.description}
Complexity: {workflow.complexity} | Duration: {workflow.estimated_duration}s

User Request Examples:
{chr(10).join(f'  - "{req}"' for req in workflow.user_request_examples)}

Workflow Steps:
{chr(10).join(f'  {i+1}. {step.get("title", "Step")} -> {step.get("tool_name", "unknown")}.{step.get("action_name", "unknown")}' for i, step in enumerate(workflow.steps))}

Example Implementation:
{{
  "title": "{workflow.title}",
  "steps": {json.dumps(workflow.steps, indent=4)}
}}
"""
                formatted_examples.append(example_text)
            
            return "\n" + "="*80 + "\n".join(formatted_examples) + "="*80
            
        except Exception as e:
            logger.error(f"Error formatting usage examples: {e}")
            return "Error formatting usage examples."
    
    def _evaluate_step_completion(self, step: WorkflowStep, workflow: WorkflowPlan) -> Dict[str, Any]:
        """Adım tamamlandıktan sonra LLM evaluation - SMART & CONTROLLED"""
        
        # Prevent infinite loop - check modification history
        current_time = datetime.now()
        workflow_key = f"{workflow.id}_{step.id}"
        
        if workflow_key in self.workflow_eval_cache:
            last_eval_time, eval_count = self.workflow_eval_cache[workflow_key]
            time_diff = (current_time - last_eval_time).total_seconds()
            
            # If evaluated recently (< 30 seconds) or too many evals, skip
            if time_diff < 30 or eval_count >= 2:
                logger.info(f"Skipping evaluation for {workflow_key} - recently evaluated or too many attempts")
                return {
                    'step_successful': step.status == StepStatus.COMPLETED,
                    'continue_workflow': True,
                    'modify_workflow': False,
                    'safe_to_modify': False
                }
        
        # Update eval cache
        eval_count = self.workflow_eval_cache.get(workflow_key, (None, 0))[1] + 1
        self.workflow_eval_cache[workflow_key] = (current_time, eval_count)
        
        # Clean base64 data from step result to prevent LLM context overflow
        cleaned_step_result = self._clean_base64_from_data(step.result) if step.result else {}
        
        evaluation_prompt = f"""
Evaluate workflow step completion: {step.tool_name}.{step.action_name}

RULES: Only modify if clear failure. DO NOT modify successful steps.

STATUS:
- Step: {step.title}
- Success: {cleaned_step_result.get('success', False)}
- Error: {cleaned_step_result.get('error', 'None')}
- Has Data: {bool(cleaned_step_result.get('data'))}

SUMMARY: {json.dumps(summarize_for_llm(step.result) if step.result else {}, indent=2)}

EXECUTION ANALYSIS:
- Success: {cleaned_step_result.get('success', False)}
- Error: {cleaned_step_result.get('error', 'None')}
- Data Received: {bool(cleaned_step_result.get('data'))}

INTELLIGENT EVALUATION CRITERIA:
1. Did the tool execute successfully? (Technical success)
2. Did it produce meaningful data? (Logical success)
3. Is there a clear indication of failure that requires intervention?
4. Would adding steps actually solve a real problem?
5. Are we missing a critical step for workflow completion?

MODIFICATION GUIDELINES:
- modify_workflow: true ONLY if there's a clear failure or missing critical step
- safe_to_modify: false if modification might cause infinite loop
- Only add steps that directly address execution failures
- Do not add steps for "nice to have" features

RESPONSE FORMAT (JSON):
{{
  "step_successful": true,
  "output_as_expected": true,
  "continue_workflow": true,
  "modify_workflow": false,
  "safe_to_modify": false,
  "confidence_score": 0.95,
  "modifications": [],
  "reasoning": "Detailed explanation of evaluation decision",
  "next_step_recommendations": {{}}
}}

EXAMPLES OF WHEN TO MODIFY:
✅ Tool failed with authentication error → Add auth step
✅ Required data missing → Add data retrieval step  
✅ Critical dependency not met → Add dependency step

EXAMPLES OF WHEN NOT TO MODIFY:
❌ Tool succeeded but could be improved → NO modification
❌ Data format different than expected but valid → NO modification
❌ Workflow could be "optimized" → NO modification
❌ Step completed successfully → NO modification

Evaluate intelligently and conservatively:
"""
        
        try:
            eval_result = registry.execute_tool_action(
                'llm_tool',
                'chat',
                message=evaluation_prompt,
                conversation_id=f"{workflow.conversation_id}_eval",
                enable_tools=False
            )
            
            if eval_result.success:
                eval_response = eval_result.data.get('response', '{}')
                return self._parse_evaluation_response(eval_response)
            
        except Exception as e:
            logger.error(f"Error in step evaluation: {str(e)}")
        
        # Default evaluation
        return {
            'step_successful': step.status == StepStatus.COMPLETED,
            'continue_workflow': True,
            'modify_workflow': False
        }
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """LLM evaluation response'unu parse et"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {str(e)}")
        
        return {'step_successful': True, 'continue_workflow': True, 'modify_workflow': False}
    
    def _modify_workflow(self, workflow: WorkflowPlan, evaluation: Dict[str, Any]) -> bool:
        """Workflow'u LLM evaluation'ına göre modify et"""
        try:
            modifications = evaluation.get('modifications', [])
            
            for mod in modifications:
                if mod['action'] == 'add_step':
                    # Yeni step ekle
                    step_data = mod['step_data']
                    new_step = WorkflowStep(
                        id=step_data.get('id', str(uuid.uuid4())),  # Use provided ID or generate UUID
                        title=step_data.get('title', 'Added Step'),
                        description=step_data.get('description', ''),
                        tool_name=step_data.get('tool_name', ''),
                        action_name=step_data.get('action_name', ''),
                        params=step_data.get('params', {}),
                        status=StepStatus.PENDING,
                        estimated_duration=step_data.get('estimated_duration'),
                        dependencies=step_data.get('dependencies', [])
                    )
                    
                    # Insert position belirle
                    insert_pos = workflow.current_step_index
                    workflow.steps.insert(insert_pos, new_step)
                    
                    logger.info(f"Added new step: {new_step.title}")
            
            workflow.updated_at = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Error modifying workflow: {str(e)}")
            return False
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Workflow durumunu al"""
        if workflow_id not in self.active_workflows:
            return {'error': 'Workflow not found'}
        
        workflow = self.active_workflows[workflow_id]
        
        # Progress calculation
        total_steps = len(workflow.steps)
        completed_steps = sum(1 for step in workflow.steps if step.status == StepStatus.COMPLETED)
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            'workflow_id': workflow.id,
            'title': workflow.title,
            'description': workflow.description,
            'status': workflow.status.value,
            'progress_percentage': progress_percentage,
            'current_step_index': workflow.current_step_index,
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'steps': [
                {
                    'id': step.id,
                    'title': step.title,
                    'description': step.description,
                    'status': step.status.value,
                    'estimated_duration': step.estimated_duration,
                    'error': step.error
                }
                for step in workflow.steps
            ],
            'created_at': workflow.created_at,
            'updated_at': workflow.updated_at
        }
    
    def get_active_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """Kullanıcının aktif workflow'larını al"""
        user_workflows = [
            self.get_workflow_status(wf.id) 
            for wf in self.active_workflows.values() 
            if wf.user_id == user_id
        ]
        
        return user_workflows
    
    def get_workflow_by_decision_id(self, decision_id: str) -> Optional[WorkflowPlan]:
        """Find workflow by decision ID"""
        try:
            for workflow in self.active_workflows.values():
                if hasattr(workflow, 'pending_decision_id') and workflow.pending_decision_id == decision_id:
                    return workflow
                # Also check step-level decision IDs
                for step in workflow.steps:
                    if hasattr(step, 'decision_id') and step.decision_id == decision_id:
                        return workflow
            return None
        except Exception as e:
            logger.error(f"Error finding workflow by decision ID: {e}")
            return None
    
    def resume_workflow_with_decision(self, workflow_id: str, decision_id: str, choice: Any, user_id: str) -> Dict[str, Any]:
        """Resume workflow execution with user decision"""
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            logger.info(f"Resuming workflow {workflow_id} with decision {decision_id}: {choice}")
            
            # Store the decision in workflow context
            if not hasattr(workflow, 'user_decisions'):
                workflow.user_decisions = {}
            workflow.user_decisions[decision_id] = choice
            
            # Clear pending decision
            if hasattr(workflow, 'pending_decision_id'):
                delattr(workflow, 'pending_decision_id')
            
            # Update workflow status to running
            workflow.status = WorkflowStatus.RUNNING
            workflow.updated_at = datetime.now()
            
            # Continue workflow execution from where it left off
            result = self.continue_workflow_execution(workflow, user_id)
            
            return {
                "success": True,
                "response": f"Decision processed: {choice}. Continuing workflow...",
                "workflow_status": workflow.status.value,
                "tool_calls": result.get("tool_calls", []),
                "tool_results": result.get("tool_results", [])
            }
            
        except Exception as e:
            logger.error(f"Error resuming workflow with decision: {e}")
            return {"success": False, "error": str(e)}
    
    def continue_workflow_execution(self, workflow: WorkflowPlan, user_id: str) -> Dict[str, Any]:
        """Continue workflow execution after decision"""
        try:
            # Find current step or next pending step
            current_step_index = workflow.current_step_index
            
            if current_step_index < len(workflow.steps):
                step = workflow.steps[current_step_index]
                
                # Execute the step that was waiting for decision
                result = self._execute_step_with_context(workflow, step, user_id)
                
                if result.success:
                    # Move to next step
                    workflow.current_step_index += 1
                    
                    # Continue with remaining steps
                    return self._execute_workflow_sequential(workflow, user_id)
                else:
                    return {
                        "success": False,
                        "error": f"Step execution failed: {result.error}",
                        "tool_calls": [],
                        "tool_results": []
                    }
            else:
                # Workflow completed
                workflow.status = WorkflowStatus.COMPLETED
                return {
                    "success": True,
                    "response": "Workflow completed successfully",
                    "workflow_status": "completed",
                    "tool_calls": [],
                    "tool_results": []
                }
                
        except Exception as e:
            logger.error(f"Error continuing workflow execution: {e}")
            return {"success": False, "error": str(e)}

# Global orchestrator instance
orchestrator = WorkflowOrchestrator()