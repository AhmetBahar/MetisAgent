"""Axis Energy Optimization Tool"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisEnergyTool(AxisBaseTool):
    """Axis Energy Optimization Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisEnergyTool initialized")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            handlers = {
                "get_dashboard": self._get_dashboard,
                "list_profiles": self._list_profiles,
                "get_profile": self._get_profile,
                "create_profile": self._create_profile,
                "get_consumption": self._get_consumption,
                "record_consumption": self._record_consumption,
                "get_cost_analysis": self._get_cost_analysis,
                "get_carbon_footprint": self._get_carbon_footprint,
                "get_optimization_recommendations": self._get_recommendations,
            }
            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")
        except Exception as e:
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "EnergyOptimization/dashboard")
        if result["success"]:
            return self._result(True, "Energy dashboard retrieved", result["data"])
        return self._error(result, "Failed to get dashboard")

    async def _list_profiles(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "EnergyOptimization/profiles")
        if result["success"]:
            profiles = result["data"]
            return self._result(True, f"Found {len(profiles)} energy profiles", profiles)
        return self._error(result, "Failed to list profiles")

    async def _get_profile(self, params: dict) -> AgentResult:
        pid = params.get("profile_id")
        if not pid:
            return self._result(False, "profile_id is required")
        result = await self._make_request("GET", f"EnergyOptimization/profiles/{pid}")
        if result["success"]:
            return self._result(True, f"Profile {pid} retrieved", result["data"])
        return self._error(result, "Failed to get profile")

    async def _create_profile(self, params: dict) -> AgentResult:
        data = {
            "name": params.get("name"),
            "description": params.get("description", ""),
            "energyType": params.get("energy_type"),
            "targetConsumption": params.get("target_consumption"),
            "costPerUnit": params.get("cost_per_unit")
        }
        result = await self._make_request("POST", "EnergyOptimization/profiles", data=data)
        if result["success"]:
            return self._result(True, "Energy profile created", result["data"])
        return self._error(result, "Failed to create profile")

    async def _get_consumption(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("profileId", "profile_id"), ("startDate", "start_date"), ("endDate", "end_date"), ("interval", "interval")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "EnergyOptimization/consumption", params=query)
        if result["success"]:
            return self._result(True, "Consumption data retrieved", result["data"])
        return self._error(result, "Failed to get consumption")

    async def _record_consumption(self, params: dict) -> AgentResult:
        data = {
            "profileId": params.get("profile_id"),
            "value": params.get("value"),
            "timestamp": params.get("timestamp")
        }
        result = await self._make_request("POST", "EnergyOptimization/consumption", data=data)
        if result["success"]:
            return self._result(True, "Consumption recorded", result["data"])
        return self._error(result, "Failed to record consumption")

    async def _get_cost_analysis(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("profileId", "profile_id"), ("startDate", "start_date"), ("endDate", "end_date")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "EnergyOptimization/consumption/summary", params=query)
        if result["success"]:
            return self._result(True, "Cost/consumption summary retrieved", result["data"])
        return self._error(result, "Failed to get cost analysis")

    async def _get_carbon_footprint(self, params: dict) -> AgentResult:
        query = {}
        if params.get("start_date"):
            query["startDate"] = params["start_date"]
        if params.get("end_date"):
            query["endDate"] = params["end_date"]
        result = await self._make_request("GET", "EnergyOptimization/line-carbon/dashboard", params=query)
        if result["success"]:
            return self._result(True, "Carbon footprint data retrieved", result["data"])
        return self._error(result, "Failed to get carbon footprint")

    async def _get_recommendations(self, params: dict) -> AgentResult:
        query = {}
        if params.get("status"):
            query["status"] = params["status"]
        result = await self._make_request("GET", "EnergyOptimization/goals", params=query)
        if result["success"]:
            goals = result["data"]
            count = len(goals) if isinstance(goals, list) else "N/A"
            return self._result(True, f"Found {count} optimization goals", goals)
        return self._error(result, "Failed to get optimization goals")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

