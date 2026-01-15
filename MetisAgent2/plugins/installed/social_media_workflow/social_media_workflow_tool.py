"""
Social Media Workflow Tool - LLM-driven 8-step campaign management
Dynamic plugin with hybrid graph memory system
"""

import json
import os
import sys
import uuid
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, FeedbackRequired

# Add parent directories to path for MCPTool imports
current_dir = os.path.dirname(os.path.abspath(__file__))
# plugins/installed/social_media_workflow -> MetisAgent2/
metis_agent2_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(metis_agent2_dir)

# Import from app directory
from app.mcp_core import MCPTool, MCPToolResult
# Campaign Graph Memory - use graph_memory tool instead
# from campaign_graph_memory import CampaignGraphMemory

logger = logging.getLogger(__name__)

class SocialMediaWorkflowTool(MCPTool):
    """LLM-driven social media campaign workflow management tool"""
    
    def __init__(self):
        super().__init__(
            name="social_media_workflow",
            description="Advanced social media campaign workflow management with 8-step LLM-driven process",
            version="1.0.0"
        )
        
        # Add capabilities
        self.add_capability("campaign_management")
        self.add_capability("workflow_orchestration")
        self.add_capability("content_planning")
        self.add_capability("approval_workflow")
        self.add_capability("platform_adaptation")
        self.add_capability("analytics_tracking")
        
        # Initialize hybrid graph memory system
        # Use registry to access graph_memory tool instead of separate class
        self.campaign_memory = None  # Will be set to CampaignGraphMemory instance
        self.system_memory = None  # Will be injected by tool coordinator
        
        # Initialize campaign memory immediately
        self._initialize_campaign_memory()
        
        # Instagram API client
        self.instagram_client = Client()
        self.logged_in_user = None
        self.session_info = None
        
        # 8-step workflow definition
        self.workflow_steps = {
            "briefing": {
                "order": 1,
                "name": "Briefing",
                "description": "Project setup, target audience, main message, platforms",
                "required_inputs": ["purpose", "target_audience", "main_message", "platforms"],
                "roles": ["Customer", "Brand Manager", "Marketing Team", "Strategist"],
                "outputs": ["campaign_brief", "brand_guidelines", "audience_personas"]
            },
            "creative_ideation": {
                "order": 2,
                "name": "Creative Idea Generation",
                "description": "Post type, concept, tone, visual ideas, formats",
                "required_inputs": ["campaign_brief"],
                "roles": ["Social Media Specialist", "Writer", "Art Director"],
                "outputs": ["creative_concepts", "tone_guidelines", "visual_concepts"]
            },
            "content_creation": {
                "order": 3,
                "name": "Post Content",
                "description": "Post title/message, video script, visual description",
                "required_inputs": ["creative_concepts"],
                "roles": ["Writer", "Content Manager", "Creative Team"],
                "outputs": ["post_content", "captions", "scripts"]
            },
            "sharing_content": {
                "order": 4,
                "name": "Sharing Content",
                "description": "Share text, emojis, hashtags",
                "required_inputs": ["post_content"],
                "roles": ["Social Media Specialist", "Content Manager"],
                "outputs": ["sharing_text", "hashtags", "engagement_copy"]
            },
            "visual_production": {
                "order": 5,
                "name": "Visual Production",
                "description": "Static designs, video planning, editing",
                "required_inputs": ["visual_concepts", "brand_guidelines"],
                "roles": ["SM Designer", "Motion Designer"],
                "outputs": ["visuals", "graphics", "videos"]
            },
            "approval": {
                "order": 6,
                "name": "Approval",
                "description": "Validation, client approval",
                "required_inputs": ["post_content", "visuals"],
                "roles": ["SM Specialist", "Creative Director", "Brand Manager", "Customer"],
                "outputs": ["approval_status", "revision_notes"]
            },
            "scheduling": {
                "order": 7,
                "name": "Scheduling",
                "description": "Publishing tool setup, timing, quality control",
                "required_inputs": ["approved_content"],
                "roles": ["Social Media Specialist"],
                "outputs": ["scheduled_posts", "publication_timeline"]
            },
            "monitoring": {
                "order": 8,
                "name": "Monitoring & Reporting",
                "description": "Response management, content moderation, analytics",
                "required_inputs": ["published_posts"],
                "roles": ["SM Specialist", "Media Planning Specialist"],
                "outputs": ["performance_metrics", "engagement_report", "recommendations"]
            }
        }
        
        # Platform-specific configurations
        self.platform_configs = {
            "instagram": {
                "image_specs": {"size": "1080x1080", "format": "jpg", "aspect_ratio": "1:1"},
                "caption_limit": 2200,
                "hashtag_limit": 30,
                "story_specs": {"size": "1080x1920", "format": "jpg", "aspect_ratio": "9:16"}
            },
            "twitter": {
                "image_specs": {"size": "1200x675", "format": "jpg", "aspect_ratio": "16:9"},
                "character_limit": 280,
                "thread_support": True,
                "hashtag_limit": 10
            },
            "linkedin": {
                "image_specs": {"size": "1200x627", "format": "jpg", "aspect_ratio": "1.91:1"},
                "character_limit": 3000,
                "tone": "professional",
                "hashtag_limit": 5
            }
        }
        
        # Register actions
        self._register_workflow_actions()
    
    def _initialize_campaign_memory(self):
        """Initialize campaign memory instance"""
        try:
            # Import here to avoid circular imports
            from .campaign_graph_memory import CampaignGraphMemory
            
            # Initialize campaign memory with local storage
            storage_path = os.path.join(os.getcwd(), "campaign_memory_storage")
            self.campaign_memory = CampaignGraphMemory(storage_path)
            logger.info("Campaign memory initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize campaign memory: {e}")
            self.campaign_memory = None
    
    def _register_workflow_actions(self):
        """Register all workflow management actions"""
        
        # Campaign management actions
        self.register_action(
            "create_campaign",
            self._create_campaign,
            required_params=["campaign_data"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "get_campaign",
            self._get_campaign,
            required_params=["campaign_id"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "update_campaign",
            self._update_campaign,
            required_params=["campaign_id", "update_data"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "list_campaigns",
            self._list_campaigns,
            required_params=[],
            optional_params=["user_id", "status", "limit"]
        )
        
        # Workflow step actions
        self.register_action(
            "execute_workflow_step",
            self._execute_workflow_step,
            required_params=["campaign_id", "step_name"],
            optional_params=["user_id", "step_data", "skip_dependencies"]
        )
        
        self.register_action(
            "get_workflow_template",
            self._get_workflow_template,
            required_params=[],
            optional_params=["campaign_type", "platforms"]
        )
        
        self.register_action(
            "validate_step_dependencies",
            self._validate_step_dependencies,
            required_params=["campaign_id", "step_name"],
            optional_params=["user_id"]
        )
        
        # Content and asset management
        self.register_action(
            "add_campaign_asset",
            self._add_campaign_asset,
            required_params=["campaign_id", "asset_data"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "get_campaign_assets",
            self._get_campaign_assets,
            required_params=["campaign_id"],
            optional_params=["user_id", "asset_type"]
        )
        
        # Platform adaptation
        self.register_action(
            "adapt_content_for_platform",
            self._adapt_content_for_platform,
            required_params=["content", "platform"],
            optional_params=["campaign_context"]
        )
        
        self.register_action(
            "get_platform_requirements",
            self._get_platform_requirements,
            required_params=["platform"],
            optional_params=[]
        )
        
        # Approval workflow
        self.register_action(
            "submit_for_approval",
            self._submit_for_approval,
            required_params=["campaign_id", "asset_ids"],
            optional_params=["user_id", "approval_type"]
        )
        
        self.register_action(
            "process_approval",
            self._process_approval,
            required_params=["campaign_id", "approval_id", "decision"],
            optional_params=["user_id", "notes"]
        )
        
        # Analytics and reporting
        self.register_action(
            "track_campaign_metrics",
            self._track_campaign_metrics,
            required_params=["campaign_id", "metrics_data"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "generate_campaign_report",
            self._generate_campaign_report,
            required_params=["campaign_id"],
            optional_params=["user_id", "report_type"]
        )
        
        # Context-aware queries
        self.register_action(
            "get_latest_campaign",
            self._get_latest_campaign,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "search_campaigns",
            self._search_campaigns,
            required_params=["query"],
            optional_params=["user_id"]
        )
        
        # Instagram Direct Actions
        self.register_action(
            "instagram_login",
            self._instagram_login,
            required_params=["username", "password"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "instagram_logout",
            self._instagram_logout,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "instagram_upload_photo",
            self._instagram_upload_photo,
            required_params=["image_path"],
            optional_params=["caption", "user_id"]
        )
        
        self.register_action(
            "instagram_upload_story",
            self._instagram_upload_story,
            required_params=["media_path"],
            optional_params=["story_type", "user_id"]
        )
        
        self.register_action(
            "instagram_like_media",
            self._instagram_like_media,
            required_params=["media_id"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "instagram_comment_media",
            self._instagram_comment_media,
            required_params=["media_id", "text"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "instagram_get_user_info",
            self._instagram_get_user_info,
            required_params=["username"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "instagram_get_followers",
            self._instagram_get_followers,
            required_params=["user_id_target"],
            optional_params=["amount", "user_id"]
        )
    
    def set_system_memory(self, system_memory_tool):
        """Inject system memory tool for hybrid memory architecture"""
        self.system_memory = system_memory_tool
        logger.info("System memory tool injected for hybrid architecture")
    
    def _create_campaign(self, campaign_data: Dict, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Create a new social media campaign"""
        try:
            # Validate required campaign data
            required_fields = ["name", "brand", "purpose", "platforms"]
            for field in required_fields:
                if field not in campaign_data:
                    return MCPToolResult(
                        success=False,
                        error=f"Missing required field: {field}"
                    )
            
            # Create campaign - fallback if memory not available
            if self.campaign_memory:
                result = self.campaign_memory.create_campaign(campaign_data, user_id)
                
                if result["success"]:
                    campaign = result["campaign"]
                    campaign_id = campaign["id"]
                    
                    # Sync to system memory for cross-domain context
                    if self.system_memory:
                        sync_result = self.campaign_memory.sync_to_system_memory(
                            self.system_memory, campaign_id, user_id
                        )
                        logger.info(f"Campaign sync to system memory: {sync_result.get('success', False)}")
                    
                    return MCPToolResult(
                        success=True,
                        data={
                            "campaign_id": campaign_id,
                            "campaign": campaign,
                            "message": f"Campaign '{campaign['name']}' created successfully"
                        }
                    )
                else:
                    return MCPToolResult(success=False, error=result["error"])
            else:
                # FALLBACK: Create campaign without memory
                campaign_id = str(uuid.uuid4())
                campaign = {
                    "id": campaign_id,
                    "name": campaign_data["name"],
                    "brand": campaign_data["brand"],
                    "purpose": campaign_data["purpose"],
                    "platforms": campaign_data["platforms"],
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "user_id": user_id,
                    "workflow_steps": self.workflow_steps
                }
                
                logger.info(f"FALLBACK: Created campaign without memory: {campaign_id}")
                
                return MCPToolResult(
                    success=True,
                    data={
                        "campaign_id": campaign_id,
                        "campaign": campaign,
                        "message": f"Campaign '{campaign['name']}' created successfully (fallback mode)",
                        "workflow_ready": True,
                        "next_steps": ["briefing", "ideation", "content_creation"]
                    }
                )
                
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_campaign(self, campaign_id: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Get specific campaign by ID"""
        try:
            if self.campaign_memory:
                result = self.campaign_memory.get_campaign(campaign_id, user_id)
                
                if result["success"]:
                    return MCPToolResult(success=True, data=result["campaign"])
                else:
                    return MCPToolResult(success=False, error=result["error"])
            else:
                # FALLBACK: Return mock campaign structure
                return MCPToolResult(
                    success=False, 
                    error="Campaign memory not available. Please check system configuration."
                )
                
        except Exception as e:
            logger.error(f"Error getting campaign: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _update_campaign(self, campaign_id: str, update_data: Dict, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Update campaign with new data"""
        try:
            if not self.campaign_memory:
                return MCPToolResult(success=False, error="Campaign memory not available")
            
            # Get existing campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            
            # Update campaign attributes
            if "attributes" in update_data:
                campaign["attributes"].update(update_data["attributes"])
            if "brief" in update_data:
                campaign["brief"].update(update_data["brief"])
            
            campaign["attributes"]["updated"] = datetime.now().isoformat()
            
            # Save updated campaign
            data = self.campaign_memory._load_campaigns(user_id)
            for i, c in enumerate(data["campaigns"]):
                if c["id"] == campaign_id:
                    data["campaigns"][i] = campaign
                    break
            
            self.campaign_memory._save_campaigns(data, user_id)
            
            # Sync to system memory
            if self.system_memory:
                self.campaign_memory.sync_to_system_memory(self.system_memory, campaign_id, user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "campaign": campaign,
                    "message": "Campaign updated successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating campaign: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_campaigns(self, user_id: str = "default", status: str = None, limit: int = None, **kwargs) -> MCPToolResult:
        """List campaigns for user with optional filtering"""
        try:
            if not self.campaign_memory:
                return MCPToolResult(
                    success=True,
                    data={"campaigns": [], "count": 0, "total_count": 0, "message": "Campaign memory not available"}
                )
            
            result = self.campaign_memory.get_user_campaigns(user_id, status)
            
            if result["success"]:
                campaigns = result["campaigns"]
                
                # Apply limit
                if limit:
                    campaigns = campaigns[:limit]
                
                return MCPToolResult(
                    success=True,
                    data={
                        "campaigns": campaigns,
                        "count": len(campaigns),
                        "total_count": result["count"]
                    }
                )
            else:
                return MCPToolResult(success=False, error=result["error"])
                
        except Exception as e:
            logger.error(f"Error listing campaigns: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _execute_workflow_step(self, campaign_id: str, step_name: str, user_id: str = "default", 
                              step_data: Dict = None, skip_dependencies: bool = False, **kwargs) -> MCPToolResult:
        """Execute a specific workflow step for a campaign"""
        try:
            # Validate step name
            if step_name not in self.workflow_steps:
                return MCPToolResult(
                    success=False,
                    error=f"Invalid step name: {step_name}. Valid steps: {list(self.workflow_steps.keys())}"
                )
            
            if not self.campaign_memory:
                return MCPToolResult(success=False, error="Campaign memory not available")
            
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            step_definition = self.workflow_steps[step_name]
            
            # Validate dependencies unless skipped
            if not skip_dependencies:
                dependency_result = self._validate_step_dependencies(campaign_id, step_name, user_id)
                if not dependency_result.success:
                    return dependency_result
            
            # Prepare step execution data
            step_execution_data = {
                "step_id": f"{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "step_name": step_name,
                "status": "in_progress",
                "started": datetime.now().isoformat(),
                "outputs": [],
                "notes": step_data.get("notes", []) if step_data else []
            }
            
            # Execute step based on type
            if step_name == "briefing":
                outputs = self._execute_briefing_step(campaign, step_data or {})
            elif step_name == "creative_ideation":
                outputs = self._execute_creative_ideation_step(campaign, step_data or {})
            elif step_name == "content_creation":
                outputs = self._execute_content_creation_step(campaign, step_data or {})
            elif step_name == "sharing_content":
                outputs = self._execute_sharing_content_step(campaign, step_data or {})
            elif step_name == "visual_production":
                outputs = self._execute_visual_production_step(campaign, step_data or {})
            elif step_name == "approval":
                outputs = self._execute_approval_step(campaign, step_data or {})
            elif step_name == "scheduling":
                outputs = self._execute_scheduling_step(campaign, step_data or {})
            elif step_name == "monitoring":
                outputs = self._execute_monitoring_step(campaign, step_data or {})
            else:
                outputs = {"message": f"Step {step_name} executed", "data": step_data or {}}
            
            # Update step execution data
            step_execution_data["outputs"] = [outputs] if not isinstance(outputs, list) else outputs
            step_execution_data["status"] = "completed"
            step_execution_data["completed"] = datetime.now().isoformat()
            
            # Update campaign with step results
            update_result = self.campaign_memory.update_campaign_step(campaign_id, step_execution_data, user_id)
            
            if update_result["success"]:
                return MCPToolResult(
                    success=True,
                    data={
                        "step": step_execution_data,
                        "outputs": outputs,
                        "campaign_id": campaign_id,
                        "message": f"Step '{step_name}' executed successfully"
                    }
                )
            else:
                return MCPToolResult(success=False, error=update_result["error"])
                
        except Exception as e:
            logger.error(f"Error executing workflow step: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _execute_briefing_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute briefing workflow step"""
        brief_data = campaign.get("brief", {})
        
        return {
            "step_type": "briefing",
            "campaign_brief": {
                "purpose": brief_data.get("purpose", ""),
                "target_audience": brief_data.get("target_audience", ""),
                "main_message": brief_data.get("main_message", ""),
                "objectives": brief_data.get("objectives", []),
                "brand_guidelines": brief_data.get("brand_guidelines", {})
            },
            "platforms": campaign["attributes"]["platforms"],
            "notes": step_data.get("additional_notes", [])
        }
    
    def _execute_creative_ideation_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute creative ideation workflow step"""
        return {
            "step_type": "creative_ideation",
            "creative_concepts": step_data.get("concepts", []),
            "tone_guidelines": {
                "primary_tone": campaign["attributes"]["persona_tone"],
                "secondary_tones": step_data.get("secondary_tones", [])
            },
            "visual_concepts": step_data.get("visual_ideas", []),
            "post_formats": step_data.get("formats", ["image_post", "carousel", "story"])
        }
    
    def _execute_content_creation_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute content creation workflow step"""
        return {
            "step_type": "content_creation",
            "post_content": step_data.get("content", ""),
            "captions": step_data.get("captions", []),
            "scripts": step_data.get("scripts", []),
            "call_to_action": step_data.get("cta", "")
        }
    
    def _execute_sharing_content_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute sharing content workflow step"""
        return {
            "step_type": "sharing_content",
            "sharing_text": step_data.get("sharing_text", ""),
            "hashtags": step_data.get("hashtags", []),
            "engagement_copy": step_data.get("engagement_copy", ""),
            "platform_specific": step_data.get("platform_adaptations", {})
        }
    
    def _execute_visual_production_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute visual production workflow step"""
        return {
            "step_type": "visual_production",
            "visuals": step_data.get("visual_assets", []),
            "graphics": step_data.get("graphics", []),
            "videos": step_data.get("videos", []),
            "design_specs": step_data.get("design_specifications", {})
        }
    
    def _execute_approval_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute approval workflow step"""
        return {
            "step_type": "approval",
            "approval_status": step_data.get("status", "pending"),
            "reviewer": step_data.get("reviewer", ""),
            "approval_date": datetime.now().isoformat(),
            "revision_notes": step_data.get("revision_notes", [])
        }
    
    def _execute_scheduling_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute scheduling workflow step"""
        return {
            "step_type": "scheduling",
            "scheduled_posts": step_data.get("schedule", []),
            "publication_timeline": step_data.get("timeline", {}),
            "quality_checks": step_data.get("quality_checks", [])
        }
    
    def _execute_monitoring_step(self, campaign: Dict, step_data: Dict) -> Dict:
        """Execute monitoring workflow step"""
        return {
            "step_type": "monitoring",
            "performance_metrics": step_data.get("metrics", {}),
            "engagement_report": step_data.get("engagement", {}),
            "recommendations": step_data.get("recommendations", [])
        }
    
    def _validate_step_dependencies(self, campaign_id: str, step_name: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Validate that required dependencies for a workflow step are met"""
        try:
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            step_definition = self.workflow_steps[step_name]
            required_inputs = step_definition.get("required_inputs", [])
            
            # Check if required inputs are available in campaign
            missing_inputs = []
            completed_steps = [step["step_name"] for step in campaign["workflow_steps"] if step["status"] == "completed"]
            
            for required_input in required_inputs:
                # Check if the input corresponds to a completed step or available data
                if required_input == "campaign_brief" and "briefing" not in completed_steps:
                    missing_inputs.append("briefing step must be completed")
                elif required_input == "creative_concepts" and "creative_ideation" not in completed_steps:
                    missing_inputs.append("creative_ideation step must be completed")
                elif required_input == "post_content" and "content_creation" not in completed_steps:
                    missing_inputs.append("content_creation step must be completed")
                elif required_input == "visual_concepts" and not campaign.get("assets"):
                    missing_inputs.append("visual concepts or assets required")
                elif required_input == "approved_content" and "approval" not in completed_steps:
                    missing_inputs.append("approval step must be completed")
                elif required_input == "published_posts" and "scheduling" not in completed_steps:
                    missing_inputs.append("scheduling step must be completed")
            
            if missing_inputs:
                return MCPToolResult(
                    success=False,
                    error=f"Missing dependencies for step '{step_name}': {', '.join(missing_inputs)}"
                )
            
            return MCPToolResult(success=True, data={"dependencies_met": True})
            
        except Exception as e:
            logger.error(f"Error validating step dependencies: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_workflow_template(self, campaign_type: str = "standard", platforms: List[str] = None, **kwargs) -> MCPToolResult:
        """Get workflow template based on campaign type and platforms"""
        try:
            template = {
                "workflow_steps": self.workflow_steps,
                "campaign_type": campaign_type,
                "platforms": platforms or ["instagram", "twitter", "linkedin"],
                "estimated_duration": "7-14 days",
                "recommended_sequence": [
                    "briefing",
                    "creative_ideation",
                    "content_creation",
                    "sharing_content",
                    "visual_production",
                    "approval",
                    "scheduling",
                    "monitoring"
                ]
            }
            
            # Customize template based on platforms
            if platforms:
                platform_customizations = {}
                for platform in platforms:
                    if platform in self.platform_configs:
                        platform_customizations[platform] = self.platform_configs[platform]
                template["platform_customizations"] = platform_customizations
            
            return MCPToolResult(success=True, data=template)
            
        except Exception as e:
            logger.error(f"Error getting workflow template: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _add_campaign_asset(self, campaign_id: str, asset_data: Dict, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Add asset to campaign"""
        try:
            result = self.campaign_memory.add_campaign_asset(campaign_id, asset_data, user_id)
            
            if result["success"]:
                return MCPToolResult(success=True, data=result["asset"])
            else:
                return MCPToolResult(success=False, error=result["error"])
                
        except Exception as e:
            logger.error(f"Error adding campaign asset: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_campaign_assets(self, campaign_id: str, user_id: str = "default", asset_type: str = None, **kwargs) -> MCPToolResult:
        """Get campaign assets, optionally filtered by type"""
        try:
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            assets = campaign.get("assets", [])
            
            # Filter by asset type if specified
            if asset_type:
                assets = [asset for asset in assets if asset.get("type") == asset_type]
            
            return MCPToolResult(
                success=True,
                data={
                    "assets": assets,
                    "count": len(assets),
                    "campaign_id": campaign_id
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting campaign assets: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _adapt_content_for_platform(self, content: str, platform: str, campaign_context: Dict = None, **kwargs) -> MCPToolResult:
        """Adapt content for specific platform requirements"""
        try:
            if platform not in self.platform_configs:
                return MCPToolResult(
                    success=False,
                    error=f"Unsupported platform: {platform}. Supported: {list(self.platform_configs.keys())}"
                )
            
            platform_config = self.platform_configs[platform]
            adapted_content = {"original_content": content, "platform": platform}
            
            # Apply character limits
            if "character_limit" in platform_config:
                limit = platform_config["character_limit"]
                if len(content) > limit:
                    adapted_content["content"] = content[:limit - 3] + "..."
                    adapted_content["truncated"] = True
                else:
                    adapted_content["content"] = content
                    adapted_content["truncated"] = False
            
            # Add platform-specific recommendations
            adapted_content["recommendations"] = {
                "image_specs": platform_config.get("image_specs", {}),
                "hashtag_limit": platform_config.get("hashtag_limit", 10),
                "tone": platform_config.get("tone", "friendly")
            }
            
            return MCPToolResult(success=True, data=adapted_content)
            
        except Exception as e:
            logger.error(f"Error adapting content for platform: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_platform_requirements(self, platform: str, **kwargs) -> MCPToolResult:
        """Get requirements and specifications for a platform"""
        try:
            if platform not in self.platform_configs:
                return MCPToolResult(
                    success=False,
                    error=f"Unsupported platform: {platform}. Supported: {list(self.platform_configs.keys())}"
                )
            
            return MCPToolResult(
                success=True,
                data={
                    "platform": platform,
                    "requirements": self.platform_configs[platform]
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting platform requirements: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _submit_for_approval(self, campaign_id: str, asset_ids: List[str], user_id: str = "default", 
                           approval_type: str = "content", **kwargs) -> MCPToolResult:
        """Submit campaign assets for approval"""
        try:
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            
            # Create approval entry
            approval_entry = {
                "approval_id": str(uuid.uuid4())[:8],
                "asset_ids": asset_ids,
                "approval_type": approval_type,
                "status": "pending",
                "submitted_by": user_id,
                "submitted_at": datetime.now().isoformat(),
                "reviewer": None,
                "reviewed_at": None,
                "notes": []
            }
            
            # Add approval to campaign
            if "approvals" not in campaign:
                campaign["approvals"] = []
            campaign["approvals"].append(approval_entry)
            
            # Update campaign
            data = self.campaign_memory._load_campaigns(user_id)
            for i, c in enumerate(data["campaigns"]):
                if c["id"] == campaign_id:
                    data["campaigns"][i] = campaign
                    break
            
            self.campaign_memory._save_campaigns(data, user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "approval_id": approval_entry["approval_id"],
                    "approval": approval_entry,
                    "message": "Assets submitted for approval"
                }
            )
            
        except Exception as e:
            logger.error(f"Error submitting for approval: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _process_approval(self, campaign_id: str, approval_id: str, decision: str, 
                         user_id: str = "default", notes: str = None, **kwargs) -> MCPToolResult:
        """Process approval decision"""
        try:
            if decision not in ["approved", "rejected", "revision_requested"]:
                return MCPToolResult(
                    success=False,
                    error="Invalid decision. Must be: approved, rejected, or revision_requested"
                )
            
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            
            # Find approval entry
            approval_entry = None
            for approval in campaign.get("approvals", []):
                if approval["approval_id"] == approval_id:
                    approval_entry = approval
                    break
            
            if not approval_entry:
                return MCPToolResult(success=False, error="Approval entry not found")
            
            # Update approval
            approval_entry["status"] = decision
            approval_entry["reviewer"] = user_id
            approval_entry["reviewed_at"] = datetime.now().isoformat()
            if notes:
                approval_entry["notes"].append(notes)
            
            # Update campaign
            data = self.campaign_memory._load_campaigns(user_id)
            for i, c in enumerate(data["campaigns"]):
                if c["id"] == campaign_id:
                    data["campaigns"][i] = campaign
                    break
            
            self.campaign_memory._save_campaigns(data, user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "approval": approval_entry,
                    "decision": decision,
                    "message": f"Approval {decision} successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing approval: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _track_campaign_metrics(self, campaign_id: str, metrics_data: Dict, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Track and store campaign performance metrics"""
        try:
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            
            # Create metrics entry
            metrics_entry = {
                "metric_id": str(uuid.uuid4())[:8],
                "timestamp": datetime.now().isoformat(),
                "platform": metrics_data.get("platform", ""),
                "post_id": metrics_data.get("post_id", ""),
                "metrics": {
                    "likes": metrics_data.get("likes", 0),
                    "comments": metrics_data.get("comments", 0),
                    "shares": metrics_data.get("shares", 0),
                    "reach": metrics_data.get("reach", 0),
                    "impressions": metrics_data.get("impressions", 0),
                    "engagement_rate": metrics_data.get("engagement_rate", 0.0),
                    "clicks": metrics_data.get("clicks", 0),
                    "saves": metrics_data.get("saves", 0)
                },
                "additional_data": metrics_data.get("additional_data", {})
            }
            
            # Add metrics to campaign
            if "metrics" not in campaign:
                campaign["metrics"] = []
            campaign["metrics"].append(metrics_entry)
            
            # Update campaign
            data = self.campaign_memory._load_campaigns(user_id)
            for i, c in enumerate(data["campaigns"]):
                if c["id"] == campaign_id:
                    data["campaigns"][i] = campaign
                    break
            
            self.campaign_memory._save_campaigns(data, user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "metric_id": metrics_entry["metric_id"],
                    "metrics": metrics_entry,
                    "message": "Metrics tracked successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking campaign metrics: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _generate_campaign_report(self, campaign_id: str, user_id: str = "default", 
                                 report_type: str = "summary", **kwargs) -> MCPToolResult:
        """Generate campaign performance report"""
        try:
            # Get campaign
            campaign_result = self.campaign_memory.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return MCPToolResult(success=False, error=campaign_result["error"])
            
            campaign = campaign_result["campaign"]
            
            # Generate report based on type
            if report_type == "summary":
                report = self._generate_summary_report(campaign)
            elif report_type == "detailed":
                report = self._generate_detailed_report(campaign)
            elif report_type == "performance":
                report = self._generate_performance_report(campaign)
            else:
                return MCPToolResult(success=False, error=f"Invalid report type: {report_type}")
            
            return MCPToolResult(success=True, data=report)
            
        except Exception as e:
            logger.error(f"Error generating campaign report: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _generate_summary_report(self, campaign: Dict) -> Dict:
        """Generate summary report for campaign"""
        return {
            "report_type": "summary",
            "campaign_id": campaign["id"],
            "campaign_name": campaign["name"],
            "brand": campaign["attributes"]["brand"],
            "status": campaign["attributes"]["status"],
            "platforms": campaign["attributes"]["platforms"],
            "created": campaign["attributes"]["created"],
            "updated": campaign["attributes"]["updated"],
            "workflow_progress": {
                "total_steps": len(self.workflow_steps),
                "completed_steps": len([s for s in campaign["workflow_steps"] if s["status"] == "completed"]),
                "current_step": campaign["attributes"]["current_step"]
            },
            "assets_count": len(campaign.get("assets", [])),
            "metrics_count": len(campaign.get("metrics", [])),
            "approval_status": self._get_overall_approval_status(campaign)
        }
    
    def _generate_detailed_report(self, campaign: Dict) -> Dict:
        """Generate detailed report for campaign"""
        summary = self._generate_summary_report(campaign)
        summary.update({
            "report_type": "detailed",
            "brief": campaign.get("brief", {}),
            "workflow_steps": campaign.get("workflow_steps", []),
            "assets": campaign.get("assets", []),
            "approvals": campaign.get("approvals", []),
            "metrics": campaign.get("metrics", [])
        })
        return summary
    
    def _generate_performance_report(self, campaign: Dict) -> Dict:
        """Generate performance-focused report for campaign"""
        metrics = campaign.get("metrics", [])
        
        # Aggregate metrics
        total_metrics = {
            "likes": sum(m["metrics"].get("likes", 0) for m in metrics),
            "comments": sum(m["metrics"].get("comments", 0) for m in metrics),
            "shares": sum(m["metrics"].get("shares", 0) for m in metrics),
            "reach": sum(m["metrics"].get("reach", 0) for m in metrics),
            "impressions": sum(m["metrics"].get("impressions", 0) for m in metrics),
            "clicks": sum(m["metrics"].get("clicks", 0) for m in metrics),
            "saves": sum(m["metrics"].get("saves", 0) for m in metrics)
        }
        
        # Calculate average engagement rate
        engagement_rates = [m["metrics"].get("engagement_rate", 0) for m in metrics if m["metrics"].get("engagement_rate", 0) > 0]
        avg_engagement_rate = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0
        
        return {
            "report_type": "performance",
            "campaign_id": campaign["id"],
            "campaign_name": campaign["name"],
            "performance_period": {
                "start": campaign["attributes"]["created"],
                "end": campaign["attributes"]["updated"]
            },
            "total_metrics": total_metrics,
            "average_engagement_rate": avg_engagement_rate,
            "platform_breakdown": self._get_platform_breakdown(metrics),
            "top_performing_posts": self._get_top_performing_posts(metrics),
            "recommendations": self._generate_performance_recommendations(total_metrics, avg_engagement_rate)
        }
    
    def _get_overall_approval_status(self, campaign: Dict) -> str:
        """Get overall approval status for campaign"""
        approvals = campaign.get("approvals", [])
        if not approvals:
            return "no_approvals"
        
        statuses = [a["status"] for a in approvals]
        if all(s == "approved" for s in statuses):
            return "fully_approved"
        elif any(s == "rejected" for s in statuses):
            return "rejected"
        elif any(s == "revision_requested" for s in statuses):
            return "revision_requested"
        else:
            return "pending"
    
    def _get_platform_breakdown(self, metrics: List[Dict]) -> Dict:
        """Get performance breakdown by platform"""
        platform_data = {}
        for metric in metrics:
            platform = metric.get("platform", "unknown")
            if platform not in platform_data:
                platform_data[platform] = {
                    "posts": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_reach": 0
                }
            
            platform_data[platform]["posts"] += 1
            platform_data[platform]["total_likes"] += metric["metrics"].get("likes", 0)
            platform_data[platform]["total_comments"] += metric["metrics"].get("comments", 0)
            platform_data[platform]["total_reach"] += metric["metrics"].get("reach", 0)
        
        return platform_data
    
    def _get_top_performing_posts(self, metrics: List[Dict], limit: int = 5) -> List[Dict]:
        """Get top performing posts based on engagement"""
        if not metrics:
            return []
        
        # Sort by total engagement (likes + comments + shares)
        sorted_metrics = sorted(
            metrics,
            key=lambda m: (
                m["metrics"].get("likes", 0) + 
                m["metrics"].get("comments", 0) + 
                m["metrics"].get("shares", 0)
            ),
            reverse=True
        )
        
        return sorted_metrics[:limit]
    
    def _generate_performance_recommendations(self, total_metrics: Dict, avg_engagement_rate: float) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if avg_engagement_rate < 0.02:  # Less than 2%
            recommendations.append("Consider improving content quality and relevance to increase engagement")
        
        if total_metrics.get("comments", 0) < total_metrics.get("likes", 0) * 0.1:
            recommendations.append("Focus on creating more conversation-driving content")
        
        if total_metrics.get("shares", 0) < total_metrics.get("likes", 0) * 0.05:
            recommendations.append("Create more shareable content that provides value")
        
        if total_metrics.get("saves", 0) < total_metrics.get("likes", 0) * 0.15:
            recommendations.append("Develop more educational or reference content that users want to save")
        
        return recommendations
    
    def _get_latest_campaign(self, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Get user's latest campaign"""
        try:
            result = self.campaign_memory.get_latest_campaign(user_id)
            
            if result["success"]:
                return MCPToolResult(success=True, data=result["campaign"])
            else:
                return MCPToolResult(success=False, error=result["error"])
                
        except Exception as e:
            logger.error(f"Error getting latest campaign: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _search_campaigns(self, query: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Search campaigns by query"""
        try:
            result = self.campaign_memory.search_campaigns(query, user_id)
            
            if result["success"]:
                return MCPToolResult(
                    success=True,
                    data={
                        "campaigns": result["campaigns"],
                        "count": result["count"],
                        "query": query
                    }
                )
            else:
                return MCPToolResult(success=False, error=result["error"])
                
        except Exception as e:
            logger.error(f"Error searching campaigns: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def health_check(self) -> MCPToolResult:
        """Check tool health and configuration"""
        try:
            return MCPToolResult(
                success=True,
                data={
                    "status": "healthy",
                    "campaign_memory": "operational",
                    "system_memory_connected": bool(self.system_memory),
                    "workflow_steps": len(self.workflow_steps),
                    "supported_platforms": list(self.platform_configs.keys()),
                    "base_storage_path": self.campaign_memory.base_path
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    # Instagram Direct Actions Implementation
    def _instagram_login(self, username: str, password: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Login to Instagram account"""
        try:
            # Use session if available
            session_file = f"/tmp/instagram_session_{username}.json"
            
            if os.path.exists(session_file):
                self.instagram_client.load_settings(session_file)
                logger.info(f"Loading Instagram session for {username}")
            
            try:
                self.instagram_client.login(username, password)
                self.logged_in_user = username
                
                # Save session
                self.instagram_client.dump_settings(session_file)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "message": f"Successfully logged in as {username}",
                        "username": username,
                        "user_id": self.instagram_client.user_id
                    }
                )
                
            except (LoginRequired, ChallengeRequired, FeedbackRequired) as e:
                return MCPToolResult(success=False, error=f"Instagram login failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during Instagram login: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_logout(self, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Logout from Instagram"""
        try:
            if self.logged_in_user:
                self.instagram_client.logout()
                username = self.logged_in_user
                self.logged_in_user = None
                
                return MCPToolResult(
                    success=True,
                    data={"message": f"Successfully logged out from {username}"}
                )
            else:
                return MCPToolResult(success=False, error="No active Instagram session")
                
        except Exception as e:
            logger.error(f"Error during Instagram logout: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_upload_photo(self, image_path: str, caption: str = "", user_id: str = "default", **kwargs) -> MCPToolResult:
        """Upload photo to Instagram"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            if not os.path.exists(image_path):
                return MCPToolResult(success=False, error=f"Image file not found: {image_path}")
            
            # Upload photo
            media = self.instagram_client.photo_upload(image_path, caption)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": "Photo uploaded successfully",
                    "media_id": media.id,
                    "media_code": media.code,
                    "caption": caption,
                    "image_path": image_path
                }
            )
            
        except Exception as e:
            logger.error(f"Error uploading Instagram photo: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_upload_story(self, media_path: str, story_type: str = "photo", user_id: str = "default", **kwargs) -> MCPToolResult:
        """Upload story to Instagram"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            if not os.path.exists(media_path):
                return MCPToolResult(success=False, error=f"Media file not found: {media_path}")
            
            # Upload story based on type
            if story_type.lower() == "photo":
                media = self.instagram_client.photo_upload_to_story(media_path)
            elif story_type.lower() == "video":
                media = self.instagram_client.video_upload_to_story(media_path)
            else:
                return MCPToolResult(success=False, error=f"Unsupported story type: {story_type}")
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Story ({story_type}) uploaded successfully",
                    "media_id": media.id,
                    "media_path": media_path,
                    "story_type": story_type
                }
            )
            
        except Exception as e:
            logger.error(f"Error uploading Instagram story: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_like_media(self, media_id: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Like Instagram media"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            # Like media
            success = self.instagram_client.media_like(media_id)
            
            if success:
                return MCPToolResult(
                    success=True,
                    data={
                        "message": "Media liked successfully",
                        "media_id": media_id,
                        "action": "like"
                    }
                )
            else:
                return MCPToolResult(success=False, error="Failed to like media")
                
        except Exception as e:
            logger.error(f"Error liking Instagram media: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_comment_media(self, media_id: str, text: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Comment on Instagram media"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            # Comment on media
            comment = self.instagram_client.media_comment(media_id, text)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": "Comment posted successfully",
                    "media_id": media_id,
                    "comment_id": comment.id,
                    "comment_text": text
                }
            )
            
        except Exception as e:
            logger.error(f"Error commenting on Instagram media: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_get_user_info(self, username: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Get Instagram user information"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            # Get user info
            user_info = self.instagram_client.user_info_by_username(username)
            
            return MCPToolResult(
                success=True,
                data={
                    "username": user_info.username,
                    "full_name": user_info.full_name,
                    "biography": user_info.biography,
                    "followers_count": user_info.follower_count,
                    "following_count": user_info.following_count,
                    "media_count": user_info.media_count,
                    "is_private": user_info.is_private,
                    "is_verified": user_info.is_verified
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting Instagram user info: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _instagram_get_followers(self, user_id_target: str, amount: int = 50, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Get Instagram user followers"""
        try:
            if not self.logged_in_user:
                return MCPToolResult(success=False, error="Please login to Instagram first")
            
            # Get followers
            followers = self.instagram_client.user_followers(int(user_id_target), amount)
            
            followers_data = []
            for user_id, user_info in followers.items():
                followers_data.append({
                    "user_id": user_id,
                    "username": user_info.username,
                    "full_name": user_info.full_name,
                    "is_private": user_info.is_private,
                    "is_verified": user_info.is_verified
                })
            
            return MCPToolResult(
                success=True,
                data={
                    "followers": followers_data,
                    "count": len(followers_data),
                    "target_user_id": user_id_target
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting Instagram followers: {e}")
            return MCPToolResult(success=False, error=str(e))


def register_tool(registry):
    """Register the Social Media Workflow tool with the registry"""
    tool = SocialMediaWorkflowTool()
    return registry.register_tool(tool)