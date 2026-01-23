"""
Base Types Module - Core Data Contracts

CLAUDE.md COMPLIANT:
- Strong type safety with Pydantic v2
- Immutable data structures
- Self-documenting with type hints
- No hard-coded values
- Generic result types for reusability
"""

from typing import Any, Dict, Optional, Generic, TypeVar, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

T = TypeVar('T')


class ExecutionStatus(str, Enum):
    """Status enumeration for execution tracking"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Priority levels for tasks and operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentResult(BaseModel, Generic[T]):
    """Generic result wrapper for all agent operations"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time_ms: Optional[float] = None
    trace_id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        frozen = True


class ValidationError(BaseModel):
    """Structured validation error information"""
    field: str
    message: str
    value: Optional[Any] = None
    error_type: str

    class Config:
        frozen = True


class ExecutionContext(BaseModel):
    """Context information for tool execution"""
    user_id: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    system_prompt: Optional[str] = None
    application_id: Optional[str] = None

    class Config:
        frozen = True


class HealthStatus(BaseModel):
    """Health status for components"""
    healthy: bool
    component: str
    message: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class ResourceUsage(BaseModel):
    """Resource usage metrics"""
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    disk_mb: Optional[float] = None
    network_kb: Optional[float] = None
    active_connections: Optional[int] = None

    class Config:
        frozen = True


class LogEntry(BaseModel):
    """Structured log entry"""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: str
    message: str
    component: str
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True