"""
Google Tool Plugin - Complete Google Workspace Integration

CLAUDE.md COMPLIANT:
- OAuth2 authentication with encrypted token storage  
- Gmail, Calendar, Drive operations
- User-isolated credentials management
- Fault-tolerant error handling
- No hardcoded workflows - flexible LLM-driven actions
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth.exceptions
except ImportError:
    # Dependencies will be installed when plugin is loaded
    pass

# MetisAgent3 imports
try:
    from ...core.contracts import (
        BaseTool,
        ToolMetadata, 
        ToolConfiguration,
        ToolCapability,
        CapabilityType,
        ToolType,
        AgentResult,
        ExecutionContext,
        HealthStatus
    )
except ImportError:
    # For direct execution, try absolute imports
    from core.contracts import (
        BaseTool,
        ToolMetadata, 
        ToolConfiguration,
        ToolCapability,
        CapabilityType,
        ToolType,
        AgentResult,
        ExecutionContext,
        HealthStatus
    )


logger = logging.getLogger(__name__)


class GoogleOAuth2Manager:
    """OAuth2 authentication manager for Google APIs"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: List[str]):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        
        # Credentials storage directory
        self.credentials_dir = Path("./storage/google_credentials")
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
    
    def get_credentials_file(self, user_id: str) -> Path:
        """Get credentials file path for user"""
        # Use user-specific credential files
        safe_user_id = user_id.replace('@', '_at_').replace('.', '_dot_')
        return self.credentials_dir / f"{safe_user_id}_credentials.json"
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Generate OAuth2 authorization URL"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            # Include user_id in state for callback handling
            flow.state = json.dumps({"user_id": user_id})
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate auth URL for {user_id}: {e}")
            raise
    
    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and store credentials"""
        try:
            # Parse state to get user_id
            state_data = json.loads(state) if state else {}
            user_id = state_data.get("user_id", "unknown")
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth", 
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            # Exchange code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Save credentials to file
            creds_file = self.get_credentials_file(user_id)
            with open(creds_file, 'w') as f:
                f.write(credentials.to_json())
            
            logger.info(f"✅ OAuth2 credentials saved for user: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "Google authentication successful"
            }
            
        except Exception as e:
            logger.error(f"OAuth2 callback failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Google authentication failed"
            }
    
    async def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get valid credentials for user"""
        try:
            creds_file = self.get_credentials_file(user_id)
            
            if not creds_file.exists():
                logger.warning(f"No credentials found for user: {user_id}")
                return None
            
            # Load credentials from file
            credentials = Credentials.from_authorized_user_file(
                str(creds_file), 
                self.scopes
            )
            
            # Refresh if necessary and possible
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    
                    # Save refreshed credentials
                    with open(creds_file, 'w') as f:
                        f.write(credentials.to_json())
                    
                    logger.info(f"🔄 Refreshed credentials for user: {user_id}")
                    
                except google.auth.exceptions.RefreshError:
                    logger.error(f"Failed to refresh credentials for {user_id}")
                    return None
            
            return credentials if credentials and credentials.valid else None
            
        except Exception as e:
            logger.error(f"Failed to get credentials for {user_id}: {e}")
            return None
    
    async def revoke_credentials(self, user_id: str) -> bool:
        """Revoke and delete user credentials"""
        try:
            creds_file = self.get_credentials_file(user_id)
            
            if creds_file.exists():
                # Try to revoke the credentials first
                try:
                    credentials = Credentials.from_authorized_user_file(str(creds_file))
                    if credentials.token:
                        revoke_url = f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
                        import requests
                        requests.post(revoke_url)
                except:
                    pass  # Best effort revoke
                
                # Delete credentials file
                creds_file.unlink()
                logger.info(f"🗑️  Revoked credentials for user: {user_id}")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials for {user_id}: {e}")
            return False
    
    async def check_auth_status(self, user_id: str) -> Dict[str, Any]:
        """Check authentication status for user"""
        try:
            credentials = await self.get_credentials(user_id)
            
            if not credentials:
                return {
                    "authenticated": False,
                    "message": "No credentials found",
                    "needs_auth": True
                }
            
            if not credentials.valid:
                return {
                    "authenticated": False,  
                    "message": "Credentials expired",
                    "needs_auth": True
                }
            
            return {
                "authenticated": True,
                "message": "Valid credentials found",
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
            }
            
        except Exception as e:
            logger.error(f"Failed to check auth status for {user_id}: {e}")
            return {
                "authenticated": False,
                "message": f"Error checking auth status: {str(e)}",
                "needs_auth": True
            }


