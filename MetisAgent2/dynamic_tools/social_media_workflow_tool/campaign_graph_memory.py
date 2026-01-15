"""
Campaign Graph Memory - Specialized graph memory for social media campaigns
Hybrid approach: Campaign-specific graph memory + sync with main system memory
"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class CampaignGraphMemory:
    """Specialized graph memory for social media campaigns"""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(os.getcwd(), "campaign_memory_storage")
        os.makedirs(self.base_path, exist_ok=True)
        
        # Campaign entity schema template
        self.campaign_schema = {
            "id": str,
            "name": str,
            "type": "social_media_campaign",
            "attributes": {
                "brand": str,
                "platforms": list,
                "current_step": str,
                "status": str,  # draft, in_progress, in_review, scheduled, completed, cancelled
                "persona_tone": str,
                "created": str,
                "updated": str,
                "deadline": str,
                "user_id": str
            },
            "brief": {
                "purpose": str,
                "target_audience": str,
                "main_message": str,
                "objectives": list,
                "brand_guidelines": dict
            },
            "workflow_steps": [],  # Step history and state
            "assets": [],  # Generated content, visuals, posts
            "approvals": [],  # Approval workflow tracking
            "metrics": [],  # Performance data post-publishing
            "relations": []  # Relations to other entities
        }
    
    def _get_user_campaign_path(self, user_id: str = "default") -> str:
        """Get user-specific campaign storage path"""
        user_dir = os.path.join(self.base_path, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "campaigns.json")
    
    def _load_campaigns(self, user_id: str = "default") -> Dict:
        """Load user campaigns from storage"""
        try:
            campaign_path = self._get_user_campaign_path(user_id)
            if os.path.exists(campaign_path):
                with open(campaign_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"campaigns": [], "relations": []}
        except Exception as e:
            logger.error(f"Error loading campaigns for user {user_id}: {str(e)}")
            return {"campaigns": [], "relations": []}
    
    def _save_campaigns(self, data: Dict, user_id: str = "default"):
        """Save user campaigns to storage"""
        try:
            campaign_path = self._get_user_campaign_path(user_id)
            with open(campaign_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Campaigns saved for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving campaigns for user {user_id}: {str(e)}")
    
    def create_campaign(self, campaign_data: Dict, user_id: str = "default") -> Dict:
        """Create a new social media campaign"""
        try:
            # Generate campaign ID
            campaign_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Build campaign entity based on schema
            campaign = {
                "id": campaign_id,
                "name": campaign_data.get("name", f"Campaign_{timestamp[:10]}"),
                "type": "social_media_campaign",
                "attributes": {
                    "brand": campaign_data.get("brand", ""),
                    "platforms": campaign_data.get("platforms", []),
                    "current_step": "briefing",
                    "status": "draft",
                    "persona_tone": campaign_data.get("persona_tone", "professional"),
                    "created": timestamp,
                    "updated": timestamp,
                    "deadline": campaign_data.get("deadline", ""),
                    "user_id": user_id
                },
                "brief": {
                    "purpose": campaign_data.get("purpose", ""),
                    "target_audience": campaign_data.get("target_audience", ""),
                    "main_message": campaign_data.get("main_message", ""),
                    "objectives": campaign_data.get("objectives", []),
                    "brand_guidelines": campaign_data.get("brand_guidelines", {})
                },
                "workflow_steps": [{
                    "step_id": "briefing_1",
                    "step_name": "briefing",
                    "status": "in_progress",
                    "started": timestamp,
                    "outputs": [],
                    "notes": []
                }],
                "assets": [],
                "approvals": [],
                "metrics": [],
                "relations": []
            }
            
            # Load existing campaigns
            data = self._load_campaigns(user_id)
            data["campaigns"].append(campaign)
            
            # Create user-campaign relation
            user_relation = {
                "from": f"user_{user_id}",
                "to": f"campaign_{campaign_id}",
                "type": "owns",
                "created": timestamp
            }
            data["relations"].append(user_relation)
            
            # Save to storage
            self._save_campaigns(data, user_id)
            
            logger.info(f"Campaign created: {campaign_id} for user {user_id}")
            return {"success": True, "campaign": campaign}
            
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_campaign(self, campaign_id: str, user_id: str = "default") -> Dict:
        """Get specific campaign by ID"""
        try:
            data = self._load_campaigns(user_id)
            campaign = next((c for c in data["campaigns"] if c["id"] == campaign_id), None)
            
            if campaign:
                return {"success": True, "campaign": campaign}
            else:
                return {"success": False, "error": "Campaign not found"}
                
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_campaign_step(self, campaign_id: str, step_data: Dict, user_id: str = "default") -> Dict:
        """Update campaign workflow step"""
        try:
            data = self._load_campaigns(user_id)
            campaign = next((c for c in data["campaigns"] if c["id"] == campaign_id), None)
            
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Update current step
            campaign["attributes"]["current_step"] = step_data.get("step_name", campaign["attributes"]["current_step"])
            campaign["attributes"]["updated"] = datetime.now().isoformat()
            
            # Add step to workflow history
            step_entry = {
                "step_id": step_data.get("step_id", str(uuid.uuid4())[:8]),
                "step_name": step_data.get("step_name", "unknown"),
                "status": step_data.get("status", "completed"),
                "started": step_data.get("started", datetime.now().isoformat()),
                "completed": step_data.get("completed", datetime.now().isoformat()),
                "outputs": step_data.get("outputs", []),
                "notes": step_data.get("notes", [])
            }
            campaign["workflow_steps"].append(step_entry)
            
            # Save changes
            self._save_campaigns(data, user_id)
            
            return {"success": True, "campaign": campaign, "step": step_entry}
            
        except Exception as e:
            logger.error(f"Error updating campaign step: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_campaign_asset(self, campaign_id: str, asset_data: Dict, user_id: str = "default") -> Dict:
        """Add asset (content, visual, post) to campaign"""
        try:
            data = self._load_campaigns(user_id)
            campaign = next((c for c in data["campaigns"] if c["id"] == campaign_id), None)
            
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Create asset entry
            asset = {
                "asset_id": str(uuid.uuid4())[:8],
                "type": asset_data.get("type", "unknown"),  # content, visual, post
                "platform": asset_data.get("platform", ""),
                "content": asset_data.get("content", ""),
                "file_path": asset_data.get("file_path", ""),
                "metadata": asset_data.get("metadata", {}),
                "created": datetime.now().isoformat(),
                "status": asset_data.get("status", "draft")  # draft, approved, scheduled, published
            }
            
            campaign["assets"].append(asset)
            campaign["attributes"]["updated"] = datetime.now().isoformat()
            
            # Save changes
            self._save_campaigns(data, user_id)
            
            return {"success": True, "asset": asset}
            
        except Exception as e:
            logger.error(f"Error adding campaign asset: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def search_campaigns(self, query: str, user_id: str = "default") -> Dict:
        """Search campaigns by name, brand, or content"""
        try:
            data = self._load_campaigns(user_id)
            matching_campaigns = []
            
            query_lower = query.lower()
            
            for campaign in data["campaigns"]:
                # Search in campaign attributes
                if (query_lower in campaign["name"].lower() or
                    query_lower in campaign["attributes"]["brand"].lower() or
                    query_lower in campaign["brief"]["purpose"].lower() or
                    query_lower in campaign["attributes"]["status"].lower()):
                    matching_campaigns.append(campaign)
            
            return {"success": True, "campaigns": matching_campaigns, "count": len(matching_campaigns)}
            
        except Exception as e:
            logger.error(f"Error searching campaigns: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_campaigns(self, user_id: str = "default", status: str = None) -> Dict:
        """Get all campaigns for a user, optionally filtered by status"""
        try:
            data = self._load_campaigns(user_id)
            campaigns = data["campaigns"]
            
            if status:
                campaigns = [c for c in campaigns if c["attributes"]["status"] == status]
            
            return {"success": True, "campaigns": campaigns, "count": len(campaigns)}
            
        except Exception as e:
            logger.error(f"Error getting user campaigns: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_latest_campaign(self, user_id: str = "default") -> Dict:
        """Get user's latest campaign"""
        try:
            data = self._load_campaigns(user_id)
            campaigns = data["campaigns"]
            
            if campaigns:
                # Sort by created date, get latest
                latest = max(campaigns, key=lambda x: x["attributes"]["created"])
                return {"success": True, "campaign": latest}
            else:
                return {"success": False, "error": "No campaigns found"}
                
        except Exception as e:
            logger.error(f"Error getting latest campaign: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def sync_to_system_memory(self, system_memory_tool, campaign_id: str, user_id: str = "default") -> Dict:
        """Sync campaign data to main system graph memory for cross-domain context"""
        try:
            # Get campaign data
            campaign_result = self.get_campaign(campaign_id, user_id)
            if not campaign_result["success"]:
                return campaign_result
            
            campaign = campaign_result["campaign"]
            
            # Create campaign entity for system memory
            campaign_entity = {
                "name": f"campaign_{campaign_id}",
                "entityType": "social_media_campaign",
                "observations": [
                    f"Campaign Name: {campaign['name']}",
                    f"Brand: {campaign['attributes']['brand']}",
                    f"Status: {campaign['attributes']['status']}",
                    f"Current Step: {campaign['attributes']['current_step']}",
                    f"Platforms: {', '.join(campaign['attributes']['platforms'])}",
                    f"Created: {campaign['attributes']['created']}",
                    f"Asset Count: {len(campaign['assets'])}",
                    f"Campaign ID: {campaign_id}"
                ]
            }
            
            # Sync to system memory
            sync_result = system_memory_tool._create_entities([campaign_entity], user_id)
            
            if sync_result.success:
                logger.info(f"Campaign {campaign_id} synced to system memory")
                return {"success": True, "synced": True}
            else:
                return {"success": False, "error": "Failed to sync to system memory"}
                
        except Exception as e:
            logger.error(f"Error syncing to system memory: {str(e)}")
            return {"success": False, "error": str(e)}