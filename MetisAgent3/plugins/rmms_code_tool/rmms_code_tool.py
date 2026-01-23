"""
RMMS Code Tool - AI-powered Code Editor

Capabilities:
- Create/Edit/Delete codes (Python, C#)
- Save codes to database
- Validate code syntax
- Manage code templates
- Execute codes for testing
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


class RMMSCodeTool(BaseTool):
    """RMMS Code Editor Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://rmms-metis-engine.azurewebsites.net/api").rstrip("/")
        self.timeout = config.config.get("timeout", 30)

        # Supported languages and their templates
        self.languages = {
            "python": {
                "description": "Python for data processing, calculations, and automation",
                "extension": ".py",
                "template": '''# RMMS Python Code
# Author: {author}
# Created: {date}
# Description: {description}

def execute(context):
    """
    Main execution function
    Args:
        context: Dictionary containing tag values and parameters
    Returns:
        Dictionary with results
    """
    result = {{
        "success": True,
        "message": "Execution completed",
        "data": {{}}
    }}
    return result
''',
                "examples": [
                    {"name": "Temperature Calculation", "code": '''def execute(context):
    temp_celsius = float(context.get("temperature", 0))
    temp_fahrenheit = (temp_celsius * 9/5) + 32
    return {"success": True, "celsius": temp_celsius, "fahrenheit": temp_fahrenheit}'''},
                    {"name": "Alarm Check", "code": '''def execute(context):
    value = float(context.get("sensor_value", 0))
    threshold = float(context.get("threshold", 100))
    is_alarm = value > threshold
    return {"success": True, "is_alarm": is_alarm, "message": f"Alarm triggered! Value: {value}" if is_alarm else "Normal"}'''}
                ]
            },
            "csharp": {
                "description": "C# for .NET integration and system operations",
                "extension": ".cs",
                "template": '''// RMMS C# Code
// Author: {author}
// Created: {date}
// Description: {description}

using System;
using System.Collections.Generic;

public class RMMSCode
{{
    public Dictionary<string, object> Execute(Dictionary<string, object> context)
    {{
        var result = new Dictionary<string, object>
        {{
            {{"success", true}},
            {{"message", "Execution completed"}},
            {{"data", new Dictionary<string, object>()}}
        }};
        return result;
    }}
}}
''',
                "examples": [
                    {"name": "Value Processing", "code": '''using System;
using System.Collections.Generic;

public class RMMSCode
{
    public Dictionary<string, object> Execute(Dictionary<string, object> context)
    {
        double value = Convert.ToDouble(context["input_value"]);
        double multiplier = Convert.ToDouble(context.GetValueOrDefault("multiplier", 1.0));
        double result = value * multiplier;
        return new Dictionary<string, object>
        {
            {"success", true},
            {"result", result},
            {"original", value}
        };
    }
}'''}
                ]
            }
        }

        logger.info(f"RMMSCodeTool initialized with API: {self.api_base_url}")

    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        logger.info(f"RMMS Code Tool executing capability: {capability}")

        try:
            if capability == "list_codes":
                result = await self._list_codes(input_data)
            elif capability == "get_code":
                result = await self._get_code(input_data)
            elif capability == "create_code":
                result = await self._create_code(input_data)
            elif capability == "update_code":
                result = await self._update_code(input_data)
            elif capability == "delete_code":
                result = await self._delete_code(input_data)
            elif capability == "validate_code":
                result = await self._validate_code(input_data)
            elif capability == "execute_code":
                result = await self._execute_code(input_data)
            elif capability == "get_template":
                result = await self._get_template(input_data)
            elif capability == "get_examples":
                result = await self._get_examples(input_data)
            elif capability == "get_languages":
                result = await self._get_languages(input_data)
            else:
                result = {"success": False, "error": f"Unknown capability: {capability}"}

            return AgentResult(
                success=result.get("success", False),
                data=result.get("data"),
                message=result.get("message") or result.get("error"),
                metadata={"capability": capability}
            )

        except Exception as e:
            logger.error(f"RMMS Code Tool error: {str(e)}")
            return AgentResult(success=False, message=str(e), metadata={"capability": capability, "error": str(e)})

    async def health_check(self) -> HealthStatus:
        """Check tool health status"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Use company 3 as test
                response = await client.get(f"{self.api_base_url}/Task/codes/3")
                healthy = response.status_code == 200
                message = "RMMS Code API accessible" if healthy else f"API returned {response.status_code}"
        except Exception as e:
            healthy = False
            message = f"API connection failed: {str(e)}"

        return HealthStatus(healthy=healthy, component="rmms_code_tool", message=message)

    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        if capability in ["get_code", "delete_code", "execute_code"]:
            if not input_data.get("code_id"):
                errors.append("code_id is required")
        elif capability == "create_code":
            if not input_data.get("name"):
                errors.append("name is required")
            if not input_data.get("code"):
                errors.append("code is required")
        elif capability == "validate_code":
            if not input_data.get("code"):
                errors.append("code is required")
        return errors

    def get_capabilities(self) -> List[str]:
        return [cap.name for cap in self.metadata.capabilities]

    async def _list_codes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        company_id = params.get("company_id")
        language = params.get("language")

        if not company_id:
            return {"success": False, "error": "company_id is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/Task/codes/{company_id}"
            response = await client.get(url)
            if response.status_code == 200:
                codes = response.json()
                # Filter by language if specified
                if language:
                    codes = [c for c in codes if c.get("language", "").lower() == language.lower()]
                return {"success": True, "data": {"codes": codes, "count": len(codes)}, "message": f"Found {len(codes)} codes"}
            return {"success": False, "error": f"API error: {response.status_code}"}

    async def _get_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code_id = params.get("code_id")
        code_name = params.get("code_name") or params.get("name")
        company_id = params.get("company_id")

        if not company_id:
            return {"success": False, "error": "company_id is required"}

        if not code_id and not code_name:
            return {"success": False, "error": "code_id or code_name is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if code_name and "." not in code_name:
                # Direct get by name (only if no dot - dots cause IIS 404)
                url = f"{self.api_base_url}/Task/code/{company_id}/{code_name}"
                response = await client.get(url)
                if response.status_code == 200:
                    code = response.json()
                    code["name"] = code_name
                    return {"success": True, "data": code, "message": f"Retrieved code '{code_name}'"}

            # Fallback: list all codes and find by name or ID
            url = f"{self.api_base_url}/Task/codes/{company_id}"
            response = await client.get(url)
            if response.status_code == 200:
                codes = response.json()
                if code_name:
                    code = next((c for c in codes if c.get("name") == code_name), None)
                else:
                    code = next((c for c in codes if str(c.get("id")) == str(code_id)), None)
                if code:
                    return {"success": True, "data": code, "message": f"Retrieved code '{code_name or code_id}'"}
            return {"success": False, "error": f"Code not found: {code_name or code_id}"}

    async def _create_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        language = params.get("language", "python")
        code_content = params.get("code")
        description = params.get("description", "")
        company_id = params.get("company_id")
        inputs = params.get("inputs", [])
        outputs = params.get("outputs", [])

        if not company_id:
            return {"success": False, "error": "company_id is required"}

        if not name or not code_content:
            return {"success": False, "error": "name and code are required"}

        if language.lower() not in ["python", "csharp"]:
            return {"success": False, "error": f"Unsupported language: {language}. Use: python or csharp"}

        # API expects: {name, companyId, json: "{language, code, inputs, outputs}"}
        code_json = {
            "language": language.lower() if language.lower() == "python" else "csharp",
            "code": code_content,
            "inputs": inputs,
            "outputs": outputs
        }

        request_data = {
            "name": name,
            "companyId": company_id,
            "json": json.dumps(code_json)
        }

        logger.info(f"Creating code '{name}' for company {company_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Note: endpoint is /Task/code (singular), not /Task/codes
            url = f"{self.api_base_url}/Task/code"
            response = await client.post(url, json=request_data)
            logger.info(f"Create code response: {response.status_code} - {response.text[:200] if response.text else 'empty'}")
            if response.status_code in [200, 201]:
                result = response.json() if response.text else {"name": name}
                return {"success": True, "data": result, "message": f"Created {language} code '{name}'"}
            return {"success": False, "error": f"Failed to create code: {response.text}"}

    async def _update_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code_id = params.get("code_id")
        code_name = params.get("code_name") or params.get("name")
        company_id = params.get("company_id")

        if not company_id:
            return {"success": False, "error": "company_id is required"}

        if not code_id and not code_name:
            return {"success": False, "error": "code_id or code_name is required"}

        existing = await self._get_code({"code_id": code_id, "code_name": code_name, "company_id": company_id})
        if not existing.get("success"):
            return existing

        code_data = existing["data"]
        old_name = code_data.get("name", "")

        new_name = params.get("new_name") or old_name
        new_code = params.get("code") or code_data.get("code", "")
        language = params.get("language") or code_data.get("language", "python")
        inputs = params.get("inputs", [])
        outputs = params.get("outputs", [])

        # Delete old code
        delete_result = await self._delete_code({"code_name": old_name, "company_id": company_id})
        if not delete_result.get("success"):
            return {"success": False, "error": f"Failed to delete old code for update: {delete_result.get('error')}"}

        # Re-create with updated fields
        create_result = await self._create_code({
            "name": new_name,
            "company_id": company_id,
            "language": language,
            "code": new_code,
            "inputs": inputs,
            "outputs": outputs
        })
        if create_result.get("success"):
            return {"success": True, "data": create_result.get("data"), "message": f"Updated code '{old_name}' successfully"}
        return {"success": False, "error": f"Failed to recreate code after delete: {create_result.get('error')}"}

    async def _delete_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code_name = params.get("code_name") or params.get("name") or params.get("code_id")
        company_id = params.get("company_id")

        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not code_name:
            return {"success": False, "error": "code_name is required"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.api_base_url}/Task/codes/{company_id}/{code_name}"
            response = await client.delete(url)
            if response.status_code in [200, 204]:
                return {"success": True, "message": f"Deleted code '{code_name}'"}
            return {"success": False, "error": f"Failed to delete code: {response.text}"}

    async def _validate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code_content = params.get("code")
        language = params.get("language", "python")

        if not code_content:
            return {"success": False, "error": "code is required"}

        errors = []
        warnings = []

        if language == "python":
            try:
                compile(code_content, "<string>", "exec")
            except SyntaxError as e:
                errors.append(f"Line {e.lineno}: {e.msg}")

            if "import os" in code_content and "os.system" in code_content:
                warnings.append("Using os.system is not recommended for security reasons")
            if "eval(" in code_content:
                warnings.append("Using eval() can be a security risk")

        elif language == "csharp":
            if "public class" not in code_content:
                errors.append("C# code must contain a public class")
            if "Execute" not in code_content:
                errors.append("C# code must have an Execute method")

        is_valid = len(errors) == 0
        return {
            "success": True,
            "data": {"is_valid": is_valid, "errors": errors, "warnings": warnings, "language": language},
            "message": "Code is valid" if is_valid else f"Validation failed: {'; '.join(errors)}"
        }

    async def _execute_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code_name = params.get("code_name") or params.get("name") or params.get("code_id")
        company_id = params.get("company_id")
        context = params.get("context", {})
        enable_logging = params.get("enable_logging", True)
        watchdog_timeout = params.get("watchdog_timeout", 3000)

        if not company_id:
            return {"success": False, "error": "company_id is required"}
        if not code_name:
            return {"success": False, "error": "code_name is required"}

        async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for execution
            url = f"{self.api_base_url}/Task/codes/execute/{company_id}/{code_name}"
            response = await client.post(
                url,
                params={"enableLogging": enable_logging, "watchdogTimeout": watchdog_timeout},
                json=context
            )
            logger.info(f"Execute code response: {response.status_code}")
            if response.status_code == 200:
                result = response.json() if response.text else {"status": "completed"}
                return {"success": True, "data": result, "message": f"Code '{code_name}' executed successfully"}
            return {"success": False, "error": f"Execution failed: {response.text}"}

    async def _get_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        language = params.get("language", "python")
        author = params.get("author", "MetisAgent")
        description = params.get("description", "Generated code")

        if language not in self.languages:
            return {"success": False, "error": f"Unsupported language: {language}"}

        template = self.languages[language]["template"].format(
            author=author, date=datetime.now().strftime("%Y-%m-%d"), description=description
        )
        return {"success": True, "data": {"language": language, "template": template}, "message": f"Generated {language} template"}

    async def _get_examples(self, params: Dict[str, Any]) -> Dict[str, Any]:
        language = params.get("language", "python")
        if language not in self.languages:
            return {"success": False, "error": f"Unsupported language: {language}"}

        examples = self.languages[language].get("examples", [])
        return {"success": True, "data": {"language": language, "examples": examples}, "message": f"Found {len(examples)} examples for {language}"}

    async def _get_languages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {"languages": {lang: {"description": info["description"], "extension": info["extension"]} for lang, info in self.languages.items()}},
            "message": f"Supported languages: {', '.join(self.languages.keys())}"
        }