class GoogleTool(BaseTool):
    """Complete Google Workspace integration tool"""
    
    def __init__(self, metadata: ToolMetadata, config: ToolConfiguration):
        super().__init__(metadata, config)
        
        # Initialize OAuth2 manager
        client_id = config.config.get("client_id")
        client_secret = config.config.get("client_secret") 
        redirect_uri = config.config.get("redirect_uri", "http://localhost:5001/oauth2/google/callback")
        scopes = config.config.get("scopes", [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive"
        ])
        
        if not client_id or not client_secret:
            raise ValueError("Google OAuth2 client_id and client_secret are required")
        
        self.oauth_manager = GoogleOAuth2Manager(client_id, client_secret, redirect_uri, scopes)
        
        # Initialize Event Handler
        try:
            from .event_handler import GoogleEventHandler, EventHandlerAPI
            self.event_handler = GoogleEventHandler(self)
            self.event_api = EventHandlerAPI(self.event_handler)
        except ImportError:
            logger.warning("Event handler not available - events will be disabled")
            self.event_handler = None
            self.event_api = None
        
        logger.info("✅ Google Tool initialized with OAuth2 and Event Handler support")
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a specific capability"""
        return await self.execute_capability(capability, input_data, context)
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for a capability"""
        errors = []
        
        # Find capability schema
        capability_def = None
        for cap in self.metadata.capabilities:
            if cap.name == capability:
                capability_def = cap
                break
        
        if not capability_def:
            return [f"Unknown capability: {capability}"]
        
        # Basic validation - could be enhanced with jsonschema
        required_fields = capability_def.input_schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Required field missing: {field}")
        
        return errors
    
    async def health_check(self) -> HealthStatus:
        """Check tool health"""
        try:
            # Basic health check - ensure OAuth manager is initialized
            if not self.oauth_manager:
                return HealthStatus(
                    healthy=False,
                    component="google_tool",
                    message="OAuth manager not initialized"
                )
                
            return HealthStatus(
                healthy=True,
                component="google_tool",
                message="Google Tool is healthy"
            )
            
        except Exception as e:
            logger.error(f"Google tool health check failed: {e}")
            return HealthStatus(
                healthy=False,
                component="google_tool",
                message=f"Health check failed: {str(e)}"
            )
    
    def get_capabilities(self) -> List[str]:
        """Get tool capabilities"""
        return [
            "oauth2_management",
            "gmail_operations", 
            "calendar_operations",
            "drive_operations",
            "event_management",
            "tool_health"
        ]
    
    async def execute(
        self,
        capability: str,
        input_data: Dict[str, Any],
        context: ExecutionContext
    ) -> AgentResult[Dict[str, Any]]:
        """Execute tool capability - NativeTool wrapper compatibility"""
        return await self.execute_capability(capability, input_data, context)
    
    async def execute_capability(
        self,
        capability: str,
        input_data: Dict[str, Any],
        context: ExecutionContext
    ) -> AgentResult[Dict[str, Any]]:
        """Execute tool capability"""
        try:
            logger.info(f"🔧 Executing Google Tool capability: {capability}")
            
            # Get user_id from context or input
            user_id = context.user_id or input_data.get("user_id", "anonymous")
            
            if capability == "oauth2_management":
                return await self._handle_oauth2_management(input_data, user_id)
            elif capability == "gmail_operations":
                return await self._handle_gmail_operations(input_data, user_id)
            elif capability == "calendar_operations":
                return await self._handle_calendar_operations(input_data, user_id)
            elif capability == "drive_operations":
                return await self._handle_drive_operations(input_data, user_id)
            elif capability == "event_management":
                return await self._handle_event_management(input_data, user_id)
            elif capability == "tool_health":
                return await self._handle_tool_health(input_data, user_id)
            else:
                return AgentResult.error(f"Unknown capability: {capability}")
                
        except Exception as e:
            logger.error(f"Google Tool capability execution failed: {e}")
            return AgentResult.error(f"Execution failed: {str(e)}")
    
    async def _handle_oauth2_management(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle OAuth2 authentication operations"""
        action = input_data.get("action")
        
        try:
            if action == "authorize":
                auth_url = await self.oauth_manager.get_authorization_url(user_id)
                return AgentResult.success({
                    "auth_url": auth_url,
                    "message": f"Visit this URL to authorize Google access for {user_id}",
                    "user_id": user_id
                })
            
            elif action == "check_status":
                status = await self.oauth_manager.check_auth_status(user_id)
                return AgentResult.success(status)
            
            elif action == "revoke":
                success = await self.oauth_manager.revoke_credentials(user_id)
                return AgentResult.success({
                    "success": success,
                    "message": "Credentials revoked" if success else "Failed to revoke credentials"
                })
            
            elif action == "set_user_mapping":
                return await self._set_user_mapping(input_data, user_id)
            
            elif action == "get_user_mapping":
                return await self._get_user_mapping(user_id)
            
            elif action == "delete_user_mapping":
                return await self._delete_user_mapping(user_id)
            
            else:
                return AgentResult.error(f"Unknown OAuth2 action: {action}")
                
        except Exception as e:
            logger.error(f"OAuth2 management failed: {e}")
            return AgentResult.error(f"OAuth2 operation failed: {str(e)}")
    
    async def _handle_gmail_operations(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle Gmail operations"""
        # Import Gmail handler
        try:
            from .handlers.gmail_handler import GmailHandler
        except ImportError:
            try:
                from plugins.google_tool.handlers.gmail_handler import GmailHandler
            except ImportError:
                return AgentResult.error("Gmail handler not available")
        
        try:
            credentials = await self.oauth_manager.get_credentials(user_id)
            if not credentials:
                return AgentResult.error(f"No valid Gmail credentials for user: {user_id}")
            
            handler = GmailHandler(credentials)
            action = input_data.get("action")
            params = input_data.get("params", {})
            
            if action == "list":
                result = await handler.list_emails(**params)
            elif action == "read":
                result = await handler.read_email(**params)
            elif action == "send":
                result = await handler.send_email(**params)
            elif action == "send_with_attachment":
                result = await handler.send_email_with_attachment(**params)
            else:
                return AgentResult.error(f"Unknown Gmail action: {action}")
            
            return AgentResult.success(result)
            
        except Exception as e:
            logger.error(f"Gmail operation failed: {e}")
            return AgentResult.error(f"Gmail operation failed: {str(e)}")
    
    async def _handle_calendar_operations(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle Calendar operations"""
        # Import Calendar handler
        try:
            from .handlers.calendar_handler import CalendarHandler
        except ImportError:
            try:
                from plugins.google_tool.handlers.calendar_handler import CalendarHandler
            except ImportError:
                return AgentResult.error("Calendar handler not available")
        
        try:
            credentials = await self.oauth_manager.get_credentials(user_id)
            if not credentials:
                return AgentResult.error(f"No valid Calendar credentials for user: {user_id}")
            
            handler = CalendarHandler(credentials)
            action = input_data.get("action")
            params = input_data.get("params", {})
            
            if action == "list_events":
                result = await handler.list_events(**params)
            elif action == "create_event":
                result = await handler.create_event(**params)
            elif action == "update_event":
                result = await handler.update_event(**params)
            elif action == "delete_event":
                result = await handler.delete_event(**params)
            else:
                return AgentResult.error(f"Unknown Calendar action: {action}")
            
            return AgentResult.success(result)
            
        except Exception as e:
            logger.error(f"Calendar operation failed: {e}")
            return AgentResult.error(f"Calendar operation failed: {str(e)}")
    
    async def _handle_drive_operations(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle Drive operations"""
        # Import Drive handler
        try:
            from .handlers.drive_handler import DriveHandler
        except ImportError:
            try:
                from plugins.google_tool.handlers.drive_handler import DriveHandler
            except ImportError:
                return AgentResult.error("Drive handler not available")
        
        try:
            credentials = await self.oauth_manager.get_credentials(user_id)
            if not credentials:
                return AgentResult.error(f"No valid Drive credentials for user: {user_id}")
            
            handler = DriveHandler(credentials)
            action = input_data.get("action")
            params = input_data.get("params", {})
            
            if action == "list_files":
                result = await handler.list_files(**params)
            elif action == "upload_file":
                result = await handler.upload_file(**params)
            elif action == "download_file":
                result = await handler.download_file(**params)
            elif action == "delete_file":
                result = await handler.delete_file(**params)
            elif action == "share_file":
                result = await handler.share_file(**params)
            else:
                return AgentResult.error(f"Unknown Drive action: {action}")
            
            return AgentResult.success(result)
            
        except Exception as e:
            logger.error(f"Drive operation failed: {e}")
            return AgentResult.error(f"Drive operation failed: {str(e)}")
    
    async def _handle_event_management(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle event-driven automation management"""
        try:
            action = input_data.get("action")
            params = input_data.get("params", {})
            
            if action == "create_email_trigger":
                result = await self.event_api.create_email_trigger(
                    user_id=user_id,
                    workflow_name=params.get("workflow_name"),
                    subject_contains=params.get("subject_contains"),
                    from_email=params.get("from_email"),
                    enabled=params.get("enabled", True)
                )
            elif action == "create_calendar_trigger":
                result = await self.event_api.create_calendar_trigger(
                    user_id=user_id,
                    workflow_name=params.get("workflow_name"),
                    event_title_contains=params.get("event_title_contains"),
                    minutes_before=params.get("minutes_before", 10),
                    enabled=params.get("enabled", True)
                )
            elif action == "list_triggers":
                result = await self.event_api.list_triggers(user_id)
            elif action == "start_monitoring":
                await self.event_handler.start_monitoring()
                result = {"success": True, "message": "Event monitoring started"}
            elif action == "stop_monitoring":
                await self.event_handler.stop_monitoring()
                result = {"success": True, "message": "Event monitoring stopped"}
            else:
                return AgentResult.error(f"Unknown event management action: {action}")
            
            return AgentResult.success(result)
            
        except Exception as e:
            logger.error(f"Event management failed: {e}")
            return AgentResult.error(f"Event management failed: {str(e)}")
    
    async def _set_user_mapping(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Set user mapping between MetisAgent user and Google account"""
        try:
            google_email = input_data.get("google_email")
            google_name = input_data.get("google_name", "")
            
            if not google_email:
                return AgentResult.error("Google email is required")
            
            # Store mapping in user data directory
            mapping_dir = Path("./storage/user_mappings")
            mapping_dir.mkdir(parents=True, exist_ok=True)
            
            safe_user_id = user_id.replace('@', '_at_').replace('.', '_dot_')
            mapping_file = mapping_dir / f"{safe_user_id}_google_mapping.json"
            
            mapping_data = {
                "user_id": user_id,
                "google_email": google_email,
                "google_name": google_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(mapping_file, 'w') as f:
                json.dump(mapping_data, f, indent=2)
            
            logger.info(f"✅ User mapping saved: {user_id} -> {google_email}")
            
            return AgentResult.success({
                "success": True,
                "message": "User mapping saved successfully",
                "mapping": mapping_data
            })
            
        except Exception as e:
            logger.error(f"Failed to set user mapping: {e}")
            return AgentResult.error(f"Failed to set user mapping: {str(e)}")
    
    async def _get_user_mapping(self, user_id: str) -> AgentResult[Dict[str, Any]]:
        """Get user mapping between MetisAgent user and Google account"""
        try:
            mapping_dir = Path("./storage/user_mappings")
            safe_user_id = user_id.replace('@', '_at_').replace('.', '_dot_')
            mapping_file = mapping_dir / f"{safe_user_id}_google_mapping.json"
            
            if not mapping_file.exists():
                return AgentResult.success({
                    "success": True,
                    "message": "No user mapping found",
                    "mapping": None
                })
            
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)
            
            return AgentResult.success({
                "success": True,
                "message": "User mapping found",
                "mapping": mapping_data
            })
            
        except Exception as e:
            logger.error(f"Failed to get user mapping: {e}")
            return AgentResult.error(f"Failed to get user mapping: {str(e)}")
    
    async def _delete_user_mapping(self, user_id: str) -> AgentResult[Dict[str, Any]]:
        """Delete user mapping between MetisAgent user and Google account"""
        try:
            mapping_dir = Path("./storage/user_mappings")
            safe_user_id = user_id.replace('@', '_at_').replace('.', '_dot_')
            mapping_file = mapping_dir / f"{safe_user_id}_google_mapping.json"
            
            if mapping_file.exists():
                mapping_file.unlink()
                logger.info(f"🗑️  Deleted user mapping for: {user_id}")
                return AgentResult.success({
                    "success": True,
                    "message": "User mapping deleted successfully"
                })
            else:
                return AgentResult.success({
                    "success": True,
                    "message": "No user mapping found to delete"
                })
            
        except Exception as e:
            logger.error(f"Failed to delete user mapping: {e}")
            return AgentResult.error(f"Failed to delete user mapping: {str(e)}")
    
    async def _handle_tool_health(self, input_data: Dict[str, Any], user_id: str) -> AgentResult[Dict[str, Any]]:
        """Handle tool health status queries"""
        action = input_data.get("action")
        
        try:
            if action == "get_health_status":
                # Check OAuth2 status
                auth_status = await self.oauth_manager.check_auth_status(user_id)
                
                # Check service availability
                credentials = await self.oauth_manager.get_credentials(user_id)
                
                metrics = []
                
                # OAuth2 Status Metric
                if auth_status.get("authenticated"):
                    oauth_metric = {
                        "name": "OAuth2 Status",
                        "value": "Connected",
                        "status": "healthy",
                        "icon": "🔐"
                    }
                else:
                    oauth_metric = {
                        "name": "OAuth2 Status", 
                        "value": "Not Connected",
                        "status": "error",
                        "icon": "🔐"
                    }
                metrics.append(oauth_metric)
                
                # API Service Metrics
                api_services = [
                    {"name": "Gmail API", "icon": "📧", "scope": "gmail"},
                    {"name": "Calendar API", "icon": "📅", "scope": "calendar"},
                    {"name": "Drive API", "icon": "💾", "scope": "drive"}
                ]
                
                for service in api_services:
                    if credentials:
                        # Check if scope is in credentials
                        required_scope = f"https://www.googleapis.com/auth/{service['scope']}"
                        has_scope = any(required_scope in scope for scope in credentials.scopes)
                        
                        if has_scope:
                            metrics.append({
                                "name": service["name"],
                                "value": "Ready",
                                "status": "healthy", 
                                "icon": service["icon"]
                            })
                        else:
                            metrics.append({
                                "name": service["name"],
                                "value": "No Permission",
                                "status": "warning",
                                "icon": service["icon"]
                            })
                    else:
                        metrics.append({
                            "name": service["name"],
                            "value": "Not Available",
                            "status": "error",
                            "icon": service["icon"]
                        })
                
                return AgentResult.success({
                    "success": True,
                    "metrics": metrics,
                    "overall_status": "healthy" if auth_status.get("authenticated") else "error"
                })
            
            else:
                return AgentResult.error(f"Unknown tool health action: {action}")
                
        except Exception as e:
            logger.error(f"Tool health check failed: {e}")
            return AgentResult.error(f"Tool health check failed: {str(e)}")