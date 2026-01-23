"""
Axis SCADA Tool - AI-powered SCADA Page Manager

Capabilities:
- List/Get/Create/Update/Delete SCADA pages
- Manage tag bindings and values
- Get custom widget definitions
"""

import logging
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

logger = logging.getLogger(__name__)


class AxisScadaTool(BaseTool):
    """Axis SCADA Page Management Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://metis-api-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)
        self.default_company_id = config.config.get("company_id", 1)
        self._token = None
        self._token_expiry = None

        logger.info(f"AxisScadaTool initialized with API: {self.api_base_url}")

    async def _get_auth_token(self) -> Optional[str]:
        """Get JWT token for Axis API authentication"""
        try:
            if self._token and self._token_expiry and datetime.now() < self._token_expiry:
                return self._token

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/Auth/login",
                    json={
                        "Username": "admin",
                        "Password": "admin123"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    self._token = data.get("token")
                    from datetime import timedelta
                    self._token_expiry = datetime.now() + timedelta(hours=23)
                    return self._token

            logger.warning("Failed to get auth token")
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

            if capability_name == "list_pages":
                return await self._list_pages(parameters)
            elif capability_name == "get_page":
                return await self._get_page(parameters)
            elif capability_name == "create_page":
                return await self._create_page(parameters)
            elif capability_name == "update_page":
                return await self._update_page(parameters)
            elif capability_name == "delete_page":
                return await self._delete_page(parameters)
            elif capability_name == "get_tags":
                return await self._get_tags(parameters)
            elif capability_name == "read_tag":
                return await self._read_tag(parameters)
            elif capability_name == "write_tag":
                return await self._write_tag(parameters)
            elif capability_name == "get_custom_widgets":
                return await self._get_custom_widgets(parameters)
            else:
                return AgentResult(success=False, message=f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"Error executing {capability_name}: {e}")
            return AgentResult(success=False, message=str(e))

    async def _list_pages(self, params: dict) -> AgentResult:
        """List all SCADA pages"""
        company_id = params.get("company_id", self.default_company_id)
        result = await self._make_request("GET", "SCADA/pages", params={"companyId": company_id})

        if result["success"]:
            pages = result["data"]
            summary = f"Found {len(pages)} SCADA pages"
            return AgentResult(success=True, message=summary, data=pages)
        return AgentResult(success=False, message=result.get("error", "Failed to list pages"))

    async def _get_page(self, params: dict) -> AgentResult:
        """Get a specific SCADA page"""
        page_id = params.get("page_id")
        if not page_id:
            return AgentResult(success=False, message="page_id is required")

        result = await self._make_request("GET", f"SCADA/pages/{page_id}")

        if result["success"]:
            page = result["data"]
            return AgentResult(success=True, message=f"Retrieved page: {page.get('pageName', page_id)}", data=page)
        return AgentResult(success=False, message=result.get("error", "Failed to get page"))

    async def _create_page(self, params: dict) -> AgentResult:
        """Create a new SCADA page"""
        page_name = params.get("page_name")
        if not page_name:
            return AgentResult(success=False, message="page_name is required")

        data = {
            "pageName": page_name,
            "description": params.get("description", ""),
            "companyId": params.get("company_id", self.default_company_id),
            "pageConfig": json.dumps(params.get("page_config", {}))
        }

        result = await self._make_request("POST", "SCADA/pages", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Created page: {page_name}", data=result["data"])
        return AgentResult(success=False, message=result.get("error", "Failed to create page"))

    async def _update_page(self, params: dict) -> AgentResult:
        """Update an existing SCADA page"""
        page_id = params.get("page_id")
        if not page_id:
            return AgentResult(success=False, message="page_id is required")

        data = {"pageId": page_id}
        if "page_name" in params:
            data["pageName"] = params["page_name"]
        if "description" in params:
            data["description"] = params["description"]
        if "page_config" in params:
            data["pageConfig"] = json.dumps(params["page_config"])

        result = await self._make_request("PUT", f"SCADA/pages/{page_id}", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Updated page {page_id}", data=result["data"])
        return AgentResult(success=False, message=result.get("error", "Failed to update page"))

    async def _delete_page(self, params: dict) -> AgentResult:
        """Delete a SCADA page"""
        page_id = params.get("page_id")
        if not page_id:
            return AgentResult(success=False, message="page_id is required")

        result = await self._make_request("DELETE", f"SCADA/pages/{page_id}")

        if result["success"]:
            return AgentResult(success=True, message=f"Deleted page {page_id}")
        return AgentResult(success=False, message=result.get("error", "Failed to delete page"))

    async def _get_tags(self, params: dict) -> AgentResult:
        """Get all tags with current values"""
        company_id = params.get("company_id", self.default_company_id)
        channel_id = params.get("channel_id")

        if channel_id:
            endpoint = f"DataSource/tags/channel/{channel_id}"
            query_params = {"companyId": company_id}
        else:
            endpoint = "DataSource/tags"
            query_params = {"companyId": company_id}

        result = await self._make_request("GET", endpoint, params=query_params)

        if result["success"]:
            tags = result["data"]
            count = len(tags) if isinstance(tags, list) else "N/A"
            return AgentResult(success=True, message=f"Found {count} tags", data=tags)
        return AgentResult(success=False, message=result.get("error", "Failed to get tags"))

    async def _read_tag(self, params: dict) -> AgentResult:
        """Read current value of a tag"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        company_id = params.get("company_id", self.default_company_id)
        result = await self._make_request("GET", "DataSource/tags", params={"companyId": company_id})

        if result["success"]:
            tags = result["data"]
            if isinstance(tags, list):
                tag = next((t for t in tags if t.get("tagId") == tag_id), None)
                if tag:
                    return AgentResult(success=True, message=f"Tag {tag_id} ({tag.get('tagName', 'N/A')}): {tag.get('currentValue', 'N/A')}", data=tag)
                return AgentResult(success=False, message=f"Tag {tag_id} not found")
            return AgentResult(success=True, message="Tags retrieved", data=tags)
        return AgentResult(success=False, message=result.get("error", "Failed to read tag"))

    async def _write_tag(self, params: dict) -> AgentResult:
        """Write value to a tag"""
        tag_id = params.get("tag_id")
        value = params.get("value")

        if not tag_id or value is None:
            return AgentResult(success=False, message="tag_id and value are required")

        company_id = params.get("company_id", self.default_company_id)
        data = {
            "tagId": tag_id,
            "companyId": company_id,
            "value": str(value),
            "timestamp": None
        }
        result = await self._make_request("POST", "DataSource/tags/write", data=data)

        if result["success"]:
            return AgentResult(success=True, message=f"Written {value} to tag {tag_id}")
        return AgentResult(success=False, message=result.get("error", "Failed to write tag"))

    async def _get_custom_widgets(self, params: dict) -> AgentResult:
        """Get custom widget definitions"""
        company_id = params.get("company_id", self.default_company_id)

        result = await self._make_request("GET", "SCADA/widgets", params={"companyId": company_id})

        if result["success"]:
            widgets = result["data"]
            summary = f"Found {len(widgets)} custom widgets"
            return AgentResult(success=True, message=summary, data=widgets)
        return AgentResult(success=False, message=result.get("error", "Failed to get custom widgets"))

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

