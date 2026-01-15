"""
Gmail Helper Tool - Gmail API kullanımını kolaylaştıran yardımcı tool
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from app.mcp_core import MCPTool, MCPToolResult
from ..internal.user_storage import get_user_storage
from app.auth_manager import auth_manager
# User mapping removed - using user_storage now

logger = logging.getLogger(__name__)

class GmailHelperTool(MCPTool):
    """Gmail API işlemlerini kolaylaştıran tool"""
    
    def __init__(self):
        super().__init__(
            name="gmail_helper",
            description="Complete Gmail operations - reading, sending, positioning with full details",
            version="1.0.0",
            llm_description="Gmail email management tool for sending emails, reading inbox, and managing email communications",
            use_cases=[
                "Send emails to recipients",
                "Send emails with file attachments",
                "Read latest emails from inbox",
                "Extract email subjects and content",
                "Manage email communications"
            ],
            keywords=[
                "email", "mail", "gmail", "e-posta", "mesaj", "message",
                "gönder", "send", "yolla", "postala", "ilet",
                "oku", "read", "al", "get", "listele", "list",
                "attachment", "ek", "dosya", "file", "ekli"
            ]
        )
        
        self.base_url = "http://localhost:5001/oauth2/google"
        
        # Register actions
        self.register_action(
            "get_latest_email_subject",
            self._get_latest_email_subject,
            required_params=[],
            optional_params=["user_id", "max_results", "user_intent"]
        )
        
        self.register_action(
            "get_positional_email",
            self._get_positional_email,
            required_params=["user_request"],
            optional_params=["user_id", "max_results"],
            description="Get email by position with complete details - no additional steps needed"
        )
        
        self.register_action(
            "get_email_details",
            self._get_email_details,
            required_params=["message_id"],
            optional_params=["user_id", "user_intent"]
        )
        
        self.register_action(
            "list_emails",
            self._list_emails,
            required_params=[],
            optional_params=["user_id", "max_results", "query"]
        )
        
        self.register_action(
            "send_email",
            self._send_email,
            required_params=["recipient", "subject", "body"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "send_email_with_attachment",
            self._send_email_with_attachment,
            required_params=["recipient", "subject", "body", "attachment_path"],
            optional_params=["user_id"]
        )
    
    def _get_user_email_from_session(self, session_token: str = None) -> str:
        """Session token'dan kullanıcının email adresini al"""
        try:
            if not session_token:
                # No session token provided, cannot determine user
                return ""
            
            # Session token ile kullanıcıyı bul
            user = auth_manager.validate_session(session_token)
            if not user:
                return ""
            
            # Use user_storage for Google credentials (removed settings_manager dependency)
            storage = get_user_storage()
            google_creds = storage.get_user_mapping(user, 'google')
            if google_creds:
                return google_creds
            
            return ""
            
        except Exception as e:
            logger.error(f"Kullanıcı email alma hatası: {e}")
            return ""
    
    def filter_response_by_intent(self, gmail_data: dict, user_intent: str) -> dict:
        """Filter Gmail response based on user intent"""
        
        if user_intent == 'sender_request':
            return {
                'from': gmail_data.get('from'),
                'intent': user_intent,
                'focused_field': 'sender'
            }
        elif user_intent == 'subject_request':
            return {
                'subject': gmail_data.get('subject'),
                'intent': user_intent,
                'focused_field': 'subject'
            }
        elif user_intent == 'attachment_request':
            return {
                'has_attachments': gmail_data.get('has_attachments'),
                'attachments': gmail_data.get('attachments', []),
                'intent': user_intent,
                'focused_field': 'attachments'
            }
        elif user_intent == 'date_request':
            return {
                'date': gmail_data.get('date'),
                'intent': user_intent,
                'focused_field': 'date'
            }
        else:
            # Return all data for general requests
            return gmail_data
    
    def _get_latest_email_subject(self, user_id: str = None, max_results: int = 1, user_intent: str = None) -> MCPToolResult:
        """Son gelen email'in subject bilgisini al"""
        try:
            if not user_id:
                user_id = self._get_user_email_from_session()
                if not user_id:
                    return MCPToolResult(success=False, error="No user context available. User must be authenticated.")
            
            # Map system user ID to Gmail account
            # Use user_storage for mapping
            storage = get_user_storage()
            gmail_user_id = storage.get_user_mapping(user_id, 'google') or user_id
            if not gmail_user_id:
                return MCPToolResult(success=False, error=f"No Gmail account mapping found for user: {user_id}")
            
            logger.info(f"Gmail API: Mapping {user_id} -> {gmail_user_id}")
                
            # Önce mesaj listesini al
            list_url = f"{self.base_url}/gmail/messages"
            params = {
                'user_id': gmail_user_id,
                'max_results': max_results
            }
            
            response = requests.get(list_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Unknown error'))
            
            messages = result.get('data', {}).get('messages', {}).get('messages', [])
            if not messages:
                return MCPToolResult(success=False, error="No messages found")
            
            # İlk mesajın detaylarını al
            message_id = messages[0]['id']
            details_result = self._get_email_details(message_id, user_id)
            
            if details_result.success:
                # Create full email data with attachments
                full_data = {
                    'subject': details_result.data.get('subject'),
                    'from': details_result.data.get('from'),
                    'date': details_result.data.get('date'),
                    'message_id': message_id,
                    'thread_id': messages[0].get('threadId'),
                    'has_attachments': len(details_result.data.get('all_headers', [])) > 0,  # Will be improved
                    'attachments': []  # Will be improved with actual attachment detection
                }
                
                # Filter response based on user intent
                if user_intent:
                    filtered_data = self.filter_response_by_intent(full_data, user_intent)
                    logger.info(f"INTENT FILTERING: {user_intent} -> {list(filtered_data.keys())}")
                    return MCPToolResult(success=True, data=filtered_data)
                else:
                    return MCPToolResult(success=True, data=full_data)
            else:
                return details_result
                
        except Exception as e:
            logger.error(f"Error getting latest email subject: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_email_details(self, message_id: str, user_id: str = None, user_intent: str = None) -> MCPToolResult:
        """Belirli bir email'in detaylarını al"""
        try:
            if not user_id:
                user_id = self._get_user_email_from_session()
                if not user_id:
                    return MCPToolResult(success=False, error="No user context available. User must be authenticated.")
            
            # Map system user ID to Gmail account
            # Use user_storage for mapping
            storage = get_user_storage()
            gmail_user_id = storage.get_user_mapping(user_id, 'google') or user_id
            logger.info(f"Gmail API: Mapping {user_id} -> {gmail_user_id}")
            
            details_url = f"{self.base_url}/gmail/messages/{message_id}"
            params = {'user_id': gmail_user_id}
            
            response = requests.get(details_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Unknown error'))
            
            message = result.get('data', {}).get('message', {})
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Header bilgilerini çıkar
            subject = None
            sender = None
            date = None
            
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    sender = value
                elif name == 'date':
                    date = value
            
            return MCPToolResult(
                success=True,
                data={
                    'message_id': message_id,
                    'subject': subject,
                    'from': sender,
                    'date': date,
                    'snippet': message.get('snippet', ''),
                    'thread_id': message.get('threadId'),
                    'all_headers': headers
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting email details: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_emails(self, user_id: str = None, max_results: int = 10, query: str = "") -> MCPToolResult:
        """Email listesini al"""
        try:
            if not user_id:
                user_id = self._get_user_email_from_session()
                if not user_id:
                    return MCPToolResult(success=False, error="No user context available. User must be authenticated.")
            
            # Map system user ID to Gmail account
            # Use user_storage for mapping
            storage = get_user_storage()
            gmail_user_id = storage.get_user_mapping(user_id, 'google') or user_id
            logger.info(f"Gmail API: Mapping {user_id} -> {gmail_user_id}")
            
            list_url = f"{self.base_url}/gmail/messages"
            params = {
                'user_id': gmail_user_id,
                'max_results': max_results,
                'query': query
            }
            
            response = requests.get(list_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Unknown error'))
            
            return MCPToolResult(success=True, data=result.get('data', {}))
            
        except Exception as e:
            logger.error(f"Error listing emails: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _send_email(self, recipient: str, subject: str, body: str, user_id: str = None) -> MCPToolResult:
        """Send email using Gmail API"""
        try:
            if not user_id:
                user_id = self._get_user_email_from_session()
                if not user_id:
                    return MCPToolResult(success=False, error="User authentication required")
            
            # Send via Gmail API using correct OAuth2 endpoint
            send_url = f"{self.base_url}/gmail/send"
            payload = {
                'user_id': user_id,
                'to': recipient,
                'subject': subject,
                'body': body
            }
            
            response = requests.post(send_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Failed to send email'))
            
            return MCPToolResult(
                success=True,
                data={
                    'message': 'Email sent successfully',
                    'recipient': recipient,
                    'subject': subject,
                    'message_id': result.get('data', {}).get('id')
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _send_email_with_attachment(self, recipient: str, subject: str, body: str, 
                                   attachment_path: str, user_id: str = None) -> MCPToolResult:
        """Send email with attachment using Gmail API"""
        try:
            if not user_id:
                user_id = self._get_user_email_from_session()
                if not user_id:
                    return MCPToolResult(success=False, error="User authentication required")
            
            # Create email with attachment
            import base64
            import os
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            
            message = MIMEMultipart()
            message['to'] = recipient
            message['subject'] = subject
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Add attachment
            if os.path.exists(attachment_path):
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                message.attach(part)
            else:
                return MCPToolResult(success=False, error=f"Attachment file not found: {attachment_path}")
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send via Gmail API using correct OAuth2 endpoint for attachments
            send_url = f"{self.base_url}/gmail/send_with_attachment"
            payload = {
                'user_id': user_id,
                'to': recipient,
                'subject': subject,
                'body': body,
                'attachment_path': attachment_path
            }
            
            response = requests.post(send_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                return MCPToolResult(success=False, error=result.get('error', 'Failed to send email'))
            
            return MCPToolResult(
                success=True,
                data={
                    'message': 'Email with attachment sent successfully',
                    'recipient': recipient,
                    'subject': subject,
                    'attachment': filename,
                    'message_id': result.get('data', {}).get('id')
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending email with attachment: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_positional_email(self, user_request: str, user_id: str = None, max_results: int = 10) -> MCPToolResult:
        """Get email based on LLM analysis of positional request"""
        try:
            # First get list of emails
            list_result = self._list_emails(user_id=user_id, max_results=max_results)
            if not list_result.success:
                return list_result
            
            # Extract messages from the result - Backend returns dict format
            messages_dict = list_result.data.get('messages', {})
            if not messages_dict:
                return MCPToolResult(success=False, error="No messages found")
            
            # Convert dict to list (newest first order)
            messages = list(messages_dict.values())
            
            # Use LLM to determine position
            from tools.internal.llm_tool import LLMTool
            llm = LLMTool()
            
            position_prompt = f"""
            Analyze this email request: "{user_request}"
            
            I have {len(messages)} emails available (index 0 = newest, index {len(messages)-1} = oldest).
            
            Determine which email position the user wants:
            - Return ONLY a number (0, 1, 2, etc.)
            - 0 = newest/latest email
            - 1 = second newest (sondan ikinci)
            - 2 = third newest (sondan üçüncü)
            - {len(messages)-1} = oldest email (ilk)
            
            Return only the index number, nothing else.
            """
            
            llm_result = llm.execute_action("chat", message=position_prompt, user_id=user_id or "system")
            if not llm_result.success:
                # Fallback to newest if LLM fails
                target_index = 0
            else:
                try:
                    target_index = int(llm_result.data.get("response", "0").strip())
                    if target_index >= len(messages):
                        target_index = 0
                except:
                    target_index = 0
            
            target_message = messages[target_index]
            
            # Extract user-friendly information
            email_subject = target_message.get('subject', 'No subject')
            email_from = target_message.get('from', 'Unknown sender')
            email_date = target_message.get('date', 'No date')
            email_snippet = target_message.get('snippet', 'No preview available')
            
            # Create user-friendly response
            position_desc = "newest" if target_index == 0 else f"{target_index + 1}. newest"
            if target_index == 1:
                position_desc = "second newest (sondan ikinci)"
            elif target_index == len(messages) - 1:
                position_desc = "oldest"
                
            response_text = f"""📧 **{position_desc.title()} Email:**

**From:** {email_from}
**Subject:** {email_subject}
**Date:** {email_date}

**Content Preview:** {email_snippet}

*Found among {len(messages)} total emails*"""
            
            return MCPToolResult(
                success=True,
                data={
                    'message': target_message,
                    'position_index': target_index,
                    'total_messages': len(messages),
                    'user_request': user_request,
                    'response': response_text,
                    'display_ready': True
                },
                metadata={
                    'method': 'get_positional_email',
                    'llm_determined_index': target_index
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting positional email: {e}")
            return MCPToolResult(success=False, error=str(e))

# Register tool function
def register_tool(registry):
    """Register Gmail Helper tool with the registry"""
    try:
        tool = GmailHelperTool()
        registry.register_tool(tool)
        logger.info("Gmail Helper tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register Gmail Helper tool: {e}")
        return False