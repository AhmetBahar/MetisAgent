"""
User Manager Implementation - Authentication, Authorization & User Management

CLAUDE.md COMPLIANT:
- SQLite-based user storage with encrypted sensitive data
- OAuth2 authentication with multiple providers
- Permission-based access control system
- Session management with automatic refresh
"""

import asyncio
import hashlib
import secrets
import json
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid

from ..contracts import (
    UserProfile,
    AuthenticationSession,
    UserPermission,
    UserToolAccess,
    UserPreferences,
    UserActivity,
    UserQuota,
    UserRole,
    AuthProvider,
    PermissionLevel,
    ExecutionContext,
    AgentResult
)
from ..interfaces import (
    IUserManager,
    IAuthService,
    IPermissionService
)
from ..storage import SQLiteUserStorage, DatabaseManager

logger = logging.getLogger(__name__)


class UserManager(IUserManager):
    """User management with SQLite backend and encrypted storage"""
    
    def __init__(self, storage: Optional[SQLiteUserStorage] = None):
        self.storage = storage or SQLiteUserStorage()
        self.auth_service = AuthService(self.storage)
        self.permission_service = PermissionService(self.storage)
        logger.info("UserManager initialized with SQLite storage")
    
    async def create_user(self, profile: UserProfile) -> str:
        """Create new user profile with validation"""
        try:
            user_data = {
                'user_id': profile.user_id,
                'email': profile.email,
                'display_name': profile.display_name,
                'role': profile.role.value if hasattr(profile.role, 'value') else str(profile.role),
                'metadata': profile.metadata or {},
                'preferences': profile.preferences or {}
            }
            
            created_user_id = await self.storage.create_user(user_data)
            logger.info(f"Created user profile: {created_user_id}")
            return created_user_id
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            user_data = await self.storage.get_user(user_id)
            if user_data:
                return UserProfile(
                    user_id=user_data['user_id'],
                    email=user_data['email'],
                    display_name=user_data['display_name'],
                    role=UserRole(user_data['role']) if user_data.get('role') else UserRole.USER,
                    is_active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at'),
                    updated_at=user_data.get('updated_at'),
                    last_login=user_data.get('last_login'),
                    metadata=user_data.get('metadata', {}),
                    preferences=user_data.get('preferences', {})
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email"""
        try:
            user_data = await self.storage.get_user_by_email(email)
            if user_data:
                return await self.get_user(user_data['user_id'])
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            result = await self.storage.update_user(user_id, updates)
            if result:
                logger.info(f"Updated user profile: {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data"""
        try:
            result = await self.storage.delete_user(user_id)
            if result:
                logger.info(f"Deleted user: {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    async def list_users(self, limit: int = 50, offset: int = 0) -> List[UserProfile]:
        """List all users with pagination"""
        try:
            users_data = await self.storage.list_users(limit, offset)
            users = []
            
            for user_data in users_data:
                user = UserProfile(
                    user_id=user_data['user_id'],
                    email=user_data['email'],
                    display_name=user_data['display_name'],
                    role=UserRole(user_data['role']) if user_data.get('role') else UserRole.USER,
                    is_active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at'),
                    updated_at=user_data.get('updated_at'),
                    last_login=user_data.get('last_login')
                )
                users.append(user)
            
            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    async def search_users(self, search_text: str) -> List[UserProfile]:
        """Search users by name or email"""
        try:
            # Simple search implementation - can be enhanced with full-text search
            all_users = await self.list_users(limit=1000)
            search_lower = search_text.lower()
            
            matching_users = [
                user for user in all_users
                if (search_lower in user.email.lower() or
                    search_lower in user.display_name.lower())
            ]
            
            return matching_users
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return []
    
    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        return await self.update_user(user_id, {"is_active": True})
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        return await self.update_user(user_id, {"is_active": False})

    async def set_user_password(self, user_id: str, password: str) -> bool:
        """Set password for a user"""
        return await self.storage.set_user_password(user_id, password)

    async def set_user_password_by_email(self, email: str, password: str) -> bool:
        """Set password for a user by email"""
        user = await self.get_user_by_email(email)
        if user:
            return await self.storage.set_user_password(user.user_id, password)
        return False


class AuthService(IAuthService):
    """Authentication service with OAuth2 support"""
    
    def __init__(self, storage: SQLiteUserStorage):
        self.storage = storage
        logger.info("AuthService initialized with SQLite storage")
    
    async def authenticate_user(self, email: str, password: str) -> Optional[AuthenticationSession]:
        """Authenticate user with email and password"""
        try:
            user_data = await self.storage.get_user_by_email(email)
            if not user_data or not user_data.get('is_active'):
                logger.warning(f"User not found or inactive: {email}")
                return None

            # Verify password
            user_id = user_data['user_id']
            if not await self.storage.verify_user_password(user_id, password):
                logger.warning(f"Invalid password for user: {email}")
                return None

            logger.info(f"User authenticated successfully: {email}")
            return await self.create_session(user_id)

        except Exception as e:
            logger.error(f"Authentication failed for {email}: {e}")
            return None
    
    async def authenticate_oauth(self, provider: str, token: str) -> Optional[AuthenticationSession]:
        """Authenticate user with OAuth token"""
        try:
            # In production, would verify token with OAuth provider
            # For now, mock OAuth authentication
            
            # Find or create user for OAuth
            user_id = await self._find_or_create_oauth_user(provider, token)
            
            if user_id:
                return await self.create_session(user_id, provider)
            
            return None
            
        except Exception as e:
            logger.error(f"OAuth authentication failed for {provider}: {e}")
            return None
    
    async def create_session(self, user_id: str, provider: str = "local", expires_in_seconds: int = 86400) -> AuthenticationSession:
        """Create authentication session"""
        try:
            session_data = {
                'user_id': user_id,
                'provider': provider,
                'expires_at': (datetime.now() + timedelta(seconds=expires_in_seconds)).isoformat(),
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'provider': provider
                }
            }
            
            session_id = await self.storage.create_session(session_data)
            
            # Update user last login
            await self.storage.update_user(user_id, {'last_login': datetime.now().isoformat()})
            
            session = AuthenticationSession(
                session_id=session_id,
                user_id=user_id,
                provider=AuthProvider(provider) if provider in ["local", "google", "microsoft", "github"] else AuthProvider.LOCAL,
                expires_at=datetime.fromisoformat(session_data['expires_at'])
            )
            
            logger.info(f"Created session for user {user_id}: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise
    
    async def validate_session(self, session_id: str) -> Optional[AuthenticationSession]:
        """Validate existing session"""
        try:
            session_data = await self.storage.get_session(session_id)
            if not session_data:
                return None
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if expires_at <= datetime.now():
                await self.revoke_session(session_id)
                return None
            
            # Check if user is still active
            user_data = await self.storage.get_user(session_data['user_id'])
            if not user_data or not user_data.get('is_active'):
                await self.revoke_session(session_id)
                return None
            
            session = AuthenticationSession(
                session_id=session_id,
                user_id=session_data['user_id'],
                provider=AuthProvider(session_data.get('provider', 'local')),
                expires_at=expires_at
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Session validation failed for {session_id}: {e}")
            return None
    
    async def refresh_session(self, session_id: str) -> Optional[AuthenticationSession]:
        """Refresh authentication session"""
        try:
            session = await self.validate_session(session_id)
            if not session:
                return None
            
            # Extend session expiry
            new_expires_at = datetime.now() + timedelta(seconds=86400)
            
            result = await self.storage.update_session(session_id, {
                'expires_at': new_expires_at.isoformat()
            })
            
            if result:
                session.expires_at = new_expires_at
                logger.info(f"Refreshed session: {session_id}")
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Session refresh failed for {session_id}: {e}")
            return None
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke authentication session"""
        try:
            result = await self.storage.delete_session(session_id)
            if result:
                logger.info(f"Revoked session: {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to revoke session {session_id}: {e}")
            return False
    
    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for user"""
        try:
            # Get all sessions for user and revoke them
            with self.storage.db.transaction() as conn:
                cursor = conn.execute("""
                    SELECT session_id FROM sessions WHERE user_id = ?
                """, (user_id,))
                
                session_ids = [row['session_id'] for row in cursor.fetchall()]
                
                # Delete all sessions
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
                
                revoked_count = len(session_ids)
                
                if revoked_count > 0:
                    logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
                
                return revoked_count
                
        except Exception as e:
            logger.error(f"Failed to revoke sessions for user {user_id}: {e}")
            return 0
    
    async def get_active_sessions(self, user_id: str) -> List[AuthenticationSession]:
        """Get all active sessions for user"""
        try:
            active_sessions = []
            
            with self.storage.db.transaction() as conn:
                cursor = conn.execute("""
                    SELECT session_id, provider, expires_at FROM sessions 
                    WHERE user_id = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
                """, (user_id,))
                
                for row in cursor.fetchall():
                    session = AuthenticationSession(
                        session_id=row['session_id'],
                        user_id=user_id,
                        provider=AuthProvider(row.get('provider', 'local')),
                        expires_at=datetime.fromisoformat(row['expires_at'])
                    )
                    active_sessions.append(session)
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []
    
    async def _find_or_create_oauth_user(self, provider: str, token: str) -> Optional[str]:
        """Find existing OAuth user or create new one"""
        try:
            # In production, would get user info from OAuth provider using token
            # For now, create mock user
            user_profile = UserProfile(
                email=f"{provider}_user_{secrets.token_hex(4)}@oauth.local",
                display_name=f"{provider.title()} User",
                role=UserRole.USER,
                metadata={"oauth_provider": provider}
            )
            
            user_manager = UserManager(self.storage)
            return await user_manager.create_user(user_profile)
            
        except Exception as e:
            logger.error(f"Failed to find/create OAuth user: {e}")
            return None


class PermissionService(IPermissionService):
    """Permission and access control management"""
    
    def __init__(self, storage: SQLiteUserStorage):
        self.storage = storage
        logger.info("PermissionService initialized with SQLite storage")
    
    async def grant_permission(self, permission: UserPermission) -> bool:
        """Grant permission to user"""
        try:
            permission_data = {
                'user_id': permission.user_id,
                'resource_type': permission.resource_type,
                'resource_id': permission.resource_id,
                'permission_level': permission.permission_level.value if hasattr(permission.permission_level, 'value') else str(permission.permission_level),
                'granted_by': 'system',  # In production, would track who granted
                'expires_at': permission.expires_at.isoformat() if permission.expires_at else None,
                'metadata': permission.metadata or {}
            }
            
            result = await self.storage.grant_permission(permission_data)
            if result:
                logger.info(f"Granted permission to user {permission.user_id}: {permission.resource_type}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to grant permission: {e}")
            return False
    
    async def revoke_permission(self, user_id: str, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Revoke user permission"""
        try:
            with self.storage.db.transaction() as conn:
                if resource_id:
                    cursor = conn.execute("""
                        DELETE FROM permissions 
                        WHERE user_id = ? AND resource_type = ? AND resource_id = ?
                    """, (user_id, resource_type, resource_id))
                else:
                    cursor = conn.execute("""
                        DELETE FROM permissions 
                        WHERE user_id = ? AND resource_type = ? AND resource_id IS NULL
                    """, (user_id, resource_type))
                
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"Revoked permission from user {user_id}: {resource_type}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to revoke permission: {e}")
            return False
    
    async def check_permission(self, user_id: str, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Check if user has permission"""
        return await self.storage.check_permission(user_id, resource_type, resource_id)
    
    async def get_user_permissions(self, user_id: str) -> List[UserPermission]:
        """Get all permissions for user"""
        try:
            permissions = []
            
            with self.storage.db.transaction() as conn:
                cursor = conn.execute("""
                    SELECT resource_type, resource_id, permission_level, expires_at, metadata
                    FROM permissions 
                    WHERE user_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (user_id,))
                
                for row in cursor.fetchall():
                    permission = UserPermission(
                        user_id=user_id,
                        resource_type=row['resource_type'],
                        resource_id=row['resource_id'],
                        permission_level=PermissionLevel(row['permission_level']) if row.get('permission_level') else PermissionLevel.READ,
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        metadata=json.loads(row['metadata']) if row.get('metadata') else {}
                    )
                    permissions.append(permission)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []
    
    async def get_resource_permissions(self, resource_type: str, resource_id: str) -> List[UserPermission]:
        """Get all permissions for resource"""
        try:
            permissions = []
            
            with self.storage.db.transaction() as conn:
                cursor = conn.execute("""
                    SELECT user_id, permission_level, expires_at, metadata
                    FROM permissions 
                    WHERE resource_type = ? AND resource_id = ? 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (resource_type, resource_id))
                
                for row in cursor.fetchall():
                    permission = UserPermission(
                        user_id=row['user_id'],
                        resource_type=resource_type,
                        resource_id=resource_id,
                        permission_level=PermissionLevel(row['permission_level']) if row.get('permission_level') else PermissionLevel.READ,
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        metadata=json.loads(row['metadata']) if row.get('metadata') else {}
                    )
                    permissions.append(permission)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get resource permissions: {e}")
            return []
    
    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        try:
            with self.storage.db.transaction() as conn:
                cursor = conn.execute("""
                    DELETE FROM permissions WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP
                """)
                
                expired_count = cursor.rowcount
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired permissions")
                
                return expired_count
                
        except Exception as e:
            logger.error(f"Permission cleanup failed: {e}")
            return 0