"""
User Contracts - User Management Data Models

CLAUDE.md COMPLIANT:
- Secure user data handling
- Immutable user profiles
- Strong authentication contracts
- Privacy-focused design
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from uuid import uuid4

from .base_types import ExecutionStatus


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"


class AuthProvider(str, Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"


class PermissionLevel(str, Enum):
    """Permission levels"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class UserProfile(BaseModel):
    """User profile information"""
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    display_name: str
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class AuthenticationSession(BaseModel):
    """User authentication session"""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    provider: AuthProvider
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    is_active: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at

    class Config:
        frozen = True


class UserPermission(BaseModel):
    """User permission for a specific resource"""
    user_id: str
    resource_type: str
    resource_id: Optional[str] = None
    permission_level: PermissionLevel
    granted_by: str
    granted_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if permission is expired"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    class Config:
        frozen = True


class UserToolAccess(BaseModel):
    """User access to specific tools"""
    user_id: str
    tool_name: str
    capabilities: List[str] = Field(default_factory=list)
    granted_at: datetime = Field(default_factory=datetime.now)
    granted_by: str
    is_enabled: bool = True
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        frozen = True


class UserPreferences(BaseModel):
    """User preferences and settings"""
    user_id: str
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    notifications: Dict[str, bool] = Field(default_factory=dict)
    ui_settings: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True


class ConversationContext(BaseModel):
    """User conversation context"""
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    context_data: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0

    class Config:
        frozen = False


class UserActivity(BaseModel):
    """User activity log entry"""
    activity_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    status: ExecutionStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None

    class Config:
        frozen = True


class UserQuota(BaseModel):
    """User resource quotas and usage"""
    user_id: str
    resource_type: str
    quota_limit: int
    current_usage: int = 0
    reset_period: str = "daily"  # daily, weekly, monthly
    last_reset: datetime = Field(default_factory=datetime.now)
    
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.current_usage >= self.quota_limit
    
    def get_remaining_quota(self) -> int:
        """Get remaining quota"""
        return max(0, self.quota_limit - self.current_usage)

    class Config:
        frozen = False