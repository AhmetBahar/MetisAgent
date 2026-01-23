"""
Axis Data Science Tool - AI-powered Analytics

Capabilities:
- Time series forecasting (Prophet)
- Anomaly detection (Isolation Forest, LOF)
- Correlation analysis
- Change point detection
- Clustering
- Root cause analysis
- Health scoring
- Early warning detection
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


class AxisDataScienceTool(BaseTool):
    """Axis Data Science and Analytics Tool for MetisAgent"""

    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        self.api_base_url = config.config.get("api_base_url", "https://metis-api-container.azurewebsites.net/api")
        self.timeout = config.config.get("timeout", 60)
        self._token = None
        self._token_expiry = None

        logger.info(f"AxisDataScienceTool initialized with API: {self.api_base_url}")

    async def _get_auth_token(self) -> Optional[str]:
        """Get JWT token for Axis API authentication"""
        try:
            if self._token and self._token_expiry and datetime.now() < self._token_expiry:
                return self._token

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/Auth/login",
                    json={"email": "admin@axis.com", "password": "admin123"}
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

            if capability_name == "forecast":
                return await self._forecast(parameters)
            elif capability_name == "anomaly_detection":
                return await self._anomaly_detection(parameters)
            elif capability_name == "correlation":
                return await self._correlation(parameters)
            elif capability_name == "change_point_detection":
                return await self._change_point_detection(parameters)
            elif capability_name == "clustering":
                return await self._clustering(parameters)
            elif capability_name == "root_cause_analysis":
                return await self._root_cause_analysis(parameters)
            elif capability_name == "health_score":
                return await self._health_score(parameters)
            elif capability_name == "early_warning":
                return await self._early_warning(parameters)
            elif capability_name == "resample":
                return await self._resample(parameters)
            else:
                return AgentResult(success=False, message=f"Unknown capability: {capability_name}")

        except Exception as e:
            logger.error(f"Error executing {capability_name}: {e}")
            return AgentResult(success=False, message=str(e))

    async def _forecast(self, params: dict) -> AgentResult:
        """Generate time series forecast"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        data = {
            "tagId": tag_id,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date"),
            "periods": params.get("periods", 24)
        }

        result = await self._make_request("POST", "DataScience/forecast", data=data)

        if result["success"]:
            forecast = result["data"]
            if isinstance(forecast, dict) and "predictions" in forecast:
                pred_count = len(forecast.get("predictions", []))
                summary = f"Generated {pred_count} forecast points for tag {tag_id}"
            else:
                summary = f"Forecast generated for tag {tag_id}"
            return AgentResult(success=True, message=summary, data=forecast)
        return AgentResult(success=False, message=result.get("error", "Failed to generate forecast"))

    async def _anomaly_detection(self, params: dict) -> AgentResult:
        """Detect anomalies in tag data"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        data = {
            "tagId": tag_id,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date"),
            "method": params.get("method", "auto")
        }

        result = await self._make_request("POST", "DataScience/anomaly", data=data)

        if result["success"]:
            anomalies = result["data"]
            if isinstance(anomalies, dict):
                anomaly_count = len(anomalies.get("anomalies", []))
                summary = f"Detected {anomaly_count} anomalies in tag {tag_id}"
            else:
                summary = f"Anomaly detection completed for tag {tag_id}"
            return AgentResult(success=True, message=summary, data=anomalies)
        return AgentResult(success=False, message=result.get("error", "Failed to detect anomalies"))

    async def _correlation(self, params: dict) -> AgentResult:
        """Analyze correlation between tags"""
        tag_ids = params.get("tag_ids")
        if not tag_ids or len(tag_ids) < 2:
            return AgentResult(success=False, message="At least 2 tag_ids are required")

        data = {
            "tagIds": tag_ids,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date")
        }

        result = await self._make_request("POST", "DataScience/correlation", data=data)

        if result["success"]:
            corr = result["data"]
            summary = f"Correlation analysis completed for {len(tag_ids)} tags"
            return AgentResult(success=True, message=summary, data=corr)
        return AgentResult(success=False, message=result.get("error", "Failed to analyze correlation"))

    async def _change_point_detection(self, params: dict) -> AgentResult:
        """Detect change points in time series"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        data = {
            "tagId": tag_id,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date")
        }

        result = await self._make_request("POST", "DataScience/changepoint", data=data)

        if result["success"]:
            changes = result["data"]
            if isinstance(changes, dict):
                change_count = len(changes.get("changePoints", []))
                summary = f"Detected {change_count} change points in tag {tag_id}"
            else:
                summary = f"Change point detection completed for tag {tag_id}"
            return AgentResult(success=True, message=summary, data=changes)
        return AgentResult(success=False, message=result.get("error", "Failed to detect change points"))

    async def _clustering(self, params: dict) -> AgentResult:
        """Cluster similar patterns"""
        tag_ids = params.get("tag_ids")
        if not tag_ids:
            return AgentResult(success=False, message="tag_ids is required")

        data = {
            "tagIds": tag_ids,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date"),
            "nClusters": params.get("n_clusters", 3)
        }

        result = await self._make_request("POST", "DataScience/clustering", data=data)

        if result["success"]:
            clusters = result["data"]
            summary = f"Clustering completed for {len(tag_ids)} tags"
            return AgentResult(success=True, message=summary, data=clusters)
        return AgentResult(success=False, message=result.get("error", "Failed to perform clustering"))

    async def _root_cause_analysis(self, params: dict) -> AgentResult:
        """Analyze potential root causes"""
        target_tag = params.get("target_tag_id")
        candidate_tags = params.get("candidate_tag_ids")

        if not target_tag or not candidate_tags:
            return AgentResult(success=False, message="target_tag_id and candidate_tag_ids are required")

        data = {
            "targetTagId": target_tag,
            "candidateTagIds": candidate_tags,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date")
        }

        result = await self._make_request("POST", "DataScience/rootcause", data=data)

        if result["success"]:
            causes = result["data"]
            summary = f"Root cause analysis completed for tag {target_tag}"
            return AgentResult(success=True, message=summary, data=causes)
        return AgentResult(success=False, message=result.get("error", "Failed to analyze root causes"))

    async def _health_score(self, params: dict) -> AgentResult:
        """Calculate equipment health score"""
        tag_ids = params.get("tag_ids")
        if not tag_ids:
            return AgentResult(success=False, message="tag_ids is required")

        data = {
            "tagIds": tag_ids,
            "weights": params.get("weights")
        }

        result = await self._make_request("POST", "DataScience/healthscore", data=data)

        if result["success"]:
            health = result["data"]
            score = health.get("overallScore", "N/A") if isinstance(health, dict) else "N/A"
            summary = f"Health score: {score}"
            return AgentResult(success=True, message=summary, data=health)
        return AgentResult(success=False, message=result.get("error", "Failed to calculate health score"))

    async def _early_warning(self, params: dict) -> AgentResult:
        """Detect early warning signs"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        data = {
            "tagId": tag_id,
            "threshold": params.get("threshold"),
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date")
        }

        result = await self._make_request("POST", "DataScience/earlywarning", data=data)

        if result["success"]:
            warnings = result["data"]
            if isinstance(warnings, dict):
                warning_count = len(warnings.get("warnings", []))
                summary = f"Detected {warning_count} early warnings for tag {tag_id}"
            else:
                summary = f"Early warning analysis completed for tag {tag_id}"
            return AgentResult(success=True, message=summary, data=warnings)
        return AgentResult(success=False, message=result.get("error", "Failed to detect early warnings"))

    async def _resample(self, params: dict) -> AgentResult:
        """Resample tag data"""
        tag_id = params.get("tag_id")
        if not tag_id:
            return AgentResult(success=False, message="tag_id is required")

        data = {
            "tagId": tag_id,
            "startDate": params.get("start_date"),
            "endDate": params.get("end_date"),
            "interval": params.get("interval", "1h"),
            "method": params.get("method", "mean")
        }

        result = await self._make_request("POST", "DataScience/resample", data=data)

        if result["success"]:
            resampled = result["data"]
            if isinstance(resampled, dict) and "data" in resampled:
                count = len(resampled.get("data", []))
                summary = f"Resampled {count} data points for tag {tag_id}"
            else:
                summary = f"Data resampled for tag {tag_id}"
            return AgentResult(success=True, message=summary, data=resampled)
        return AgentResult(success=False, message=result.get("error", "Failed to resample data"))

    async def health_check(self) -> HealthStatus:
        """Check tool health"""
        try:
            result = await self._make_request("GET", "DataScience/health")
            if result["success"]:
                return HealthStatus(healthy=True, message="Axis Data Science API is operational")
            return HealthStatus(healthy=False, message="Data Science API is not responding")
        except Exception as e:
            return HealthStatus(healthy=False, message=str(e))

    async def validate_input(self, capability: str, input_data: dict) -> list:
        return []

