"""
Axis Alarm Tool - AI-powered Alarm Management

Capabilities:
- List active alarms
- Confirm/acknowledge alarms
- Get alarm history and statistics
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


class AxisAlarmTool(BaseTool):
    """Axis Alarm Management Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://metis-api-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)
        self.default_company_id = config.config.get("company_id", 1)
        self._token = None
        self._token_expiry = None

        logger.info(f"AxisAlarmTool initialized with API: {self.api_base_url}")

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

            if capability_name == "list_active_alarms":
                return await self._list_active_alarms(parameters)
            elif capability_name == "get_alarm":
                return await self._get_alarm(parameters)
            elif capability_name == "confirm_alarm":
                return await self._confirm_alarm(parameters)
            elif capability_name == "get_alarm_history":
                return await self._get_alarm_history(parameters)
            elif capability_name == "get_alarm_stats":
                return await self._get_alarm_stats(parameters)
            else:
                return AgentResult(success=False, message=f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"Error executing {capability_name}: {e}")
            return AgentResult(success=False, message=str(e))

    async def _list_active_alarms(self, params: dict) -> AgentResult:
        """List all active alarms"""
        company_id = params.get("company_id", self.default_company_id)
        query_params = {"companyId": company_id}

        result = await self._make_request("GET", "Alarm", params=query_params)

        if result["success"]:
            alarms = result["data"]
            if isinstance(alarms, list):
                severity_filter = params.get("severity")
                if severity_filter:
                    alarms = [a for a in alarms if a.get("statusCode", "").lower() == severity_filter.lower()]
                total = len(alarms)
                critical = sum(1 for a in alarms if a.get("statusCode", "").lower() in ["critical", "high"])
                unconfirmed = sum(1 for a in alarms if a.get("confirm_") != 1)
                summary = f"Found {total} alarms ({critical} high priority, {unconfirmed} unconfirmed)"
                return AgentResult(success=True, message=summary, data=alarms)
            return AgentResult(success=True, message="Alarms retrieved", data=alarms)
        return AgentResult(success=False, message=result.get("error", "Failed to list alarms"))

    async def _get_alarm(self, params: dict) -> AgentResult:
        """Get a specific alarm"""
        alarm_id = params.get("alarm_id")
        if not alarm_id:
            return AgentResult(success=False, message="alarm_id is required")

        result = await self._make_request("GET", f"Alarm/{alarm_id}")

        if result["success"]:
            alarm = result["data"]
            return AgentResult(success=True, message=f"Alarm #{alarm_id}: {alarm.get('message', 'N/A')}", data=alarm)
        return AgentResult(success=False, message=result.get("error", "Failed to get alarm"))

    async def _confirm_alarm(self, params: dict) -> AgentResult:
        """Confirm/acknowledge an alarm"""
        alarm_id = params.get("alarm_id")
        if not alarm_id:
            return AgentResult(success=False, message="alarm_id is required")

        company_id = params.get("company_id", self.default_company_id)
        data = {
            "ID": alarm_id,
            "Confirm_": 1,
            "CompanyID": company_id
        }

        result = await self._make_request("POST", "Alarm/updateConfirmStatus", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Alarm #{alarm_id} confirmed successfully")
        return AgentResult(success=False, message=result.get("error", "Failed to confirm alarm"))

    async def _get_alarm_history(self, params: dict) -> AgentResult:
        """Get alarm history"""
        company_id = params.get("company_id", self.default_company_id)
        data = {
            "companyId": company_id,
            "status": "all",
            "priority": "all",
            "alarmStatus": "all",
            "search": "",
            "page": 1,
            "pageSize": 50,
            "sortField": "date",
            "sortDirection": "desc"
        }

        if params.get("start_date"):
            data["startDate"] = params["start_date"]
        if params.get("end_date"):
            data["endDate"] = params["end_date"]
        if params.get("search"):
            data["search"] = params["search"]

        result = await self._make_request("POST", "Alarm/GetAlarmList", data=data)

        if result["success"]:
            response_data = result["data"]
            alarms = response_data.get("alarms", []) if isinstance(response_data, dict) else response_data
            total = response_data.get("totalCount", len(alarms)) if isinstance(response_data, dict) else len(alarms)
            return AgentResult(success=True, message=f"Found {total} alarm records", data=alarms)
        return AgentResult(success=False, message=result.get("error", "Failed to get alarm history"))

    async def _get_alarm_stats(self, params: dict) -> AgentResult:
        """Get alarm statistics"""
        company_id = params.get("company_id", self.default_company_id)
        query_params = {
            "companyId": company_id,
            "status": "all",
            "priority": "all",
            "alarmStatus": "all",
            "search": ""
        }

        result = await self._make_request("GET", "Alarm/GetAlarmStats", params=query_params)

        if result["success"]:
            stats = result["data"]
            if isinstance(stats, dict):
                summary = f"Alarm Stats - Total: {stats.get('totalCount', 'N/A')}, Confirmed: {stats.get('confirmedCount', 'N/A')}, Unconfirmed: {stats.get('unconfirmedCount', 'N/A')}"
                return AgentResult(success=True, message=summary, data=stats)
            return AgentResult(success=True, message="Statistics retrieved", data=stats)
        return AgentResult(success=False, message=result.get("error", "Failed to get alarm stats"))

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

