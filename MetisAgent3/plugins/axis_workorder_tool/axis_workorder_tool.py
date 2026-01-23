"""
Axis Work Order Tool - AI-powered Work Order Management

Capabilities:
- List/Get/Create/Update work orders
- Take and close work orders
- Get work order statistics
"""

import logging
import httpx
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

logger = logging.getLogger(__name__)


class AxisWorkOrderTool(BaseTool):
    """Axis Work Order Management Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://metis-api-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)
        self.default_company_id = config.config.get("company_id", 1)
        self._token = None
        self._token_expiry = None

        logger.info(f"AxisWorkOrderTool initialized with API: {self.api_base_url}")

    async def _get_auth_token(self) -> Optional[str]:
        """Get JWT token for Axis API authentication"""
        try:
            if self._token and self._token_expiry and datetime.now() < self._token_expiry:
                return self._token

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/Auth/login",
                    json={"Username": "admin", "Password": "admin123"}
                )

                if response.status_code == 200:
                    data = response.json()
                    self._token = data.get("token")
                    self._token_expiry = datetime.now() + timedelta(hours=23)
                    return self._token
            return None
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return None

    async def _make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Make authenticated request to Axis API"""
        token = await self._get_auth_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/{endpoint}"

            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown method: {method}")

            if response.status_code >= 400:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

            try:
                return {"success": True, "data": response.json()}
            except:
                return {"success": True, "data": response.text}

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a capability"""
        try:
            logger.info(f"Executing capability: {capability_name} with params: {parameters}")

            if capability_name == "list_workorders":
                return await self._list_workorders(parameters)
            elif capability_name == "get_workorder":
                return await self._get_workorder(parameters)
            elif capability_name == "create_workorder":
                return await self._create_workorder(parameters)
            elif capability_name == "update_workorder":
                return await self._update_workorder(parameters)
            elif capability_name == "take_workorder":
                return await self._take_workorder(parameters)
            elif capability_name == "close_workorder":
                return await self._close_workorder(parameters)
            elif capability_name == "get_workorder_stats":
                return await self._get_workorder_stats(parameters)
            else:
                return AgentResult(success=False, message=f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"Error executing {capability_name}: {e}")
            return AgentResult(success=False, message=str(e))

    async def _list_workorders(self, params: dict) -> AgentResult:
        """List all work orders"""
        query_params = {"companyId": params.get("company_id", self.default_company_id)}
        if params.get("status"):
            query_params["status"] = params["status"]
        if params.get("priority"):
            query_params["priority"] = params["priority"]
        if params.get("assigned_user_id"):
            query_params["assignedUserId"] = params["assigned_user_id"]

        result = await self._make_request("GET", "WorkOrder/list", params=query_params)

        if result["success"]:
            workorders = result["data"]
            summary = f"Found {len(workorders)} work orders"
            return AgentResult(success=True, message=summary, data=workorders)
        return AgentResult(success=False, message=result.get("error", "Failed to list work orders"))

    async def _get_workorder(self, params: dict) -> AgentResult:
        """Get a specific work order"""
        workorder_id = params.get("workorder_id")
        if not workorder_id:
            return AgentResult(success=False, message="workorder_id is required")

        result = await self._make_request("GET", f"WorkOrder/{workorder_id}")

        if result["success"]:
            wo = result["data"]
            return AgentResult(success=True, message=f"Work order #{workorder_id}: {wo.get('title', 'N/A')}", data=wo)
        return AgentResult(success=False, message=result.get("error", "Failed to get work order"))

    async def _create_workorder(self, params: dict) -> AgentResult:
        """Create a new work order"""
        title = params.get("title")
        if not title:
            return AgentResult(success=False, message="title is required")

        data = {
            "title": title,
            "description": params.get("description", ""),
            "priority": params.get("priority", "Medium"),
            "workOrderType": params.get("work_order_type", "Maintenance"),
            "location": params.get("location", ""),
            "equipment": params.get("equipment", ""),
            "estimatedHours": params.get("estimated_hours"),
            "assignedUserId": params.get("assigned_user_id"),
            "dueDate": params.get("due_date"),
            "companyId": params.get("company_id", self.default_company_id)
        }

        result = await self._make_request("POST", "WorkOrder/createUserRequest", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Created work order: {title}", data=result["data"])
        return AgentResult(success=False, message=result.get("error", "Failed to create work order"))

    async def _update_workorder(self, params: dict) -> AgentResult:
        """Update an existing work order"""
        workorder_id = params.get("workorder_id")
        if not workorder_id:
            return AgentResult(success=False, message="workorder_id is required")

        data = {"workOrderId": workorder_id}
        field_mapping = {
            "title": "title",
            "description": "description",
            "priority": "priority",
            "status": "workOrderStatus",
            "location": "location",
            "equipment": "equipment"
        }

        for param_key, api_key in field_mapping.items():
            if param_key in params:
                data[api_key] = params[param_key]

        result = await self._make_request("PUT", f"WorkOrder/{workorder_id}", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Updated work order #{workorder_id}", data=result["data"])
        return AgentResult(success=False, message=result.get("error", "Failed to update work order"))

    async def _take_workorder(self, params: dict) -> AgentResult:
        """Take/assign a work order"""
        workorder_id = params.get("workorder_id")
        user_id = params.get("user_id")

        if not workorder_id or not user_id:
            return AgentResult(success=False, message="workorder_id and user_id are required")

        result = await self._make_request("POST", f"WorkOrder/{workorder_id}/take", data={"userId": user_id})

        if result["success"]:
            return AgentResult(success=True, message=f"Work order #{workorder_id} assigned to user {user_id}")
        return AgentResult(success=False, message=result.get("error", "Failed to take work order"))

    async def _close_workorder(self, params: dict) -> AgentResult:
        """Close/complete a work order"""
        workorder_id = params.get("workorder_id")
        if not workorder_id:
            return AgentResult(success=False, message="workorder_id is required")

        data = {
            "actualHours": params.get("actual_hours"),
            "completionNotes": params.get("completion_notes", "")
        }

        result = await self._make_request("POST", f"WorkOrder/{workorder_id}/close", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Work order #{workorder_id} closed successfully")
        return AgentResult(success=False, message=result.get("error", "Failed to close work order"))

    async def _get_workorder_stats(self, params: dict) -> AgentResult:
        """Get work order statistics"""
        company_id = params.get("company_id", self.default_company_id)

        result = await self._make_request("GET", "WorkOrder/list", params={"companyId": company_id})

        if result["success"]:
            workorders = result["data"]
            stats = {"Open": 0, "InProgress": 0, "Completed": 0, "Total": len(workorders)}

            for wo in workorders:
                status = wo.get("workOrderStatus", "Open")
                if status in stats:
                    stats[status] += 1

            summary = f"Work Orders - Open: {stats['Open']}, In Progress: {stats['InProgress']}, Completed: {stats['Completed']}"
            return AgentResult(success=True, message=summary, data=stats)
        return AgentResult(success=False, message=result.get("error", "Failed to get statistics"))

    async def health_check(self) -> HealthStatus:
        """Check tool health"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_base_url}/health")
                if response.status_code == 200:
                    return HealthStatus(healthy=True, message="Axis API is reachable")
            return HealthStatus(healthy=False, message="Axis API is not responding")
        except Exception as e:
            return HealthStatus(healthy=False, message=str(e))

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

