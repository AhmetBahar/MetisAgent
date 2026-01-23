"""Axis MES Tool - Manufacturing Execution System"""

import logging
from typing import Any, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from axis_base_tool import AxisBaseTool
from core.contracts import ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext

logger = logging.getLogger(__name__)


class AxisMESTool(AxisBaseTool):
    """Axis MES Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        logger.info(f"AxisMESTool initialized with API: {self.api_base_url}")

    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        try:
            logger.info(f"MES executing: {capability_name}")

            handlers = {
                "get_dashboard": self._get_dashboard,
                "list_orders": self._list_orders,
                "get_order": self._get_order,
                "create_order": self._create_order,
                "start_order": self._start_order,
                "complete_order": self._complete_order,
                "list_work_centers": self._list_work_centers,
                "get_bottleneck_analysis": self._get_bottleneck,
                "list_products": self._list_products,
            }

            handler = handlers.get(capability_name)
            if handler:
                return await handler(parameters)
            return self._result(False, f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"MES error: {e}")
            return self._result(False, str(e))

    async def _get_dashboard(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "MES/dashboard")
        if result["success"]:
            return self._result(True, "MES dashboard retrieved", result["data"])
        return self._error(result, "Failed to get MES dashboard")

    async def _list_orders(self, params: dict) -> AgentResult:
        query = {}
        if params.get("status"):
            query["status"] = params["status"]
        if params.get("line_id"):
            query["lineId"] = params["line_id"]

        result = await self._make_request("GET", "MES/orders", params=query)
        if result["success"]:
            orders = result["data"]
            return self._result(True, f"Found {len(orders)} production orders", orders)
        return self._error(result, "Failed to list orders")

    async def _get_order(self, params: dict) -> AgentResult:
        order_id = params.get("order_id")
        if not order_id:
            return self._result(False, "order_id is required")

        result = await self._make_request("GET", f"MES/orders/{order_id}")
        if result["success"]:
            return self._result(True, f"Order #{order_id} retrieved", result["data"])
        return self._error(result, "Failed to get order")

    async def _create_order(self, params: dict) -> AgentResult:
        data = {
            "productId": params.get("product_id"),
            "lineId": params.get("line_id"),
            "plannedQuantity": params.get("planned_quantity"),
            "plannedStart": params.get("planned_start"),
            "plannedEnd": params.get("planned_end"),
            "priority": params.get("priority", 1)
        }
        result = await self._make_request("POST", "MES/orders", data=data)
        if result["success"]:
            return self._result(True, "Production order created", result["data"])
        return self._error(result, "Failed to create order")

    async def _start_order(self, params: dict) -> AgentResult:
        order_id = params.get("order_id")
        result = await self._make_request("POST", f"MES/orders/{order_id}/start")
        if result["success"]:
            return self._result(True, f"Order #{order_id} started")
        return self._error(result, "Failed to start order")

    async def _complete_order(self, params: dict) -> AgentResult:
        order_id = params.get("order_id")
        data = {
            "producedQuantity": params.get("produced_quantity"),
            "scrapQuantity": params.get("scrap_quantity", 0)
        }
        result = await self._make_request("POST", f"MES/orders/{order_id}/complete", data=data)
        if result["success"]:
            return self._result(True, f"Order #{order_id} completed")
        return self._error(result, "Failed to complete order")

    async def _list_work_centers(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "MES/work-centers")
        if result["success"]:
            centers = result["data"]
            return self._result(True, f"Found {len(centers)} work centers", centers)
        return self._error(result, "Failed to list work centers")

    async def _get_bottleneck(self, params: dict) -> AgentResult:
        query = {}
        if params.get("start_date"):
            query["startDate"] = params["start_date"]
        if params.get("end_date"):
            query["endDate"] = params["end_date"]

        result = await self._make_request("GET", "MES/bottleneck-analysis", params=query)
        if result["success"]:
            return self._result(True, "Bottleneck analysis completed", result["data"])
        return self._error(result, "Failed to get bottleneck analysis")

    async def _list_products(self, params: dict) -> AgentResult:
        result = await self._make_request("GET", "MES/products")
        if result["success"]:
            products = result["data"]
            return self._result(True, f"Found {len(products)} products", products)
        return self._error(result, "Failed to list products")

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

