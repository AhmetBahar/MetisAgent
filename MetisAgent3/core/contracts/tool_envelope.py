"""
Tool Call Envelope - Standard Request/Response Wrapper

CLAUDE.md COMPLIANT:
- Idempotency support with request tracking
- Multi-tenant context (company_id, site_id, user_id)
- Dry-run capability for previews
- Transaction support for rollback
- Policy-based confirmation requirements
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4


class RiskLevel(str, Enum):
    """Risk level for tool operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfirmationPolicy(str, Enum):
    """Policy for operation confirmation requirements"""
    AUTO = "auto"           # Execute automatically, no confirmation
    ROLE_CHECK = "role_check"  # Check user role/permission
    CONFIRM = "confirm"     # Require user confirmation
    TWO_PERSON = "two_person"  # Require approval from another person


class OperationType(str, Enum):
    """Type of operation for auditing"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    CONFIGURE = "configure"


class IdempotencyStatus(str, Enum):
    """Status of idempotency check"""
    NEW = "new"             # First time seeing this request
    DUPLICATE = "duplicate" # Already processed, returning cached result
    IN_PROGRESS = "in_progress"  # Currently being processed
    EXPIRED = "expired"     # Previous result expired, treating as new


class ToolCallContext(BaseModel):
    """
    Multi-tenant context for tool execution.

    Includes all organizational hierarchy and tracing information.
    """
    company_id: str
    site_id: Optional[str] = None
    user_id: str
    role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    locale: str = "en-US"
    timezone: str = "UTC"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class ToolCallEnvelope(BaseModel):
    """
    Standard envelope wrapping all tool calls.

    Provides idempotency, tracing, and policy enforcement.
    """
    # Identification
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    idempotency_key: Optional[str] = None  # Client-provided for deduplication
    correlation_id: Optional[str] = None   # Links related requests

    # Tool information
    tool_name: str
    capability_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Context
    context: ToolCallContext

    # Execution options
    dry_run: bool = False  # Preview without executing
    timeout_seconds: int = 30
    priority: str = "medium"

    # Tracing
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_span_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    class Config:
        frozen = True

    def get_idempotency_key(self) -> str:
        """Get or generate idempotency key"""
        if self.idempotency_key:
            return self.idempotency_key
        # Generate from request signature
        return f"{self.tool_name}:{self.capability_name}:{self.context.user_id}:{hash(str(sorted(self.parameters.items())))}"


class ToolCallResult(BaseModel):
    """
    Standard result envelope for tool responses.

    Includes execution metadata and rollback information.
    """
    # Request reference
    request_id: str
    idempotency_key: Optional[str] = None

    # Result
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Execution info
    operation_type: OperationType
    risk_level: RiskLevel = RiskLevel.LOW
    side_effects: List[str] = Field(default_factory=list)  # What was modified

    # Idempotency
    idempotency_status: IdempotencyStatus = IdempotencyStatus.NEW
    cached_at: Optional[datetime] = None  # When result was cached (for duplicates)

    # Rollback support
    rollback_token: Optional[str] = None  # Token to undo this operation
    rollback_expires_at: Optional[datetime] = None

    # Confirmation (if required)
    requires_confirmation: bool = False
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.AUTO
    confirmation_message: Optional[str] = None

    # Tracing
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    execution_time_ms: float = 0.0

    # Timestamps
    completed_at: datetime = Field(default_factory=datetime.now)

    # Audit
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        frozen = False  # Allow updates during processing


class IdempotencyRecord(BaseModel):
    """
    Record of a processed request for idempotency tracking.

    Stored in database/cache for deduplication.
    """
    idempotency_key: str
    request_id: str
    tool_name: str
    capability_name: str
    company_id: str
    user_id: str
    status: IdempotencyStatus
    result: Optional[ToolCallResult] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime  # When this record expires
    last_accessed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class ToolMetadataExtended(BaseModel):
    """
    Extended tool metadata with risk and policy information.

    Augments basic ToolMetadata with security and confirmation settings.
    """
    tool_name: str
    version: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.AUTO
    side_effects: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None
    idempotent_capabilities: List[str] = Field(default_factory=list)  # Capabilities that are naturally idempotent
    computer_mode: Optional[str] = None  # "off", "restricted", "dev" for computer tools

    class Config:
        frozen = True
