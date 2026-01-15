"""
Google Event Handler - Event-driven workflow automation

CLAUDE.md COMPLIANT:
- Event-driven workflow automation
- Gmail/Calendar/Drive event triggers
- Background monitoring with configurable intervals
- User-specific event handling
- Integration with MetisAgent3 workflow system
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Google service event types"""
    GMAIL_NEW_EMAIL = "gmail_new_email"
    GMAIL_EMAIL_RECEIVED = "gmail_email_received"
    CALENDAR_EVENT_STARTING = "calendar_event_starting"
    CALENDAR_EVENT_REMINDER = "calendar_event_reminder"
    DRIVE_FILE_CHANGED = "drive_file_changed"
    DRIVE_FILE_SHARED = "drive_file_shared"


class EventTrigger:
    """Event trigger configuration"""
    
    def __init__(
        self,
        event_type: EventType,
        user_id: str,
        workflow_name: str,
        conditions: Dict[str, Any] = None,
        parameters: Dict[str, Any] = None,
        enabled: bool = True
    ):
        self.event_type = event_type
        self.user_id = user_id
        self.workflow_name = workflow_name
        self.conditions = conditions or {}
        self.parameters = parameters or {}
        self.enabled = enabled
        self.created_at = datetime.now()
        self.last_triggered = None
        self.trigger_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "workflow_name": self.workflow_name,
            "conditions": self.conditions,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventTrigger':
        trigger = cls(
            event_type=EventType(data["event_type"]),
            user_id=data["user_id"],
            workflow_name=data["workflow_name"],
            conditions=data.get("conditions", {}),
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True)
        )
        trigger.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_triggered"):
            trigger.last_triggered = datetime.fromisoformat(data["last_triggered"])
        trigger.trigger_count = data.get("trigger_count", 0)
        return trigger


