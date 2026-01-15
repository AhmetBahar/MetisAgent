"""
User Management Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract user management contracts
- Secure authentication interfaces
- Permission-based access control
- Privacy-focused design
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime

from ..contracts import (
    UserProfile,
    AuthenticationSession,
    UserPermission,
    UserToolAccess,
    UserPreferences,
    UserActivity,
    UserQuota,
    ExecutionContext
)


class IUserManager(ABC):
    """Abstract interface for user management"""
    
    @abstractmethod
    async def create_user(self, profile: UserProfile) -> str:
        """Create new user profile"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data"""
        pass
    
    @abstractmethod
    async def list_users(self, limit: int = 50, offset: int = 0) -> List[UserProfile]:
        """List all users with pagination"""
        pass
    
    @abstractmethod
    async def search_users(self, search_text: str) -> List[UserProfile]:
        """Search users by name or email"""
        pass
    
    @abstractmethod
    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        pass
    
    @abstractmethod
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        pass


class IAuthService(ABC):
    """Abstract interface for authentication"""
    
    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> Optional[AuthenticationSession]:
        """Authenticate user with credentials"""
        pass
    
    @abstractmethod
    async def authenticate_oauth(self, provider: str, token: str) -> Optional[AuthenticationSession]:
        """Authenticate user with OAuth token"""
        pass
    
    @abstractmethod
    async def create_session(self, user_id: str, expires_in_seconds: int = 86400) -> AuthenticationSession:
        """Create authentication session"""
        pass
    
    @abstractmethod
    async def validate_session(self, session_id: str) -> Optional[AuthenticationSession]:
        """Validate existing session"""
        pass
    
    @abstractmethod
    async def refresh_session(self, session_id: str) -> Optional[AuthenticationSession]:
        """Refresh authentication session"""
        pass
    
    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke authentication session"""
        pass
    
    @abstractmethod
    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for user"""
        pass
    
    @abstractmethod
    async def get_active_sessions(self, user_id: str) -> List[AuthenticationSession]:
        """Get all active sessions for user"""
        pass


class IPermissionService(ABC):
    """Abstract interface for permission management"""
    
    @abstractmethod
    async def grant_permission(self, permission: UserPermission) -> bool:
        """Grant permission to user"""
        pass
    
    @abstractmethod
    async def revoke_permission(self, user_id: str, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Revoke user permission"""
        pass
    
    @abstractmethod
    async def check_permission(self, user_id: str, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Check if user has permission"""
        pass
    
    @abstractmethod
    async def get_user_permissions(self, user_id: str) -> List[UserPermission]:
        """Get all permissions for user"""
        pass
    
    @abstractmethod
    async def get_resource_permissions(self, resource_type: str, resource_id: str) -> List[UserPermission]:
        """Get all permissions for resource"""
        pass
    
    @abstractmethod
    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        pass


class IUserToolService(ABC):
    """Abstract interface for user tool access management"""
    
    @abstractmethod
    async def grant_tool_access(self, access: UserToolAccess) -> bool:
        """Grant tool access to user"""
        pass
    
    @abstractmethod
    async def revoke_tool_access(self, user_id: str, tool_name: str) -> bool:
        """Revoke tool access from user"""
        pass
    
    @abstractmethod
    async def check_tool_access(self, user_id: str, tool_name: str, capability: str) -> bool:
        """Check if user can access tool capability"""
        pass
    
    @abstractmethod
    async def get_user_tools(self, user_id: str) -> List[UserToolAccess]:
        """Get all tools accessible by user"""
        pass
    
    @abstractmethod
    async def update_tool_access(self, user_id: str, tool_name: str, updates: Dict[str, Any]) -> bool:
        """Update user tool access settings"""
        pass


class IUserPreferencesService(ABC):
    """Abstract interface for user preferences management"""
    
    @abstractmethod
    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        pass
    
    @abstractmethod
    async def update_preferences(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user preferences"""
        pass
    
    @abstractmethod
    async def reset_preferences(self, user_id: str) -> bool:
        """Reset preferences to defaults"""
        pass
    
    @abstractmethod
    async def export_preferences(self, user_id: str) -> Dict[str, Any]:
        """Export user preferences"""
        pass
    
    @abstractmethod
    async def import_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Import user preferences"""
        pass


class IUserActivityService(ABC):
    """Abstract interface for user activity tracking"""
    
    @abstractmethod
    async def log_activity(self, activity: UserActivity) -> str:
        """Log user activity"""
        pass
    
    @abstractmethod
    async def get_user_activity(self, user_id: str, limit: int = 50) -> List[UserActivity]:
        """Get user activity history"""
        pass
    
    @abstractmethod
    async def search_activity(self, user_id: str, search_params: Dict[str, Any]) -> List[UserActivity]:
        """Search user activity with filters"""
        pass
    
    @abstractmethod
    async def get_activity_summary(self, user_id: str, date_range: str) -> Dict[str, Any]:
        """Get activity summary for date range"""
        pass
    
    @abstractmethod
    async def cleanup_old_activity(self, retention_days: int = 90) -> int:
        """Clean up old activity logs"""
        pass


class IUserQuotaService(ABC):
    """Abstract interface for user quota management"""
    
    @abstractmethod
    async def set_quota(self, quota: UserQuota) -> bool:
        """Set user quota for resource"""
        pass
    
    @abstractmethod
    async def get_quota(self, user_id: str, resource_type: str) -> Optional[UserQuota]:
        """Get user quota for resource"""
        pass
    
    @abstractmethod
    async def update_usage(self, user_id: str, resource_type: str, usage_delta: int) -> bool:
        """Update resource usage"""
        pass
    
    @abstractmethod
    async def check_quota(self, user_id: str, resource_type: str, requested_amount: int = 1) -> bool:
        """Check if user has quota available"""
        pass
    
    @abstractmethod
    async def reset_quota(self, user_id: str, resource_type: str) -> bool:
        """Reset quota usage to zero"""
        pass
    
    @abstractmethod
    async def get_user_quotas(self, user_id: str) -> List[UserQuota]:
        """Get all quotas for user"""
        pass
    
    @abstractmethod
    async def reset_expired_quotas(self) -> int:
        """Reset quotas that have reached reset period"""
        pass