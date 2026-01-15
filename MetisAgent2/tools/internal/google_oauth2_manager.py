"""
Google OAuth2 Manager Tool - Gmail API erişimi için OAuth2 yönetimi
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app.mcp_core import MCPTool, MCPToolResult
from .user_storage import get_user_storage
from .settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

class GoogleOAuth2Manager(MCPTool):
    """Google OAuth2 ve Gmail API yönetimi"""
    
    def __init__(self):
        super().__init__(
            name="google_oauth2_manager",
            description="Google OAuth2 authentication and Gmail API access",
            version="1.0.0"
        )
        
        # Register actions
        self.register_action(
            "gmail_list_messages",
            self._gmail_list_messages,
            required_params=[],
            optional_params=["user_id", "max_results", "query"]
        )
        
        self.register_action(
            "gmail_get_message",
            self._gmail_get_message,
            required_params=["message_id"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "gmail_send_message",
            self._gmail_send_message,
            required_params=["to", "subject", "body"],
            optional_params=["user_id", "cc", "bcc"]
        )
        
        self.register_action(
            "gmail_send_message_with_attachment",
            self._gmail_send_message_with_attachment,
            required_params=["to", "subject", "body", "attachment_path"],
            optional_params=["user_id", "cc", "bcc", "attachment_name"]
        )
        
        self.register_action(
            "get_auth_url",
            self._get_auth_url,
            required_params=[],
            optional_params=["user_id", "services"]
        )
        
        self.register_action(
            "exchange_code",
            self._exchange_code,
            required_params=["code"],
            optional_params=["state", "user_id"]
        )
        
        self.register_action(
            "get_oauth2_status",
            self._get_oauth2_status,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "refresh_token",
            self._refresh_token,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "revoke_token",
            self._revoke_token,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "get_user_token",
            self._get_user_token,
            required_params=["user_id"],
            optional_params=[]
        )
        
        self.register_action(
            "list_authorized_users",
            self._list_authorized_users,
            required_params=[],
            optional_params=[]
        )
        
        # Google Calendar API actions
        self.register_action(
            "calendar_list_calendars",
            self._calendar_list_calendars,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "calendar_list_events",
            self._calendar_list_events,
            required_params=[],
            optional_params=["user_id", "calendar_id", "max_results", "time_min", "time_max"]
        )
        
        self.register_action(
            "calendar_create_event",
            self._calendar_create_event,
            required_params=["summary", "start_time", "end_time"],
            optional_params=["user_id", "calendar_id", "description", "location", "attendees"]
        )
        
        self.register_action(
            "calendar_update_event",
            self._calendar_update_event,
            required_params=["event_id"],
            optional_params=["user_id", "calendar_id", "summary", "start_time", "end_time", "description", "location"]
        )
        
        self.register_action(
            "calendar_delete_event",
            self._calendar_delete_event,
            required_params=["event_id"],
            optional_params=["user_id", "calendar_id"]
        )
    
    def _get_user_gmail_mapping(self, user_id: str) -> Optional[str]:
        """Get Gmail account mapped to user ID"""
        try:
            storage = get_user_storage()
            # Try to get Gmail mapping from user storage
            mapping = storage.get_user_mapping(user_id, 'google')
            if mapping:
                return mapping
            
            # Fallback: check for stored Gmail credentials
            gmail_creds = storage.get_api_key(user_id, 'gmail')
            if gmail_creds and isinstance(gmail_creds, dict):
                return gmail_creds.get('email') or gmail_creds.get('user_email')
            
            return None
        except Exception as e:
            logger.error(f"Error getting Gmail mapping for {user_id}: {e}")
            return None
    
    def _is_token_expired(self, oauth_token: Dict[str, Any]) -> bool:
        """Check if OAuth token is expired or will expire soon (within 5 minutes)"""
        try:
            expires_at = oauth_token.get('expires_at')
            expires_in = oauth_token.get('expires_in')
            
            if expires_at:
                # If expires_at is a timestamp
                if isinstance(expires_at, (int, float)):
                    current_time = time.time()
                    # Token expires soon (within 5 minutes)
                    return expires_at <= (current_time + 300)
                # If expires_at is a datetime string
                elif isinstance(expires_at, str):
                    try:
                        exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        current_dt = datetime.now()
                        # Token expires soon (within 5 minutes)
                        return exp_dt <= (current_dt + timedelta(minutes=5))
                    except:
                        pass
            
            # Fallback: check if token was created more than 55 minutes ago
            # (assuming 1 hour expiry with 5 minute buffer)
            created_at = oauth_token.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at)
                        current_dt = datetime.now()
                        age = current_dt - created_dt
                        return age > timedelta(minutes=55)
                except:
                    pass
            
            # If no expiry info, assume token might be expired
            logger.warning("No token expiry information available, assuming token needs refresh")
            return True
            
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True
    
    def _ensure_valid_token(self, user_id: str) -> bool:
        """Ensure user has a valid OAuth token, refresh if needed"""
        try:
            settings_manager = get_settings_manager()
            
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                logger.warning(f"No Gmail mapping found for user {user_id}")
                return False
            
            # Get OAuth token from Google email
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            if not oauth_token:
                logger.warning(f"No OAuth token found for Gmail user {gmail_user}")
                return False
            
            # Check if token is expired or will expire soon
            if self._is_token_expired(oauth_token):
                logger.info(f"Token expired for user {user_id}, attempting refresh...")
                
                # Attempt to refresh token using Gmail user ID
                refresh_result = self._refresh_token(gmail_user)
                if refresh_result.success:
                    logger.info(f"Token successfully refreshed for user {user_id}")
                    return True
                else:
                    logger.error(f"Token refresh failed for user {user_id}: {refresh_result.error}")
                    return False
            
            # Token is still valid
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring valid token for user {user_id}: {e}")
            return False
    
    def _gmail_list_messages(self, user_id: str = None, max_results: int = 10, query: str = None, 
                            userId: str = None, maxResults: int = None, auto_subject_fetch: bool = True, **kwargs) -> MCPToolResult:
        """List Gmail messages"""
        try:
            # PARAMETER MAPPING: Handle both Python and Google API parameter formats
            if userId and not user_id:
                user_id = userId
                logger.info(f"PARAM MAP: Converted 'userId' to 'user_id': {user_id}")
            
            if maxResults and not (max_results and max_results != 10):  # 10 is default
                max_results = maxResults
                logger.info(f"PARAM MAP: Converted 'maxResults' to 'max_results': {max_results}")
            
            if not user_id:
                return MCPToolResult(
                    success=False, 
                    error="No user context available. User must be authenticated."
                )
            
            # OAuth2 Authentication Check with Auto-Refresh  
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"OAuth2 token expired and refresh failed for user {user_id}. Please re-authenticate with Google at http://localhost:5001/oauth2/google/start"
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping for authenticated user first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google') if gmail_user else None
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}. Please complete OAuth2 setup."
                )
            
            logger.info(f"Gmail API: Authenticated user {user_id} -> {gmail_user}")
            
            # Use the OAuth2 API endpoint
            import requests
            
            list_url = "http://localhost:5001/oauth2/google/gmail/messages"
            params = {
                'user_id': gmail_user,
                'max_results': max_results
            }
            if query:
                params['query'] = query
            
            response = requests.get(list_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Unknown error'))
            
            # Auto-fetch subjects if enabled and max_results is small (2-5) to avoid infinite loops
            data = result.get('data', {})
            if (auto_subject_fetch and 2 <= max_results <= 5 and 
                data.get('messages', {}).get('messages') and 
                len(data['messages']['messages']) > 0):
                
                logger.info(f"AUTO SUBJECT FETCH - Detected subject request with {max_results} messages")
                
                # Get subjects for all messages
                subjects = []
                messages = data['messages']['messages'][:max_results]
                
                for msg in messages:
                    message_id = msg.get('id')
                    if message_id:
                        try:
                            # Get message details with metadata format (disable auto-fetch to prevent recursion)
                            get_url = f"http://localhost:5001/oauth2/google/gmail/messages/{message_id}"
                            get_params = {'user_id': gmail_user, 'format': 'metadata', 'auto_subject_fetch': 'false'}
                            
                            msg_response = requests.get(get_url, params=get_params)
                            msg_response.raise_for_status()
                            msg_result = msg_response.json()
                            
                            if msg_result.get('success') and msg_result.get('data', {}).get('message'):
                                message = msg_result['data']['message']
                                # Extract subject from headers
                                if 'payload' in message and 'headers' in message['payload']:
                                    for header in message['payload']['headers']:
                                        if header.get('name') == 'Subject':
                                            subject = header.get('value', '').strip()
                                            if subject:
                                                subjects.append(subject)
                                                logger.info(f"AUTO SUBJECT FETCH - Found: {subject}")
                                            break
                        except Exception as e:
                            logger.error(f"Error fetching subject for message {message_id}: {e}")
                
                # Add subjects to response data
                if subjects:
                    data['extracted_subjects'] = subjects
                    data['subject_count'] = len(subjects)
                    logger.info(f"AUTO SUBJECT FETCH - Extracted {len(subjects)} subjects")
            
            return MCPToolResult(success=True, data=data)
            
        except Exception as e:
            logger.error(f"Error listing Gmail messages: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _gmail_get_message(self, message_id: str, user_id: str = None, 
                          userId: str = None, id: str = None, **kwargs) -> MCPToolResult:
        """Get Gmail message details"""
        try:
            # PARAMETER MAPPING: Handle both Python and Google API parameter formats
            if userId and not user_id:
                user_id = userId
                logger.info(f"PARAM MAP: Converted 'userId' to 'user_id': {user_id}")
            
            if id and not message_id:
                message_id = id
                logger.info(f"PARAM MAP: Converted 'id' to 'message_id': {message_id}")
            
            if not user_id:
                return MCPToolResult(
                    success=False, 
                    error="No user context available. User must be authenticated."
                )
            
            # OAuth2 Authentication Check with Auto-Refresh  
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"OAuth2 token expired and refresh failed for user {user_id}. Please re-authenticate with Google at http://localhost:5001/oauth2/google/start"
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping for authenticated user first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}. Please complete OAuth2 setup."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            logger.info(f"Gmail API: Authenticated user {user_id} -> {gmail_user}")
            
            # Use the OAuth2 API endpoint
            import requests
            
            get_url = f"http://localhost:5001/oauth2/google/gmail/messages/{message_id}"
            params = {'user_id': gmail_user, 'format': 'metadata'}
            
            response = requests.get(get_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Unknown error'))
            
            return MCPToolResult(success=True, data=result.get('data', {}))
            
        except Exception as e:
            logger.error(f"Error getting Gmail message {message_id}: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _gmail_send_message(self, to: str, subject: str, body: str, 
                           user_id: str = None, cc: str = None, bcc: str = None) -> MCPToolResult:
        """Send email using Gmail API"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping for authenticated user first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Create email message
            import base64
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = gmail_user
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Call Gmail API
            import requests
            
            headers = {
                'Authorization': f'Bearer {oauth_token["access_token"]}',
                'Content-Type': 'application/json'
            }
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            
            payload = {'raw': raw_message}
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            return MCPToolResult(
                success=True,
                data={
                    'message_id': result.get('id'),
                    'thread_id': result.get('threadId'),
                    'recipient': to,
                    'subject': subject,
                    'from': gmail_user,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Gmail send message error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _gmail_send_message_with_attachment(self, to: str, subject: str, body: str, 
                                          attachment_path: str, user_id: str = None, 
                                          cc: str = None, bcc: str = None, 
                                          attachment_name: str = None) -> MCPToolResult:
        """Send email with attachment using Gmail API"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping for authenticated user first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Check if attachment file exists
            import os
            if not os.path.exists(attachment_path):
                return MCPToolResult(
                    success=False, 
                    error=f"Attachment file not found: {attachment_path}"
                )
            
            # Create email message with attachment
            import base64
            import mimetypes
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = gmail_user
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Add attachment
            if not attachment_name:
                attachment_name = os.path.basename(attachment_path)
            
            # Guess the content type based on the file's extension
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            
            main_type, sub_type = ctype.split('/', 1)
            
            with open(attachment_path, 'rb') as fp:
                attachment_data = fp.read()
                
                if main_type == 'text':
                    attachment = MIMEText(attachment_data.decode('utf-8'), _subtype=sub_type)
                elif main_type == 'image':
                    from email.mime.image import MIMEImage
                    attachment = MIMEImage(attachment_data, _subtype=sub_type)
                elif main_type == 'audio':
                    from email.mime.audio import MIMEAudio
                    attachment = MIMEAudio(attachment_data, _subtype=sub_type)
                else:
                    attachment = MIMEBase(main_type, sub_type)
                    attachment.set_payload(attachment_data)
                    encoders.encode_base64(attachment)
                
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_name}"'
                )
                message.attach(attachment)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Call Gmail API
            import requests
            
            headers = {
                'Authorization': f'Bearer {oauth_token["access_token"]}',
                'Content-Type': 'application/json'
            }
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            
            payload = {'raw': raw_message}
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            return MCPToolResult(
                success=True,
                data={
                    'message_id': result.get('id'),
                    'thread_id': result.get('threadId'),
                    'recipient': to,
                    'subject': subject,
                    'attachment': attachment_name,
                    'attachment_size': len(attachment_data),
                    'from': gmail_user,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Gmail send message with attachment error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_auth_url(self, user_id: str = None, services: List[str] = None, **kwargs) -> MCPToolResult:
        """Get OAuth2 authorization URL"""
        try:
            # Get user_id from kwargs if not provided directly
            if not user_id:
                user_id = kwargs.get('user_id')
            
            if not user_id:
                return MCPToolResult(
                    success=False, 
                    error="No user context available. User must be authenticated."
                )
            
            # Check if user already has OAuth2 token
            storage = get_user_storage()
            # Get Gmail mapping first
            gmail_user = storage.get_user_mapping(user_id, 'google')
            existing_token = None
            if gmail_user:
                existing_token = storage.get_oauth_token(gmail_user, 'google')
            
            if existing_token and existing_token.get('access_token'):
                # Verify token is still valid by checking expiry
                if not self._is_token_expired(existing_token):
                    logger.info(f"User {user_id} already authenticated with Google OAuth2")
                    return MCPToolResult(
                        success=True,
                        data={
                            'auth_url': None,
                            'state': None,  # No state needed for already authenticated users
                            'message': 'User is already authenticated with Google OAuth2',
                            'user_id': user_id,
                            'services': services or ['gmail'],
                            'already_authenticated': True,
                            'expires_in': 0
                        }
                    )
                else:
                    logger.info(f"User {user_id} has expired token, need fresh authorization")
            
            # Default services if not provided
            if not services:
                services = ['gmail']
            
            # Generate Google OAuth2 URL directly
            import urllib.parse
            import uuid
            
            # OAuth2 credentials from settings_manager
            settings_manager = get_settings_manager()
            google_creds = settings_manager.get_google_client_credentials()
            
            if not google_creds:
                return MCPToolResult(
                    success=False,
                    error="Google OAuth2 client credentials not configured. Please setup client_id and client_secret first."
                )
            
            client_id = google_creds.get('client_id')
            client_secret = google_creds.get('client_secret')
            
            if not client_id or not client_secret:
                return MCPToolResult(
                    success=False,
                    error=f"Google OAuth2 credentials incomplete. client_id: {bool(client_id)}, client_secret: {bool(client_secret)}"
                )
            
            redirect_uri = "http://localhost:5001/oauth2/google/callback"
            
            # Define scopes based on services
            scopes = []
            if 'gmail' in services:
                scopes.extend([
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send'
                ])
            if 'calendar' in services:
                scopes.extend([
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events'
                ])
            if 'drive' in services:
                scopes.extend([
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file'
                ])
            if 'basic' in services:
                scopes.extend([
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ])
            
            # Default scopes if none specified (include Drive and Calendar)
            if not scopes:
                scopes = [
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events'
                ]
            
            # Generate state parameter
            state = str(uuid.uuid4())
            logger.info(f"Generated OAuth2 state: {state} for user: {user_id}")
            
            # Get existing Gmail mapping if any
            storage = get_user_storage()
            gmail_user = storage.get_user_mapping(user_id, 'google')
            
            # Store state under Gmail user if mapping exists, otherwise system user
            state_storage_user = gmail_user if gmail_user else user_id
            
            # Store state temporarily in user properties (for validation in callback) 
            temp_state_data = {
                'system_user_id': user_id,  # Always keep system user reference
                'gmail_user': gmail_user,   # Keep Gmail mapping if exists
                'services': services,
                'created_at': time.time(),
                'expires_at': time.time() + 600  # 10 minutes
            }
            # Use storage directly to avoid MCP action issues
            storage.set_property(state_storage_user, f"oauth_state_{state}", json.dumps(temp_state_data))
            logger.info(f"OAuth state stored under: {state_storage_user} (system: {user_id}, gmail: {gmail_user})")
            
            # Build OAuth2 URL
            auth_params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'scope': ' '.join(scopes),
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent',
                'state': state
            }
            
            auth_url = 'https://accounts.google.com/o/oauth2/auth?' + urllib.parse.urlencode(auth_params)
            logger.info(f"Generated OAuth2 URL with state: {state}")
            
            return MCPToolResult(
                success=True, 
                data={
                    'auth_url': auth_url,
                    'state': state,
                    'services': services,
                    'user_id': user_id,
                    'expires_in': 600
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting auth URL: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return MCPToolResult(success=False, error=str(e))
    
    def _exchange_code(self, code: str, state: str = None, user_id: str = None) -> MCPToolResult:
        """Exchange authorization code for tokens and store them"""
        try:
            import requests
            import json
            from urllib.parse import parse_qs
            
            logger.info(f"OAuth2 code exchange: code={code[:10]}..., state={state}, user_id={user_id}")
            
            # State validation
            if not state:
                return MCPToolResult(success=False, error="Missing state parameter for OAuth2 security")
            
            # OAuth2 credentials from settings_manager
            settings_manager = get_settings_manager()
            
            # Validate state parameter - we need to find which user has this state
            state_data = None
            actual_user_id = None
            
            # Check all users for this state (since we don't know which user yet)
            storage = get_user_storage()
            for check_user_id in storage.list_users():
                try:
                    state_property = settings_manager.get_user_property(check_user_id, f"oauth_state_{state}")
                    if state_property:
                        state_data = json.loads(state_property)
                        actual_user_id = check_user_id
                        break
                except:
                    continue
            
            if not state_data:
                logger.error(f"Invalid or expired OAuth2 state: {state}")
                return MCPToolResult(success=False, error="Invalid or expired OAuth2 state parameter")
            
            # Check expiration
            if time.time() > state_data.get('expires_at', 0):
                logger.error(f"Expired OAuth2 state: {state}")
                return MCPToolResult(success=False, error="OAuth2 state parameter has expired")
            
            # Extract user_id from state if not provided
            if not user_id:
                # Use system_user_id from state data (this is the original requesting user)
                user_id = state_data.get('system_user_id') or state_data.get('user_id') or actual_user_id
            
            logger.info(f"OAuth2 state validated: user_id={user_id}, gmail_user={state_data.get('gmail_user')}, services={state_data.get('services')}")
            
            # Clean up state
            settings_manager.delete_user_property(actual_user_id, f"oauth_state_{state}")
            
            google_creds = settings_manager.get_google_client_credentials()
            client_id = google_creds['client_id']
            client_secret = google_creds['client_secret']
            redirect_uri = "http://localhost:5001/oauth2/google/callback"
            
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            
            logger.info(f"Token exchange request: {token_data}")
            response = requests.post(token_url, data=token_data)
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return MCPToolResult(
                    success=False, 
                    error=f"Token exchange failed: {response.status_code} - {response.text}"
                )
            
            token_response = response.json()
            logger.info(f"Token exchange successful: {list(token_response.keys())}")
            
            if 'access_token' not in token_response:
                return MCPToolResult(success=False, error="No access token received")
            
            # Get user info with access token
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f'Bearer {token_response["access_token"]}'}
            user_response = requests.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()
            
            google_email = user_info.get('email')
            if not google_email:
                return MCPToolResult(success=False, error="Could not get user email from Google")
            
            # Determine system user ID
            if not user_id:
                # Create or find system user based on Google email
                user_id = f"user_{google_email.split('@')[0]}"
            
            # Store tokens and mapping using settings_manager
            settings_manager = get_settings_manager()
            
            # Store OAuth2 tokens with proper expiration
            expires_in = token_response.get('expires_in', 3600)
            token_data = {
                'access_token': token_response['access_token'],
                'refresh_token': token_response.get('refresh_token'),
                'expires_in': expires_in,
                'expires_at': time.time() + expires_in,
                'token_type': token_response.get('token_type', 'Bearer'),
                'scope': token_response.get('scope', ''),
                'created_at': datetime.now().isoformat()
            }
            
            # Store OAuth2 credentials under Google user ID (not system user ID)
            settings_manager.set_oauth2_credentials(google_email, 'google', token_data)
            
            # Store user mapping: system_user -> google_email  
            settings_manager.set_user_mapping(user_id, 'google', google_email)
            
            # Also store reverse mapping: google_email -> system_user for lookup
            settings_manager.set_user_mapping(google_email, 'system', user_id)
            
            # Store user profile info
            profile_data = {
                'email': google_email,
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', ''),
                'locale': user_info.get('locale', ''),
                'verified_email': user_info.get('verified_email', False),
                'last_login': datetime.now().isoformat()
            }
            settings_manager.set_user_profile(user_id, profile_data)
            
            logger.info(f"OAuth2 exchange successful: {user_id} -> {google_email}")
            
            return MCPToolResult(
                success=True,
                data={
                    'user_id': user_id,
                    'google_email': google_email,
                    'user_info': user_info,
                    'services': ['gmail'],
                    'expires_in': token_response.get('expires_in', 3600)
                }
            )
            
        except Exception as e:
            logger.error(f"OAuth2 code exchange error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_oauth2_status(self, user_id: str = None) -> MCPToolResult:
        """Get OAuth2 authorization status"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            logger.info(f"OAuth2 status check for user: {user_id}")
            
            # Use user storage directly instead of settings manager MCP calls
            storage = get_user_storage()
            
            # Get user mapping (system user -> google email)
            user_mapping = storage.get_user_mapping(user_id, 'google')
            
            # Get OAuth2 credentials from Google email, not system user
            oauth_token = None
            if user_mapping:
                oauth_token = storage.get_oauth_token(user_mapping, 'google')
            
            # Get user profile from properties (no get_user_profile method exists)
            user_profile = None
            try:
                # Try to get profile info from user properties
                email_prop = storage.get_property(user_id, 'email')
                name_prop = storage.get_property(user_id, 'display_name')
                if email_prop or name_prop:
                    user_profile = {
                        'email': email_prop,
                        'name': name_prop
                    }
            except Exception:
                pass
            
            logger.info(f"OAuth token exists: {bool(oauth_token)}")
            logger.info(f"User mapping exists: {bool(user_mapping)} -> {user_mapping}")
            logger.info(f"User profile exists: {bool(user_profile)}")
            
            if oauth_token and user_mapping:
                result_data = {
                    'authorized': True,
                    'user_info': user_profile or {'email': user_mapping},
                    'has_token': True,
                    'user_id': user_id,
                    'google_email': user_mapping
                }
                logger.info(f"User authorized: {result_data}")
                return MCPToolResult(success=True, data=result_data)
            else:
                result_data = {
                    'authorized': False,
                    'has_token': False,
                    'user_id': user_id
                }
                logger.info(f"User not authorized: {result_data}")
                return MCPToolResult(success=True, data=result_data)
                
        except Exception as e:
            logger.error(f"OAuth2 status check error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _refresh_token(self, user_id: str = None) -> MCPToolResult:
        """Refresh OAuth2 token"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # Use user storage directly
            storage = get_user_storage()
            
            # Check if user_id is already a Google email
            if '@' in user_id:
                # This is already a Google email, use it directly
                oauth_token = storage.get_oauth_token(user_id, 'google')
                google_email = user_id
            else:
                # This is a system user ID, get the Google mapping first
                google_email = storage.get_user_mapping(user_id, 'google')
                if not google_email:
                    return MCPToolResult(success=False, error=f"No Google email mapping found for user {user_id}")
                oauth_token = storage.get_oauth_token(google_email, 'google')
            
            if not oauth_token or not oauth_token.get('refresh_token'):
                return MCPToolResult(success=False, error="No refresh token available")
            
            import requests
            
            # Get Google OAuth2 client credentials from system storage
            google_creds = storage.get_property('system', 'google_oauth_client', {})
            client_id = google_creds.get('client_id') or os.environ.get('GOOGLE_CLIENT_ID')
            client_secret = google_creds.get('client_secret') or os.environ.get('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                return MCPToolResult(success=False, error="Google OAuth2 client credentials not configured")
            
            # Refresh token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': oauth_token['refresh_token'],
                'grant_type': 'refresh_token'
            }
            
            logger.info(f"Token refresh request for {user_id}: client_id={client_id[:20]}..., refresh_token={oauth_token['refresh_token'][:20]}...")
            
            response = requests.post(token_url, data=token_data)
            
            # Debug response before raising exception
            if response.status_code != 200:
                logger.error(f"Token refresh failed with status {response.status_code}: {response.text}")
                
                # Parse error for better user message
                try:
                    error_data = response.json()
                    if error_data.get('error') == 'invalid_grant':
                        return MCPToolResult(
                            success=False, 
                            error=f"Google authorization has been revoked or expired. Please re-authorize at http://localhost:5001/oauth2/google/start"
                        )
                except:
                    pass
            
            response.raise_for_status()
            token_response = response.json()
            
            # Update stored token with proper expiration
            updated_token = oauth_token.copy()
            updated_token['access_token'] = token_response['access_token']
            updated_token['expires_in'] = token_response.get('expires_in', 3600)
            # Set expires_at timestamp for easier expiry checking
            updated_token['expires_at'] = time.time() + token_response.get('expires_in', 3600)
            updated_token['refreshed_at'] = datetime.now().isoformat()
            
            # Update token in storage (use Google email as key)
            storage.set_oauth_token(google_email, 'google', updated_token)
            
            return MCPToolResult(
                success=True,
                data={
                    'refreshed': True,
                    'user_id': user_id,
                    'expires_in': token_response.get('expires_in', 3600)
                }
            )
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _revoke_token(self, user_id: str = None) -> MCPToolResult:
        """Revoke OAuth2 token"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # Use user storage directly
            storage = get_user_storage()
            
            # Get Gmail mapping first
            gmail_user = storage.get_user_mapping(user_id, 'google')
            oauth_token = None
            if gmail_user:
                oauth_token = storage.get_oauth_token(gmail_user, 'google')
            
            if oauth_token and oauth_token.get('access_token'):
                import requests
                
                # Revoke token at Google
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={oauth_token['access_token']}"
                try:
                    requests.post(revoke_url)
                except:
                    pass  # Continue even if revoke fails
            
            # Remove stored tokens and mapping - comprehensive cleanup
            try:
                # Delete token under system user ID (legacy)
                storage.delete_property(user_id, 'oauth_token_google')
                storage.delete_property(user_id, 'user_mapping_google')
                
                # Delete token under Google email (new storage)
                if gmail_user:
                    storage.delete_property(gmail_user, 'oauth_token_google')
                    storage.delete_property(gmail_user, 'user_mapping_system')
                    
            except Exception as e:
                logger.warning(f"Error cleaning up OAuth data: {e}")
            
            return MCPToolResult(
                success=True,
                data={
                    'revoked': True,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Token revoke error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_user_token(self, user_id: str) -> MCPToolResult:
        """Get OAuth2 access token for user"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # Get token from storage using Google email
            settings_manager = get_settings_manager()
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}"
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            if not oauth_token:
                return MCPToolResult(
                    success=False, 
                    error=f"No OAuth2 token found for user {user_id}"
                )
            
            access_token = oauth_token.get('access_token')
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="No access token in stored credentials"
                )
            
            # Check if token needs refresh
            expires_at = oauth_token.get('expires_at')
            if expires_at:
                import time
                if time.time() > (expires_at - 300):  # Refresh 5 minutes before expiry
                    logger.info(f"Token expires soon for {user_id}, refreshing...")
                    refresh_result = self._refresh_token(gmail_user)
                    if refresh_result.success:
                        # Get refreshed token from Google email
                        oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
                        access_token = oauth_token.get('access_token')
            
            return MCPToolResult(
                success=True,
                data={
                    'access_token': access_token,
                    'token_type': 'Bearer',
                    'expires_in': oauth_token.get('expires_in', 3600),
                    'scope': oauth_token.get('scope', ''),
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Get user token error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_authorized_users(self) -> MCPToolResult:
        """List all authorized users"""
        try:
            settings_manager = get_settings_manager()
            users = settings_manager.get_all_users()
            
            authorized_users = []
            for user_id in users:
                oauth_token = settings_manager.get_oauth2_credentials(user_id, 'google')
                user_mapping = settings_manager.get_user_mapping(user_id, 'google')
                user_profile = settings_manager.get_user_profile(user_id)
                
                if oauth_token and user_mapping:
                    authorized_users.append({
                        'user_id': user_id,
                        'google_email': user_mapping,
                        'user_info': user_profile or {'email': user_mapping}
                    })
            
            return MCPToolResult(
                success=True,
                data={
                    'authorized_users': authorized_users,
                    'count': len(authorized_users)
                }
            )
            
        except Exception as e:
            logger.error(f"List authorized users error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calendar_list_calendars(self, user_id: str = None) -> MCPToolResult:
        """List user's Google Calendars"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}. Please authenticate with Google first."
                )
            
            settings_manager = get_settings_manager()
            # Get user mapping first
            google_user = settings_manager.get_user_mapping(user_id, 'google')
            if not google_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Google account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(google_user, 'google')
            
            # Call Google Calendar API
            import requests
            
            headers = {'Authorization': f'Bearer {oauth_token["access_token"]}'}
            url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract calendar info
            calendars = []
            for calendar in result.get('items', []):
                calendars.append({
                    'id': calendar.get('id'),
                    'summary': calendar.get('summary'),
                    'description': calendar.get('description', ''),
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole', ''),
                    'time_zone': calendar.get('timeZone', '')
                })
            
            return MCPToolResult(
                success=True,
                data={
                    'calendars': calendars,
                    'count': len(calendars),
                    'user_id': user_id,
                    'google_user': google_user
                }
            )
            
        except Exception as e:
            logger.error(f"Calendar list error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calendar_list_events(self, user_id: str = None, calendar_id: str = "primary", 
                            max_results: int = 10, time_min: str = None, time_max: str = None) -> MCPToolResult:
        """List events from a Google Calendar"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Call Google Calendar API
            import requests
            from datetime import datetime, timezone
            
            headers = {'Authorization': f'Bearer {oauth_token["access_token"]}'}
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            
            params = {
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            # Set time range if provided
            if time_min:
                params['timeMin'] = time_min
            else:
                # Default to current time
                params['timeMin'] = datetime.now(timezone.utc).isoformat()
            
            if time_max:
                params['timeMax'] = time_max
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract event info
            events = []
            for event in result.get('items', []):
                events.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': event.get('start', {}),
                    'end': event.get('end', {}),
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', ''),
                    'created': event.get('created', ''),
                    'updated': event.get('updated', '')
                })
            
            return MCPToolResult(
                success=True,
                data={
                    'events': events,
                    'count': len(events),
                    'calendar_id': calendar_id,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Calendar events list error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calendar_create_event(self, summary: str, start_time: str, end_time: str,
                             user_id: str = None, calendar_id: str = "primary", 
                             description: str = "", location: str = "", 
                             attendees: List[str] = None) -> MCPToolResult:
        """Create a new event in Google Calendar"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Prepare event data
            event_data = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC'
                }
            }
            
            # Add attendees if provided
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
            
            # Call Google Calendar API
            import requests
            
            headers = {
                'Authorization': f'Bearer {oauth_token["access_token"]}',
                'Content-Type': 'application/json'
            }
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            
            response = requests.post(url, headers=headers, json=event_data)
            response.raise_for_status()
            
            result = response.json()
            
            return MCPToolResult(
                success=True,
                data={
                    'event_id': result.get('id'),
                    'summary': result.get('summary'),
                    'start': result.get('start'),
                    'end': result.get('end'),
                    'html_link': result.get('htmlLink'),
                    'calendar_id': calendar_id,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Calendar event creation error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calendar_update_event(self, event_id: str, user_id: str = None, 
                             calendar_id: str = "primary", **kwargs) -> MCPToolResult:
        """Update an existing event in Google Calendar"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Build update data from kwargs
            event_data = {}
            if 'summary' in kwargs:
                event_data['summary'] = kwargs['summary']
            if 'description' in kwargs:
                event_data['description'] = kwargs['description']
            if 'location' in kwargs:
                event_data['location'] = kwargs['location']
            if 'start_time' in kwargs:
                event_data['start'] = {
                    'dateTime': kwargs['start_time'],
                    'timeZone': 'UTC'
                }
            if 'end_time' in kwargs:
                event_data['end'] = {
                    'dateTime': kwargs['end_time'],
                    'timeZone': 'UTC'
                }
            
            # Call Google Calendar API
            import requests
            
            headers = {
                'Authorization': f'Bearer {oauth_token["access_token"]}',
                'Content-Type': 'application/json'
            }
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
            
            response = requests.patch(url, headers=headers, json=event_data)
            response.raise_for_status()
            
            result = response.json()
            
            return MCPToolResult(
                success=True,
                data={
                    'event_id': result.get('id'),
                    'summary': result.get('summary'),
                    'updated': result.get('updated'),
                    'html_link': result.get('htmlLink'),
                    'calendar_id': calendar_id,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Calendar event update error: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _calendar_delete_event(self, event_id: str, user_id: str = None, 
                             calendar_id: str = "primary") -> MCPToolResult:
        """Delete an event from Google Calendar"""
        try:
            if not user_id:
                return MCPToolResult(success=False, error="User ID required")
            
            # OAuth2 Authentication Check with Auto-Refresh
            if not self._ensure_valid_token(user_id):
                return MCPToolResult(
                    success=False,
                    error=f"No valid Google OAuth2 authentication found for user {user_id}."
                )
            
            settings_manager = get_settings_manager()
            # Get Gmail mapping first
            gmail_user = settings_manager.get_user_mapping(user_id, 'google')
            if not gmail_user:
                return MCPToolResult(
                    success=False,
                    error=f"No Gmail account mapping found for user {user_id}."
                )
            
            # Get OAuth token from Google email, not system user
            oauth_token = settings_manager.get_oauth2_credentials(gmail_user, 'google')
            
            # Call Google Calendar API
            import requests
            
            headers = {'Authorization': f'Bearer {oauth_token["access_token"]}'}
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
            
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            
            return MCPToolResult(
                success=True,
                data={
                    'deleted': True,
                    'event_id': event_id,
                    'calendar_id': calendar_id,
                    'user_id': user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Calendar event deletion error: {e}")
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the Google OAuth2 Manager tool"""
    try:
        tool = GoogleOAuth2Manager()
        registry.register_tool(tool)
        logger.info("Google OAuth2 Manager tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register Google OAuth2 Manager tool: {e}")
        return False