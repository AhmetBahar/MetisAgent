"""
Gmail Handler - Gmail API operations with complete functionality

CLAUDE.md COMPLIANT:
- Full Gmail API integration (list, read, send, attachments)
- Fault-tolerant error handling
- Clean data formatting for LLM consumption
- User-friendly message parsing
"""

import logging
import base64
import email
import mimetypes
import os
from typing import Any, Dict, List, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
except ImportError:
    pass

logger = logging.getLogger(__name__)


class GmailHandler:
    """Gmail API operations handler"""
    
    def __init__(self, credentials: 'Credentials'):
        self.credentials = credentials
        self.service = build('gmail', 'v1', credentials=credentials)
        logger.info("✅ Gmail handler initialized")
    
    async def list_emails(
        self, 
        max_results: int = 10,
        query: str = "",
        label_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """List emails from inbox"""
        try:
            logger.info(f"📧 Listing {max_results} emails with query: '{query}'")
            
            # Build request parameters
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'q': query
            }
            
            if label_ids:
                request_params['labelIds'] = label_ids
            
            # Get email list
            results = self.service.users().messages().list(**request_params).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return {
                    "success": True,
                    "emails": [],
                    "count": 0,
                    "message": "No emails found"
                }
            
            # Get detailed information for each email
            email_list = []
            for msg in messages:
                try:
                    email_detail = self.service.users().messages().get(
                        userId='me', 
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date']
                    ).execute()
                    
                    headers = {h['name']: h['value'] for h in email_detail['payload'].get('headers', [])}
                    
                    email_info = {
                        "id": msg['id'],
                        "thread_id": email_detail.get('threadId'),
                        "from": headers.get('From', 'Unknown'),
                        "to": headers.get('To', 'Unknown'),
                        "subject": headers.get('Subject', 'No Subject'),
                        "date": headers.get('Date', 'Unknown'),
                        "snippet": email_detail.get('snippet', '')
                    }
                    
                    email_list.append(email_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to get details for email {msg['id']}: {e}")
                    continue
            
            return {
                "success": True,
                "emails": email_list,
                "count": len(email_list),
                "message": f"Listed {len(email_list)} emails successfully"
            }
            
        except HttpError as e:
            logger.error(f"Gmail list API error: {e}")
            return {
                "success": False,
                "error": f"Gmail API error: {str(e)}",
                "message": "Failed to list emails"
            }
        except Exception as e:
            logger.error(f"Gmail list failed: {e}")
            return {
                "success": False, 
                "error": str(e),
                "message": "Failed to list emails"
            }
    
    async def read_email(
        self,
        message_id: str,
        format: str = 'full'
    ) -> Dict[str, Any]:
        """Read specific email by ID"""
        try:
            logger.info(f"📖 Reading email: {message_id}")
            
            # Get email details
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            
            # Extract headers
            headers = {}
            if 'payload' in message and 'headers' in message['payload']:
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract body content
            body_content = self._extract_email_body(message['payload'])
            
            # Check for attachments
            attachments = self._get_attachments_info(message['payload'])
            
            email_data = {
                "id": message['id'],
                "thread_id": message.get('threadId'),
                "from": headers.get('From', 'Unknown'),
                "to": headers.get('To', 'Unknown'),
                "subject": headers.get('Subject', 'No Subject'),
                "date": headers.get('Date', 'Unknown'),
                "body": body_content,
                "snippet": message.get('snippet', ''),
                "attachments": attachments,
                "labels": message.get('labelIds', [])
            }
            
            return {
                "success": True,
                "email": email_data,
                "message": "Email read successfully"
            }
            
        except HttpError as e:
            logger.error(f"Gmail read API error: {e}")
            return {
                "success": False,
                "error": f"Gmail API error: {str(e)}",
                "message": f"Failed to read email {message_id}"
            }
        except Exception as e:
            logger.error(f"Gmail read failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to read email {message_id}"
            }
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract email body content (text and HTML)"""
        body = {"text": "", "html": ""}
        
        def extract_from_part(part):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    body['text'] = base64.urlsafe_b64decode(data).decode('utf-8')
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    body['html'] = base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                for subpart in part['parts']:
                    extract_from_part(subpart)
        
        if 'parts' in payload:
            for part in payload['parts']:
                extract_from_part(part)
        else:
            extract_from_part(payload)
        
        return body
    
    def _get_attachments_info(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get information about email attachments"""
        attachments = []
        
        def find_attachments(part):
            if part.get('filename'):
                attachment = {
                    "filename": part['filename'],
                    "mime_type": part.get('mimeType'),
                    "size": part.get('body', {}).get('size', 0),
                    "attachment_id": part.get('body', {}).get('attachmentId')
                }
                attachments.append(attachment)
            
            if 'parts' in part:
                for subpart in part['parts']:
                    find_attachments(subpart)
        
        if 'parts' in payload:
            for part in payload['parts']:
                find_attachments(part)
        else:
            find_attachments(payload)
        
        return attachments
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        body_type: str = "text"  # "text" or "html"
    ) -> Dict[str, Any]:
        """Send email"""
        try:
            logger.info(f"📤 Sending email to: {to}, subject: {subject}")
            
            # Create message
            if body_type == "html":
                message = MIMEText(body, 'html')
            else:
                message = MIMEText(body, 'plain')
            
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_request = {
                'raw': raw_message
            }
            
            result = self.service.users().messages().send(
                userId='me',
                body=send_request
            ).execute()
            
            return {
                "success": True,
                "message_id": result['id'],
                "thread_id": result.get('threadId'),
                "message": f"Email sent successfully to {to}"
            }
            
        except HttpError as e:
            logger.error(f"Gmail send API error: {e}")
            return {
                "success": False,
                "error": f"Gmail API error: {str(e)}",
                "message": f"Failed to send email to {to}"
            }
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send email to {to}"
            }
    
    async def send_email_with_attachment(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        body_type: str = "text"
    ) -> Dict[str, Any]:
        """Send email with attachment"""
        try:
            logger.info(f"📎 Sending email with attachment to: {to}")
            
            # Create multipart message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body
            if body_type == "html":
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))
            
            # Add attachment
            if os.path.exists(attachment_path):
                filename = os.path.basename(attachment_path)
                
                with open(attachment_path, 'rb') as f:
                    attachment_data = f.read()
                
                # Guess content type
                content_type, encoding = mimetypes.guess_type(attachment_path)
                if content_type is None or encoding is not None:
                    content_type = 'application/octet-stream'
                
                attachment = MIMEApplication(attachment_data)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(attachment)
            else:
                return {
                    "success": False,
                    "error": f"Attachment file not found: {attachment_path}",
                    "message": "Failed to send email with attachment"
                }
            
            # Send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_request = {
                'raw': raw_message
            }
            
            result = self.service.users().messages().send(
                userId='me',
                body=send_request
            ).execute()
            
            return {
                "success": True,
                "message_id": result['id'],
                "thread_id": result.get('threadId'),
                "attachment_sent": filename,
                "message": f"Email with attachment sent successfully to {to}"
            }
            
        except HttpError as e:
            logger.error(f"Gmail send with attachment API error: {e}")
            return {
                "success": False,
                "error": f"Gmail API error: {str(e)}",
                "message": f"Failed to send email with attachment to {to}"
            }
        except Exception as e:
            logger.error(f"Gmail send with attachment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send email with attachment to {to}"
            }
    
    async def get_positional_email(
        self,
        position: int,
        query: str = ""
    ) -> Dict[str, Any]:
        """Get email by position (e.g., latest, second latest)"""
        try:
            logger.info(f"📧 Getting email at position {position}")
            
            # List emails to get the position
            emails_result = await self.list_emails(max_results=position + 1, query=query)
            
            if not emails_result["success"]:
                return emails_result
            
            emails = emails_result["emails"]
            if len(emails) <= position:
                return {
                    "success": False,
                    "error": f"No email found at position {position}",
                    "message": f"Only {len(emails)} emails available"
                }
            
            # Get the specific email
            target_email = emails[position]
            return await self.read_email(target_email["id"])
            
        except Exception as e:
            logger.error(f"Get positional email failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get email at position {position}"
            }