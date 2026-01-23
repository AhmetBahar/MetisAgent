"""Axis Quality Control Tool"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisQualityTool(AxisBaseTool):
    """Axis Quality Control Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisQualityTool initialized")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            handlers = {
                "get_dashboard": self._get_dashboard,
                "list_templates": self._list_templates,
                "get_template": self._get_template,
                "create_template": self._create_template,
                "list_inspections": self._list_inspections,
                "create_inspection": self._create_inspection,
                "list_defects": self._list_defects,
                "record_defect": self._record_defect,
                "get_spc_data": self._get_spc_data,
            }
            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")
        except Exception as e:
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "QualityControl/dashboard")
        if result["success"]:
            return self._result(True, "QC Dashboard retrieved", result["data"])
        return self._error(result, "Failed to get QC dashboard")

    async def _list_templates(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "QualityControl/templates")
        if result["success"]:
            return self._result(True, f"Found {len(result['data'])} templates", result["data"])
        return self._error(result, "Failed to list templates")

    async def _get_template(self, params: dict) -> AgentResult:
        tid = params.get("template_id")
        result = await self._make_request("GET", f"QualityControl/templates/{tid}")
        if result["success"]:
            return self._result(True, f"Template {tid} retrieved", result["data"])
        return self._error(result, "Failed to get template")

    async def _create_template(self, params: dict) -> AgentResult:
        data = {
            "name": params.get("name"),
            "description": params.get("description", ""),
            "inspectionType": params.get("inspection_type"),
            "checkItems": params.get("check_items", [])
        }
        result = await self._make_request("POST", "QualityControl/templates", data=data)
        if result["success"]:
            return self._result(True, "Template created", result["data"])
        return self._error(result, "Failed to create template")

    async def _list_inspections(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("templateId", "template_id"), ("result", "result"), ("startDate", "start_date"), ("endDate", "end_date")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "QualityControl/inspections", params=query)
        if result["success"]:
            return self._result(True, f"Found {len(result['data'])} inspections", result["data"])
        return self._error(result, "Failed to list inspections")

    async def _create_inspection(self, params: dict) -> AgentResult:
        data = {
            "templateId": params.get("template_id"),
            "productId": params.get("product_id"),
            "batchNumber": params.get("batch_number"),
            "results": params.get("results", {})
        }
        result = await self._make_request("POST", "QualityControl/inspections", data=data)
        if result["success"]:
            return self._result(True, "Inspection recorded", result["data"])
        return self._error(result, "Failed to create inspection")

    async def _list_defects(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("defectType", "defect_type"), ("severity", "severity"), ("startDate", "start_date"), ("endDate", "end_date")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "QualityControl/defects", params=query)
        if result["success"]:
            return self._result(True, f"Found {len(result['data'])} defects", result["data"])
        return self._error(result, "Failed to list defects")

    async def _record_defect(self, params: dict) -> AgentResult:
        data = {
            "defectType": params.get("defect_type"),
            "severity": params.get("severity"),
            "description": params.get("description", ""),
            "productId": params.get("product_id"),
            "batchNumber": params.get("batch_number"),
            "quantity": params.get("quantity", 1)
        }
        result = await self._make_request("POST", "QualityControl/defects", data=data)
        if result["success"]:
            return self._result(True, "Defect recorded", result["data"])
        return self._error(result, "Failed to record defect")

    async def _get_spc_data(self, params: dict) -> AgentResult:
        query = {"parameterId": params.get("parameter_id")}
        if params.get("start_date"):
            query["startDate"] = params["start_date"]
        if params.get("end_date"):
            query["endDate"] = params["end_date"]
        result = await self._make_request("GET", "QualityControl/spc", params=query)
        if result["success"]:
            return self._result(True, "SPC data retrieved", result["data"])
        return self._error(result, "Failed to get SPC data")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

