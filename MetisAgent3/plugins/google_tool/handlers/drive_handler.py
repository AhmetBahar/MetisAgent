"""
Drive Handler - Google Drive API operations

CLAUDE.md COMPLIANT:
- Complete Drive API integration
- File upload, download, sharing operations
- Clean data formatting
- Fault-tolerant error handling
"""

import logging
import os
import io
from typing import Any, Dict, List, Optional
from pathlib import Path
import mimetypes

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.oauth2.credentials import Credentials
except ImportError:
    pass

logger = logging.getLogger(__name__)


class DriveHandler:
    """Google Drive API operations handler"""
    
    def __init__(self, credentials: 'Credentials'):
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
        logger.info("✅ Drive handler initialized")
    
    async def list_files(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        order_by: str = "modifiedTime desc",
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List files from Drive"""
        try:
            logger.info(f"📁 Listing {max_results} files from Drive")
            
            # Build query
            search_query = ""
            if folder_id:
                search_query = f"'{folder_id}' in parents"
            elif query:
                search_query = query
            else:
                search_query = "trashed = false"  # Exclude trashed files
            
            # Get file list
            results = self.service.files().list(
                q=search_query,
                pageSize=max_results,
                orderBy=order_by,
                fields="files(id,name,mimeType,size,modifiedTime,createdTime,owners,webViewLink,parents)"
            ).execute()
            
            files = results.get('files', [])
            
            # Format files for better readability
            formatted_files = []
            for file_info in files:
                formatted_file = {
                    "id": file_info.get('id'),
                    "name": file_info.get('name'),
                    "mime_type": file_info.get('mimeType'),
                    "size": int(file_info.get('size', 0)) if file_info.get('size') else 0,
                    "size_readable": self._format_file_size(int(file_info.get('size', 0)) if file_info.get('size') else 0),
                    "created_time": file_info.get('createdTime'),
                    "modified_time": file_info.get('modifiedTime'),
                    "owners": [owner.get('displayName', owner.get('emailAddress', 'Unknown')) for owner in file_info.get('owners', [])],
                    "web_view_link": file_info.get('webViewLink'),
                    "parents": file_info.get('parents', [])
                }
                formatted_files.append(formatted_file)
            
            return {
                "success": True,
                "files": formatted_files,
                "count": len(formatted_files),
                "message": f"Listed {len(formatted_files)} files successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive list API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": "Failed to list Drive files"
            }
        except Exception as e:
            logger.error(f"Drive list failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list Drive files"
            }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        size_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and size_index < len(size_names) - 1:
            size_index += 1
            size /= 1024.0
        
        return f"{size:.1f} {size_names[size_index]}"
    
    async def upload_file(
        self,
        file_path: str,
        drive_filename: Optional[str] = None,
        folder_id: Optional[str] = None,
        description: Optional[str] = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Upload file to Drive"""
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "message": "Upload failed - file not found"
                }
            
            filename = drive_filename or os.path.basename(file_path)
            logger.info(f"⬆️ Uploading file: {filename}")
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # File metadata
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            if description:
                file_metadata['description'] = description
            
            # Upload file
            media = MediaFileUpload(file_path, mimetype=mime_type)
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,size'
            ).execute()
            
            file_id = uploaded_file.get('id')
            
            # Make public if requested
            if public:
                try:
                    self.service.permissions().create(
                        fileId=file_id,
                        body={'role': 'reader', 'type': 'anyone'}
                    ).execute()
                except:
                    logger.warning("Failed to make file public")
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "web_view_link": uploaded_file.get('webViewLink'),
                "size": uploaded_file.get('size'),
                "public": public,
                "message": f"File '{filename}' uploaded successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive upload API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": f"Failed to upload file '{filename}'"
            }
        except Exception as e:
            logger.error(f"Drive upload failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to upload file"
            }
    
    async def download_file(
        self,
        file_id: str,
        download_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download file from Drive"""
        try:
            logger.info(f"⬇️ Downloading file: {file_id}")
            
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            filename = file_metadata.get('name', f"file_{file_id}")
            
            # Determine download path
            if not download_path:
                download_path = f"./downloads/{filename}"
            
            # Create download directory if needed
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            with open(download_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "download_path": download_path,
                "message": f"File '{filename}' downloaded successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive download API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": f"Failed to download file {file_id}"
            }
        except Exception as e:
            logger.error(f"Drive download failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to download file {file_id}"
            }
    
    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete file from Drive"""
        try:
            logger.info(f"🗑️ Deleting file: {file_id}")
            
            # Get file name before deletion
            try:
                file_metadata = self.service.files().get(fileId=file_id, fields='name').execute()
                filename = file_metadata.get('name', file_id)
            except:
                filename = file_id
            
            # Delete file
            self.service.files().delete(fileId=file_id).execute()
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "message": f"File '{filename}' deleted successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive delete API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": f"Failed to delete file {file_id}"
            }
        except Exception as e:
            logger.error(f"Drive delete failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to delete file {file_id}"
            }
    
    async def share_file(
        self,
        file_id: str,
        email: Optional[str] = None,
        role: str = "reader",
        make_public: bool = False
    ) -> Dict[str, Any]:
        """Share file with specific user or make public"""
        try:
            logger.info(f"🔗 Sharing file: {file_id}")
            
            permissions = []
            
            if make_public:
                # Make file publicly accessible
                permission = {
                    'role': 'reader',
                    'type': 'anyone'
                }
                created_permission = self.service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                permissions.append({
                    "type": "anyone",
                    "role": "reader",
                    "id": created_permission.get('id')
                })
            
            if email:
                # Share with specific user
                permission = {
                    'role': role,  # reader, writer, owner
                    'type': 'user',
                    'emailAddress': email
                }
                created_permission = self.service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    sendNotificationEmail=True
                ).execute()
                permissions.append({
                    "type": "user",
                    "role": role,
                    "email": email,
                    "id": created_permission.get('id')
                })
            
            # Get file web view link
            file_metadata = self.service.files().get(
                fileId=file_id, 
                fields='name,webViewLink'
            ).execute()
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": file_metadata.get('name'),
                "web_view_link": file_metadata.get('webViewLink'),
                "permissions": permissions,
                "message": f"File shared successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive share API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": f"Failed to share file {file_id}"
            }
        except Exception as e:
            logger.error(f"Drive share failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to share file {file_id}"
            }
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get detailed file information"""
        try:
            logger.info(f"📋 Getting file info: {file_id}")
            
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id,name,mimeType,size,createdTime,modifiedTime,owners,parents,webViewLink,description,permissions"
            ).execute()
            
            # Get permissions
            permissions = []
            if 'permissions' in file_info:
                for perm in file_info['permissions']:
                    permissions.append({
                        "type": perm.get('type'),
                        "role": perm.get('role'),
                        "email": perm.get('emailAddress'),
                        "display_name": perm.get('displayName')
                    })
            
            formatted_info = {
                "id": file_info.get('id'),
                "name": file_info.get('name'),
                "mime_type": file_info.get('mimeType'),
                "size": int(file_info.get('size', 0)) if file_info.get('size') else 0,
                "size_readable": self._format_file_size(int(file_info.get('size', 0)) if file_info.get('size') else 0),
                "created_time": file_info.get('createdTime'),
                "modified_time": file_info.get('modifiedTime'),
                "description": file_info.get('description', ''),
                "owners": [owner.get('displayName', owner.get('emailAddress', 'Unknown')) for owner in file_info.get('owners', [])],
                "web_view_link": file_info.get('webViewLink'),
                "parents": file_info.get('parents', []),
                "permissions": permissions
            }
            
            return {
                "success": True,
                "file_info": formatted_info,
                "message": "File information retrieved successfully"
            }
            
        except HttpError as e:
            logger.error(f"Drive file info API error: {e}")
            return {
                "success": False,
                "error": f"Drive API error: {str(e)}",
                "message": f"Failed to get file info for {file_id}"
            }
        except Exception as e:
            logger.error(f"Drive file info failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get file info for {file_id}"
            }