"""
RMMS SCADA Tool - AI-powered SCADA Page Designer

Capabilities:
- List/Get/Create/Update SCADA pages
- Add/Remove/Configure widgets
- Manage tag bindings and properties
- Page layout management
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


class RMMSScadaTool(BaseTool):
    """RMMS SCADA Page Design Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://app-rmmsapi.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 30)

        # Authentication settings
        self.auth_user_id = config.config.get("auth_user_id", "metis-agent")
        self.default_company_id = config.config.get("auth_company_id", "3")
        # Token cache per company: {company_id: {"token": str, "expiry": datetime}}
        self._tokens = {}

        # Standard Widget type definitions for AI guidance
        self.widget_types = {
            # === Display Widgets ===
            "text-label": {
                "description": "Displays static text or dynamic tag values",
                "properties": ["text", "fontSize", "fontWeight", "backgroundColor", "foreColor", "borderColor", "borderWidth", "borderRadius", "tagBinding", "colorMap", "valueTextMap"]
            },
            "text-box": {
                "description": "Editable text input field",
                "properties": ["text", "placeholder", "fontSize", "backgroundColor", "foreColor", "borderColor", "borderWidth", "tagBinding"]
            },
            "led-indicator": {
                "description": "LED status indicator light",
                "properties": ["color", "offColor", "size", "tagBinding", "colorMap"]
            },
            "progress-bar": {
                "description": "Progress bar showing percentage or value",
                "properties": ["minValue", "maxValue", "value", "backgroundColor", "foreColor", "barColor", "tagBinding", "showLabel"]
            },
            "gauge": {
                "description": "Circular gauge/meter display",
                "properties": ["minValue", "maxValue", "unit", "ranges", "tagBinding", "showValue", "needleColor"]
            },

            # === Input/Control Widgets ===
            "button": {
                "description": "Clickable button for actions or navigation",
                "properties": ["text", "actionType", "navigateTo", "tagBinding", "setValue", "backgroundColor", "foreColor", "fontSize", "fontWeight", "borderRadius", "variant"]
            },
            "button-menu": {
                "description": "Button with dropdown options (ON/OFF, custom values)",
                "properties": ["text", "options", "tagBinding", "isStatusLabel", "colorMap", "valueTextMap"]
            },
            "set-value": {
                "description": "Input widget for setting tag values",
                "properties": ["text", "fontSize", "backgroundColor", "foreColor", "borderColor", "borderWidth", "borderRadius", "tagBinding", "unit", "placeholder", "minValue", "maxValue"]
            },
            "toggle-switch": {
                "description": "ON/OFF toggle switch control",
                "properties": ["tagBinding", "onValue", "offValue", "onColor", "offColor", "label", "labelPosition"]
            },
            "combobox": {
                "description": "Dropdown selection list",
                "properties": ["options", "tagBinding", "placeholder", "backgroundColor", "foreColor", "borderColor"]
            },

            # === Chart/Visualization Widgets ===
            "trend-chart": {
                "description": "Time-series trend chart for historical data",
                "properties": ["tagBindings", "timeRange", "refreshInterval", "chartType", "showLegend", "showGrid", "colors"]
            },

            # === Shape/Container Widgets ===
            "box": {
                "description": "Container box for grouping widgets",
                "properties": ["backgroundColor", "borderColor", "borderWidth", "borderRadius", "isContainer"]
            },
            "line": {
                "description": "Line shape for connecting or separating elements",
                "properties": ["x1", "y1", "x2", "y2", "strokeColor", "strokeWidth", "strokeStyle"]
            },
            "circle": {
                "description": "Circle shape",
                "properties": ["radius", "backgroundColor", "borderColor", "borderWidth", "tagBinding"]
            },

            # === Special Widgets ===
            "image": {
                "description": "Image display widget",
                "properties": ["src", "alt", "objectFit"]
            },
            "navigation-button": {
                "description": "Alias for button with navigation action",
                "properties": ["text", "targetPageId", "backgroundColor", "foreColor"]
            }
        }

        # Custom widgets will be loaded dynamically from API
        self.custom_widgets = {}

        logger.info(f"RMMSScadaTool initialized with API: {self.api_base_url}")

    async def _get_auth_token(self, company_id: Optional[str] = None) -> Optional[str]:
        """Get JWT token for RMMS API authentication - cached per company"""
        try:
            # Use provided company_id or default
            cid = str(company_id) if company_id else self.default_company_id

            # Check if we have a valid cached token for this company
            if cid in self._tokens:
                cached = self._tokens[cid]
                if cached.get("expiry") and datetime.now() < cached["expiry"]:
                    return cached["token"]

            # Request new token for this company
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/Person/Generate_token",
                    json={
                        "userId": self.auth_user_id,
                        "companyId": cid
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        from datetime import timedelta
                        self._tokens[cid] = {
                            "token": data.get("token"),
                            "expiry": datetime.now() + timedelta(hours=23)
                        }
                        logger.info(f"🔑 RMMS API token acquired for company {cid}")
                        return self._tokens[cid]["token"]

            logger.warning(f"⚠️ Failed to acquire RMMS API token for company {cid}")
            return None

        except Exception as e:
            logger.error(f"❌ Token acquisition error: {str(e)}")
            return None

    async def _get_auth_headers(self, company_id: Optional[str] = None) -> Dict[str, str]:
        """Get HTTP headers with authentication token for specific company"""
        headers = {"Content-Type": "application/json"}
        token = await self._get_auth_token(company_id)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        logger.info(f"RMMS SCADA Tool executing capability: {capability}")

        try:
            if capability == "list_pages":
                result = await self._list_pages(input_data)
            elif capability == "get_page":
                result = await self._get_page(input_data)
            elif capability == "create_page":
                result = await self._create_page(input_data)
            elif capability == "update_page":
                result = await self._update_page(input_data)
            elif capability == "delete_page":
                result = await self._delete_page(input_data)
            elif capability == "add_widget":
                result = await self._add_widget(input_data)
            elif capability == "update_widget":
                result = await self._update_widget(input_data)
            elif capability == "remove_widget":
                result = await self._remove_widget(input_data)
            elif capability == "get_widget_types":
                result = await self._get_widget_types(input_data)
            elif capability == "get_tags":
                result = await self._get_tags(input_data)
            elif capability == "set_page_background":
                result = await self._set_page_background(input_data)
            elif capability == "get_custom_widgets":
                result = await self._get_custom_widgets(input_data)
            elif capability == "add_custom_widget":
                result = await self._add_custom_widget(input_data)
            elif capability == "analyze_page":
                result = await self._analyze_page(input_data)
            elif capability == "find_widget":
                result = await self._find_widget(input_data)
            elif capability == "resize_widgets_by_type":
                result = await self._resize_widgets_by_type(input_data)
            else:
                result = {"success": False, "error": f"Unknown capability: {capability}"}

            return AgentResult(
                success=result.get("success", False),
                data=result.get("data"),
                error=result.get("error") if not result.get("success") else None,
                metadata={"capability": capability, "message": result.get("message")}
            )

        except Exception as e:
            logger.error(f"RMMS SCADA Tool error: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"capability": capability}
            )

    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            headers = await self._get_auth_headers(self.default_company_id)
            async with httpx.AsyncClient(timeout=10) as client:
                # Include companyId in health check - use default_company_id from config
                url = f"{self.api_base_url}/scada/pages?companyId={self.default_company_id}"
                response = await client.get(url, headers=headers)
                healthy = response.status_code == 200
                message = "RMMS SCADA API accessible" if healthy else f"API returned {response.status_code}"
        except Exception as e:
            healthy = False
            message = f"API connection failed: {str(e)}"

        return HealthStatus(
            healthy=healthy,
            component="rmms_scada_tool",
            message=message
        )

    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []

        if capability == "get_page" and not input_data.get("page_id"):
            errors.append("page_id is required")
        elif capability == "create_page":
            if not input_data.get("page_name"):
                errors.append("page_name is required")
            if not input_data.get("company_id"):
                errors.append("company_id is required")
        elif capability == "add_widget":
            if not input_data.get("page_id"):
                errors.append("page_id is required")
            if not input_data.get("widget_type"):
                errors.append("widget_type is required")
        elif capability == "update_widget":
            if not input_data.get("page_id"):
                errors.append("page_id is required")
            if not input_data.get("widget_id"):
                errors.append("widget_id is required")

        return errors

    def get_capabilities(self) -> List[str]:
        """Return list of capability names"""
        return [cap.name for cap in self.metadata.capabilities]

    async def _list_pages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all SCADA pages, optionally filtered by company"""
        company_id = params.get("company_id", self.default_company_id)
        headers = await self._get_auth_headers(company_id)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/scada/pages?companyId={company_id}"

            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                pages = response.json()
                return {
                    "success": True,
                    "data": {"pages": pages, "count": len(pages)},
                    "message": f"Found {len(pages)} SCADA pages"
                }
            elif response.status_code == 401:
                return {"success": False, "error": "Authentication failed - invalid token"}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific SCADA page with its configuration"""
        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        if not page_id:
            return {"success": False, "error": "page_id is required"}

        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base_url}/scada/pages/{page_id}", headers=headers)

            if response.status_code == 200:
                page = response.json()
                if isinstance(page.get("pageConfig"), str):
                    try:
                        page["pageConfig"] = json.loads(page["pageConfig"])
                    except:
                        pass
                return {
                    "success": True,
                    "data": page,
                    "message": f"Retrieved page {page_id}"
                }
            else:
                return {"success": False, "error": f"Page not found: {page_id}"}

    async def _analyze_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a SCADA page and return summary with component counts and tag bindings.

        Returns structured data optimized for LLM understanding:
        - Component counts by type (gauges, buttons, etc.)
        - Tag bindings with component info
        - Page metadata
        """
        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        if not page_id:
            return {"success": False, "error": "page_id is required"}

        # Get the page data
        page_result = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not page_result.get("success"):
            return page_result

        page = page_result.get("data", {})
        page_config = page.get("pageConfig", {})

        # Handle string pageConfig
        if isinstance(page_config, str):
            try:
                page_config = json.loads(page_config)
            except:
                page_config = {}

        components = page_config.get("components", [])

        # Count components by type and collect IDs
        component_counts = {}
        components_by_type = {}  # Store widget IDs grouped by type
        tag_bindings = []

        for comp in components:
            comp_type = comp.get("type", "unknown")
            comp_id = comp.get("id")
            component_counts[comp_type] = component_counts.get(comp_type, 0) + 1

            # Collect widget IDs by type
            if comp_type not in components_by_type:
                components_by_type[comp_type] = []
            if comp_id:
                comp_info = {
                    "id": comp_id,
                    "width": comp.get("width") or comp.get("props", {}).get("width"),
                    "height": comp.get("height") or comp.get("props", {}).get("height"),
                    "x": comp.get("x"),
                    "y": comp.get("y")
                }
                components_by_type[comp_type].append(comp_info)

            # Extract tag bindings
            props = comp.get("props", {})
            tag_id = props.get("tagBinding") or props.get("tagId")
            if tag_id:
                tag_bindings.append({
                    "componentId": comp_id,
                    "componentType": comp_type,
                    "componentName": props.get("text") or props.get("label") or comp_id,
                    "tagId": tag_id
                })

        # Build summary with widget IDs for each type
        summary = {
            "pageId": page.get("pageId"),
            "pageName": page.get("pageName"),
            "companyId": page.get("companyId"),
            "totalComponents": len(components),
            "componentCounts": component_counts,
            "componentsByType": components_by_type,  # Include widget IDs grouped by type
            "boxWidgetIds": [c["id"] for c in components_by_type.get("box", [])],  # Convenience: list of box IDs
            "tagBindings": tag_bindings,
            "tagBindingCount": len(tag_bindings)
        }

        # Create human-readable message
        counts_str = ", ".join([f"{count} {ctype}" for ctype, count in component_counts.items()])
        message = f"Page '{page.get('pageName')}' (ID: {page_id}) has {len(components)} components: {counts_str}. {len(tag_bindings)} components are bound to tags."

        # Add box dimensions to message if boxes exist
        boxes = components_by_type.get("box", [])
        if boxes:
            box_dims = [f"{b['id']}({b.get('width', '?')}x{b.get('height', '?')})" for b in boxes[:5]]
            if len(boxes) > 5:
                box_dims.append(f"...and {len(boxes)-5} more")
            message += f" Box dimensions: {', '.join(box_dims)}."

        # DEBUG: Log the exact counts
        logger.info(f"🔍 DEBUG analyze_page result - componentCounts: {component_counts}")
        logger.info(f"🔍 DEBUG analyze_page message: {message}")

        return {
            "success": True,
            "data": summary,
            "message": message
        }

    async def _find_widget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find a widget by text, title, or type.

        Search for widgets on a page by their text content, label, or type.
        Returns the widget_id and current properties for use in update_widget.
        """
        logger.info(f"🔍 _find_widget called with params: {params}")

        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        search_text = params.get("text") or params.get("search") or params.get("title") or params.get("label")
        widget_type = params.get("type") or params.get("widget_type")

        if not page_id:
            return {"success": False, "error": "page_id is required"}

        if not search_text and not widget_type:
            return {"success": False, "error": "Either text/search/title/label or type is required"}

        # Get page data
        page_result = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not page_result.get("success"):
            return page_result

        page = page_result.get("data", {})
        page_config = page.get("pageConfig", {})
        if isinstance(page_config, str):
            try:
                page_config = json.loads(page_config)
            except:
                page_config = {}

        components = page_config.get("components", [])
        matches = []

        search_upper = search_text.upper() if search_text else None

        for comp in components:
            props = comp.get("properties", {}) or comp.get("props", {})

            # Check if widget matches search criteria
            match = False

            # Search by text content
            if search_upper:
                text_content = str(props.get("text", "")).upper()
                label_content = str(props.get("label", "")).upper()
                title_content = str(props.get("title", "")).upper()

                if search_upper in text_content or search_upper in label_content or search_upper in title_content:
                    match = True

            # Search by type
            if widget_type and comp.get("type") == widget_type:
                match = True

            if match:
                matches.append({
                    "widget_id": comp.get("id"),
                    "type": comp.get("type"),
                    "x": comp.get("x"),
                    "y": comp.get("y"),
                    "width": comp.get("width"),
                    "height": comp.get("height"),
                    "text": props.get("text", ""),
                    "properties": props
                })

        if not matches:
            return {
                "success": False,
                "error": f"No widget found matching '{search_text or widget_type}' on page {page_id}"
            }

        # Return first match with all matches info
        first_match = matches[0]
        message = f"Found widget '{first_match['widget_id']}' (type: {first_match['type']}) at position x={first_match['x']}, y={first_match['y']}"
        if len(matches) > 1:
            message += f". {len(matches)} total matches found."

        logger.info(f"🔍 find_widget: {message}")

        return {
            "success": True,
            "data": {
                "widget_id": first_match["widget_id"],
                "widget": first_match,
                "all_matches": matches,
                "match_count": len(matches)
            },
            "message": message
        }

    async def _create_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new SCADA page"""
        page_name = params.get("page_name")
        company_id = params.get("company_id")
        width = params.get("width", 1920)
        height = params.get("height", 1080)
        background_color = params.get("background_color", "#1e1e1e")

        if not page_name or not company_id:
            return {"success": False, "error": "page_name and company_id are required"}

        page_config = {
            "components": [],
            "canvasSize": {"width": width, "height": height},
            "backgroundColor": background_color,
            "canvasProperties": {"backgroundColor": background_color},
            "metadata": {"inputs": [], "outputs": [], "events": [], "customCode": ""}
        }

        page_data = {
            "pageName": page_name,
            "companyId": company_id,
            "width": width,
            "height": height,
            "pageConfig": json.dumps(page_config),
            "backgroundColor": background_color,
            "isActive": True,
            "isHomePage": params.get("is_home_page", False)
        }

        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base_url}/scada/pages",
                json=page_data,
                headers=headers
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "message": f"Created page '{page_name}' with ID {result.get('pageId', 'N/A')}"
                }
            else:
                return {"success": False, "error": f"Failed to create page: {response.text}"}

    async def _update_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing SCADA page"""
        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        if not page_id:
            return {"success": False, "error": "page_id is required"}

        existing = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not existing.get("success"):
            return existing

        page_data = existing["data"]
        # Use company_id from page data if available
        company_id = page_data.get("companyId", company_id)

        if "page_name" in params:
            page_data["pageName"] = params["page_name"]
        if "background_color" in params:
            page_data["backgroundColor"] = params["background_color"]
        if "width" in params:
            page_data["width"] = params["width"]
        if "height" in params:
            page_data["height"] = params["height"]
        if "is_home_page" in params:
            page_data["isHomePage"] = params["is_home_page"]
        if "page_config" in params:
            page_data["pageConfig"] = json.dumps(params["page_config"]) if isinstance(params["page_config"], dict) else params["page_config"]
        elif "pageConfig" in page_data and isinstance(page_data["pageConfig"], dict):
            # Ensure pageConfig is always a string for API
            page_data["pageConfig"] = json.dumps(page_data["pageConfig"])

        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.api_base_url}/scada/pages/{page_id}",
                json=page_data,
                headers=headers
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": page_data,
                    "message": f"Updated page {page_id}"
                }
            else:
                return {"success": False, "error": f"Failed to update page: {response.text}"}

    async def _delete_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a SCADA page by ID or name"""
        logger.info(f"🗑️ delete_page called with params: {params}")

        page_id = params.get("page_id")
        page_name = params.get("page_name") or params.get("name") or params.get("text") or params.get("title")
        company_id = params.get("company_id")

        logger.info(f"🔍 Extracted: page_id={page_id}, page_name={page_name}, company_id={company_id}")

        # If page_name provided but not page_id, look up the page_id
        if not page_id and page_name:
            # List pages to find the one with matching name - search all companies if not specified
            companies_to_search = [company_id] if company_id else ["3", "4", "1", "2", "5"]
            for search_company in companies_to_search:
                list_result = await self._list_pages({"company_id": search_company})
                if list_result.get("success"):
                    pages = list_result.get("data", {}).get("pages", [])
                    for page in pages:
                        # Case-insensitive comparison with Turkish character normalization
                        page_name_db = page.get("pageName", "").lower()
                        search_name = page_name.lower()
                        if page_name_db == search_name or page_name_db.replace("ı", "i") == search_name.replace("ı", "i"):
                            page_id = page.get("pageId")
                            company_id = str(page.get("companyId", search_company))
                            logger.info(f"✅ Found page '{page_name}' with id={page_id} in company {company_id}")
                            break
                if page_id:
                    break
            if not page_id:
                return {"success": False, "error": f"Page '{page_name}' not found in any company"}

        if not page_id:
            return {"success": False, "error": "page_id or page_name is required"}

        # If company_id not provided, get it from the page itself
        if not company_id:
            # Try to get page info to determine company_id
            # Use a temporary token to fetch page info
            for try_company in [self.default_company_id, "3", "4", "1", "2"]:
                try:
                    headers = await self._get_auth_headers(try_company)
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(f"{self.api_base_url}/scada/pages/{page_id}", headers=headers)
                        if response.status_code == 200:
                            page_data = response.json()
                            company_id = str(page_data.get("companyId", try_company))
                            break
                except:
                    continue
            if not company_id:
                company_id = self.default_company_id

        # Try to delete with the determined company_id first
        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(f"{self.api_base_url}/scada/pages/{page_id}", headers=headers)

            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted page {page_id}"}

            # If 404 or 403, try other companies
            if response.status_code in [403, 404]:
                for try_company in ["3", "4", "1", "2", "5"]:
                    if try_company == company_id:
                        continue
                    try:
                        headers = await self._get_auth_headers(try_company)
                        response = await client.delete(f"{self.api_base_url}/scada/pages/{page_id}", headers=headers)
                        if response.status_code in [200, 204]:
                            return {"success": True, "message": f"Deleted page {page_id}"}
                    except:
                        continue

            return {"success": False, "error": f"Failed to delete page: {response.text}"}

    async def _add_widget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a widget to a SCADA page"""
        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        widget_type = params.get("widget_type")
        x = params.get("x", 100)
        y = params.get("y", 100)
        width = params.get("width", 200)
        height = params.get("height", 100)
        properties = params.get("properties", {})

        if not page_id or not widget_type:
            return {"success": False, "error": "page_id and widget_type are required"}

        existing = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not existing.get("success"):
            return existing

        page_data = existing["data"]
        page_config = page_data.get("pageConfig", {})
        if isinstance(page_config, str):
            page_config = json.loads(page_config)

        components = page_config.get("components", [])

        existing_ids = [c.get("id", "") for c in components]
        widget_num = 1
        while f"comp_{widget_num}" in existing_ids:
            widget_num += 1
        widget_id = f"comp_{widget_num}"

        # Auto-position: if y is default (100) and there are existing components, stack vertically
        if y == 100 and len(components) > 0:
            max_y = max((c.get("y", 0) + c.get("height", 100) for c in components), default=100)
            y = max_y + 20  # 20px gap between widgets

        new_widget = {
            "id": widget_id,
            "type": widget_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "zIndex": len(components) + 1
        }

        # Flatten common properties to widget level (RMMS format)
        common_props = ["text", "tagBinding", "fontSize", "fontWeight", "backgroundColor",
                       "foreColor", "borderColor", "borderWidth", "borderRadius", "placeholder",
                       "colorMap", "valueTextMap", "minValue", "maxValue", "unit"]
        for prop in common_props:
            if prop in properties:
                new_widget[prop] = properties[prop]
            elif prop in params:
                new_widget[prop] = params[prop]

        # Keep remaining properties in properties object
        remaining_props = {k: v for k, v in properties.items() if k not in common_props}
        if remaining_props:
            new_widget["properties"] = remaining_props

        if widget_type == "box":
            new_widget["isContainer"] = True

        # Handle navigation button with correct RMMS structure
        if widget_type in ["navigation-button", "button"]:
            target_page = properties.get("targetPageId") or properties.get("navigateTo") or params.get("targetPageId")
            button_text = properties.get("text") or properties.get("buttonText") or params.get("text", "Button")
            new_widget = {
                "id": widget_id,
                "type": "button",
                "component": "Button",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "zIndex": len(components) + 1,
                "text": button_text,
                "actionType": "navigation",
                "navigateTo": str(target_page) if target_page else "",
                "backgroundColor": properties.get("backgroundColor", "#1976d2"),
                "foreColor": properties.get("foreColor", "#ffffff"),
                "fontSize": properties.get("fontSize", 14),
                "fontWeight": properties.get("fontWeight", "bold"),
                "borderRadius": properties.get("borderRadius", 8),
                "borderWidth": properties.get("borderWidth", 0),
                "borderColor": properties.get("borderColor", "#000000"),
                "variant": "contained"
            }

        components.append(new_widget)
        page_config["components"] = components

        result = await self._update_page({
            "page_id": page_id,
            "page_config": page_config
        })

        if result.get("success"):
            return {
                "success": True,
                "data": {"widget_id": widget_id, "widget": new_widget},
                "message": f"Added {widget_type} widget '{widget_id}' to page {page_id}"
            }
        return result

    async def _update_widget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update a widget's properties.

        Supports relative position changes:
        - y: "+50" means move down 50px
        - y: "-50" means move up 50px
        - x: "+100" means move right 100px
        - Also supports: "move_up", "move_down", "move_left", "move_right" with delta parameter
        """
        logger.info(f"🔧 _update_widget called with params: {params}")

        page_id = params.get("page_id")
        widget_id = params.get("widget_id")
        company_id = params.get("company_id", self.default_company_id)

        # Support both nested "updates" object and flat parameters
        updates = params.get("updates", {})
        # If flat parameters provided, merge them into updates
        for key in ["x", "y", "width", "height", "zIndex", "properties", "tagBinding", "delta", "move_up", "move_down", "move_left", "move_right"]:
            if key in params and key not in updates:
                updates[key] = params[key]

        if not page_id or not widget_id:
            return {"success": False, "error": "page_id and widget_id are required"}

        existing = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not existing.get("success"):
            return existing

        page_data = existing["data"]
        page_config = page_data.get("pageConfig", {})
        if isinstance(page_config, str):
            page_config = json.loads(page_config)

        components = page_config.get("components", [])

        widget_found = False
        old_position = {}
        new_position = {}

        for component in components:
            if component.get("id") == widget_id:
                widget_found = True
                old_position = {"x": component.get("x"), "y": component.get("y")}

                # Handle relative position changes
                delta = updates.get("delta", 50)  # Default delta is 50px
                try:
                    delta = float(delta)
                except:
                    delta = 50

                # Handle move_up, move_down, move_left, move_right
                if updates.get("move_up"):
                    component["y"] = component.get("y", 0) - delta
                elif updates.get("move_down"):
                    component["y"] = component.get("y", 0) + delta
                elif updates.get("move_left"):
                    component["x"] = component.get("x", 0) - delta
                elif updates.get("move_right"):
                    component["x"] = component.get("x", 0) + delta

                # Handle x, y with relative values ("+50", "-50")
                for key in ["x", "y", "width", "height", "zIndex"]:
                    if key in updates:
                        value = updates[key]
                        current_value = component.get(key, 0)

                        # Check if it's a relative value string
                        if isinstance(value, str):
                            value = value.strip()
                            if value.startswith("+") or value.startswith("-"):
                                try:
                                    offset = float(value)
                                    component[key] = current_value + offset
                                    logger.info(f"🔧 Relative update: {key} = {current_value} + {offset} = {component[key]}")
                                except ValueError:
                                    logger.warning(f"Invalid relative value for {key}: {value}")
                            else:
                                # Try to convert to number
                                try:
                                    component[key] = float(value)
                                except ValueError:
                                    logger.warning(f"Invalid value for {key}: {value}, keeping original")
                        else:
                            # Absolute value
                            component[key] = value

                new_position = {"x": component.get("x"), "y": component.get("y")}

                if "properties" in updates:
                    component["properties"] = {**component.get("properties", {}), **updates["properties"]}
                if "tagBinding" in updates:
                    component["tagBinding"] = updates["tagBinding"]
                    if "properties" not in component:
                        component["properties"] = {}
                    component["properties"]["tagBinding"] = updates["tagBinding"]
                break

        if not widget_found:
            return {"success": False, "error": f"Widget {widget_id} not found"}

        page_config["components"] = components

        result = await self._update_page({
            "page_id": page_id,
            "page_config": page_config
        })

        if result.get("success"):
            message = f"Updated widget {widget_id} on page {page_id}"
            if old_position and new_position:
                message += f". Position changed from ({old_position['x']:.1f}, {old_position['y']:.1f}) to ({new_position['x']:.1f}, {new_position['y']:.1f})"
            logger.info(f"✅ {message}")
            return {
                "success": True,
                "data": {"widget_id": widget_id, "old_position": old_position, "new_position": new_position},
                "message": message
            }
        return result

    async def _remove_widget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a widget from a page"""
        page_id = params.get("page_id")
        widget_id = params.get("widget_id")
        company_id = params.get("company_id", self.default_company_id)

        if not page_id or not widget_id:
            return {"success": False, "error": "page_id and widget_id are required"}

        existing = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not existing.get("success"):
            return existing

        page_data = existing["data"]
        page_config = page_data.get("pageConfig", {})
        if isinstance(page_config, str):
            page_config = json.loads(page_config)

        components = page_config.get("components", [])
        original_count = len(components)

        components = [c for c in components if c.get("id") != widget_id]

        if len(components) == original_count:
            return {"success": False, "error": f"Widget {widget_id} not found"}

        page_config["components"] = components

        result = await self._update_page({
            "page_id": page_id,
            "page_config": page_config
        })

        if result.get("success"):
            return {
                "success": True,
                "message": f"Removed widget {widget_id} from page {page_id}"
            }
        return result

    async def _get_widget_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get available widget types and their properties"""
        return {
            "success": True,
            "data": {"widget_types": self.widget_types},
            "message": f"Available widget types: {', '.join(self.widget_types.keys())}"
        }

    async def _get_tags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get tags for a company to use in widget bindings"""
        company_id = params.get("company_id", self.default_company_id)
        search = params.get("search", "")
        limit = params.get("limit", 50)

        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/Tags/GetTagList"
            body = {"companyId": str(company_id)}

            response = await client.post(url, json=body, headers=headers)

            if response.status_code == 200:
                tags = response.json()
                if search:
                    search_lower = search.lower()
                    tags = [t for t in tags if search_lower in (t.get("tagName", "") or "").lower() or search_lower in (t.get("tagName2", "") or "").lower()]
                if limit:
                    tags = tags[:limit]
                return {
                    "success": True,
                    "data": {"tags": tags, "count": len(tags)},
                    "message": f"Found {len(tags)} tags"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _set_page_background(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set page background color or image"""
        page_id = params.get("page_id")
        background_color = params.get("background_color")
        background_image = params.get("background_image")

        if not page_id:
            return {"success": False, "error": "page_id is required"}

        updates = {}
        if background_color:
            updates["background_color"] = background_color
        if background_image:
            existing = await self._get_page({"page_id": page_id})
            if existing.get("success"):
                page_config = existing["data"].get("pageConfig", {})
                if isinstance(page_config, str):
                    page_config = json.loads(page_config)
                page_config["backgroundImage"] = background_image
                updates["page_config"] = page_config

        updates["page_id"] = page_id
        return await self._update_page(updates)

    async def _get_custom_widgets(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get available custom widgets from SCADA Widgets table"""
        company_id = params.get("company_id", self.default_company_id)

        headers = await self._get_auth_headers(company_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/scada/widgets"
            if company_id:
                url += f"?companyId={company_id}"

            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                widgets = response.json()
                # Parse widget configs and extract sub-components info
                parsed_widgets = []
                for w in widgets:
                    widget_config = w.get("widgetConfig", "{}")
                    if isinstance(widget_config, str):
                        try:
                            widget_config = json.loads(widget_config)
                        except:
                            widget_config = {}

                    parsed_widgets.append({
                        "widgetId": w.get("widgetId"),
                        "widgetName": w.get("widgetName"),
                        "widgetType": w.get("widgetType"),
                        "companyId": w.get("companyId"),
                        "components": widget_config.get("components", []),
                        "componentCount": len(widget_config.get("components", []))
                    })

                # Cache custom widgets for later use
                for pw in parsed_widgets:
                    self.custom_widgets[pw["widgetId"]] = pw

                return {
                    "success": True,
                    "data": {"custom_widgets": parsed_widgets, "count": len(parsed_widgets)},
                    "message": f"Found {len(parsed_widgets)} custom widgets"
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    async def _add_custom_widget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a custom widget to a SCADA page by expanding its sub-components"""
        page_id = params.get("page_id")
        custom_widget_id = params.get("custom_widget_id")
        company_id = params.get("company_id", self.default_company_id)
        x = params.get("x", 100)
        y = params.get("y", 100)
        properties = params.get("properties", {})

        if not page_id or not custom_widget_id:
            return {"success": False, "error": "page_id and custom_widget_id are required"}

        # Get custom widget definition if not cached
        if custom_widget_id not in self.custom_widgets:
            await self._get_custom_widgets({"company_id": company_id})

        if custom_widget_id not in self.custom_widgets:
            return {"success": False, "error": f"Custom widget {custom_widget_id} not found"}

        custom_widget = self.custom_widgets[custom_widget_id]
        components = custom_widget.get("components", [])

        if not components:
            return {"success": False, "error": "Custom widget has no components"}

        # Get existing page
        existing = await self._get_page({"page_id": page_id})
        if not existing.get("success"):
            return existing

        page_data = existing["data"]
        page_config = page_data.get("pageConfig", {})
        if isinstance(page_config, str):
            page_config = json.loads(page_config)

        existing_components = page_config.get("components", [])
        existing_ids = [c.get("id", "") for c in existing_components]

        # Add each sub-component with offset
        added_widgets = []
        for i, comp in enumerate(components):
            # Generate unique ID
            widget_num = 1
            while f"custom_{custom_widget_id}_{widget_num}" in existing_ids:
                widget_num += 1
            widget_id = f"custom_{custom_widget_id}_{widget_num}"
            existing_ids.append(widget_id)

            # Create new widget with position offset
            new_widget = {
                "id": widget_id,
                "type": comp.get("type", "text-label"),
                "x": x + comp.get("x", 0),
                "y": y + comp.get("y", 0),
                "width": comp.get("width", 100),
                "height": comp.get("height", 50),
                "zIndex": len(existing_components) + i + 1,
                "properties": {**comp.get("properties", {}), **properties},
                "customWidgetId": custom_widget_id,
                "customWidgetName": custom_widget.get("widgetName")
            }

            # Copy additional properties from component
            for key in ["text", "tagBinding", "backgroundColor", "foreColor", "fontSize"]:
                if key in comp and key not in new_widget:
                    new_widget[key] = comp[key]

            existing_components.append(new_widget)
            added_widgets.append(widget_id)

        page_config["components"] = existing_components

        # Save page
        result = await self._update_page({
            "page_id": page_id,
            "page_config": page_config
        })

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "custom_widget_name": custom_widget.get("widgetName"),
                    "added_widgets": added_widgets,
                    "component_count": len(added_widgets)
                },
                "message": f"Added custom widget '{custom_widget.get('widgetName')}' with {len(added_widgets)} sub-components"
            }
        return result

    async def _resize_widgets_by_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resize all widgets of a specific type on a page by a percentage.

        This is a bulk operation that resizes all widgets of the specified type
        (e.g., 'box', 'button', 'text-label') by the given percentage.

        Args:
            page_id: The page ID
            company_id: Optional company ID (defaults to 4)
            widget_type: Type of widgets to resize (e.g., 'box')
            increase_percent: Percentage to INCREASE size (e.g., 50 means 50% bigger, 100 means double)
        """
        page_id = params.get("page_id")
        company_id = params.get("company_id", self.default_company_id)
        widget_type = params.get("widget_type", "box")

        # Support both increase_percent and scale_percent for backwards compatibility
        increase_percent = params.get("increase_percent") or params.get("scale_percent", 50)

        if not page_id:
            return {"success": False, "error": "page_id is required"}

        # Convert increase_percent to multiplier
        # 50 means 50% bigger = multiply by 1.5
        # -40 means 40% smaller = multiply by 0.6
        # 100 means double = multiply by 2.0
        # -50 means half size = multiply by 0.5
        if isinstance(increase_percent, str):
            increase_percent = float(increase_percent.replace('%', ''))

        # Prevent values that would make widgets disappear (< -90%)
        if increase_percent <= -90:
            logger.warning(f"⚠️ increase_percent ({increase_percent}) too small, limiting to -90")
            increase_percent = -90

        scale_multiplier = (100 + increase_percent) / 100.0
        action = "shrinking" if increase_percent < 0 else "enlarging"
        logger.info(f"📏 {action} widgets: increase_percent={increase_percent}, scale_multiplier={scale_multiplier}")
        
        # Get page data
        existing = await self._get_page({"page_id": page_id, "company_id": company_id})
        if not existing.get("success"):
            return existing
        
        page_data = existing["data"]
        page_config = page_data.get("pageConfig", {})
        if isinstance(page_config, str):
            page_config = json.loads(page_config)
        
        components = page_config.get("components", [])
        updated_count = 0
        updated_widgets = []
        
        for comp in components:
            if comp.get("type") == widget_type:
                # Get current dimensions - check both root and props
                props = comp.get("props", {})
                old_width = comp.get("width") or props.get("width") or 100
                old_height = comp.get("height") or props.get("height") or 100

                # Handle string values
                if isinstance(old_width, str):
                    old_width = float(old_width.replace('px', ''))
                if isinstance(old_height, str):
                    old_height = float(old_height.replace('px', ''))

                # Calculate new dimensions
                new_width = int(old_width * scale_multiplier)
                new_height = int(old_height * scale_multiplier)
                logger.info(f"📐 Widget {comp.get('id')}: {old_width}x{old_height} -> {new_width}x{new_height}")

                # Update component - set both root AND props for compatibility
                comp["width"] = new_width
                comp["height"] = new_height
                if "props" in comp:
                    comp["props"]["width"] = new_width
                    comp["props"]["height"] = new_height
                
                updated_widgets.append({
                    "id": comp.get("id"),
                    "old_size": f"{old_width}x{old_height}",
                    "new_size": f"{new_width}x{new_height}"
                })
                updated_count += 1
        
        if updated_count == 0:
            return {
                "success": False, 
                "error": f"No widgets of type '{widget_type}' found on page {page_id}"
            }
        
        # Save the updated page
        page_config["components"] = components
        result = await self._update_page({
            "page_id": page_id,
            "company_id": company_id,
            "page_config": page_config
        })
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "page_id": page_id,
                    "widget_type": widget_type,
                    "increase_percent": increase_percent,
                    "updated_count": updated_count,
                    "updated_widgets": updated_widgets
                },
                "message": f"Increased size of {updated_count} '{widget_type}' widgets by {increase_percent}% on page {page_id}"
            }
        return result
