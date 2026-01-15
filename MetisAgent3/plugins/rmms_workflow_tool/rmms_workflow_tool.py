"""
RMMS Workflow Tool - AI-powered Workflow Designer

Capabilities:
- List/Get/Create/Update/Delete workflows
- Add/Remove/Configure workflow nodes
- Define node connections
- Manage triggers and conditions
"""

import logging
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

# Import MetisAgent base contracts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

# Import proper RMMS node definitions
from plugins.rmms_workflow_tool.node_definitions import (
    NODE_TYPES, EDGE_SCHEMA, WORKFLOW_STRUCTURE,
    get_node_type_description, get_all_node_types, get_node_types_for_llm
)

logger = logging.getLogger(__name__)


class RMMSWorkflowTool(BaseTool):
    """RMMS Workflow Design Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://rmms-metis-engine.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)

        # Use proper RMMS node types from node_definitions.py
        self.node_types = NODE_TYPES

        # Condition operators supported by RMMS WorkflowExecutor
        self.operators = ["==", "!=", ">", "<", ">=", "<="]

        logger.info(f"RMMSWorkflowTool initialized with API: {self.api_base_url}")
        logger.info(f"Available node types: {get_all_node_types()}")

    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        logger.info(f"RMMS Workflow Tool executing capability: {capability}")
        logger.info(f"RMMS Workflow Tool input_data: {json.dumps(input_data, default=str)[:2000]}")

        try:
            if capability == "list_workflows":
                result = await self._list_workflows(input_data)
            elif capability == "get_workflow":
                result = await self._get_workflow(input_data)
            elif capability == "create_workflow":
                result = await self._create_workflow(input_data)
            elif capability == "update_workflow":
                result = await self._update_workflow(input_data)
            elif capability == "delete_workflow":
                result = await self._delete_workflow(input_data)
            elif capability == "add_node":
                result = await self._add_node(input_data)
            elif capability == "update_node":
                result = await self._update_node(input_data)
            elif capability == "remove_node":
                result = await self._remove_node(input_data)
            elif capability == "connect_nodes":
                result = await self._connect_nodes(input_data)
            elif capability == "disconnect_nodes":
                result = await self._disconnect_nodes(input_data)
            elif capability == "get_node_types":
                result = await self._get_node_types(input_data)
            elif capability == "validate_workflow":
                result = await self._validate_workflow(input_data)
            elif capability == "execute_workflow":
                result = await self._execute_workflow(input_data)
            elif capability == "get_last_error":
                result = await self._get_last_error(input_data)
            elif capability == "list_tags":
                result = await self._list_tags(input_data)
            elif capability == "create_complete_workflow":
                result = await self._create_complete_workflow(input_data)
            else:
                result = {"success": False, "error": f"Unknown capability: {capability}"}

            return AgentResult(
                success=result.get("success", False),
                data=result.get("data"),
                message=result.get("message") or result.get("error"),
                metadata={"capability": capability}
            )

        except Exception as e:
            logger.error(f"RMMS Workflow Tool error: {str(e)}")
            return AgentResult(success=False, message=str(e), metadata={"capability": capability, "error": str(e)})

    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Use Task API to check health
                response = await client.get(f"{self.api_base_url}/Task/tasks/3")
                healthy = response.status_code == 200
                message = "RMMS Workflow API accessible" if healthy else f"API returned {response.status_code}"
        except Exception as e:
            healthy = False
            message = f"API connection failed: {str(e)}"

        return HealthStatus(healthy=healthy, component="rmms_workflow_tool", message=message)

    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        if capability in ["get_workflow", "delete_workflow", "validate_workflow", "execute_workflow"]:
            if not input_data.get("workflow_id"):
                errors.append("workflow_id is required")
        elif capability == "create_workflow":
            if not input_data.get("workflow_name"):
                errors.append("workflow_name is required")
            if not input_data.get("company_id"):
                errors.append("company_id is required")
        elif capability == "add_node":
            if not input_data.get("workflow_id"):
                errors.append("workflow_id is required")
            if not input_data.get("node_type"):
                errors.append("node_type is required")
        return errors

    def get_capabilities(self) -> List[str]:
        return [cap.name for cap in self.metadata.capabilities]

    async def _list_workflows(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List workflow tasks from Task API"""
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Workflows are accessed through Task API
            url = f"{self.api_base_url}/Task/tasks/{company_id}"
            response = await client.get(url)
            if response.status_code == 200:
                all_tasks = response.json()
                # Filter only workflow type tasks
                workflows = [t for t in all_tasks if t.get("taskType") == "workflow"]
                # Return summarized info
                workflow_summary = []
                for w in workflows:
                    workflow_summary.append({
                        "id": w.get("id"),
                        "name": w.get("name"),
                        "workflowName": w.get("contentName") or w.get("configuration", {}).get("WorkflowName"),
                        "executionMode": w.get("executionMode"),
                        "executionLocation": w.get("executionLocation"),
                        "status": w.get("status"),
                        "isEnabled": w.get("isEnabled"),
                        "lastStartTime": w.get("lastStartTime"),
                        "lastEndTime": w.get("lastEndTime")
                    })
                return {"success": True, "data": {"workflows": workflow_summary, "count": len(workflows)}, "message": f"Found {len(workflows)} workflows"}
            return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        workflow_name = params.get("workflow_name") or params.get("workflow_id") or params.get("name")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not workflow_name:
            return {"success": False, "error": "workflow_name is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use correct endpoint: /api/Task/workflows/{companyId}/{name}
            response = await client.get(f"{self.api_base_url}/workflows/{company_id}/{workflow_name}")
            if response.status_code == 200:
                workflow = response.json()
                # Parse JSON if it's a string
                if isinstance(workflow.get("json"), str):
                    try:
                        workflow["parsed_json"] = json.loads(workflow["json"])
                    except:
                        pass
                return {"success": True, "data": workflow, "message": f"Retrieved workflow {workflow_name}"}
            return {"success": False, "error": f"Workflow not found: {workflow_name}"}

    async def _create_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow task via Task API"""
        workflow_name = params.get("workflow_name") or params.get("name")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        if not workflow_name:
            return {"success": False, "error": "workflow_name is required"}

        # Execution mode: manual, scheduler, or tag-based
        execution_mode = params.get("execution_mode") or params.get("trigger_type", "manual")
        execution_location = params.get("execution_location", "cloud")
        interval = params.get("interval", 3600)

        logger.info(f"Creating workflow '{workflow_name}' - mode:{execution_mode}, location:{execution_location}, interval:{interval}, params:{params}")

        # Build task data for workflow type
        task_data = {
            "Name": workflow_name,
            "Type": "workflow",
            "ExecutionLocation": execution_location,
            "ExecutionMode": execution_mode,
            "IsEnabled": params.get("is_enabled", True),
            "CompanyId": company_id,
            "Configuration": {
                "ExecutionLocation": execution_location,
                "ExecutionMode": execution_mode,
                "WorkflowName": params.get("content_name", workflow_name),
                "EnableLogging": params.get("enable_logging", True),
                "WatchdogTimeout": params.get("watchdog_timeout", 3000),
                "Timeout": params.get("timeout", 120)
            }
        }

        # Add scheduler settings if scheduler mode
        if execution_mode == "scheduler":
            task_data["Configuration"]["SchedulerSettings"] = {
                "interval": params.get("interval", 3600),
                "type": params.get("scheduler_type", "interval"),
                "specificTimes": params.get("specific_times", [])
            }

        # Add tag-based settings if tag-based mode
        if execution_mode == "tag-based":
            task_data["Configuration"]["TagBasedTasks"] = params.get("tag_triggers", [])

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base_url}/Task/tasks", json=task_data)
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "data": {"task_id": result.get("id"), "name": workflow_name, "task": result},
                    "message": f"Created workflow task '{workflow_name}' with {execution_mode} trigger"
                }
            return {"success": False, "error": f"Failed to create workflow: {response.text}"}

    async def _update_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        workflow_id = params.get("workflow_id")
        if not workflow_id:
            return {"success": False, "error": "workflow_id is required"}
        existing = await self._get_workflow({"workflow_id": workflow_id})
        if not existing.get("success"):
            return existing

        workflow_data = existing["data"]
        if "workflow_name" in params:
            workflow_data["name"] = params["workflow_name"]
        if "description" in params:
            workflow_data["description"] = params["description"]
        if "is_active" in params:
            workflow_data["isActive"] = params["is_active"]
        if "definition" in params:
            workflow_data["definition"] = json.dumps(params["definition"]) if isinstance(params["definition"], dict) else params["definition"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(f"{self.api_base_url}/Workflows/{workflow_id}", json=workflow_data)
            if response.status_code == 200:
                return {"success": True, "data": workflow_data, "message": f"Updated workflow {workflow_id}"}
            return {"success": False, "error": f"Failed to update workflow: {response.text}"}

    async def _delete_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a workflow task via Task API"""
        workflow_name = params.get("workflow_name") or params.get("name") or params.get("workflow_id")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        if not workflow_name:
            return {"success": False, "error": "workflow_name is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(f"{self.api_base_url}/Task/tasks/{company_id}/{workflow_name}")
            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted workflow '{workflow_name}'"}
            return {"success": False, "error": f"Failed to delete workflow: {response.text}"}

    async def _add_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a node to a workflow using proper RMMS node structure.

        Required params:
        - workflow_id or workflow_name: Workflow identifier
        - company_id: Company ID (required)
        - node_type: One of the valid RMMS node types (circularNode, Condition, Arithmetic, etc.)

        Optional params:
        - node_data: Dict with node-specific properties (depends on node_type)
        - position: {x, y} coordinates
        - node_id: Custom node ID (auto-generated if not provided)
        """
        workflow_name = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")
        node_type = params.get("node_type")

        if not workflow_name:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not node_type:
            return {"success": False, "error": "node_type is required"}

        # Validate node type
        valid_types = get_all_node_types()
        if node_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid node_type: {node_type}. Valid types: {', '.join(valid_types)}"
            }

        existing = await self._get_workflow({"workflow_name": workflow_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get parsed workflow JSON
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        nodes = parsed_json.get("nodes", [])
        edges = parsed_json.get("edges", [])

        # Generate node ID if not provided
        node_id = params.get("node_id") or str(len(nodes))

        # Get node data with defaults from node_definitions
        node_info = get_node_type_description(node_type)
        node_data = params.get("node_data", {})

        # Add default label if not provided
        if "label" not in node_data:
            node_data["label"] = params.get("label", f"{node_type} {len(nodes) + 1}")

        # Calculate position
        position = params.get("position", {"x": 250, "y": 100 + len(nodes) * 100})

        # Create new node in RMMS format
        new_node = {
            "id": node_id,
            "type": node_type,
            "data": node_data,
            "position": position
        }

        nodes.append(new_node)
        parsed_json["nodes"] = nodes

        # Update workflow via API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
            update_data = {"json": json.dumps(parsed_json)}
            response = await client.put(url, json=update_data)

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": {"node_id": node_id, "node": new_node},
                    "message": f"Added {node_type} node '{node_id}' to workflow '{workflow_name}'"
                }
            return {"success": False, "error": f"Failed to add node: {response.text}"}

    async def _update_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a node in a workflow.

        Required params:
        - workflow_id or workflow_name: Workflow identifier
        - company_id: Company ID (required)
        - node_id: Node ID to update
        - updates: Dict with updates (data, position, etc.)
        """
        workflow_name = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")
        node_id = params.get("node_id")
        updates = params.get("updates", {})

        if not workflow_name:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not node_id:
            return {"success": False, "error": "node_id is required"}

        existing = await self._get_workflow({"workflow_name": workflow_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get parsed workflow JSON
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        nodes = parsed_json.get("nodes", [])

        node_found = False
        for node in nodes:
            if node.get("id") == node_id:
                node_found = True
                # Update position if provided
                if "position" in updates:
                    node["position"] = updates["position"]
                # Update data fields
                if "data" in updates:
                    node["data"] = {**node.get("data", {}), **updates["data"]}
                # Update specific data fields directly
                for key in ["label", "selectedCondition", "selectedVariable1", "selectedVariable2",
                           "expression", "outputVariable", "expressionId", "to", "subject", "message",
                           "phoneNumber", "selectedTag", "commandValue", "workflowName"]:
                    if key in updates:
                        node.setdefault("data", {})[key] = updates[key]
                break

        if not node_found:
            return {"success": False, "error": f"Node {node_id} not found in workflow"}

        parsed_json["nodes"] = nodes

        # Update workflow via API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
            update_data = {"json": json.dumps(parsed_json)}
            response = await client.put(url, json=update_data)

            if response.status_code == 200:
                return {"success": True, "message": f"Updated node {node_id}"}
            return {"success": False, "error": f"Failed to update node: {response.text}"}

    async def _remove_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove a node from a workflow.

        Required params:
        - workflow_id or workflow_name: Workflow identifier
        - company_id: Company ID (required)
        - node_id: Node ID to remove
        """
        workflow_name = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")
        node_id = params.get("node_id")

        if not workflow_name:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not node_id:
            return {"success": False, "error": "node_id is required"}

        existing = await self._get_workflow({"workflow_name": workflow_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get parsed workflow JSON
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        nodes = parsed_json.get("nodes", [])
        edges = parsed_json.get("edges", [])

        original_count = len(nodes)
        nodes = [n for n in nodes if n.get("id") != node_id]

        if len(nodes) == original_count:
            return {"success": False, "error": f"Node {node_id} not found in workflow"}

        # Remove edges connected to this node
        edges = [e for e in edges if e.get("source") != node_id and e.get("target") != node_id]

        parsed_json["nodes"] = nodes
        parsed_json["edges"] = edges

        # Update workflow via API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
            update_data = {"json": json.dumps(parsed_json)}
            response = await client.put(url, json=update_data)

            if response.status_code == 200:
                return {"success": True, "message": f"Removed node {node_id} from workflow"}
            return {"success": False, "error": f"Failed to remove node: {response.text}"}

    async def _connect_nodes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Connect two nodes in a workflow with an edge.

        Required params:
        - workflow_id or workflow_name: Workflow identifier
        - company_id: Company ID (required)
        - source_id: Source node ID
        - target_id: Target node ID

        Optional params:
        - sourceHandle: 'true' or 'false' for condition node branches
        - label: Edge label
        """
        workflow_name = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")
        source_id = params.get("source_id")
        target_id = params.get("target_id")

        if not workflow_name:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not source_id or not target_id:
            return {"success": False, "error": "source_id and target_id are required"}

        existing = await self._get_workflow({"workflow_name": workflow_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get parsed workflow JSON
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        nodes = parsed_json.get("nodes", [])
        edges = parsed_json.get("edges", [])

        # Validate node IDs exist
        node_ids = {n.get("id") for n in nodes}
        if source_id not in node_ids:
            return {"success": False, "error": f"Source node '{source_id}' not found"}
        if target_id not in node_ids:
            return {"success": False, "error": f"Target node '{target_id}' not found"}

        # Check if edge already exists
        source_handle = params.get("sourceHandle")
        for edge in edges:
            if edge.get("source") == source_id and edge.get("target") == target_id:
                if source_handle is None or edge.get("sourceHandle") == source_handle:
                    return {"success": False, "error": "Connection already exists"}

        # Create edge ID in RMMS format (e.g., "e1-2")
        edge_id = f"e{source_id}-{target_id}"
        if source_handle:
            edge_id = f"e{source_id}-{target_id}-{source_handle}"

        # Create new edge in RMMS format
        new_edge = {
            "id": edge_id,
            "source": source_id,
            "target": target_id
        }

        # Add sourceHandle for condition branches ('true' or 'false')
        if source_handle:
            new_edge["sourceHandle"] = source_handle

        # Add optional label
        if params.get("label"):
            new_edge["label"] = params["label"]

        edges.append(new_edge)
        parsed_json["edges"] = edges

        # Update workflow via API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
            update_data = {"json": json.dumps(parsed_json)}
            response = await client.put(url, json=update_data)

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": {"edge_id": edge_id, "edge": new_edge},
                    "message": f"Connected {source_id} -> {target_id}" + (f" (branch: {source_handle})" if source_handle else "")
                }
            return {"success": False, "error": f"Failed to connect nodes: {response.text}"}

    async def _disconnect_nodes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove an edge between two nodes.

        Required params:
        - workflow_id or workflow_name: Workflow identifier
        - company_id: Company ID (required)
        - source_id: Source node ID
        - target_id: Target node ID
        """
        workflow_name = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")
        source_id = params.get("source_id")
        target_id = params.get("target_id")

        if not workflow_name:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not source_id or not target_id:
            return {"success": False, "error": "source_id and target_id are required"}

        existing = await self._get_workflow({"workflow_name": workflow_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get parsed workflow JSON
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        edges = parsed_json.get("edges", [])
        original_count = len(edges)

        # Remove edge(s) matching source and target
        edges = [e for e in edges if not (e.get("source") == source_id and e.get("target") == target_id)]

        if len(edges) == original_count:
            return {"success": False, "error": f"Connection {source_id} -> {target_id} not found"}

        parsed_json["edges"] = edges

        # Update workflow via API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
            update_data = {"json": json.dumps(parsed_json)}
            response = await client.put(url, json=update_data)

            if response.status_code == 200:
                return {"success": True, "message": f"Disconnected {source_id} -> {target_id}"}
            return {"success": False, "error": f"Failed to disconnect nodes: {response.text}"}

    async def _get_node_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get available RMMS workflow node types with their schemas"""
        # Generate LLM-friendly description
        llm_description = get_node_types_for_llm()

        return {
            "success": True,
            "data": {
                "node_types": self.node_types,
                "operators": self.operators,
                "edge_schema": EDGE_SCHEMA,
                "workflow_structure": WORKFLOW_STRUCTURE,
                "llm_description": llm_description
            },
            "message": f"Available RMMS node types: {', '.join(get_all_node_types())}"
        }

    async def _validate_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow structure based on RMMS requirements"""
        workflow_id = params.get("workflow_id") or params.get("workflow_name")
        company_id = params.get("company_id")

        if not workflow_id:
            return {"success": False, "error": "workflow_id or workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        existing = await self._get_workflow({"workflow_name": workflow_id, "company_id": company_id})
        if not existing.get("success"):
            return existing

        # Get workflow JSON from the response
        workflow_data = existing["data"]
        parsed_json = workflow_data.get("parsed_json") or {}

        nodes = parsed_json.get("nodes", [])
        edges = parsed_json.get("edges", [])
        errors = []
        warnings = []

        # Validate: Must have Start and End nodes (circularNode)
        start_nodes = [n for n in nodes if n.get("type") == "circularNode" and n.get("data", {}).get("label") == "Start"]
        end_nodes = [n for n in nodes if n.get("type") == "circularNode" and n.get("data", {}).get("label") == "End"]

        if len(start_nodes) == 0:
            errors.append("Workflow must have a Start node (circularNode with label='Start')")
        if len(start_nodes) > 1:
            warnings.append("Multiple Start nodes found - only one is recommended")
        if len(end_nodes) == 0:
            errors.append("Workflow must have an End node (circularNode with label='End')")

        # Validate node types
        valid_types = get_all_node_types()
        for node in nodes:
            node_type = node.get("type")
            if node_type and node_type not in valid_types:
                errors.append(f"Unknown node type: {node_type}")

        # Validate edges reference valid nodes
        node_ids = {n.get("id") for n in nodes}
        for edge in edges:
            if edge.get("source") not in node_ids:
                errors.append(f"Edge references unknown source node: {edge.get('source')}")
            if edge.get("target") not in node_ids:
                errors.append(f"Edge references unknown target node: {edge.get('target')}")

        is_valid = len(errors) == 0
        return {
            "success": True,
            "data": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "node_count": len(nodes),
                "edge_count": len(edges)
            },
            "message": "Valid workflow" if is_valid else f"Invalid: {'; '.join(errors)}"
        }

    async def _execute_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow by name"""
        workflow_name = params.get("workflow_name") or params.get("name") or params.get("workflow_id")
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}
        enable_logging = params.get("enable_logging", True)
        watchdog_timeout = params.get("watchdog_timeout", 3000)

        if not workflow_name:
            return {"success": False, "error": "workflow_name is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use Task API workflow execution endpoint
            url = f"{self.api_base_url}/Task/workflows/execute/{company_id}/{workflow_name}"
            response = await client.post(
                url,
                params={"enableLogging": enable_logging, "watchdogTimeout": watchdog_timeout}
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "message": f"Workflow '{workflow_name}' executed. Status: {result.get('Status', 'Unknown')}"
                }
            return {"success": False, "error": f"Execution failed: {response.text}"}

    async def _get_last_error(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get last workflow error for a company"""
        company_id = params.get("company_id")
        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/Task/workflows/last-error/{company_id}"
            response = await client.get(url)
            if response.status_code == 200:
                error_data = response.json()
                return {
                    "success": True,
                    "data": error_data,
                    "message": f"Last workflow error for company {company_id}"
                }
            return {"success": False, "error": f"Failed to get last error: {response.text}"}

    async def _list_tags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tags for a company. Use this to show user available tags before creating workflow."""
        company_id = params.get("company_id")
        search = params.get("search", "").lower()

        if not company_id:
            return {"success": False, "error": "company_id is required. Please ask user which company to use."}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Tags API endpoint
            url = f"https://rmms-metis-engine.azurewebsites.net/api/Tags/all/{company_id}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                tags = data.get("tags", [])

                # Filter by search term if provided
                if search:
                    tags = [t for t in tags if search in t.get("tagName", "").lower() or search in t.get("tagName2", "").lower()]

                # Format for easy reading
                tag_list = []
                for t in tags[:50]:  # Limit to 50 tags
                    tag_list.append({
                        "id": f"tag_{t['tagID']}",
                        "name": t.get("tagName2") or t.get("tagName"),
                        "full_name": t.get("tagName")
                    })

                return {
                    "success": True,
                    "data": {
                        "company_id": company_id,
                        "total_tags": len(data.get("tags", [])),
                        "showing": len(tag_list),
                        "tags": tag_list
                    },
                    "message": f"Found {len(data.get('tags', []))} tags for company {company_id}. Use tag_XXXX format in workflows."
                }
            return {"success": False, "error": f"Failed to get tags: {response.text}"}

    async def _create_complete_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a complete workflow with nodes and edges in a SINGLE API call.

        This is the PREFERRED method for creating workflows as it:
        - Creates the workflow definition with all nodes and edges at once
        - Avoids issues with creating empty workflows first
        - Uses the correct RMMS workflow format

        Required params:
        - workflow_name: Name of the workflow
        - company_id: Company ID (REQUIRED)
        - workflow_json: Complete workflow definition object with:
            - nodes: Array of node objects
            - edges: Array of edge objects
            - localVars: Array of local variables (can be empty [])

        Example workflow_json:
        {
            "nodes": [
                {"id": "0", "type": "circularNode", "data": {"label": "Start"}, "position": {"x": 250, "y": 5}},
                {"id": "1", "type": "Condition", "data": {"label": "Temp > 30?", "selectedCondition": ">", "selectedVariable1": "tag_11445", "selectedVariable2": "30", "inputType1": "select", "inputType2": "text"}, "position": {"x": 250, "y": 100}},
                {"id": "2", "type": "Alarm", "data": {"label": "High Temp", "message": "Temperature exceeded!", "severity": "critical", "variables": []}, "position": {"x": 100, "y": 200}},
                {"id": "9999", "type": "circularNode", "data": {"label": "End"}, "position": {"x": 250, "y": 300}}
            ],
            "edges": [
                {"id": "e0-1", "source": "0", "target": "1"},
                {"id": "e1-2-true", "source": "1", "target": "2", "sourceHandle": "true"},
                {"id": "e1-9999-false", "source": "1", "target": "9999", "sourceHandle": "false"},
                {"id": "e2-9999", "source": "2", "target": "9999"}
            ],
            "localVars": []
        }
        """
        workflow_name = params.get("workflow_name") or params.get("name")
        company_id = params.get("company_id")
        workflow_json = params.get("workflow_json")

        if not workflow_name:
            return {"success": False, "error": "workflow_name is required"}
        if not company_id:
            return {"success": False, "error": "company_id is required. Ask user which company to use."}
        if not workflow_json:
            return {"success": False, "error": "workflow_json is required. Use COMPLETE_WORKFLOW_EXAMPLE as template."}

        # Validate workflow_json structure
        if not isinstance(workflow_json, dict):
            try:
                workflow_json = json.loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
            except json.JSONDecodeError:
                return {"success": False, "error": "workflow_json must be a valid JSON object"}

        nodes = workflow_json.get("nodes", [])
        edges = workflow_json.get("edges", [])
        local_vars = workflow_json.get("localVars", [])

        if not nodes:
            return {"success": False, "error": "workflow_json.nodes is required and must not be empty"}

        # Validate node types are correct case
        valid_types = get_all_node_types()
        for node in nodes:
            node_type = node.get("type")
            if node_type and node_type not in valid_types:
                # Check for common case mistakes
                for valid in valid_types:
                    if node_type.lower() == valid.lower() and node_type != valid:
                        return {
                            "success": False,
                            "error": f"Invalid node type '{node_type}'. Did you mean '{valid}'? Node types are CASE-SENSITIVE."
                        }
                return {"success": False, "error": f"Unknown node type: {node_type}. Valid types: {', '.join(valid_types)}"}

        # Validate edges reference valid node IDs
        node_ids = {n.get("id") for n in nodes}
        for edge in edges:
            if edge.get("source") not in node_ids:
                return {"success": False, "error": f"Edge references unknown source node: {edge.get('source')}"}
            if edge.get("target") not in node_ids:
                return {"success": False, "error": f"Edge references unknown target node: {edge.get('target')}"}

        # Prepare workflow data for API
        workflow_data = {
            "name": workflow_name,
            "companyId": company_id,
            "json": json.dumps(workflow_json)
        }

        logger.info(f"Creating complete workflow '{workflow_name}' for company {company_id} with {len(nodes)} nodes and {len(edges)} edges")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use POST to create workflow with full definition
            post_url = f"{self.api_base_url}/workflows"
            response = await client.post(post_url, json=workflow_data)

            logger.info(f"Workflow creation response: {response.status_code} - {response.text[:500] if response.text else 'empty'}")

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "data": {
                        "workflow_name": workflow_name,
                        "company_id": company_id,
                        "node_count": len(nodes),
                        "edge_count": len(edges)
                    },
                    "message": f"Created workflow '{workflow_name}' with {len(nodes)} nodes and {len(edges)} edges"
                }

            # If POST fails, try PUT to update existing
            if response.status_code in [400, 409]:  # Conflict or bad request might mean it exists
                put_url = f"{self.api_base_url}/workflows/{company_id}/{workflow_name}"
                response = await client.put(put_url, json={"json": json.dumps(workflow_json)})

                if response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "data": {
                            "workflow_name": workflow_name,
                            "company_id": company_id,
                            "node_count": len(nodes),
                            "edge_count": len(edges)
                        },
                        "message": f"Updated workflow '{workflow_name}' with {len(nodes)} nodes and {len(edges)} edges"
                    }

            return {"success": False, "error": f"Failed to create workflow: {response.status_code} - {response.text}"}
