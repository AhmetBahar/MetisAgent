"""
Google Tool Legacy Interface - Compatible with NativeTool loader
Integrated with MetisAgent3 Storage and User Mapping System
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add MetisAgent3 paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.storage.sqlite_storage import SQLiteUserStorage
from .google_tool import GoogleOAuth2Manager

logger = logging.getLogger(__name__)


class EnhancedGoogleOAuth2Manager(GoogleOAuth2Manager):
    """Enhanced OAuth2 manager with MetisAgent3 storage integration"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: list, storage: SQLiteUserStorage):
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.storage = storage
        
    async def get_user_mapping(self, metis_user_id: str) -> Optional[str]:
        """Get actual Google email from MetisAgent user mapping"""
        try:
            # Try to get mapped Google credentials
            google_credentials = await self.storage.get_user_attribute(metis_user_id, 'google_credentials')
            if google_credentials:
                return google_credentials.get('email')
            
            # Fallback: if user_id looks like email, use it
            if '@' in metis_user_id:
                return metis_user_id
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user mapping for {metis_user_id}: {e}")
            return None
    
    async def store_credentials_secure(self, metis_user_id: str, credentials_data: dict) -> bool:
        """Store OAuth2 credentials in MetisAgent3 secure storage"""
        try:
            google_email = await self.get_user_mapping(metis_user_id)
            if not google_email:
                logger.error(f"No Google email mapping found for user {metis_user_id}")
                return False
            
            # Store credentials with both MetisAgent user_id and Google email mapping
            credential_data = {
                'metis_user_id': metis_user_id,
                'google_email': google_email,
                'oauth2_credentials': credentials_data,
                'stored_at': credentials_data.get('created_at', 'unknown')
            }
            
            await self.storage.set_user_attribute(
                metis_user_id, 
                'google_oauth2_credentials', 
                credential_data,
                encrypt=True
            )
            
            logger.info(f"✅ Stored OAuth2 credentials for {metis_user_id} → {google_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth2 credentials for {metis_user_id}: {e}")
            return False
    
    async def get_credentials_secure(self, metis_user_id: str):
        """Get OAuth2 credentials from MetisAgent3 secure storage"""
        try:
            credential_data = await self.storage.get_user_attribute(metis_user_id, 'google_oauth2_credentials')
            if not credential_data:
                logger.warning(f"No OAuth2 credentials found for user {metis_user_id}")
                return None
            
            oauth2_creds = credential_data.get('oauth2_credentials')
            if not oauth2_creds:
                return None
            
            # Import here to avoid circular imports
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            import google.auth.exceptions
            
            # Create credentials object
            credentials = Credentials(
                token=oauth2_creds.get('token'),
                refresh_token=oauth2_creds.get('refresh_token'),
                id_token=oauth2_creds.get('id_token'),
                token_uri=oauth2_creds.get('token_uri'),
                client_id=oauth2_creds.get('client_id'),
                client_secret=oauth2_creds.get('client_secret'),
                scopes=oauth2_creds.get('scopes')
            )
            
            # Auto-refresh if expired
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    
                    # Save refreshed credentials back to storage
                    updated_oauth2_creds = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'id_token': credentials.id_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes,
                        'expiry': credentials.expiry.isoformat() if credentials.expiry else None
                    }
                    
                    credential_data['oauth2_credentials'] = updated_oauth2_creds
                    await self.storage.set_user_attribute(
                        metis_user_id,
                        'google_oauth2_credentials', 
                        credential_data,
                        encrypt=True
                    )
                    
                    logger.info(f"🔄 Auto-refreshed OAuth2 credentials for {metis_user_id}")
                    
                except google.auth.exceptions.RefreshError:
                    logger.error(f"Failed to refresh OAuth2 credentials for {metis_user_id}")
                    return None
            
            return credentials if credentials and credentials.valid else None
            
        except Exception as e:
            logger.error(f"Failed to get OAuth2 credentials for {metis_user_id}: {e}")
            return None

    async def revoke_credentials_secure(self, metis_user_id: str) -> bool:
        """Revoke and delete OAuth2 credentials from secure storage"""
        try:
            # Get credentials to revoke them with Google first
            credentials = await self.get_credentials_secure(metis_user_id)
            if credentials and credentials.token:
                try:
                    import requests
                    revoke_url = f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
                    requests.post(revoke_url)
                    logger.info(f"🗑️ Revoked OAuth2 token with Google for {metis_user_id}")
                except:
                    pass  # Best effort revoke
            
            # Delete from storage
            await self.storage.delete_user_attribute(metis_user_id, 'google_oauth2_credentials')
            logger.info(f"🗑️ Deleted OAuth2 credentials from storage for {metis_user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke OAuth2 credentials for {metis_user_id}: {e}")
            return False

    async def exchange_code_for_token(self, auth_code: str):
        """Exchange authorization code for OAuth2 tokens and get user info"""
        try:
            from google_auth_oauthlib.flow import Flow
            import google.auth.transport.requests
            
            # Create flow instance
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
                scopes=self.scopes
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for token
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            
            # Get user info from Google to get actual email
            try:
                from googleapiclient.discovery import build
                service = build('oauth2', 'v2', credentials=credentials)
                user_info = service.userinfo().get().execute()
                
                google_email = user_info.get('email')
                google_name = user_info.get('name', '')
                
                logger.info(f"🔍 OAuth2 user info: {google_email} ({google_name})")
                
                # Return credentials with user info
                return credentials, {
                    'email': google_email,
                    'name': google_name,
                    'verified_email': user_info.get('verified_email', False)
                }
                
            except Exception as e:
                logger.error(f"Failed to get user info from Google: {e}")
                # Return credentials without user info
                return credentials, None
            
        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            return None, None
    
    async def create_user_mapping(self, metis_user_id: str, google_email: str, google_name: str = "") -> bool:
        """Create mapping between MetisAgent user and Google account"""
        try:
            mapping_data = {
                'google_email': google_email,
                'google_name': google_name,
                'mapped_at': datetime.now().isoformat(),
                'mapping_type': 'oauth2_flow'
            }
            
            await self.storage.set_user_attribute(
                metis_user_id, 
                'google_user_mapping', 
                mapping_data,
                encrypt=True
            )
            
            logger.info(f"✅ Created user mapping: {metis_user_id} → {google_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user mapping: {e}")
            return False
    
    async def get_user_mapping(self, metis_user_id: str) -> Optional[str]:
        """Get actual Google email from MetisAgent user mapping"""
        try:
            # First check explicit mapping
            mapping = await self.storage.get_user_attribute(metis_user_id, 'google_user_mapping')
            if mapping and mapping.get('google_email'):
                google_email = mapping.get('google_email')
                logger.info(f"🗂️ Found user mapping: {metis_user_id} → {google_email}")
                return google_email
            
            # Legacy: Try to get mapped Google credentials
            google_credentials = await self.storage.get_user_attribute(metis_user_id, 'google_credentials')
            if google_credentials:
                return google_credentials.get('email')
            
            # Fallback: if user_id looks like email and it's Gmail, use it
            if '@gmail.com' in metis_user_id or '@googlemail.com' in metis_user_id:
                logger.info(f"📧 Using Gmail user ID directly: {metis_user_id}")
                return metis_user_id
            
            # No mapping found
            logger.warning(f"⚠️ No Google email mapping found for MetisAgent user: {metis_user_id}")
            return None
                
        except Exception as e:
            logger.error(f"Failed to get user mapping for {metis_user_id}: {e}")
            return None


