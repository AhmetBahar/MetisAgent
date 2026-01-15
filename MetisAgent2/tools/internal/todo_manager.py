"""
Internal Todo Manager Tool for MetisAgent2 (MCP Tool)
Provides internal todo list management with workflow integration and WebSocket broadcasting.
"""

import json
import uuid
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

@dataclass
class TodoItem:
    """Represents a single todo item"""
    id: str
    content: str
    status: str  # pending, in_progress, completed
    priority: str  # high, medium, low
    created_at: str
    updated_at: str
    user_id: str
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None

class TodoManagerTool(MCPTool):
    """Internal todo manager MCP Tool with workflow integration"""
    
    def __init__(self):
        """Initialize Todo Manager MCP Tool"""
        super().__init__(
            name="todo_manager",
            description="Internal todo list management with workflow integration",
            version="2.0.0"
        )
        
        # Storage setup
        self.storage_dir = Path(__file__).parent.parent / "storage" / "todos"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Register capabilities
        self.add_capability("todo_management")
        self.add_capability("workflow_integration")
        self.add_capability("task_tracking")
        self.add_capability("priority_management")
        
        # Register actions
        self.register_action(
            "create_todos",
            self._create_todos,
            required_params=["user_id", "todos_data"],
            optional_params=["workflow_id"]
        )
        
        self.register_action(
            "get_todos",
            self._get_todos,
            required_params=["user_id"],
            optional_params=["workflow_id", "status", "priority"]
        )
        
        self.register_action(
            "update_todo_status",
            self._update_todo_status,
            required_params=["user_id", "todo_id", "status"],
            optional_params=["workflow_id"]
        )
        
        self.register_action(
            "delete_todo",
            self._delete_todo,
            required_params=["user_id", "todo_id"],
            optional_params=["workflow_id"]
        )
        
        self.register_action(
            "get_workflow_todos",
            self._get_workflow_todos,
            required_params=["user_id", "workflow_id"],
            optional_params=[]
        )
        
        self.register_action(
            "clear_completed_todos",
            self._clear_completed_todos,
            required_params=["user_id"],
            optional_params=["workflow_id"]
        )
        
        logger.info("Todo Manager MCP Tool initialized")
    
    def _get_user_todos(self, user_id: str) -> Dict[str, TodoItem]:
        """Load todos for a specific user"""
        todo_file = self.storage_dir / f"{user_id}_todos.json"
        todos = {}
        
        try:
            if todo_file.exists():
                with open(todo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for todo_data in data:
                        todo = TodoItem(**todo_data)
                        todos[todo.id] = todo
                logger.debug(f"Loaded {len(todos)} todos for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading todos for user {user_id}: {e}")
            
        return todos
    
    def _save_user_todos(self, user_id: str, todos: Dict[str, TodoItem]) -> bool:
        """Save todos for a specific user"""
        todo_file = self.storage_dir / f"{user_id}_todos.json"
        
        try:
            todos_data = [asdict(todo) for todo in todos.values()]
            with open(todo_file, 'w', encoding='utf-8') as f:
                json.dump(todos_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(todos)} todos for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving todos for user {user_id}: {e}")
            return False
    
    def _create_todos(self, user_id: str, todos_data: List[Dict], workflow_id: str = None) -> MCPToolResult:
        """Create multiple todos from list of todo data"""
        try:
            todos = self._get_user_todos(user_id)
            created_todos = []
            current_time = datetime.now().isoformat()
            
            for todo_data in todos_data:
                # Generate ID if not provided
                todo_id = todo_data.get('id', str(uuid.uuid4())[:8])
                
                # Create todo item
                todo = TodoItem(
                    id=todo_id,
                    content=todo_data['content'],
                    status=todo_data.get('status', 'pending'),
                    priority=todo_data.get('priority', 'medium'),
                    created_at=current_time,
                    updated_at=current_time,
                    user_id=user_id,
                    workflow_id=workflow_id or todo_data.get('workflow_id'),
                    step_id=todo_data.get('step_id')
                )
                
                todos[todo_id] = todo
                created_todos.append(asdict(todo))
                
                logger.info(f"Created todo '{todo.content}' with ID {todo_id}")
            
            # Save todos
            if self._save_user_todos(user_id, todos):
                return MCPToolResult(
                    success=True,
                    data={
                        'message': f'Created {len(created_todos)} todos',
                        'todos': created_todos,
                        'total_todos': len(todos)
                    },
                    metadata={"user_id": user_id, "workflow_id": workflow_id}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Failed to save todos",
                    metadata={"user_id": user_id}
                )
            
        except Exception as e:
            logger.error(f"Error creating todos for user {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id}
            )
    
    def _get_todos(self, user_id: str, workflow_id: str = None, status: str = None, 
                   priority: str = None) -> MCPToolResult:
        """Get todos with optional filtering"""
        try:
            todos = self._get_user_todos(user_id)
            filtered_todos = []
            
            for todo in todos.values():
                # Apply filters
                if workflow_id and todo.workflow_id != workflow_id:
                    continue
                if status and todo.status != status:
                    continue
                if priority and todo.priority != priority:
                    continue
                    
                filtered_todos.append(asdict(todo))
            
            # Sort by created_at descending
            filtered_todos.sort(key=lambda x: x['created_at'], reverse=True)
            
            return MCPToolResult(
                success=True,
                data={
                    'todos': filtered_todos,
                    'total_count': len(filtered_todos),
                    'filtered_count': len(filtered_todos),
                    'filters': {
                        'workflow_id': workflow_id,
                        'status': status,
                        'priority': priority
                    }
                },
                metadata={"user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Error getting todos for user {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id}
            )
    
    def _update_todo_status(self, user_id: str, todo_id: str, status: str, 
                           workflow_id: str = None) -> MCPToolResult:
        """Update todo status"""
        try:
            todos = self._get_user_todos(user_id)
            
            if todo_id not in todos:
                return MCPToolResult(
                    success=False,
                    error=f"Todo {todo_id} not found",
                    metadata={"user_id": user_id, "todo_id": todo_id}
                )
            
            # Update todo
            todo = todos[todo_id]
            old_status = todo.status
            todo.status = status
            todo.updated_at = datetime.now().isoformat()
            
            # Save todos
            if self._save_user_todos(user_id, todos):
                logger.info(f"Updated todo {todo_id} status: {old_status} -> {status}")
                
                return MCPToolResult(
                    success=True,
                    data={
                        'todo_id': todo_id,
                        'old_status': old_status,
                        'new_status': status,
                        'todo': asdict(todo)
                    },
                    metadata={"user_id": user_id, "workflow_id": workflow_id}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Failed to save todo update",
                    metadata={"user_id": user_id, "todo_id": todo_id}
                )
            
        except Exception as e:
            logger.error(f"Error updating todo {todo_id} for user {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "todo_id": todo_id}
            )
    
    def _delete_todo(self, user_id: str, todo_id: str, workflow_id: str = None) -> MCPToolResult:
        """Delete a todo"""
        try:
            todos = self._get_user_todos(user_id)
            
            if todo_id not in todos:
                return MCPToolResult(
                    success=False,
                    error=f"Todo {todo_id} not found",
                    metadata={"user_id": user_id, "todo_id": todo_id}
                )
            
            # Delete todo
            deleted_todo = todos.pop(todo_id)
            
            # Save todos
            if self._save_user_todos(user_id, todos):
                logger.info(f"Deleted todo {todo_id}: '{deleted_todo.content}'")
                
                return MCPToolResult(
                    success=True,
                    data={
                        'todo_id': todo_id,
                        'deleted_todo': asdict(deleted_todo),
                        'remaining_todos': len(todos)
                    },
                    metadata={"user_id": user_id, "workflow_id": workflow_id}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Failed to save after deletion",
                    metadata={"user_id": user_id, "todo_id": todo_id}
                )
            
        except Exception as e:
            logger.error(f"Error deleting todo {todo_id} for user {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "todo_id": todo_id}
            )
    
    def _get_workflow_todos(self, user_id: str, workflow_id: str) -> MCPToolResult:
        """Get all todos for a specific workflow"""
        try:
            todos = self._get_user_todos(user_id)
            workflow_todos = []
            
            for todo in todos.values():
                if todo.workflow_id == workflow_id:
                    workflow_todos.append(asdict(todo))
            
            # Sort by created_at
            workflow_todos.sort(key=lambda x: x['created_at'])
            
            # Calculate workflow progress
            total_todos = len(workflow_todos)
            completed_todos = len([t for t in workflow_todos if t['status'] == 'completed'])
            in_progress_todos = len([t for t in workflow_todos if t['status'] == 'in_progress'])
            
            progress_percentage = (completed_todos / total_todos * 100) if total_todos > 0 else 0
            
            return MCPToolResult(
                success=True,
                data={
                    'workflow_id': workflow_id,
                    'todos': workflow_todos,
                    'total_todos': total_todos,
                    'completed_todos': completed_todos,
                    'in_progress_todos': in_progress_todos,
                    'pending_todos': total_todos - completed_todos - in_progress_todos,
                    'progress_percentage': progress_percentage
                },
                metadata={"user_id": user_id}
            )
            
        except Exception as e:
            logger.error(f"Error getting workflow todos for {workflow_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id, "workflow_id": workflow_id}
            )
    
    def _clear_completed_todos(self, user_id: str, workflow_id: str = None) -> MCPToolResult:
        """Clear completed todos"""
        try:
            todos = self._get_user_todos(user_id)
            completed_todos = []
            remaining_todos = {}
            
            for todo_id, todo in todos.items():
                if todo.status == 'completed':
                    # Filter by workflow if specified
                    if workflow_id is None or todo.workflow_id == workflow_id:
                        completed_todos.append(asdict(todo))
                        continue
                
                remaining_todos[todo_id] = todo
            
            # Save remaining todos
            if self._save_user_todos(user_id, remaining_todos):
                logger.info(f"Cleared {len(completed_todos)} completed todos for user {user_id}")
                
                return MCPToolResult(
                    success=True,
                    data={
                        'cleared_count': len(completed_todos),
                        'remaining_count': len(remaining_todos),
                        'cleared_todos': completed_todos
                    },
                    metadata={"user_id": user_id, "workflow_id": workflow_id}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Failed to save after clearing todos",
                    metadata={"user_id": user_id}
                )
            
        except Exception as e:
            logger.error(f"Error clearing completed todos for user {user_id}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"user_id": user_id}
            )

    # Legacy compatibility methods
    def todo_create(self, user_id: str, todos_data: List[Dict], workflow_id: str = None) -> Dict[str, Any]:
        """Legacy compatibility method"""
        result = self._create_todos(user_id, todos_data, workflow_id)
        return {
            'success': result.success,
            'data': result.data,
            'error': result.error
        }
    
    def todo_update_status(self, user_id: str, todo_id: str, status: str, workflow_id: str = None) -> Dict[str, Any]:
        """Legacy compatibility method"""
        result = self._update_todo_status(user_id, todo_id, status, workflow_id)
        return {
            'success': result.success,
            'data': result.data,
            'error': result.error
        }

class TodoTool:
    """Legacy wrapper class for backward compatibility"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._tool = TodoManagerTool()
    
    def todo_create(self, user_id: str, todos_data: List[Dict], workflow_id: str = None) -> Dict[str, Any]:
        result = self._tool._create_todos(user_id, todos_data, workflow_id)
        return {
            'success': result.success,
            'data': result.data,
            'error': result.error
        }
    
    def todo_update_status(self, user_id: str, todo_id: str, status: str, workflow_id: str = None) -> Dict[str, Any]:
        result = self._tool._update_todo_status(user_id, todo_id, status, workflow_id)
        return {
            'success': result.success,
            'data': result.data,
            'error': result.error
        }

def register_tool(registry):
    """Register Todo Manager tool with the registry"""
    try:
        tool = TodoManagerTool()
        registry.register_tool(tool)
        logger.info("Todo Manager MCP tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register Todo Manager tool: {e}")
        return False

# Global todo tool instance - legacy compatibility
_todo_tool = None

def get_todo_tool():
    """Legacy compatibility function"""
    global _todo_tool
    if _todo_tool is None:
        _todo_tool = TodoManagerTool()
    return _todo_tool