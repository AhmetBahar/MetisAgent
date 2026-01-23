"""Axis OEE Tool - Overall Equipment Effectiveness"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisOEETool(AxisBaseTool):
    """Axis OEE Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisOEETool initialized with API: {self.api_base_url}")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            logger.info(f"OEE executing: {capability_name}")

            handlers = {
                "get_dashboard": self._get_dashboard,
                "get_oee_by_machine": self._get_oee_by_machine,
                "list_downtime_categories": self._list_categories,
                "list_downtime_reasons": self._list_reasons,
                "record_downtime": self._record_downtime,
                "get_downtime_analysis": self._get_downtime_analysis,
                "list_machines": self._list_machines,
                "get_shift_report": self._get_shift_report,
            }

            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"OEE error: {e}")
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        query = {}
        if params.get("plant_id"):
            query["plantId"] = params["plant_id"]

        result = await self._make_request("GET", "OEE/dashboard", params=query)
        if result["success"]:
            data = result["data"]
            oee = data.get("oee", "N/A") if isinstance(data, dict) else "N/A"
            return self._result(True, f"OEE Dashboard - Overall: {oee}%", data)
        return self._error(result, "Failed to get OEE dashboard")

    async def _get_oee_by_machine(self, params: dict) -> AgentResult:
        machine_id = params.get("machine_id")
        if not machine_id:
            return self._result(False, "machine_id is required")

        data = {"machineId": machine_id}
        if params.get("start_date"):
            data["startDate"] = params["start_date"]
        if params.get("end_date"):
            data["endDate"] = params["end_date"]

        result = await self._make_request("POST", "OEE/calculate", data=data)
        if result["success"]:
            return self._result(True, f"OEE for machine {machine_id}", result["data"])
        return self._error(result, "Failed to get machine OEE")

    async def _list_categories(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "OEE/categories")
        if result["success"]:
            cats = result["data"]
            return self._result(True, f"Found {len(cats)} downtime categories", cats)
        return self._error(result, "Failed to list categories")

    async def _list_reasons(self, params: dict) -> AgentResult:
        query = {}
        if params.get("category_id"):
            query["categoryId"] = params["category_id"]

        result = await self._make_request("GET", "OEE/reasons", params=query)
        if result["success"]:
            reasons = result["data"]
            return self._result(True, f"Found {len(reasons)} downtime reasons", reasons)
        return self._error(result, "Failed to list reasons")

    async def _record_downtime(self, params: dict) -> AgentResult:
        data = {
            "machineId": params.get("machine_id"),
            "reasonId": params.get("reason_id"),
            "startTime": params.get("start_time"),
            "endTime": params.get("end_time"),
            "notes": params.get("notes", "")
        }
        result = await self._make_request("POST", "OEE/downtime-events", data=data)
        if result["success"]:
            return self._result(True, "Downtime recorded")
        return self._error(result, "Failed to record downtime")

    async def _get_downtime_analysis(self, params: dict) -> AgentResult:
        query = {}
        if params.get("machine_id"):
            query["machineId"] = params["machine_id"]
        if params.get("start_date"):
            query["startDate"] = params["start_date"]
        if params.get("end_date"):
            query["endDate"] = params["end_date"]

        result = await self._make_request("GET", "OEE/reports/pareto", params=query)
        if result["success"]:
            return self._result(True, "Downtime analysis completed", result["data"])
        return self._error(result, "Failed to analyze downtime")

    async def _list_machines(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "OEE/speed-profiles")
        if result["success"]:
            profiles = result["data"]
            count = len(profiles) if isinstance(profiles, list) else "N/A"
            return self._result(True, f"Found {count} machine speed profiles", profiles)
        return self._error(result, "Failed to list machines")

    async def _get_shift_report(self, params: dict) -> AgentResult:
        query = {}
        if params.get("machine_id"):
            query["machineId"] = params["machine_id"]
        if params.get("start_date"):
            query["startDate"] = params["start_date"]
        if params.get("end_date"):
            query["endDate"] = params["end_date"]

        result = await self._make_request("GET", "OEE/reports/trend", params=query)
        if result["success"]:
            return self._result(True, "Shift/trend report retrieved", result["data"])
        return self._error(result, "Failed to get shift report")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