class GoogleTool:
    """Google Tool with MetisAgent3 storage integration and user mapping"""
    
    def __init__(self):
        # Initialize storage connection
        self.storage = None
        self.oauth_manager = None
        
        # OAuth2 configuration - set defaults first
        self.client_id = "${GOOGLE_CLIENT_ID}"  # Will be loaded from config  
        self.client_secret = "${GOOGLE_CLIENT_SECRET}"  # Will be loaded from config
        self.redirect_uri = "http://localhost:5001/oauth2/google/callback"
        self.scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send", 
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Load configuration from file
        self._load_oauth2_config()
        
        self._initialize_storage()
        
    def _load_oauth2_config(self):
        """Load OAuth2 configuration from config file"""
        try:
            import json
            config_path = Path(__file__).parent.parent.parent / "config" / "google_oauth2_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                if config.get('enabled', False):
                    self.client_id = config.get('client_id', self.client_id)
                    self.client_secret = config.get('client_secret', self.client_secret)
                    self.redirect_uri = config.get('redirect_uri', self.redirect_uri)
                    self.scopes = config.get('scopes', self.scopes)
                    
                    logger.info("✅ Loaded Google OAuth2 configuration from config file")
                else:
                    logger.warning("⚠️ Google OAuth2 is disabled in configuration")
            else:
                logger.warning(f"⚠️ Google OAuth2 config file not found: {config_path}")
                logger.info("💡 Run setup_google_oauth2.py to configure OAuth2 credentials")
                
        except Exception as e:
            logger.error(f"Failed to load OAuth2 configuration: {e}")
        
    def _initialize_storage(self):
        """Initialize storage connection"""
        try:
            self.storage = SQLiteUserStorage()
            
            # Initialize OAuth2 manager with storage integration
            self.oauth_manager = EnhancedGoogleOAuth2Manager(
                self.client_id,
                self.client_secret, 
                self.redirect_uri,
                self.scopes,
                self.storage
            )
            
            logger.info("✅ Google Tool initialized with MetisAgent3 storage integration")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Tool storage: {e}")
            self.storage = None
            self.oauth_manager = None
    
    async def oauth2_management(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """OAuth2 authentication operations with MetisAgent3 storage integration"""
        if not self.oauth_manager:
            return {"success": False, "error": "OAuth manager not initialized"}
        
        action = input_data.get("action")
        user_id = input_data.get("user_id", context.user_id if context else "anonymous")
        
        try:
            if action == "authorize":
                # Generate OAuth2 authorization URL
                auth_url = await self.oauth_manager.get_authorization_url(user_id)
                return {
                    "success": True,
                    "auth_url": auth_url,
                    "message": f"Visit this URL to authorize Google access for {user_id}",
                    "user_id": user_id,
                    "redirect_uri": self.redirect_uri
                }
            
            elif action == "check_status":
                # Check if user has valid OAuth2 credentials
                credentials = await self.oauth_manager.get_credentials_secure(user_id)
                google_email = await self.oauth_manager.get_user_mapping(user_id)
                
                if credentials and credentials.valid:
                    return {
                        "success": True,
                        "authenticated": True,
                        "user": {
                            "email": google_email,
                            "metis_user_id": user_id
                        },
                        "status": "authorized",
                        "expiry": credentials.expiry.isoformat() if credentials.expiry else None
                    }
                else:
                    return {
                        "success": True,
                        "authenticated": False,
                        "status": "not_authorized",
                        "message": "No valid OAuth2 credentials found"
                    }
            
            elif action == "revoke":
                # Revoke OAuth2 credentials
                success = await self.oauth_manager.revoke_credentials_secure(user_id)
                return {
                    "success": success,
                    "message": "OAuth2 credentials revoked successfully" if success else "Failed to revoke credentials"
                }
            
            elif action == "set_user_mapping":
                # Manuel user mapping oluşturma
                google_email = input_data.get("google_email", "").strip()
                google_name = input_data.get("google_name", "").strip()
                
                if not google_email:
                    return {"success": False, "error": "Google email is required"}
                
                if not google_email.endswith(('@gmail.com', '@googlemail.com')):
                    return {"success": False, "error": "Only Gmail addresses are supported"}
                
                success = await self.oauth_manager.create_user_mapping(user_id, google_email, google_name)
                return {
                    "success": success,
                    "message": f"User mapping created: {user_id} → {google_email}" if success else "Failed to create user mapping"
                }
            
            elif action == "get_user_mapping":
                # User mapping durumunu kontrol et
                google_email = await self.oauth_manager.get_user_mapping(user_id)
                mapping = await self.oauth_manager.storage.get_user_attribute(user_id, 'google_user_mapping')
                
                return {
                    "success": True,
                    "google_email": google_email,
                    "mapping_exists": google_email is not None,
                    "mapping_details": mapping if mapping else {}
                }
            
            elif action == "delete_user_mapping":
                # User mapping silme
                try:
                    await self.oauth_manager.storage.delete_user_attribute(user_id, 'google_user_mapping')
                    return {
                        "success": True,
                        "message": f"User mapping deleted for {user_id}"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to delete user mapping: {str(e)}"
                    }
            
            elif action == "store_token":
                # Handle OAuth2 callback token storage
                auth_code = input_data.get("code")
                if not auth_code:
                    return {"success": False, "error": "Authorization code is required"}
                
                # Exchange authorization code for tokens and get user info
                credentials, user_info = await self.oauth_manager.exchange_code_for_token(auth_code)
                if not credentials:
                    return {"success": False, "error": "Failed to exchange authorization code"}
                
                # Create user mapping if we got user info from Google
                if user_info and user_info.get('email'):
                    google_email = user_info.get('email')
                    google_name = user_info.get('name', '')
                    
                    # Create user mapping: MetisAgent user → Google account
                    mapping_success = await self.oauth_manager.create_user_mapping(
                        user_id, google_email, google_name
                    )
                    
                    if not mapping_success:
                        logger.warning(f"Failed to create user mapping for {user_id} → {google_email}")
                else:
                    logger.warning("No user info received from Google OAuth2")
                    google_email = "unknown@gmail.com"
                
                # Store credentials securely
                credentials_data = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'id_token': credentials.id_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes,
                    'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                    'created_at': datetime.now().isoformat()
                }
                
                success = await self.oauth_manager.store_credentials_secure(user_id, credentials_data)
                if success:
                    actual_google_email = await self.oauth_manager.get_user_mapping(user_id)
                    return {
                        "success": True,
                        "message": f"OAuth2 credentials stored successfully",
                        "authenticated": True,
                        "user": {
                            "email": actual_google_email or google_email,
                            "metis_user_id": user_id
                        },
                        "mapping_created": user_info is not None
                    }
                else:
                    return {"success": False, "error": "Failed to store OAuth2 credentials"}
            
            else:
                return {"success": False, "error": f"Unknown OAuth2 action: {action}"}
                
        except Exception as e:
            logger.error(f"OAuth2 management failed: {e}")
            return {"success": False, "error": f"OAuth2 operation failed: {str(e)}"}
    
    async def gmail_operations(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """Gmail operations"""
        try:
            from .handlers.gmail_handler import GmailHandler
        except ImportError:
            return {"success": False, "error": "Gmail handler not available"}
        
        user_id = input_data.get("user_id", context.user_id if context else "anonymous")
        
        try:
            credentials = await self.oauth_manager.get_credentials_secure(user_id)
            if not credentials:
                return {"success": False, "error": f"No valid Gmail credentials for user: {user_id}"}
            
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
            elif action == "get_positional_email":
                result = await handler.get_positional_email(**params)
            else:
                return {"success": False, "error": f"Unknown Gmail action: {action}"}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Gmail operation failed: {e}")
            return {"success": False, "error": f"Gmail operation failed: {str(e)}"}
    
    async def calendar_operations(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """Calendar operations"""
        try:
            from .handlers.calendar_handler import CalendarHandler
        except ImportError:
            return {"success": False, "error": "Calendar handler not available"}
        
        user_id = input_data.get("user_id", context.user_id if context else "anonymous")
        
        try:
            credentials = await self.oauth_manager.get_credentials_secure(user_id)
            if not credentials:
                return {"success": False, "error": f"No valid Calendar credentials for user: {user_id}"}
            
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
                return {"success": False, "error": f"Unknown Calendar action: {action}"}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Calendar operation failed: {e}")
            return {"success": False, "error": f"Calendar operation failed: {str(e)}"}
    
    async def drive_operations(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """Drive operations"""
        try:
            from .handlers.drive_handler import DriveHandler
        except ImportError:
            return {"success": False, "error": "Drive handler not available"}
        
        user_id = input_data.get("user_id", context.user_id if context else "anonymous")
        
        try:
            credentials = await self.oauth_manager.get_credentials_secure(user_id)
            if not credentials:
                return {"success": False, "error": f"No valid Drive credentials for user: {user_id}"}
            
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
                return {"success": False, "error": f"Unknown Drive action: {action}"}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Drive operation failed: {e}")
            return {"success": False, "error": f"Drive operation failed: {str(e)}"}
    
    async def execute(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """Main execute method for tool interface compatibility"""
        capability = input_data.get("capability")
        
        if capability == "oauth2_management":
            return await self.oauth2_management(input_data, context)
        elif capability == "gmail_operations":
            return await self.gmail_operations(input_data, context)
        elif capability == "calendar_operations":
            return await self.calendar_operations(input_data, context)
        elif capability == "drive_operations":
            return await self.drive_operations(input_data, context)
        elif capability == "event_management":
            return await self.event_management(input_data, context)
        else:
            return {"success": False, "error": f"Unknown capability: {capability}"}
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for tool interface compatibility"""
        try:
            # Basic validation - ensure required fields exist
            if not isinstance(input_data, dict):
                return False
            
            capability = input_data.get("capability")
            if not capability:
                return False
            
            # Capability-specific validation
            if capability == "oauth2_management":
                action = input_data.get("action")
                return action in ["authorize", "check_status", "revoke", "store_token", "set_user_mapping", "get_user_mapping", "delete_user_mapping"]
                
            elif capability in ["gmail_operations", "calendar_operations", "drive_operations"]:
                action = input_data.get("action")
                return action is not None
                
            elif capability == "event_management":
                action = input_data.get("action")
                return action in ["create_email_trigger", "create_calendar_trigger", "list_triggers", "start_monitoring", "stop_monitoring"]
            
            # Unknown capability
            return False
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return False
    
    async def event_management(self, input_data: Dict[str, Any], context) -> Dict[str, Any]:
        """Event management operations (placeholder for future automation features)"""
        action = input_data.get("action")
        user_id = input_data.get("user_id", context.user_id if context else "anonymous")
        
        try:
            if action == "list_triggers":
                return {
                    "success": True,
                    "data": {"triggers": []},
                    "message": "Event trigger system not yet implemented"
                }
            
            elif action in ["create_email_trigger", "create_calendar_trigger", "start_monitoring", "stop_monitoring"]:
                return {
                    "success": False,
                    "message": f"Event automation '{action}' not yet implemented"
                }
            
            else:
                return {"success": False, "error": f"Unknown event management action: {action}"}
                
        except Exception as e:
            logger.error(f"Event management failed: {e}")
            return {"success": False, "error": f"Event management operation failed: {str(e)}"}