"""
Tool Events Service - Socket.IO Events for Tool Calls

Implements real-time event emission for tool execution lifecycle:
- tool_call_started: When a tool execution begins
- tool_call_completed: When a tool execution completes successfully
- tool_call_failed: When a tool execution fails
- tool_call_progress: For long-running operations (optional)

Events include trace_id for correlation and observability.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class ToolEventType(str, Enum):
    """Types of tool call events"""
    STARTED = "tool_call_started"
    COMPLETED = "tool_call_completed"
    FAILED = "tool_call_failed"
    PROGRESS = "tool_call_progress"
    CONFIRMATION_REQUIRED = "tool_call_confirmation_required"
    CONFIRMATION_RECEIVED = "tool_call_confirmation_received"
    CANCELLED = "tool_call_cancelled"


@dataclass
class ToolEvent:
    """Tool call event data"""
    event_type: ToolEventType
    trace_id: str
    request_id: str
    tool_name: str
    capability_name: str
    user_id: str
    company_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Optional fields based on event type
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: Optional[float] = None
    progress_percent: Optional[int] = None
    progress_message: Optional[str] = None
    confirmation_message: Optional[str] = None
    risk_level: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Socket.IO emission"""
        data = {
            "event_type": self.event_type.value,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "capability_name": self.capability_name,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "timestamp": self.timestamp.isoformat()
        }

        # Add optional fields if present
        if self.parameters is not None:
            data["parameters"] = self.parameters
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        if self.error_code is not None:
            data["error_code"] = self.error_code
        if self.execution_time_ms is not None:
            data["execution_time_ms"] = self.execution_time_ms
        if self.progress_percent is not None:
            data["progress_percent"] = self.progress_percent
        if self.progress_message is not None:
            data["progress_message"] = self.progress_message
        if self.confirmation_message is not None:
            data["confirmation_message"] = self.confirmation_message
        if self.risk_level is not None:
            data["risk_level"] = self.risk_level
        if self.metadata:
            data["metadata"] = self.metadata

        return data