class GoogleEventHandler:
    """Event-driven workflow automation for Google services"""
    
    def __init__(self, google_tool: 'GoogleTool'):
        self.google_tool = google_tool
        self.triggers: List[EventTrigger] = []
        self.monitoring_active = False
        self.monitoring_task = None
        
        # Event state tracking
        self.last_gmail_check = {}  # user_id -> datetime
        self.last_calendar_check = {}  # user_id -> datetime
        self.last_drive_check = {}  # user_id -> datetime
        
        # Configuration
        self.check_interval = 60  # seconds
        self.triggers_file = Path("./storage/google_event_triggers.json")
        
        # Load existing triggers
        self._load_triggers()
        
        logger.info("✅ Google Event Handler initialized")
    
    def _load_triggers(self):
        """Load event triggers from storage"""
        try:
            if self.triggers_file.exists():
                with open(self.triggers_file, 'r') as f:
                    triggers_data = json.load(f)
                
                self.triggers = [
                    EventTrigger.from_dict(trigger_data)
                    for trigger_data in triggers_data
                ]
                
                logger.info(f"📂 Loaded {len(self.triggers)} event triggers")
            
        except Exception as e:
            logger.error(f"Failed to load event triggers: {e}")
            self.triggers = []
    
    def _save_triggers(self):
        """Save event triggers to storage"""
        try:
            self.triggers_file.parent.mkdir(parents=True, exist_ok=True)
            
            triggers_data = [trigger.to_dict() for trigger in self.triggers]
            
            with open(self.triggers_file, 'w') as f:
                json.dump(triggers_data, f, indent=2)
            
            logger.info(f"💾 Saved {len(self.triggers)} event triggers")
            
        except Exception as e:
            logger.error(f"Failed to save event triggers: {e}")
    
    def add_trigger(self, trigger: EventTrigger) -> bool:
        """Add new event trigger"""
        try:
            # Check if similar trigger exists
            existing = self._find_trigger(
                trigger.event_type, 
                trigger.user_id, 
                trigger.workflow_name
            )
            
            if existing:
                logger.warning(f"Similar trigger already exists for {trigger.user_id}")
                return False
            
            self.triggers.append(trigger)
            self._save_triggers()
            
            logger.info(f"➕ Added event trigger: {trigger.event_type} → {trigger.workflow_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add trigger: {e}")
            return False
    
    def remove_trigger(self, event_type: EventType, user_id: str, workflow_name: str) -> bool:
        """Remove event trigger"""
        try:
            original_count = len(self.triggers)
            self.triggers = [
                trigger for trigger in self.triggers
                if not (
                    trigger.event_type == event_type and
                    trigger.user_id == user_id and
                    trigger.workflow_name == workflow_name
                )
            ]
            
            if len(self.triggers) < original_count:
                self._save_triggers()
                logger.info(f"➖ Removed event trigger: {event_type} → {workflow_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove trigger: {e}")
            return False
    
    def _find_trigger(self, event_type: EventType, user_id: str, workflow_name: str) -> Optional[EventTrigger]:
        """Find specific trigger"""
        for trigger in self.triggers:
            if (
                trigger.event_type == event_type and
                trigger.user_id == user_id and
                trigger.workflow_name == workflow_name
            ):
                return trigger
        return None
    
    def get_user_triggers(self, user_id: str) -> List[EventTrigger]:
        """Get all triggers for a user"""
        return [trigger for trigger in self.triggers if trigger.user_id == user_id]
    
    async def start_monitoring(self):
        """Start background event monitoring"""
        if self.monitoring_active:
            logger.warning("Event monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔄 Started Google event monitoring")
    
    async def stop_monitoring(self):
        """Stop background event monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ Stopped Google event monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._check_all_events()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_events(self):
        """Check all event types for all users"""
        try:
            # Group triggers by user for efficient API usage
            user_triggers = {}
            for trigger in self.triggers:
                if trigger.enabled:
                    if trigger.user_id not in user_triggers:
                        user_triggers[trigger.user_id] = []
                    user_triggers[trigger.user_id].append(trigger)
            
            # Check events for each user
            for user_id, triggers in user_triggers.items():
                try:
                    await self._check_user_events(user_id, triggers)
                except Exception as e:
                    logger.error(f"Failed to check events for user {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Event checking failed: {e}")
    
    async def _check_user_events(self, user_id: str, triggers: List[EventTrigger]):
        """Check events for specific user"""
        try:
            # Check Gmail events
            gmail_triggers = [t for t in triggers if t.event_type.value.startswith("gmail_")]
            if gmail_triggers:
                await self._check_gmail_events(user_id, gmail_triggers)
            
            # Check Calendar events
            calendar_triggers = [t for t in triggers if t.event_type.value.startswith("calendar_")]
            if calendar_triggers:
                await self._check_calendar_events(user_id, calendar_triggers)
            
            # Check Drive events
            drive_triggers = [t for t in triggers if t.event_type.value.startswith("drive_")]
            if drive_triggers:
                await self._check_drive_events(user_id, drive_triggers)
            
        except Exception as e:
            logger.error(f"Failed to check events for user {user_id}: {e}")
    
    async def _check_gmail_events(self, user_id: str, triggers: List[EventTrigger]):
        """Check Gmail events"""
        try:
            # Get credentials
            credentials = await self.google_tool.oauth_manager.get_credentials(user_id)
            if not credentials:
                return
            
            # Check for new emails since last check
            last_check = self.last_gmail_check.get(user_id)
            if last_check:
                # Query for emails after last check
                query = f"after:{int(last_check.timestamp())}"
            else:
                # First check - look for emails in last hour
                query = f"after:{int((datetime.now() - timedelta(hours=1)).timestamp())}"
            
            # Import Gmail handler
            from .handlers.gmail_handler import GmailHandler
            gmail_handler = GmailHandler(credentials)
            
            result = await gmail_handler.list_emails(max_results=10, query=query)
            
            if result["success"] and result["emails"]:
                for email in result["emails"]:
                    # Check each trigger
                    for trigger in triggers:
                        if trigger.event_type == EventType.GMAIL_NEW_EMAIL:
                            if self._matches_conditions(email, trigger.conditions):
                                await self._trigger_workflow(trigger, email)
            
            self.last_gmail_check[user_id] = datetime.now()
            
        except Exception as e:
            logger.error(f"Gmail event check failed for {user_id}: {e}")
    
    async def _check_calendar_events(self, user_id: str, triggers: List[EventTrigger]):
        """Check Calendar events"""
        try:
            # Get credentials
            credentials = await self.google_tool.oauth_manager.get_credentials(user_id)
            if not credentials:
                return
            
            # Import Calendar handler
            from .handlers.calendar_handler import CalendarHandler
            calendar_handler = CalendarHandler(credentials)
            
            # Get upcoming events (next 2 hours)
            time_min = datetime.now().isoformat() + 'Z'
            time_max = (datetime.now() + timedelta(hours=2)).isoformat() + 'Z'
            
            result = await calendar_handler.list_events(
                time_min=time_min,
                time_max=time_max,
                max_results=20
            )
            
            if result["success"] and result["events"]:
                for event in result["events"]:
                    # Check for starting events (within 10 minutes)
                    event_start = datetime.fromisoformat(event["start"].replace('Z', '+00:00'))
                    time_until_start = (event_start - datetime.now().replace(tzinfo=event_start.tzinfo)).total_seconds()
                    
                    if 0 <= time_until_start <= 600:  # 10 minutes
                        for trigger in triggers:
                            if trigger.event_type == EventType.CALENDAR_EVENT_STARTING:
                                if self._matches_conditions(event, trigger.conditions):
                                    await self._trigger_workflow(trigger, event)
            
            self.last_calendar_check[user_id] = datetime.now()
            
        except Exception as e:
            logger.error(f"Calendar event check failed for {user_id}: {e}")
    
    async def _check_drive_events(self, user_id: str, triggers: List[EventTrigger]):
        """Check Drive events"""
        try:
            # Get credentials
            credentials = await self.google_tool.oauth_manager.get_credentials(user_id)
            if not credentials:
                return
            
            # Import Drive handler
            from .handlers.drive_handler import DriveHandler
            drive_handler = DriveHandler(credentials)
            
            # Get recent file changes
            result = await drive_handler.list_files(
                max_results=20,
                order_by="modifiedTime desc"
            )
            
            if result["success"] and result["files"]:
                last_check = self.last_drive_check.get(user_id, datetime.now() - timedelta(hours=1))
                
                for file_info in result["files"]:
                    # Check if file was modified since last check
                    modified_time = datetime.fromisoformat(file_info["modified_time"].replace('Z', '+00:00'))
                    
                    if modified_time > last_check:
                        for trigger in triggers:
                            if trigger.event_type == EventType.DRIVE_FILE_CHANGED:
                                if self._matches_conditions(file_info, trigger.conditions):
                                    await self._trigger_workflow(trigger, file_info)
            
            self.last_drive_check[user_id] = datetime.now()
            
        except Exception as e:
            logger.error(f"Drive event check failed for {user_id}: {e}")
    
    def _matches_conditions(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Check if data matches trigger conditions"""
        try:
            for key, expected_value in conditions.items():
                if key not in data:
                    return False
                
                actual_value = data[key]
                
                # String contains matching
                if isinstance(expected_value, str) and isinstance(actual_value, str):
                    if expected_value.lower() not in actual_value.lower():
                        return False
                # Exact matching
                elif actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Condition matching failed: {e}")
            return False
    
    async def _trigger_workflow(self, trigger: EventTrigger, event_data: Dict[str, Any]):
        """Trigger workflow execution"""
        try:
            logger.info(f"🔥 Triggering workflow: {trigger.workflow_name} for {trigger.event_type}")
            
            # Update trigger statistics
            trigger.last_triggered = datetime.now()
            trigger.trigger_count += 1
            self._save_triggers()
            
            # TODO: Integration with MetisAgent3 workflow system
            # This would trigger the workflow orchestrator with:
            # - workflow_name: trigger.workflow_name
            # - user_id: trigger.user_id
            # - context_data: event_data + trigger.parameters
            
            # For now, log the trigger
            logger.info(f"📋 Workflow trigger details:")
            logger.info(f"   User: {trigger.user_id}")
            logger.info(f"   Workflow: {trigger.workflow_name}")
            logger.info(f"   Event: {trigger.event_type}")
            logger.info(f"   Data: {event_data}")
            
        except Exception as e:
            logger.error(f"Workflow trigger failed: {e}")


