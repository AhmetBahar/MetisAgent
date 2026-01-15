"""
RMMS DataSource Tool - PLC, Channel, Tag Management

Capabilities:
- List/Create/Update/Delete PLCs
- List/Create/Update/Delete Channels
- List/Create/Update/Delete Tags
- Auto-generate channels
- Get channel statistics
"""

import logging
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

# Import MetisAgent base contracts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import (
    BaseTool, ToolMetadata, ToolConfiguration,
    AgentResult, ExecutionContext, HealthStatus
)

logger = logging.getLogger(__name__)


class RMMSDataSourceTool(BaseTool):
    """RMMS DataSource Management Tool for MetisAgent - Manages PLCs, Channels, and Tags"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://app-rmmsapi.azurewebsites.net/api")
        # MetisEngine API for tag value reads
        self.metis_api_url = config.config.get("metis_api_url", "https://rmms-metis-engine.azurewebsites.net/api")
        # RmmsTagApi for tag value writes
        self.tag_api_url = config.config.get("tag_api_url", "https://app-rmmstagapi.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)

        # Authentication settings
        self.auth_user_id = config.config.get("auth_user_id", "metis-agent")
        self.auth_company_id = config.config.get("auth_company_id", "3")
        self._token = None
        self._token_expiry = None

        logger.info(f"RMMSDataSourceTool initialized with APIs: {self.api_base_url}, MetisEngine: {self.metis_api_url}, TagApi: {self.tag_api_url}")

    async def _get_auth_token(self) -> Optional[str]:
        """Get JWT token for RMMS API authentication"""
        try:
            # Check if we have a valid cached token
            if self._token and self._token_expiry:
                if datetime.now() < self._token_expiry:
                    return self._token

            # Request new token
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/Person/Generate_token",
                    json={
                        "userId": self.auth_user_id,
                        "companyId": self.auth_company_id
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self._token = data.get("token")
                        from datetime import timedelta
                        self._token_expiry = datetime.now() + timedelta(hours=23)
                        logger.info("🔑 RMMS DataSource API token acquired successfully")
                        return self._token
                    else:
                        logger.warning(f"Token request failed: {data.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"Token request returned status {response.status_code}")

            return None
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            return None

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication token"""
        headers = {"Content-Type": "application/json"}
        token = await self._get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        logger.info(f"RMMS DataSource Tool executing capability: {capability}")

        try:
            # PLC operations
            if capability == "list_plcs":
                result = await self._list_plcs(input_data)
            # Channel operations
            elif capability == "list_channels":
                result = await self._list_channels(input_data)
            elif capability == "create_channel":
                result = await self._create_channel(input_data)
            elif capability == "update_channel":
                result = await self._update_channel(input_data)
            elif capability == "delete_channel":
                result = await self._delete_channel(input_data)
            elif capability == "auto_generate_channels":
                result = await self._auto_generate_channels(input_data)
            elif capability == "get_channel_stats":
                result = await self._get_channel_stats(input_data)
            elif capability == "clear_channels":
                result = await self._clear_channels(input_data)
            # Tag operations
            elif capability == "list_tags":
                result = await self._list_tags(input_data)
            elif capability == "create_tag":
                result = await self._create_tag(input_data)
            elif capability == "update_tag":
                result = await self._update_tag(input_data)
            elif capability == "delete_tag":
                result = await self._delete_tag(input_data)
            # Variable operations
            elif capability == "list_vars":
                result = await self._list_vars(input_data)
            elif capability == "get_variables":
                result = await self._get_variables(input_data)
            # Tag Value operations (read/write)
            elif capability == "read_tag_value":
                result = await self._read_tag_value(input_data)
            elif capability == "read_tag_values":
                result = await self._read_tag_values(input_data)
            elif capability == "write_tag_value":
                result = await self._write_tag_value(input_data)
            elif capability == "write_tag_values":
                result = await self._write_tag_values(input_data)
            # Variable Value operations (read)
            elif capability == "read_var_value":
                result = await self._read_var_value(input_data)
            elif capability == "read_var_values":
                result = await self._read_var_values(input_data)
            # Legacy compatibility
            elif capability == "list_datasources":
                result = await self._list_plcs(input_data)
            elif capability == "get_datasource_types":
                result = await self._get_datasource_types(input_data)
            else:
                result = {"success": False, "error": f"Unknown capability: {capability}"}

            return AgentResult(
                success=result.get("success", False),
                data=result.get("data"),
                message=result.get("message") or result.get("error"),
                metadata={"capability": capability}
            )

        except Exception as e:
            logger.error(f"RMMS DataSource Tool error: {str(e)}")
            return AgentResult(
                success=False,
                message=str(e),
                metadata={"capability": capability, "error": str(e)}
            )

    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            headers = await self._get_auth_headers()
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"{self.api_base_url}/DataSource/plc/list?companyId={self.auth_company_id}"
                response = await client.get(url, headers=headers)
                healthy = response.status_code == 200
                message = "RMMS DataSource API accessible" if healthy else f"API returned {response.status_code}"
        except Exception as e:
            healthy = False
            message = f"API connection failed: {str(e)}"

        return HealthStatus(
            healthy=healthy,
            component="rmms_datasource_tool",
            message=message
        )

    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        if capability in ["list_plcs", "list_channels", "list_tags", "list_vars", "get_channel_stats"]:
            if not input_data.get("company_id"):
                errors.append("company_id is required")
        elif capability in ["create_channel", "create_tag"]:
            if not input_data.get("company_id"):
                errors.append("company_id is required")
        elif capability in ["update_channel", "delete_channel"]:
            if not input_data.get("channel_id"):
                errors.append("channel_id is required")
        elif capability in ["update_tag", "delete_tag"]:
            if not input_data.get("tag_id"):
                errors.append("tag_id is required")
        elif capability == "read_tag_value":
            if not input_data.get("tag_id"):
                errors.append("tag_id is required")
        elif capability == "read_tag_values":
            if not input_data.get("tag_ids"):
                errors.append("tag_ids is required (list of tag IDs)")
        elif capability == "write_tag_value":
            if not input_data.get("tag_id"):
                errors.append("tag_id is required")
            if input_data.get("value") is None:
                errors.append("value is required")
        elif capability == "write_tag_values":
            if not input_data.get("tags"):
                errors.append("tags is required (list of {tag_id, value} objects)")
        elif capability == "read_var_value":
            if not input_data.get("var_id"):
                errors.append("var_id is required")
        elif capability == "read_var_values":
            if not input_data.get("var_ids"):
                errors.append("var_ids is required (list of var IDs)")
        return errors

    def get_capabilities(self) -> List[str]:
        """Return list of capability names"""
        return [cap.name for cap in self.metadata.capabilities]

    # ========== PLC Operations ==========
    async def _list_plcs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all PLCs for a company"""
        company_id = params.get("company_id", self.auth_company_id)
        headers = await self._get_auth_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/DataSource/plc/list?companyId={company_id}"
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                plcs = response.json()
                return {
                    "success": True,
                    "data": {"plcs": plcs, "count": len(plcs)},
                    "message": f"Found {len(plcs)} PLCs"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    # ========== Channel Operations ==========
    async def _list_channels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all channels for a company"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/DataSource/channels/list?companyId={company_id}"
            response = await client.get(url)

            if response.status_code == 200:
                channels = response.json()
                return {
                    "success": True,
                    "data": {"channels": channels, "count": len(channels)},
                    "message": f"Found {len(channels)} channels"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _create_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new channel"""
        channel_data = {
            "channelName": params.get("channel_name", ""),
            "plcId": params.get("plc_id", 0),
            "start": params.get("start", 0),
            "length": params.get("length", 50),
            "type": params.get("type", 0),
            "dbNo": params.get("db_no", 0),
            "interval": params.get("interval", 5000),
            "opcType": params.get("opc_type", 0),
            "companyId": params.get("company_id", 3)
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/DataSource/channels",
                json=channel_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "message": f"Created channel '{channel_data['channelName']}'"
                }
            else:
                return {"success": False, "error": f"Failed to create channel: {response.text}"}

    async def _update_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing channel"""
        channel_id = params.get("channel_id")
        if not channel_id:
            return {"success": False, "error": "channel_id is required"}

        channel_data = {
            "channelName": params.get("channel_name", ""),
            "plcId": params.get("plc_id", 0),
            "start": params.get("start", 0),
            "length": params.get("length", 50),
            "type": params.get("type", 0),
            "dbNo": params.get("db_no", 0),
            "interval": params.get("interval", 5000),
            "opcType": params.get("opc_type", 0),
            "companyId": params.get("company_id", 3)
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.api_base_url}/DataSource/channels/{channel_id}",
                json=channel_data
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": channel_data,
                    "message": f"Updated channel {channel_id}"
                }
            else:
                return {"success": False, "error": f"Failed to update channel: {response.text}"}

    async def _delete_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a channel"""
        channel_id = params.get("channel_id")
        company_id = params.get("company_id", 3)

        if not channel_id:
            return {"success": False, "error": "channel_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.api_base_url}/DataSource/channels/{channel_id}?companyId={company_id}"
            )

            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted channel {channel_id}"}
            else:
                return {"success": False, "error": f"Failed to delete channel: {response.text}"}

    async def _auto_generate_channels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate channels based on PLC grouping"""
        request_data = {
            "companyId": params.get("company_id", 3),
            "tagsPerChannel": params.get("tags_per_channel", 50)
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.api_base_url}/DataSource/channels/auto-generate",
                json=request_data
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "message": f"Auto-generated {result.get('channelsCreated', 0)} channels, updated {result.get('tagsUpdated', 0)} tags"
                }
            else:
                return {"success": False, "error": f"Failed to auto-generate channels: {response.text}"}

    async def _get_channel_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get channel statistics"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/DataSource/channels/stats?companyId={company_id}"
            )

            if response.status_code == 200:
                stats = response.json()
                return {
                    "success": True,
                    "data": stats,
                    "message": f"Total tags: {stats.get('totalTags', 0)}, Channels: {stats.get('channelCount', 0)}"
                }
            else:
                return {"success": False, "error": f"Failed to get stats: {response.text}"}

    async def _clear_channels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clear all auto-generated channels"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.api_base_url}/DataSource/channels/clear-auto?companyId={company_id}"
            )

            if response.status_code == 200:
                return {"success": True, "message": "All channels cleared"}
            else:
                return {"success": False, "error": f"Failed to clear channels: {response.text}"}

    # ========== Tag Operations ==========
    async def _list_tags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all tags for a company"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/DataSource/tags/list?companyId={company_id}"
            response = await client.get(url)

            if response.status_code == 200:
                tags = response.json()
                return {
                    "success": True,
                    "data": {"tags": tags, "count": len(tags)},
                    "message": f"Found {len(tags)} tags"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _create_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tag"""
        tag_data = {
            "tagName": params.get("tag_name", ""),
            "majorAddress": params.get("major_address", 0),
            "minorAddress": params.get("minor_address", 0),
            "dbNo": params.get("db_no", 0),
            "type": params.get("type", 0),
            "dataType": params.get("data_type", 0),
            "plcId": params.get("plc_id"),
            "channelId": params.get("channel_id"),
            "moduleId": params.get("module_id", 0),
            "formule": params.get("formula", ""),
            "unit": params.get("unit", ""),
            "alarm": params.get("alarm", ""),
            "alarmCondition": params.get("alarm_condition"),
            "companyId": params.get("company_id", 3)
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/DataSource/tags",
                json=tag_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "message": f"Created tag '{tag_data['tagName']}'"
                }
            else:
                return {"success": False, "error": f"Failed to create tag: {response.text}"}

    async def _update_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing tag"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return {"success": False, "error": "tag_id is required"}

        tag_data = {
            "tagName": params.get("tag_name", ""),
            "majorAddress": params.get("major_address", 0),
            "minorAddress": params.get("minor_address", 0),
            "dbNo": params.get("db_no", 0),
            "type": params.get("type", 0),
            "dataType": params.get("data_type", 0),
            "plcId": params.get("plc_id"),
            "channelId": params.get("channel_id"),
            "moduleId": params.get("module_id", 0),
            "formule": params.get("formula", ""),
            "unit": params.get("unit", ""),
            "alarm": params.get("alarm", ""),
            "alarmCondition": params.get("alarm_condition"),
            "companyId": params.get("company_id", 3)
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.api_base_url}/DataSource/tags/{tag_id}",
                json=tag_data
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": tag_data,
                    "message": f"Updated tag {tag_id}"
                }
            else:
                return {"success": False, "error": f"Failed to update tag: {response.text}"}

    async def _delete_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a tag"""
        tag_id = params.get("tag_id")
        company_id = params.get("company_id", 3)

        if not tag_id:
            return {"success": False, "error": "tag_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.api_base_url}/DataSource/tags/{tag_id}?companyId={company_id}"
            )

            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted tag {tag_id}"}
            else:
                return {"success": False, "error": f"Failed to delete tag: {response.text}"}

    # ========== Variable Operations ==========
    async def _list_vars(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all variables for a company"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/DataSource/vars/list?companyId={company_id}"
            response = await client.get(url)

            if response.status_code == 200:
                vars_list = response.json()
                return {
                    "success": True,
                    "data": {"variables": vars_list, "count": len(vars_list)},
                    "message": f"Found {len(vars_list)} variables"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_variables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get combined tags and variables"""
        company_id = params.get("company_id", 3)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/DataSource/variables?companyId={company_id}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "message": f"Found {len(data.get('Tags', []))} tags and {len(data.get('Vars', []))} variables"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_datasource_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get available data source types (for compatibility)"""
        return {
            "success": True,
            "data": {
                "datasource_types": {
                    "plc": "PLC connections (Siemens S7, etc.)",
                    "channel": "Data channels grouping tags",
                    "tag": "Individual data points",
                    "variable": "Calculated/formula-based variables"
                }
            },
            "message": "Available types: plc, channel, tag, variable"
        }

    # ========== Tag Value Operations (Read/Write) ==========
    async def _read_tag_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a single tag's current value from MetisEngine"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return {"success": False, "error": "tag_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.metis_api_url}/Tags/value/{tag_id}"
            response = await client.get(url)

            if response.status_code == 200:
                value_data = response.json()
                return {
                    "success": True,
                    "data": value_data,
                    "message": f"Tag {tag_id} value: {value_data.get('value', 'N/A')}"
                }
            elif response.status_code == 404:
                return {"success": False, "error": f"No value found for tag {tag_id}"}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}

    async def _read_tag_values(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read multiple tags' current values from MetisEngine"""
        tag_ids = params.get("tag_ids", [])
        if not tag_ids:
            return {"success": False, "error": "tag_ids is required (list of tag IDs)"}

        # Ensure tag_ids is a list of integers
        if isinstance(tag_ids, str):
            tag_ids = [int(x.strip()) for x in tag_ids.split(",")]
        elif isinstance(tag_ids, list):
            tag_ids = [int(x) for x in tag_ids]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.metis_api_url}/Tags/values"
            response = await client.post(url, json=tag_ids)

            if response.status_code == 200:
                result = response.json()
                values = result.get("values", [])
                return {
                    "success": True,
                    "data": {"values": values, "count": len(values)},
                    "message": f"Retrieved {len(values)} tag values"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}

    async def _write_tag_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write a single tag value to RmmsTagApi"""
        logger.info(f"🔧 _write_tag_value called with params: {params}")

        tag_id = params.get("tag_id")
        value = params.get("value")
        tag_name = params.get("tag_name", "")

        logger.info(f"🔧 Extracted: tag_id={tag_id}, value={value}, tag_name={tag_name}")

        if not tag_id:
            return {"success": False, "error": "tag_id is required"}
        if value is None:
            return {"success": False, "error": "value is required"}

        tag_data = {
            "TagId": str(tag_id),
            "TagValue": str(value),
            "TagName": tag_name
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.tag_api_url}/Tag/SetTagValue"
            response = await client.post(url, json=tag_data)

            if response.status_code == 200:
                result = response.json() if response.text else True
                if result:
                    return {
                        "success": True,
                        "data": {"tag_id": tag_id, "value": value},
                        "message": f"Successfully wrote value {value} to tag {tag_id}"
                    }
                else:
                    return {"success": False, "error": "Failed to write tag value"}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}

    async def _write_tag_values(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write multiple tag values to RmmsTagApi"""
        tags = params.get("tags", [])
        if not tags:
            return {"success": False, "error": "tags is required (list of {tag_id, value} objects)"}

        # Format tags for API: [{TagId, TagValue, TagName}, ...]
        tag_list = []
        for tag in tags:
            tag_list.append({
                "TagId": str(tag.get("tag_id", tag.get("TagId", ""))),
                "TagValue": str(tag.get("value", tag.get("TagValue", ""))),
                "TagName": tag.get("tag_name", tag.get("TagName", ""))
            })

        async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for batch
            url = f"{self.tag_api_url}/Tag/SetTagValues"
            response = await client.post(url, json=tag_list)

            if response.status_code == 200:
                result = response.json() if response.text else True
                if result:
                    return {
                        "success": True,
                        "data": {"tags_written": len(tag_list)},
                        "message": f"Successfully wrote {len(tag_list)} tag values"
                    }
                else:
                    return {"success": False, "error": "Failed to write tag values"}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}

    # ========== Variable Value Operations (Read) ==========
    async def _read_var_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a single variable's current value from MetisEngine"""
        var_id = params.get("var_id")
        company_id = params.get("company_id", 3)

        if not var_id:
            return {"success": False, "error": "var_id is required"}

        logger.info(f"🔧 _read_var_value called: var_id={var_id}, company_id={company_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.metis_api_url}/Task/variables/{company_id}/{var_id}"
            response = await client.get(url)

            if response.status_code == 200:
                var_data = response.json()
                return {
                    "success": True,
                    "data": var_data,
                    "message": f"Variable '{var_data.get('name', var_id)}' value: {var_data.get('currentValue', 'N/A')}"
                }
            elif response.status_code == 404:
                return {"success": False, "error": f"Variable {var_id} not found"}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}

    async def _read_var_values(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read multiple variables' current values from MetisEngine"""
        var_ids = params.get("var_ids", [])
        company_id = params.get("company_id", 3)

        if not var_ids:
            return {"success": False, "error": "var_ids is required (list of var IDs)"}

        # Ensure var_ids is a list
        if isinstance(var_ids, str):
            var_ids = [int(x.strip()) for x in var_ids.split(",")]
        elif isinstance(var_ids, list):
            var_ids = [int(x) for x in var_ids]

        logger.info(f"🔧 _read_var_values called: var_ids={var_ids}, company_id={company_id}")

        results = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for var_id in var_ids:
                url = f"{self.metis_api_url}/Task/variables/{company_id}/{var_id}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        results.append(response.json())
                except Exception as e:
                    logger.warning(f"Failed to read var {var_id}: {e}")

        return {
            "success": True,
            "data": {"variables": results, "count": len(results)},
            "message": f"Retrieved {len(results)} variable values"
        }