class ToolEventsService:
    """
    Service for emitting tool call events via Socket.IO.

    Provides real-time visibility into tool execution for the frontend.
    """

    def __init__(self, socketio=None):
        """
        Initialize tool events service.

        Args:
            socketio: Flask-SocketIO instance (optional, can be set later)
        """
        self.socketio = socketio
        self._event_handlers: Dict[ToolEventType, List[Callable]] = {
            event_type: [] for event_type in ToolEventType
        }
        self._event_history: List[ToolEvent] = []
        self._max_history = 1000

    def set_socketio(self, socketio):
        """Set the Socket.IO instance"""
        self.socketio = socketio

    def register_handler(self, event_type: ToolEventType, handler: Callable):
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Callback function(event: ToolEvent)
        """
        self._event_handlers[event_type].append(handler)

    def unregister_handler(self, event_type: ToolEventType, handler: Callable):
        """Unregister an event handler"""
        if handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)

    def emit_started(
        self,
        trace_id: str,
        request_id: str,
        tool_name: str,
        capability_name: str,
        user_id: str,
        company_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        risk_level: Optional[str] = None
    ):
        """
        Emit tool_call_started event.

        Args:
            trace_id: Trace ID for correlation
            request_id: Request ID
            tool_name: Name of the tool
            capability_name: Name of the capability
            user_id: User ID
            company_id: Company ID
            parameters: Tool parameters (sanitized)
            risk_level: Risk level of the operation
        """
        event = ToolEvent(
            event_type=ToolEventType.STARTED,
            trace_id=trace_id,
            request_id=request_id,
            tool_name=tool_name,
            capability_name=capability_name,
            user_id=user_id,
            company_id=company_id,
            parameters=self._sanitize_parameters(parameters),
            risk_level=risk_level
        )
        self._emit_event(event)

    def emit_completed(
        self,
        trace_id: str,
        request_id: str,
        tool_name: str,
        capability_name: str,
        user_id: str,
        company_id: str,
        result: Any,
        execution_time_ms: float
    ):
        """
        Emit tool_call_completed event.

        Args:
            trace_id: Trace ID for correlation
            request_id: Request ID
            tool_name: Name of the tool
            capability_name: Name of the capability
            user_id: User ID
            company_id: Company ID
            result: Tool execution result (sanitized)
            execution_time_ms: Execution time in milliseconds
        """
        event = ToolEvent(
            event_type=ToolEventType.COMPLETED,
            trace_id=trace_id,
            request_id=request_id,
            tool_name=tool_name,
            capability_name=capability_name,
            user_id=user_id,
            company_id=company_id,
            result=self._sanitize_result(result),
            execution_time_ms=execution_time_ms
        )
        self._emit_event(event)

    def emit_failed(
        self,
        trace_id: str,
        request_id: str,
        tool_name: str,
        capability_name: str,
        user_id: str,
        company_id: str,
        error: str,
        error_code: Optional[str] = None,
        execution_time_ms: Optional[float] = None
    ):
        """
        Emit tool_call_failed event.

        Args:
            trace_id: Trace ID for correlation
            request_id: Request ID
            tool_name: Name of the tool
            capability_name: Name of the capability
            user_id: User ID
            company_id: Company ID
            error: Error message
            error_code: Error code
            execution_time_ms: Execution time in milliseconds
        """
        event = ToolEvent(
            event_type=ToolEventType.FAILED,
            trace_id=trace_id,
            request_id=request_id,
            tool_name=tool_name,
            capability_name=capability_name,
            user_id=user_id,
            company_id=company_id,
            error=error,
            error_code=error_code,
            execution_time_ms=execution_time_ms
        )
        self._emit_event(event)

    def emit_progress(
        self,
        trace_id: str,
        request_id: str,
        tool_name: str,
        capability_name: str,
        user_id: str,
        company_id: str,
        progress_percent: int,
        progress_message: Optional[str] = None
    ):
        """
        Emit tool_call_progress event.

        Args:
            trace_id: Trace ID for correlation
            request_id: Request ID
            tool_name: Name of the tool
            capability_name: Name of the capability
            user_id: User ID
            company_id: Company ID
            progress_percent: Progress percentage (0-100)
            progress_message: Optional progress message
        """
        event = ToolEvent(
            event_type=ToolEventType.PROGRESS,
            trace_id=trace_id,
            request_id=request_id,
            tool_name=tool_name,
            capability_name=capability_name,
            user_id=user_id,
            company_id=company_id,
            progress_percent=progress_percent,
            progress_message=progress_message
        )
        self._emit_event(event)

    def emit_confirmation_required(
        self,
        trace_id: str,
        request_id: str,
        tool_name: str,
        capability_name: str,
        user_id: str,
        company_id: str,
        confirmation_message: str,
        risk_level: str,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Emit tool_call_confirmation_required event.

        Args:
            trace_id: Trace ID for correlation
            request_id: Request ID
            tool_name: Name of the tool
            capability_name: Name of the capability
            user_id: User ID
            company_id: Company ID
            confirmation_message: Message to show user
            risk_level: Risk level of the operation
            parameters: Tool parameters for review
        """
        event = ToolEvent(
            event_type=ToolEventType.CONFIRMATION_REQUIRED,
            trace_id=trace_id,
            request_id=request_id,
            tool_name=tool_name,
            capability_name=capability_name,
            user_id=user_id,
            company_id=company_id,
            confirmation_message=confirmation_message,
            risk_level=risk_level,
            parameters=self._sanitize_parameters(parameters)
        )
        self._emit_event(event)

    def _emit_event(self, event: ToolEvent):
        """Emit an event via Socket.IO and call handlers"""
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Emit via Socket.IO
        if self.socketio:
            try:
                event_data = event.to_dict()
                room = f"company_{event.company_id}"

                # Emit to company room
                self.socketio.emit(event.event_type.value, event_data, room=room)

                # Also emit to user-specific room
                user_room = f"user_{event.user_id}"
                self.socketio.emit(event.event_type.value, event_data, room=user_room)

                logger.debug(f"Emitted {event.event_type.value} for trace_id={event.trace_id}")

            except Exception as e:
                logger.error(f"Failed to emit Socket.IO event: {e}")

        # Call registered handlers
        for handler in self._event_handlers[event.event_type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def _sanitize_parameters(self, params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Sanitize parameters to remove sensitive data"""
        if not params:
            return params

        sensitive_keys = {'password', 'token', 'secret', 'key', 'credential', 'auth'}
        sanitized = {}

        for key, value in params.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_parameters(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_result(self, result: Any) -> Any:
        """Sanitize result to remove sensitive data"""
        if isinstance(result, dict):
            return self._sanitize_parameters(result)
        return result

    def get_recent_events(
        self,
        trace_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        event_type: Optional[ToolEventType] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent events with optional filtering.

        Args:
            trace_id: Filter by trace ID
            tool_name: Filter by tool name
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        events = self._event_history.copy()

        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Return most recent first
        events = events[-limit:]
        events.reverse()

        return [e.to_dict() for e in events]

    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics"""
        stats = {
            "total_events": len(self._event_history),
            "events_by_type": {},
            "recent_errors": 0,
            "avg_execution_time_ms": 0.0
        }

        execution_times = []
        for event in self._event_history:
            event_type = event.event_type.value
            stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1

            if event.event_type == ToolEventType.FAILED:
                stats["recent_errors"] += 1

            if event.execution_time_ms:
                execution_times.append(event.execution_time_ms)

        if execution_times:
            stats["avg_execution_time_ms"] = sum(execution_times) / len(execution_times)

        return stats
