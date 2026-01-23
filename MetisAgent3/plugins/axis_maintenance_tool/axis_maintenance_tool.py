"""Axis Maintenance Tool - Predictive/TPM"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisMaintenanceTool(AxisBaseTool):
    """Axis Maintenance Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisMaintenanceTool initialized")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            handlers = {
                "get_dashboard": self._get_dashboard,
                "get_health_score": self._get_health_score,
                "get_predictive_alerts": self._get_predictive_alerts,
                "list_spare_parts": self._list_spare_parts,
                "update_spare_part": self._update_spare_part,
                "list_autonomous_tasks": self._list_autonomous_tasks,
                "complete_autonomous_task": self._complete_autonomous_task,
                "get_maintenance_history": self._get_maintenance_history,
                "schedule_maintenance": self._schedule_maintenance,
            }
            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")
        except Exception as e:
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "Maintenance/dashboard")
        if result["success"]:
            return self._result(True, "Maintenance dashboard retrieved", result["data"])
        return self._error(result, "Failed to get dashboard")

    async def _get_health_score(self, params: dict) -> AgentResult:
        eq_id = params.get("equipment_id")
        if not eq_id:
            return self._result(False, "equipment_id is required")
        result = await self._make_request("GET", f"Maintenance/health-score/{eq_id}")
        if result["success"]:
            data = result["data"]
            score = data.get("score", "N/A") if isinstance(data, dict) else "N/A"
            return self._result(True, f"Health score: {score}", data)
        return self._error(result, "Failed to get health score")

    async def _get_predictive_alerts(self, params: dict) -> AgentResult:
        query = {}
        if params.get("equipment_id"):
            query["equipmentId"] = params["equipment_id"]
        if params.get("severity"):
            query["severity"] = params["severity"]
        result = await self._make_request("GET", "Maintenance/predictive-alerts", params=query)
        if result["success"]:
            alerts = result["data"]
            return self._result(True, f"Found {len(alerts)} predictive alerts", alerts)
        return self._error(result, "Failed to get predictive alerts")

    async def _list_spare_parts(self, params: dict) -> AgentResult:
        query = {}
        if params.get("equipment_id"):
            query["equipmentId"] = params["equipment_id"]
        if params.get("low_stock_only"):
            query["lowStockOnly"] = params["low_stock_only"]
        result = await self._make_request("GET", "Maintenance/spare-parts", params=query)
        if result["success"]:
            parts = result["data"]
            return self._result(True, f"Found {len(parts)} spare parts", parts)
        return self._error(result, "Failed to list spare parts")

    async def _update_spare_part(self, params: dict) -> AgentResult:
        data = {
            "partId": params.get("part_id"),
            "quantityChange": params.get("quantity_change"),
            "reason": params.get("reason", "")
        }
        result = await self._make_request("POST", "Maintenance/spare-parts/update", data=data)
        if result["success"]:
            return self._result(True, "Spare part updated", result["data"])
        return self._error(result, "Failed to update spare part")

    async def _list_autonomous_tasks(self, params: dict) -> AgentResult:
        query = {}
        if params.get("equipment_id"):
            query["equipmentId"] = params["equipment_id"]
        if params.get("status"):
            query["status"] = params["status"]
        result = await self._make_request("GET", "Maintenance/autonomous-tasks", params=query)
        if result["success"]:
            tasks = result["data"]
            return self._result(True, f"Found {len(tasks)} autonomous tasks", tasks)
        return self._error(result, "Failed to list autonomous tasks")

    async def _complete_autonomous_task(self, params: dict) -> AgentResult:
        data = {
            "taskId": params.get("task_id"),
            "result": params.get("result"),
            "notes": params.get("notes", "")
        }
        result = await self._make_request("POST", "Maintenance/autonomous-tasks/complete", data=data)
        if result["success"]:
            return self._result(True, "Autonomous task completed", result["data"])
        return self._error(result, "Failed to complete task")

    async def _get_maintenance_history(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("equipmentId", "equipment_id"), ("maintenanceType", "maintenance_type"), ("startDate", "start_date"), ("endDate", "end_date")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "Maintenance/history", params=query)
        if result["success"]:
            history = result["data"]
            return self._result(True, f"Found {len(history)} maintenance records", history)
        return self._error(result, "Failed to get maintenance history")

    async def _schedule_maintenance(self, params: dict) -> AgentResult:
        data = {
            "equipmentId": params.get("equipment_id"),
            "maintenanceType": params.get("maintenance_type"),
            "scheduledDate": params.get("scheduled_date"),
            "description": params.get("description", ""),
            "estimatedDuration": params.get("estimated_duration")
        }
        result = await self._make_request("POST", "Maintenance/schedule", data=data)
        if result["success"]:
            return self._result(True, "Maintenance scheduled", result["data"])
        return self._error(result, "Failed to schedule maintenance")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

