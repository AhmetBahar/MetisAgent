"""Axis Traceability Tool"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisTraceabilityTool(AxisBaseTool):
    """Axis Traceability Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisTraceabilityTool initialized")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            handlers = {
                "get_dashboard": self._get_dashboard,
                "trace_batch": self._trace_batch,
                "list_batches": self._list_batches,
                "create_batch": self._create_batch,
                "record_consumption": self._record_consumption,
                "get_genealogy": self._get_genealogy,
                "get_process_history": self._get_process_history,
                "recall_simulation": self._recall_simulation,
            }
            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")
        except Exception as e:
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "Traceability/dashboard")
        if result["success"]:
            return self._result(True, "Traceability dashboard retrieved", result["data"])
        return self._error(result, "Failed to get dashboard")

    async def _trace_batch(self, params: dict) -> AgentResult:
        batch = params.get("batch_number")
        if not batch:
            return self._result(False, "batch_number is required")
        result = await self._make_request("GET", f"Traceability/trace/{batch}")
        if result["success"]:
            return self._result(True, f"Trace for batch {batch}", result["data"])
        return self._error(result, "Failed to trace batch")

    async def _list_batches(self, params: dict) -> AgentResult:
        query = {}
        for k, v in [("productId", "product_id"), ("status", "status"), ("startDate", "start_date"), ("endDate", "end_date")]:
            if params.get(v):
                query[k] = params[v]
        result = await self._make_request("GET", "Traceability/batches", params=query)
        if result["success"]:
            return self._result(True, f"Found {len(result['data'])} batches", result["data"])
        return self._error(result, "Failed to list batches")

    async def _create_batch(self, params: dict) -> AgentResult:
        data = {
            "batchNumber": params.get("batch_number"),
            "productId": params.get("product_id"),
            "quantity": params.get("quantity"),
            "productionDate": params.get("production_date"),
            "expiryDate": params.get("expiry_date")
        }
        result = await self._make_request("POST", "Traceability/batches", data=data)
        if result["success"]:
            return self._result(True, f"Batch {params.get('batch_number')} created", result["data"])
        return self._error(result, "Failed to create batch")

    async def _record_consumption(self, params: dict) -> AgentResult:
        data = {
            "batchNumber": params.get("batch_number"),
            "materialBatch": params.get("material_batch"),
            "quantity": params.get("quantity")
        }
        result = await self._make_request("POST", "Traceability/consumption", data=data)
        if result["success"]:
            return self._result(True, "Consumption recorded", result["data"])
        return self._error(result, "Failed to record consumption")

    async def _get_genealogy(self, params: dict) -> AgentResult:
        batch = params.get("batch_number")
        direction = params.get("direction", "both")
        result = await self._make_request("GET", f"Traceability/genealogy/{batch}", params={"direction": direction})
        if result["success"]:
            return self._result(True, f"Genealogy for {batch}", result["data"])
        return self._error(result, "Failed to get genealogy")

    async def _get_process_history(self, params: dict) -> AgentResult:
        batch = params.get("batch_number")
        result = await self._make_request("GET", f"Traceability/process-history/{batch}")
        if result["success"]:
            return self._result(True, f"Process history for {batch}", result["data"])
        return self._error(result, "Failed to get process history")

    async def _recall_simulation(self, params: dict) -> AgentResult:
        data = {
            "batchNumber": params.get("batch_number"),
            "reason": params.get("reason", "Simulation")
        }
        result = await self._make_request("POST", "Traceability/recall-simulation", data=data)
        if result["success"]:
            return self._result(True, "Recall simulation completed", result["data"])
        return self._error(result, "Failed to simulate recall")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

