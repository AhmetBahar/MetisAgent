"""
RMMS Task Tool - AI-powered Task Management

Capabilities:
- Create/Edit/Delete tasks
- Assign tasks to users
- Track task status and progress
- Manage priorities and due dates
- Add comments and notes
"""

import logging
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

# Import MetisAgent base contracts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

logger = logging.getLogger(__name__)


class RMMSTaskTool(BaseTool):
    """RMMS Task Management Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://app-metis-task-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)

        self.statuses = {
            "pending": {"description": "Task created but not started", "color": "#FFA500"},
            "in_progress": {"description": "Task being worked on", "color": "#2196F3"},
            "completed": {"description": "Task finished successfully", "color": "#4CAF50"},
            "cancelled": {"description": "Task cancelled", "color": "#9E9E9E"}
        }

        self.priorities = {
            "low": {"description": "Low priority task", "value": 1, "color": "#8BC34A"},
            "medium": {"description": "Medium priority task", "value": 2, "color": "#FF9800"},
            "high": {"description": "High priority task", "value": 3, "color": "#F44336"},
            "critical": {"description": "Critical priority task", "value": 4, "color": "#9C27B0"}
        }

        self.categories = ["maintenance", "inspection", "repair", "installation", "calibration", "monitoring", "documentation", "training", "other"]

        logger.info(f"RMMSTaskTool initialized with API: {self.api_base_url}")

    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        logger.info(f"RMMS Task Tool executing capability: {capability}")

        try:
            if capability == "list_tasks":
                result = await self._list_tasks(input_data)
            elif capability == "get_task":
                result = await self._get_task(input_data)
            elif capability == "create_task":
                result = await self._create_task(input_data)
            elif capability == "update_task":
                result = await self._update_task(input_data)
            elif capability == "delete_task":
                result = await self._delete_task(input_data)
            elif capability == "assign_task":
                result = await self._assign_task(input_data)
            elif capability == "update_status":
                result = await self._update_status(input_data)
            elif capability == "add_comment":
                result = await self._add_comment(input_data)
            elif capability == "get_comments":
                result = await self._get_comments(input_data)
            elif capability == "get_task_history":
                result = await self._get_task_history(input_data)
            elif capability == "get_statuses":
                result = await self._get_statuses(input_data)
            elif capability == "get_priorities":
                result = await self._get_priorities(input_data)
            elif capability == "get_categories":
                result = await self._get_categories(input_data)
            elif capability == "get_users":
                result = await self._get_users(input_data)
            elif capability == "start_task":
                result = await self._start_task(input_data)
            elif capability == "stop_task":
                result = await self._stop_task(input_data)
            elif capability == "get_task_status":
                result = await self._get_task_status(input_data)
            # Tag capabilities
            elif capability == "list_tags":
                result = await self._list_tags(input_data)
            elif capability == "get_tag":
                result = await self._get_tag(input_data)
            elif capability == "get_tag_value":
                result = await self._get_tag_value(input_data)
            elif capability == "get_tag_values":
                result = await self._get_tag_values(input_data)
            # Variable capabilities
            elif capability == "list_variables":
                result = await self._list_variables(input_data)
            elif capability == "get_variable" or capability == "read_var_value":
                result = await self._get_variable(input_data)
            elif capability == "create_variable":
                result = await self._create_variable(input_data)
            elif capability == "update_variable":
                result = await self._update_variable(input_data)
            elif capability == "delete_variable":
                result = await self._delete_variable(input_data)
            elif capability == "get_variable_history":
                result = await self._get_variable_history(input_data)
            # Task Execution History capabilities
            elif capability == "get_task_execution_history":
                result = await self._get_task_execution_history(input_data)
            elif capability == "get_task_execution_logs":
                result = await self._get_task_execution_logs(input_data)
            else:
                result = {"success": False, "error": f"Unknown capability: {capability}"}

            return AgentResult(
                success=result.get("success", False),
                data=result.get("data"),
                message=result.get("message") or result.get("error"),
                metadata={"capability": capability}
            )

        except Exception as e:
            logger.error(f"RMMS Task Tool error: {str(e)}")
            return AgentResult(success=False, message=str(e), metadata={"capability": capability, "error": str(e)})

    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Use correct endpoint: /tasks/{companyId}
                response = await client.get(f"{self.api_base_url}/tasks/3")
                healthy = response.status_code == 200
                message = "RMMS Task API accessible" if healthy else f"API returned {response.status_code}"
        except Exception as e:
            healthy = False
            message = f"API connection failed: {str(e)}"

        return HealthStatus(healthy=healthy, component="rmms_task_tool", message=message)

    def _build_workflow_json(self, params: Dict[str, Any], name: str) -> Dict[str, Any]:
        """
        Build empty workflow JSON template with Start and End nodes.
        Actual workflow nodes should be added via UI or add_node API.

        Available node types (from WorkflowExecutor):
        - circularNode: Start/End markers
        - Condition: Evaluate conditions (selectedCondition, selectedVariable1, selectedVariable2, inputType1, inputType2)
        - And/Or/Xor/Not: Logical operators
        - Arithmetic: Math expressions (expression, outputVariable, expressionId)
        - Service: Web API calls (service, method, parameterMappings)
        - Switch: Route by value matching
        - For/Loop: Iteration nodes
        - Scenario: Call sub-workflow (workflowName)
        - Email: Send email (to, subject, message)
        - SMS: Send SMS (phoneNumber, message)
        - Alarm: Create alarm (message, severity, variables)
        - PLCCommand: Write to PLC tag (selectedTag, commandValue, tagInputType, valueInputType)
        - RisingEdge: Detect rising edge condition
        """
        # Create empty workflow with just Start and End nodes
        nodes = [
            {
                "id": "0",
                "type": "circularNode",
                "data": {"label": "Start"},
                "position": {"x": 250, "y": 5},
                "style": {"background": "transparent", "border": "none", "boxShadow": "none"}
            },
            {
                "id": "9999",
                "type": "circularNode",
                "data": {"label": "End"},
                "position": {"x": 250, "y": 200},
                "style": {"background": "transparent", "border": "none", "boxShadow": "none"}
            }
        ]
        edges = [
            {"id": "e0-9999", "source": "0", "target": "9999"}
        ]

        # If workflow_nodes are provided, add them
        workflow_nodes = params.get("workflow_nodes") or params.get("nodes") or []
        if workflow_nodes:
            # Remove the direct Start->End edge
            edges = []
            y_position = 100
            prev_node_id = "0"

            for i, node in enumerate(workflow_nodes):
                node_id = node.get("id", str(i + 1))
                node_type = node.get("type")
                node_data = node.get("data", {})

                nodes.insert(-1, {  # Insert before End node
                    "id": node_id,
                    "type": node_type,
                    "data": node_data,
                    "position": node.get("position", {"x": 250, "y": y_position})
                })

                edges.append({
                    "id": f"e{prev_node_id}-{node_id}",
                    "source": prev_node_id,
                    "target": node_id
                })
                prev_node_id = node_id
                y_position += 100

            # Connect last node to End
            edges.append({
                "id": f"e{prev_node_id}-9999",
                "source": prev_node_id,
                "target": "9999"
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "localVars": params.get("local_vars", []),
            "name": name,
            "description": params.get("description", f"Workflow: {name}")
        }

    def _build_scheduler_settings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build SchedulerSettings with proper type detection"""
        specific_times = params.get("specific_times") or params.get("specificTimes") or []
        cron = params.get("cron") or params.get("customCron", "")
        interval = params.get("interval", 3600)

        # Determine scheduler type based on provided parameters
        if cron:
            scheduler_type = "cron"
        elif specific_times and len(specific_times) > 0:
            scheduler_type = "specificTimes"
        else:
            scheduler_type = "interval"

        return {
            "interval": interval,
            "type": scheduler_type,
            "customCron": cron,
            "specificTimes": specific_times,
            "specificTime": specific_times[0] if specific_times and len(specific_times) == 1 else None
        }

    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        if capability in ["get_task", "delete_task", "get_comments", "get_task_history"]:
            if not input_data.get("task_id"):
                errors.append("task_id is required")
        elif capability == "create_task":
            if not input_data.get("title"):
                errors.append("title is required")
        elif capability == "assign_task":
            if not input_data.get("task_id"):
                errors.append("task_id is required")
            if not input_data.get("user_id"):
                errors.append("user_id is required")
        elif capability == "update_status":
            if not input_data.get("task_id"):
                errors.append("task_id is required")
            if not input_data.get("status"):
                errors.append("status is required")
        elif capability == "add_comment":
            if not input_data.get("task_id"):
                errors.append("task_id is required")
            if not input_data.get("comment"):
                errors.append("comment is required")
        return errors

    def get_capabilities(self) -> List[str]:
        return [cap.name for cap in self.metadata.capabilities]

    async def _list_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/tasks/{company_id}"

            response = await client.get(url)
            if response.status_code == 200:
                tasks = response.json()
                # Filter by status/priority if provided
                status = params.get("status")
                priority = params.get("priority")
                if status:
                    tasks = [t for t in tasks if t.get("status", "").lower() == status.lower()]
                if priority:
                    tasks = [t for t in tasks if t.get("priority", "").lower() == priority.lower()]
                return {"success": True, "data": {"tasks": tasks, "count": len(tasks)}, "message": f"Found {len(tasks)} tasks"}
            return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_name = params.get("task_name") or params.get("task_id")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not task_name:
            return {"success": False, "error": "task_name is required"}

        # First get all tasks, then find the specific one
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/tasks/{company_id}")
            if response.status_code == 200:
                tasks = response.json()
                # Find task by name or id
                task = next((t for t in tasks if t.get("name") == task_name or str(t.get("id")) == str(task_name)), None)
                if task:
                    return {"success": True, "data": task, "message": f"Retrieved task {task_name}"}
                return {"success": False, "error": f"Task not found: {task_name}"}
            return {"success": False, "error": f"API error: {response.status_code}"}

    async def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name") or params.get("title")
        if not name:
            return {"success": False, "error": "name/title is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        task_type = params.get("task_type", "code")  # code, workflow
        execution_location = params.get("execution_location", "cloud")  # cloud, local
        execution_mode = params.get("execution_mode", "manual")  # manual, scheduler, tag-based

        logger.info(f"Creating task '{name}' - type:{task_type}, location:{execution_location}, mode:{execution_mode}, params:{params}")

        # Normalize execution_mode
        if execution_mode in ["tag_change", "tagChange", "tagBased", "tag-based", "tag_based"]:
            execution_mode = "tag-based"
        elif execution_mode in ["schedule", "scheduled", "scheduler"]:
            execution_mode = "scheduler"

        # Build tag-based trigger configuration if applicable
        tag_based_tasks = []
        used_tags = []
        is_tag_based = execution_mode == "tag-based" or params.get("tag_id") or params.get("tag_triggers")
        if is_tag_based:
            tag_id = params.get("tag_id") or params.get("tagId")
            threshold = params.get("threshold") or params.get("threshold_value") or params.get("thresholdValue")
            condition = params.get("condition") or params.get("trigger_condition") or params.get("comparison_operator", "greaterThanOrEqual")

            if tag_id:
                tag_based_tasks.append({
                    "TagId": int(tag_id),
                    "TagType": "T",
                    "TriggerCondition": condition,
                    "ComparisonOperator": condition,
                    "ThresholdValue": threshold
                })
                used_tags.append(str(tag_id))

            # Also support multiple tag triggers
            if params.get("tag_triggers"):
                for trigger in params.get("tag_triggers"):
                    tag_based_tasks.append(trigger)
                    used_tags.append(str(trigger.get("TagId", "")))

        # Build configuration object (PascalCase for .NET API)
        configuration = {
            "ExecutionLocation": execution_location,
            "ExecutionMode": execution_mode,
            "Language": params.get("language", "python") if task_type == "code" else None,
            "WorkflowName": params.get("workflow_name", name) if task_type == "workflow" else "",
            "CodeName": params.get("code_name", name) if task_type == "code" else "",
            "EnableLogging": params.get("enable_logging", True),
            "WatchdogTimeout": params.get("watchdog_timeout", 3000),
            "Timeout": params.get("timeout", 120),
            "TagBasedTasks": tag_based_tasks,
            "UsedTags": used_tags,
            "SchedulerSettings": self._build_scheduler_settings(params) if execution_mode == "scheduler" else None
        }

        task_data = {
            "Name": name,
            "Type": task_type,  # API expects "Type" not "taskType"
            "ExecutionLocation": execution_location,
            "ExecutionMode": execution_mode,
            "IsEnabled": params.get("is_enabled", True),
            "Configuration": configuration,
            "ContentName": params.get("content_name", name),
            "CompanyId": company_id
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/tasks", json=task_data)
            if response.status_code in [200, 201]:
                result = response.json() if response.text else {"name": name}

                # If this is a workflow task, also create/update the workflow JSON content
                if task_type == "workflow":
                    workflow_json = self._build_workflow_json(params, name)
                    workflow_request = {
                        "Name": name,
                        "Description": params.get("description", f"Workflow: {name}"),
                        "Category": params.get("category", "General"),
                        "Json": json.dumps(workflow_json),
                        "CompanyId": company_id,
                        "UserId": params.get("user_id", "system")
                    }
                    # Try to create workflow, if fails with duplicate, try update
                    wf_response = await client.post(f"{self.api_base_url}/workflows", json=workflow_request)
                    if wf_response.status_code not in [200, 201]:
                        if "duplicate" in wf_response.text.lower() or "unique" in wf_response.text.lower():
                            # Try updating existing workflow
                            wf_update_response = await client.put(f"{self.api_base_url}/workflows/{name}", json=workflow_request)
                            if wf_update_response.status_code in [200]:
                                result["workflow_json"] = "updated"
                            else:
                                logger.warning(f"Workflow JSON update failed: {wf_update_response.text}")
                                result["workflow_json_warning"] = f"Task created but workflow JSON update failed"
                        else:
                            logger.warning(f"Workflow JSON creation failed: {wf_response.text}")
                            result["workflow_json_warning"] = f"Task created but workflow JSON failed: {wf_response.text}"
                    else:
                        result["workflow_json"] = "created"

                return {"success": True, "data": result, "message": f"Created task '{name}'"}
            return {"success": False, "error": f"Failed to create task: {response.text}"}

    async def _update_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_name = params.get("task_name") or params.get("task_id") or params.get("name")
        if not task_name:
            return {"success": False, "error": "task_name is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        # First get the existing task
        existing = await self._get_task({"task_name": task_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        task_data = existing["data"]

        # Update fields
        field_mapping = {
            "name": "name",
            "title": "name",
            "description": "description",
            "task_type": "taskType",
            "is_enabled": "isEnabled",
            "script_code": "scriptCode"
        }
        for field, api_field in field_mapping.items():
            if field in params:
                task_data[api_field] = params[field]
        task_data["updatedAt"] = datetime.now().isoformat()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use task name for update endpoint
            original_name = existing["data"].get("name", task_name)
            response = await client.put(f"{self.api_base_url}/tasks/{original_name}", json=task_data)
            if response.status_code == 200:
                return {"success": True, "data": task_data, "message": f"Updated task '{task_name}'"}
            return {"success": False, "error": f"Failed to update task: {response.text}"}

    async def _delete_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_name = params.get("task_name") or params.get("task_id") or params.get("name")
        if not task_name:
            return {"success": False, "error": "task_name is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # DELETE /tasks/{companyId}/{name}
            response = await client.delete(f"{self.api_base_url}/tasks/{company_id}/{task_name}")
            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted task '{task_name}'"}
            return {"success": False, "error": f"Failed to delete task: {response.text}"}

    async def _assign_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get("task_id")
        user_id = params.get("user_id")
        if not task_id or not user_id:
            return {"success": False, "error": "task_id and user_id are required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/Tasks/{task_id}/assign", json={"userId": user_id})
            if response.status_code == 200:
                return {"success": True, "message": f"Task {task_id} assigned to user {user_id}"}
            return {"success": False, "error": f"Failed to assign task: {response.text}"}

    async def _update_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get("task_id")
        status = params.get("status")
        if not task_id or not status:
            return {"success": False, "error": "task_id and status are required"}
        if status not in self.statuses:
            return {"success": False, "error": f"Invalid status: {status}"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/Tasks/{task_id}/status",
                json={"status": status, "notes": params.get("notes", ""), "updatedAt": datetime.now().isoformat()})
            if response.status_code == 200:
                return {"success": True, "message": f"Task {task_id} status updated to '{status}'"}
            return {"success": False, "error": f"Failed to update status: {response.text}"}

    async def _add_comment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get("task_id")
        comment = params.get("comment")
        if not task_id or not comment:
            return {"success": False, "error": "task_id and comment are required"}

        comment_data = {"taskId": task_id, "comment": comment, "author": params.get("author", "MetisAgent"), "createdAt": datetime.now().isoformat()}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/Tasks/{task_id}/comments", json=comment_data)
            if response.status_code in [200, 201]:
                return {"success": True, "data": comment_data, "message": f"Comment added to task {task_id}"}
            return {"success": False, "error": f"Failed to add comment: {response.text}"}

    async def _get_comments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/Tasks/{task_id}/comments")
            if response.status_code == 200:
                comments = response.json()
                return {"success": True, "data": {"comments": comments, "count": len(comments)}, "message": f"Found {len(comments)} comments"}
            return {"success": False, "error": f"Failed to get comments: {response.text}"}

    async def _get_task_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/Tasks/{task_id}/history")
            if response.status_code == 200:
                history = response.json()
                return {"success": True, "data": {"history": history, "count": len(history)}, "message": f"Found {len(history)} history entries"}
            return {"success": False, "error": f"Failed to get history: {response.text}"}

    async def _get_statuses(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "data": {"statuses": self.statuses}, "message": f"Available statuses: {', '.join(self.statuses.keys())}"}

    async def _get_priorities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "data": {"priorities": self.priorities}, "message": f"Available priorities: {', '.join(self.priorities.keys())}"}

    async def _get_categories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "data": {"categories": self.categories}, "message": f"Available categories: {', '.join(self.categories)}"}

    async def _get_users(self, params: Dict[str, Any]) -> Dict[str, Any]:
        company_id = params.get("company_id")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/Users"
            if company_id:
                url += f"?companyId={company_id}"

            response = await client.get(url)
            if response.status_code == 200:
                users = response.json()
                return {"success": True, "data": {"users": users, "count": len(users)}, "message": f"Found {len(users)} users"}
            return {"success": False, "error": f"Failed to get users: {response.text}"}

    async def _start_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start a task execution"""
        task_name = params.get("task_name") or params.get("task_id") or params.get("name")
        if not task_name:
            return {"success": False, "error": "task_name is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # POST /tasks/{companyId}/{name}/start
            response = await client.post(f"{self.api_base_url}/tasks/{company_id}/{task_name}/start")
            if response.status_code == 200:
                return {"success": True, "message": f"Task '{task_name}' started"}
            return {"success": False, "error": f"Failed to start task: {response.text}"}

    async def _stop_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a running task"""
        task_name = params.get("task_name") or params.get("task_id") or params.get("name")
        if not task_name:
            return {"success": False, "error": "task_name is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # POST /tasks/{companyId}/{name}/stop
            response = await client.post(f"{self.api_base_url}/tasks/{company_id}/{task_name}/stop")
            if response.status_code == 200:
                return {"success": True, "message": f"Task '{task_name}' stopped"}
            return {"success": False, "error": f"Failed to stop task: {response.text}"}

    async def _get_task_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get task execution status for a company"""
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # GET /tasks/status/{companyId}
            response = await client.get(f"{self.api_base_url}/tasks/status/{company_id}")
            if response.status_code == 200:
                status_data = response.json()
                return {"success": True, "data": status_data, "message": f"Task status for company {company_id}"}
            return {"success": False, "error": f"Failed to get task status: {response.text}"}

    # ==================== TAG OPERATIONS ====================

    async def _list_tags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List tags for a company with optional search and limit"""
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        limit = params.get("limit", 50)  # Default limit to prevent context overflow
        search = params.get("search", "").lower()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Tags API is on MetisEngine: /api/Tags/all/{companyId}
            tags_api = self.api_base_url.replace("/Task", "/Tags")
            response = await client.get(f"{tags_api}/all/{company_id}")
            if response.status_code == 200:
                result = response.json()
                all_tags = result.get("tags", result.get("Tags", [])) if isinstance(result, dict) else result
                total_count = len(all_tags)

                # Filter by search term if provided
                if search:
                    all_tags = [t for t in all_tags if search in t.get("tagName", "").lower() or search in t.get("tagName2", "").lower()]

                # Return summarized info to reduce response size
                tags_summary = []
                for tag in all_tags[:limit]:
                    tags_summary.append({
                        "tagID": tag.get("tagID"),
                        "tagName": tag.get("tagName"),
                        "tagName2": tag.get("tagName2"),
                        "type": tag.get("type"),
                        "unit": tag.get("unit", "")
                    })

                filtered_count = len(all_tags)
                return {
                    "success": True,
                    "data": {
                        "tags": tags_summary,
                        "returned": len(tags_summary),
                        "filtered": filtered_count,
                        "total": total_count
                    },
                    "message": f"Showing {len(tags_summary)} of {filtered_count} tags (total: {total_count}). Use 'search' param to filter or increase 'limit'."
                }
            return {"success": False, "error": f"Failed to list tags: {response.text}"}

    async def _get_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific tag by ID"""
        tag_id = params.get("tag_id") or params.get("id")
        if not tag_id:
            return {"success": False, "error": "tag_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tags_api = self.api_base_url.replace("/Task", "/Tags")
            response = await client.get(f"{tags_api}/{tag_id}")
            if response.status_code == 200:
                result = response.json()
                tag = result.get("Tag", result) if isinstance(result, dict) else result
                return {"success": True, "data": tag, "message": f"Retrieved tag {tag_id}"}
            return {"success": False, "error": f"Failed to get tag: {response.text}"}

    async def _get_tag_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current value of a tag"""
        tag_id = params.get("tag_id") or params.get("id")
        if not tag_id:
            return {"success": False, "error": "tag_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tags_api = self.api_base_url.replace("/Task", "/Tags")
            response = await client.get(f"{tags_api}/value/{tag_id}")
            if response.status_code == 200:
                value_data = response.json()
                return {"success": True, "data": value_data, "message": f"Tag {tag_id} value: {value_data.get('Value', 'N/A')}"}
            return {"success": False, "error": f"Failed to get tag value: {response.text}"}

    async def _get_tag_values(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current values for multiple tags"""
        tag_ids = params.get("tag_ids") or params.get("ids")
        if not tag_ids:
            return {"success": False, "error": "tag_ids is required (list of tag IDs)"}

        if isinstance(tag_ids, str):
            tag_ids = [int(x.strip()) for x in tag_ids.split(",")]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tags_api = self.api_base_url.replace("/Task", "/Tags")
            response = await client.post(f"{tags_api}/values", json=tag_ids)
            if response.status_code == 200:
                result = response.json()
                values = result.get("Values", result) if isinstance(result, dict) else result
                return {"success": True, "data": {"values": values, "count": len(values)}, "message": f"Retrieved {len(values)} tag values"}
            return {"success": False, "error": f"Failed to get tag values: {response.text}"}

    # ==================== VARIABLE OPERATIONS ====================

    async def _list_variables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all variables for a company"""
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/variables/list/{company_id}")
            if response.status_code == 200:
                variables = response.json()
                return {"success": True, "data": {"variables": variables, "count": len(variables)}, "message": f"Found {len(variables)} variables"}
            return {"success": False, "error": f"Failed to list variables: {response.text}"}

    async def _get_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific variable by ID"""
        var_id = params.get("var_id") or params.get("variable_id") or params.get("id")
        company_id = params.get("company_id", 3)  # Default to company 3
        if not var_id:
            return {"success": False, "error": "var_id is required"}

        logger.info(f"🔧 _get_variable called: var_id={var_id}, company_id={company_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/variables/{company_id}/{var_id}")
            if response.status_code == 200:
                variable = response.json()
                return {"success": True, "data": variable, "message": f"Retrieved variable {var_id}"}
            return {"success": False, "error": f"Failed to get variable: {response.text}"}

    async def _create_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new variable"""
        var_name = params.get("var_name") or params.get("name")
        if not var_name:
            return {"success": False, "error": "var_name is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        var_data = {
            "VarName": var_name,
            "Type": params.get("type", 0),  # 0 = numeric, etc.
            "Formula": params.get("formula", ""),
            "Unit": params.get("unit", ""),
            "CompanyId": company_id,
            "AlternateName": params.get("alternate_name", ""),
            "Alarm": params.get("alarm", ""),
            "ThirdName": params.get("third_name", ""),
            "DecimalPlaces": params.get("decimal_places", "2"),
            "Value": params.get("value", ""),
            "UserId": params.get("user_id", "MetisAgent")
        }

        logger.info(f"Creating variable '{var_name}' for company {company_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/variables/{company_id}", json=var_data)
            if response.status_code in [200, 201]:
                result = response.json() if response.text else {"VarName": var_name}
                return {"success": True, "data": result, "message": f"Created variable '{var_name}'"}
            return {"success": False, "error": f"Failed to create variable: {response.text}"}

    async def _update_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing variable"""
        var_id = params.get("var_id") or params.get("variable_id") or params.get("id")
        if not var_id:
            return {"success": False, "error": "var_id is required"}

        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        # Build update data
        var_data = {"CompanyId": company_id}
        field_mapping = {
            "var_name": "VarName",
            "name": "VarName",
            "type": "Type",
            "formula": "Formula",
            "unit": "Unit",
            "alternate_name": "AlternateName",
            "alarm": "Alarm",
            "third_name": "ThirdName",
            "decimal_places": "DecimalPlaces",
            "value": "Value"
        }
        for field, api_field in field_mapping.items():
            if field in params:
                var_data[api_field] = params[field]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(f"{self.api_base_url}/variables/{var_id}", json=var_data)
            if response.status_code == 200:
                result = response.json() if response.text else {"VarId": var_id}
                return {"success": True, "data": result, "message": f"Updated variable {var_id}"}
            return {"success": False, "error": f"Failed to update variable: {response.text}"}

    async def _delete_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a variable"""
        var_id = params.get("var_id") or params.get("variable_id") or params.get("id")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not var_id:
            return {"success": False, "error": "var_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(f"{self.api_base_url}/variables/{company_id}/{var_id}")
            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted variable {var_id}"}
            return {"success": False, "error": f"Failed to delete variable: {response.text}"}

    async def _get_variable_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get variable value history"""
        var_id = params.get("var_id") or params.get("variable_id") or params.get("id")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not var_id:
            return {"success": False, "error": "var_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/variables/{company_id}/{var_id}/history"
            # Add date filters if provided
            query_params = {}
            if params.get("start_date"):
                query_params["startDate"] = params["start_date"]
            if params.get("end_date"):
                query_params["endDate"] = params["end_date"]

            response = await client.get(url, params=query_params if query_params else None)
            if response.status_code == 200:
                history = response.json()
                return {"success": True, "data": {"history": history, "count": len(history)}, "message": f"Found {len(history)} history entries"}
            return {"success": False, "error": f"Failed to get variable history: {response.text}"}

    # ==================== Task Execution History ====================

    async def _get_task_execution_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get task execution history for all tasks or a specific task"""
        company_id = params.get("company_id", 3)
        task_name = params.get("task_name")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        status = params.get("status")  # e.g., "completed", "failed", "running"
        limit = params.get("limit", 50)

        logger.info(f"🔧 _get_task_execution_history called: company_id={company_id}, task_name={task_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/executions/history/{company_id}"
            query_params = {}
            if start_date:
                query_params["startDate"] = start_date
            if end_date:
                query_params["endDate"] = end_date
            if status:
                query_params["status"] = status
            if limit:
                query_params["limit"] = limit

            response = await client.get(url, params=query_params if query_params else None)
            if response.status_code == 200:
                executions = response.json()

                # Filter by task_name if provided
                if task_name:
                    executions = [e for e in executions if e.get("taskName", "").lower() == task_name.lower()]

                if not executions:
                    return {
                        "success": True,
                        "data": {"executions": [], "count": 0},
                        "message": f"No execution history found" + (f" for task '{task_name}'" if task_name else "")
                    }

                # Format the response with human-readable info
                formatted_executions = []
                for ex in executions:
                    formatted_ex = {
                        "id": ex.get("id"),
                        "taskId": ex.get("taskId"),
                        "taskName": ex.get("taskName"),
                        "taskType": ex.get("taskType"),
                        "status": ex.get("status"),
                        "startTime": ex.get("startTime"),
                        "endTime": ex.get("endTime"),
                        "duration": ex.get("duration"),
                        "errorMessage": ex.get("errorMessage"),
                        "result": ex.get("result")
                    }
                    formatted_executions.append(formatted_ex)

                # Get last execution info for summary
                last_exec = formatted_executions[0] if formatted_executions else None
                summary_msg = f"Found {len(formatted_executions)} execution(s)"
                if task_name and last_exec:
                    summary_msg += f". Last run: {last_exec.get('startTime')} - Status: {last_exec.get('status')}"

                return {
                    "success": True,
                    "data": {
                        "executions": formatted_executions,
                        "count": len(formatted_executions),
                        "last_execution": last_exec
                    },
                    "message": summary_msg
                }
            return {"success": False, "error": f"Failed to get execution history: {response.text}"}

    async def _get_task_execution_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get logs for a specific task execution"""
        company_id = params.get("company_id", 3)
        task_id = params.get("task_id")
        execution_id = params.get("execution_id")

        if not task_id:
            return {"success": False, "error": "task_id is required"}
        if not execution_id:
            return {"success": False, "error": "execution_id is required"}

        logger.info(f"🔧 _get_task_execution_logs called: task_id={task_id}, execution_id={execution_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/executions/{company_id}/{task_id}/{execution_id}/logs"

            response = await client.get(url)
            if response.status_code == 200:
                result = response.json()
                logs = result.get("logs", [])

                return {
                    "success": True,
                    "data": {
                        "taskId": result.get("taskId"),
                        "executionId": result.get("executionId"),
                        "logs": logs,
                        "count": len(logs)
                    },
                    "message": f"Found {len(logs)} log entries for execution {execution_id}"
                }
            return {"success": False, "error": f"Failed to get execution logs: {response.text}"}
