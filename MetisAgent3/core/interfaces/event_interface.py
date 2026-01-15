"""
Event System Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract event system contracts
- Async event handling
- Extensible event bus architecture
- No implementation coupling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from datetime import datetime
from enum import Enum
from uuid import uuid4

from ..contracts import ExecutionContext


class EventPriority(str, Enum):
    """Event priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Event:
    """Base event class"""
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str,
        priority: EventPriority = EventPriority.MEDIUM,
        context: Optional[ExecutionContext] = None
    ):
        self.event_id = str(uuid4())
        self.event_type = event_type
        self.data = data
        self.source = source
        self.priority = priority
        self.context = context
        self.timestamp = datetime.now()
        self.processed = False


class IEventBus(ABC):
    """Abstract interface for event bus"""
    
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """Publish event to the bus"""
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: 'IEventHandler') -> str:
        """Subscribe to events of specific type"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[Event]) -> List[bool]:
        """Publish multiple events"""
        pass
    
    @abstractmethod
    async def get_pending_events(self, event_type: Optional[str] = None) -> List[Event]:
        """Get pending events"""
        pass


class IEventHandler(ABC):
    """Abstract interface for event handlers"""
    
    @abstractmethod
    async def handle_event(self, event: Event) -> bool:
        """Handle specific event"""
        pass
    
    @abstractmethod
    async def can_handle(self, event_type: str) -> bool:
        """Check if handler can process event type"""
        pass
    
    @abstractmethod
    async def get_supported_events(self) -> List[str]:
        """Get list of supported event types"""
        pass
    
    @abstractmethod
    async def on_error(self, event: Event, error: Exception) -> None:
        """Handle event processing errors"""
        pass


class IEventStore(ABC):
    """Abstract interface for event storage"""
    
    @abstractmethod
    async def store_event(self, event: Event) -> str:
        """Store event permanently"""
        pass
    
    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Retrieve event by ID"""
        pass
    
    @abstractmethod
    async def query_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """Query events with filters"""
        pass
    
    @abstractmethod
    async def delete_event(self, event_id: str) -> bool:
        """Delete event from store"""
        pass
    
    @abstractmethod
    async def cleanup_old_events(self, retention_days: int = 30) -> int:
        """Clean up old events"""
        pass


class IEventProcessor(ABC):
    """Abstract interface for event processing"""
    
    @abstractmethod
    async def process_event(self, event: Event) -> bool:
        """Process single event"""
        pass
    
    @abstractmethod
    async def process_batch(self, events: List[Event]) -> List[bool]:
        """Process multiple events"""
        pass
    
    @abstractmethod
    async def retry_failed_event(self, event_id: str) -> bool:
        """Retry processing failed event"""
        pass
    
    @abstractmethod
    async def get_failed_events(self) -> List[Event]:
        """Get events that failed processing"""
        pass


class IEventFilter(ABC):
    """Abstract interface for event filtering"""
    
    @abstractmethod
    async def filter_event(self, event: Event, criteria: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria"""
        pass
    
    @abstractmethod
    async def create_filter(self, name: str, criteria: Dict[str, Any]) -> str:
        """Create named filter"""
        pass
    
    @abstractmethod
    async def apply_filter(self, filter_name: str, events: List[Event]) -> List[Event]:
        """Apply named filter to event list"""
        pass
    
    @abstractmethod
    async def delete_filter(self, filter_name: str) -> bool:
        """Delete named filter"""
        pass


class IEventMetrics(ABC):
    """Abstract interface for event metrics"""
    
    @abstractmethod
    async def track_event_metrics(self, event: Event) -> None:
        """Track metrics for event"""
        pass
    
    @abstractmethod
    async def get_event_stats(self, time_range: str) -> Dict[str, Any]:
        """Get event processing statistics"""
        pass
    
    @abstractmethod
    async def get_handler_performance(self, handler_id: str) -> Dict[str, Any]:
        """Get performance metrics for handler"""
        pass
    
    @abstractmethod
    async def get_throughput_metrics(self) -> Dict[str, float]:
        """Get event throughput metrics"""
        pass


class IEventScheduler(ABC):
    """Abstract interface for event scheduling"""
    
    @abstractmethod
    async def schedule_event(self, event: Event, schedule_time: datetime) -> str:
        """Schedule event for future execution"""
        pass
    
    @abstractmethod
    async def schedule_recurring_event(self, event: Event, cron_expression: str) -> str:
        """Schedule recurring event"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_event(self, schedule_id: str) -> bool:
        """Cancel scheduled event"""
        pass
    
    @abstractmethod
    async def get_scheduled_events(self) -> List[Dict[str, Any]]:
        """Get all scheduled events"""
        pass


__all__ = [
    "EventPriority",
    "Event",
    "IEventBus",
    "IEventHandler",
    "IEventStore", 
    "IEventProcessor",
    "IEventFilter",
    "IEventMetrics",
    "IEventScheduler"
]