# Event Handler Management API
class EventHandlerAPI:
    """API for managing event triggers"""
    
    def __init__(self, event_handler: GoogleEventHandler):
        self.event_handler = event_handler
    
    async def create_email_trigger(
        self,
        user_id: str,
        workflow_name: str,
        subject_contains: Optional[str] = None,
        from_email: Optional[str] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Create email event trigger"""
        try:
            conditions = {}
            if subject_contains:
                conditions["subject"] = subject_contains
            if from_email:
                conditions["from"] = from_email
            
            trigger = EventTrigger(
                event_type=EventType.GMAIL_NEW_EMAIL,
                user_id=user_id,
                workflow_name=workflow_name,
                conditions=conditions,
                enabled=enabled
            )
            
            success = self.event_handler.add_trigger(trigger)
            
            return {
                "success": success,
                "trigger_id": f"{trigger.event_type}_{user_id}_{workflow_name}",
                "message": "Email trigger created" if success else "Failed to create trigger"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create email trigger"
            }
    
    async def create_calendar_trigger(
        self,
        user_id: str,
        workflow_name: str,
        event_title_contains: Optional[str] = None,
        minutes_before: int = 10,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Create calendar event trigger"""
        try:
            conditions = {}
            if event_title_contains:
                conditions["title"] = event_title_contains
            
            parameters = {"minutes_before": minutes_before}
            
            trigger = EventTrigger(
                event_type=EventType.CALENDAR_EVENT_STARTING,
                user_id=user_id,
                workflow_name=workflow_name,
                conditions=conditions,
                parameters=parameters,
                enabled=enabled
            )
            
            success = self.event_handler.add_trigger(trigger)
            
            return {
                "success": success,
                "trigger_id": f"{trigger.event_type}_{user_id}_{workflow_name}",
                "message": "Calendar trigger created" if success else "Failed to create trigger"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create calendar trigger"
            }
    
    async def list_triggers(self, user_id: str) -> Dict[str, Any]:
        """List user's event triggers"""
        try:
            triggers = self.event_handler.get_user_triggers(user_id)
            
            trigger_list = [
                {
                    "event_type": trigger.event_type.value,
                    "workflow_name": trigger.workflow_name,
                    "conditions": trigger.conditions,
                    "enabled": trigger.enabled,
                    "trigger_count": trigger.trigger_count,
                    "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None
                }
                for trigger in triggers
            ]
            
            return {
                "success": True,
                "triggers": trigger_list,
                "count": len(trigger_list),
                "message": f"Found {len(trigger_list)} triggers"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list triggers"
            }