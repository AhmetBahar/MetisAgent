"""
Google Drive Tool - Google Drive API operations with secure OAuth2 integration
"""

import requests
import logging
import mimetypes
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from app.mcp_core import MCPTool, MCPToolResult
from ..internal.user_storage import get_user_storage
from app.auth_manager import auth_manager

logger = logging.getLogger(__name__)

class GoogleDriveTool(MCPTool):
    """Google Drive API operations tool"""
    
    def __init__(self):
        super().__init__(
            name="google_drive",
            description="Google Drive file operations - upload, download, list, share",
            version="1.0.0"
        )
        
        self.base_url = "http://localhost:5001/oauth2/google"
        
        # Register capabilities
        self.add_capability("file_upload")
        self.add_capability("file_download")
        self.add_capability("file_management")
        self.add_capability("sharing_permissions")
        
        # Register actions
        self.register_action(
            "upload_file",
            self._upload_file,
            required_params=["file_path"],
            optional_params=["user_id", "folder_id", "description", "public"]
        )
        
        self.register_action(
            "download_file",
            self._download_file,
            required_params=["file_id"],
            optional_params=["user_id", "download_path"]
        )
        
        self.register_action(
            "list_files",
            self._list_files,
            required_params=[],
            optional_params=["user_id", "folder_id", "query", "max_results", "file_type"]
        )
        
        self.register_action(
            "create_folder",
            self._create_folder,
            required_params=["folder_name"],
            optional_params=["user_id", "parent_folder_id", "description"]
        )
        
        self.register_action(
            "share_file",
            self._share_file,
            required_params=["file_id"],
            optional_params=["user_id", "email", "role", "public"]
        )
        
        self.register_action(
            "delete_file",
            self._delete_file,
            required_params=["file_id"],
            optional_params=["user_id", "permanent"]
        )
        
        self.register_action(
            "get_file_info",
            self._get_file_info,
            required_params=["file_id"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "search_files",
            self._search_files,
            required_params=["search_query"],
            optional_params=["user_id", "max_results", "file_type"]
        )
    
    def _get_access_token(self, user_id: str) -> Optional[str]:
        """Get OAuth2 access token for user"""
        try:
            if user_id:
                # Use same user mapping as Gmail tool
                user_storage = get_user_storage()
                google_email = user_storage.get_user_mapping(user_id, 'google')
                if google_email:
                    user_id = google_email
                    logger.info(f"Drive tool mapped user {user_id} to Google email {google_email}")
            
            response = requests.get(f"{self.base_url}/token/{user_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            else:
                logger.error(f"Token fetch failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def _upload_file(self, file_path: str, user_id: Optional[str] = None, 
                    folder_id: Optional[str] = None, description: Optional[str] = None,
                    public: bool = False, **kwargs) -> MCPToolResult:
        """Upload file to Google Drive"""
        try:
            file_path = Path(file_path)
            
            # Validate file exists
            if not file_path.exists():
                return MCPToolResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            # Get access token
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            # Prepare file metadata
            metadata = {
                'name': file_path.name,
            }
            
            if description:
                metadata['description'] = description
                
            if folder_id:
                metadata['parents'] = [folder_id]
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Upload file
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Use multipart upload for files
            files = {
                'metadata': (None, str(metadata).replace("'", '"'), 'application/json'),
                'file': (file_path.name, file_path.open('rb'), mime_type)
            }
            
            upload_url = 'https://www.googleapis.com/upload/drive/v3/files'
            params = {'uploadType': 'multipart'}
            
            response = requests.post(upload_url, headers=headers, files=files, params=params)
            
            if response.status_code in [200, 201]:
                file_data = response.json()
                
                # Set public permissions if requested
                if public:
                    self._make_file_public(file_data['id'], access_token)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "file_id": file_data['id'],
                        "name": file_data['name'],
                        "web_view_link": file_data.get('webViewLink'),
                        "web_content_link": file_data.get('webContentLink'),
                        "size": file_path.stat().st_size,
                        "mime_type": mime_type,
                        "public": public
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Upload failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _download_file(self, file_id: str, user_id: Optional[str] = None,
                      download_path: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Download file from Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get file metadata first
            metadata_url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
            metadata_response = requests.get(metadata_url, headers=headers)
            
            if metadata_response.status_code != 200:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to get file metadata: {metadata_response.text}"
                )
            
            file_metadata = metadata_response.json()
            filename = file_metadata['name']
            
            # Download file content
            download_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
            response = requests.get(download_url, headers=headers)
            
            if response.status_code == 200:
                # Determine download path
                if download_path:
                    save_path = Path(download_path) / filename
                else:
                    save_path = Path.cwd() / filename
                
                # Create directory if needed
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "file_id": file_id,
                        "filename": filename,
                        "download_path": str(save_path),
                        "size_bytes": len(response.content),
                        "mime_type": file_metadata.get('mimeType')
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Download failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error downloading file from Drive: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_files(self, user_id: Optional[str] = None, folder_id: Optional[str] = None,
                   query: Optional[str] = None, max_results: int = 10, 
                   file_type: Optional[str] = None, **kwargs) -> MCPToolResult:
        """List files in Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Build query parameters
            params = {
                'pageSize': min(max_results, 1000),
                'fields': 'files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,parents)'
            }
            
            # Build search query
            query_parts = []
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            if query:
                query_parts.append(f"name contains '{query}'")
            
            if file_type:
                if file_type.lower() == 'folder':
                    query_parts.append("mimeType='application/vnd.google-apps.folder'")
                elif file_type.lower() == 'document':
                    query_parts.append("mimeType='application/vnd.google-apps.document'")
                elif file_type.lower() == 'spreadsheet':
                    query_parts.append("mimeType='application/vnd.google-apps.spreadsheet'")
                elif file_type.lower() == 'image':
                    query_parts.append("mimeType contains 'image/'")
                else:
                    query_parts.append(f"mimeType contains '{file_type}'")
            
            if query_parts:
                params['q'] = ' and '.join(query_parts)
            
            # Make API request
            list_url = 'https://www.googleapis.com/drive/v3/files'
            response = requests.get(list_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('files', [])
                
                file_list = []
                for file in files:
                    file_info = {
                        "id": file['id'],
                        "name": file['name'],
                        "mime_type": file['mimeType'],
                        "size": file.get('size', 'N/A'),
                        "created_time": file['createdTime'],
                        "modified_time": file['modifiedTime'],
                        "web_view_link": file.get('webViewLink'),
                        "is_folder": file['mimeType'] == 'application/vnd.google-apps.folder'
                    }
                    file_list.append(file_info)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "files": file_list,
                        "total_count": len(file_list),
                        "query_used": params.get('q'),
                        "folder_id": folder_id
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"List files failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error listing Drive files: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _create_folder(self, folder_name: str, user_id: Optional[str] = None,
                      parent_folder_id: Optional[str] = None, 
                      description: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Create folder in Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare folder metadata
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if description:
                metadata['description'] = description
                
            if parent_folder_id:
                metadata['parents'] = [parent_folder_id]
            
            # Create folder
            create_url = 'https://www.googleapis.com/drive/v3/files'
            response = requests.post(create_url, headers=headers, json=metadata)
            
            if response.status_code in [200, 201]:
                folder_data = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "folder_id": folder_data['id'],
                        "name": folder_data['name'],
                        "web_view_link": folder_data.get('webViewLink'),
                        "parent_folder_id": parent_folder_id
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Folder creation failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error creating Drive folder: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _share_file(self, file_id: str, user_id: Optional[str] = None,
                   email: Optional[str] = None, role: str = "reader", 
                   public: bool = False, **kwargs) -> MCPToolResult:
        """Share file in Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            permissions = []
            
            # Share with specific email
            if email:
                permission_data = {
                    'type': 'user',
                    'role': role,  # reader, writer, commenter
                    'emailAddress': email
                }
                permissions.append(permission_data)
            
            # Make public
            if public:
                permission_data = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                permissions.append(permission_data)
            
            if not permissions:
                return MCPToolResult(
                    success=False,
                    error="No sharing permissions specified"
                )
            
            # Apply permissions
            results = []
            for permission in permissions:
                permission_url = f'https://www.googleapis.com/drive/v3/files/{file_id}/permissions'
                response = requests.post(permission_url, headers=headers, json=permission)
                
                if response.status_code in [200, 201]:
                    results.append({
                        "type": permission['type'],
                        "role": permission['role'],
                        "email": permission.get('emailAddress', 'anyone'),
                        "success": True
                    })
                else:
                    results.append({
                        "type": permission['type'],
                        "role": permission['role'],
                        "email": permission.get('emailAddress', 'anyone'),
                        "success": False,
                        "error": response.text
                    })
            
            return MCPToolResult(
                success=True,
                data={
                    "file_id": file_id,
                    "permissions": results,
                    "all_successful": all(r['success'] for r in results)
                }
            )
            
        except Exception as e:
            logger.error(f"Error sharing Drive file: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _delete_file(self, file_id: str, user_id: Optional[str] = None,
                    permanent: bool = False, **kwargs) -> MCPToolResult:
        """Delete file from Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Delete file (moves to trash by default)
            delete_url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
            response = requests.delete(delete_url, headers=headers)
            
            if response.status_code == 200:
                return MCPToolResult(
                    success=True,
                    data={
                        "file_id": file_id,
                        "deleted": True,
                        "permanent": permanent
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Delete failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error deleting Drive file: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_file_info(self, file_id: str, user_id: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Get detailed file information"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get file metadata
            params = {
                'fields': 'id,name,mimeType,size,createdTime,modifiedTime,webViewLink,webContentLink,parents,description,owners,permissions'
            }
            
            info_url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
            response = requests.get(info_url, headers=headers, params=params)
            
            if response.status_code == 200:
                file_data = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "id": file_data['id'],
                        "name": file_data['name'],
                        "mime_type": file_data['mimeType'],
                        "size": file_data.get('size', 'N/A'),
                        "created_time": file_data['createdTime'],
                        "modified_time": file_data['modifiedTime'],
                        "web_view_link": file_data.get('webViewLink'),
                        "web_content_link": file_data.get('webContentLink'),
                        "parents": file_data.get('parents', []),
                        "description": file_data.get('description'),
                        "owners": file_data.get('owners', []),
                        "is_folder": file_data['mimeType'] == 'application/vnd.google-apps.folder'
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Get file info failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error getting Drive file info: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _search_files(self, search_query: str, user_id: Optional[str] = None,
                     max_results: int = 20, file_type: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Search files in Google Drive"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Drive access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Build search query
            query_parts = [f"name contains '{search_query}'"]
            
            if file_type:
                if file_type.lower() == 'folder':
                    query_parts.append("mimeType='application/vnd.google-apps.folder'")
                elif file_type.lower() == 'document':
                    query_parts.append("mimeType='application/vnd.google-apps.document'")
                else:
                    query_parts.append(f"mimeType contains '{file_type}'")
            
            params = {
                'q': ' and '.join(query_parts),
                'pageSize': min(max_results, 1000),
                'fields': 'files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)'
            }
            
            search_url = 'https://www.googleapis.com/drive/v3/files'
            response = requests.get(search_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('files', [])
                
                return MCPToolResult(
                    success=True,
                    data={
                        "search_query": search_query,
                        "results_count": len(files),
                        "files": files
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Search failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error searching Drive files: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _make_file_public(self, file_id: str, access_token: str):
        """Helper method to make file public"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            permission_data = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            permission_url = f'https://www.googleapis.com/drive/v3/files/{file_id}/permissions'
            requests.post(permission_url, headers=headers, json=permission_data)
            
        except Exception as e:
            logger.warning(f"Failed to make file public: {str(e)}")
    
    def health_check(self) -> MCPToolResult:
        """Check if Google Drive tool is working properly"""
        try:
            # Test OAuth2 endpoint availability
            response = requests.get(f"{self.base_url}/health", timeout=5)
            
            if response.status_code == 200:
                return MCPToolResult(
                    success=True,
                    data={
                        "status": "healthy",
                        "oauth2_endpoint": "available",
                        "drive_api": "ready"
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="OAuth2 endpoint not available"
                )
        except Exception as e:
            return MCPToolResult(
                success=False,
                error=f"Health check failed: {str(e)}"
            )

def register_tool(registry):
    """Register the Google Drive tool with the registry"""
    tool = GoogleDriveTool()
    return registry.register_tool(tool)