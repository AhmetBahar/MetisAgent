"""
Axis Base Tool - Common functionality for all Axis plugins

Provides:
- Authentication
- HTTP request handling
- Error handling
- Health check
"""

import logging
import httpx
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from abc import abstractmethod

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

logger = logging.getLogger(__name__)


class AxisBaseTool(BaseTool):
    """Base class for all Axis tools"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://metis-api-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)
        self.default_company_id = config.config.get("company_id", 1)
        self._token = None
        self._token_expiry = None

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

            try:
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

            except httpx.TimeoutException:
                return {"success": False, "error": "Request timeout"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _result(self, success: bool, message: str, data: Any = None) -> AgentResult:
        """Create AgentResult helper"""
        return AgentResult(success=success, message=message, data=data)

    def _error(self, result: dict, default_msg: str) -> AgentResult:
        """Create error AgentResult from request result"""
        return AgentResult(success=False, message=result.get("error", default_msg))

    @abstractmethod
    async def execute(self, capability_name: str, parameters: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a capability - must be implemented by subclass"""
        pass

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
