"""
Google Calendar Tool - Google Calendar API operations with secure OAuth2 integration
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.mcp_core import MCPTool, MCPToolResult
from ..internal.user_storage import get_user_storage
from app.auth_manager import auth_manager

logger = logging.getLogger(__name__)

class GoogleCalendarTool(MCPTool):
    """Google Calendar API operations tool"""
    
    def __init__(self):
        super().__init__(
            name="google_calendar",
            description="Google Calendar operations - events, scheduling, reminders",
            version="1.0.0"
        )
        
        self.base_url = "http://localhost:5001/oauth2/google"
        
        # Register capabilities
        self.add_capability("event_management")
        self.add_capability("calendar_access")
        self.add_capability("scheduling")
        self.add_capability("reminders")
        
        # Register actions
        self.register_action(
            "create_event",
            self._create_event,
            required_params=["title", "start_time"],
            optional_params=["user_id", "end_time", "description", "location", "attendees", "calendar_id"]
        )
        
        self.register_action(
            "list_events",
            self._list_events,
            required_params=[],
            optional_params=["user_id", "calendar_id", "time_min", "time_max", "max_results", "query"]
        )
        
        self.register_action(
            "get_event",
            self._get_event,
            required_params=["event_id"],
            optional_params=["user_id", "calendar_id"]
        )
        
        self.register_action(
            "update_event",
            self._update_event,
            required_params=["event_id"],
            optional_params=["user_id", "calendar_id", "title", "start_time", "end_time", "description", "location"]
        )
        
        self.register_action(
            "delete_event",
            self._delete_event,
            required_params=["event_id"],
            optional_params=["user_id", "calendar_id"]
        )
        
        self.register_action(
            "get_calendars",
            self._get_calendars,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "create_calendar",
            self._create_calendar,
            required_params=["calendar_name"],
            optional_params=["user_id", "description", "time_zone"]
        )
        
        self.register_action(
            "get_busy_times",
            self._get_busy_times,
            required_params=["start_time", "end_time"],
            optional_params=["user_id", "calendar_ids"]
        )
        
        self.register_action(
            "find_free_time",
            self._find_free_time,
            required_params=["duration_minutes"],
            optional_params=["user_id", "start_date", "end_date", "time_range"]
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
                    logger.info(f"Calendar tool mapped user {user_id} to Google email {google_email}")
            
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
    
    def _format_datetime(self, dt_string: str) -> dict:
        """Format datetime for Google Calendar API"""
        try:
            # Try parsing different formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d"
            ]
            
            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(dt_string, fmt)
                    break
                except ValueError:
                    continue
            
            if not dt:
                # Try ISO format
                dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            
            # Return Google Calendar format
            return {
                'dateTime': dt.isoformat(),
                'timeZone': 'UTC'
            }
            
        except Exception as e:
            logger.error(f"Error formatting datetime {dt_string}: {str(e)}")
            # Return as all-day event if parsing fails
            return {
                'date': dt_string.split('T')[0] if 'T' in dt_string else dt_string
            }
    
    def _create_event(self, title: str, start_time: str, user_id: Optional[str] = None,
                     end_time: Optional[str] = None, description: Optional[str] = None,
                     location: Optional[str] = None, attendees: Optional[List[str]] = None,
                     calendar_id: str = 'primary', **kwargs) -> MCPToolResult:
        """Create event in Google Calendar"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare event data
            event_data = {
                'summary': title,
                'start': self._format_datetime(start_time)
            }
            
            # Set end time (default to 1 hour later if not specified)
            if end_time:
                event_data['end'] = self._format_datetime(end_time)
            else:
                # Default 1 hour duration
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = start_dt + timedelta(hours=1)
                    event_data['end'] = {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': 'UTC'
                    }
                except:
                    # If start_time parsing fails, use same format as start
                    event_data['end'] = event_data['start'].copy()
            
            if description:
                event_data['description'] = description
                
            if location:
                event_data['location'] = location
            
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
            
            # Create event
            create_url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'
            response = requests.post(create_url, headers=headers, json=event_data)
            
            if response.status_code in [200, 201]:
                event = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "event_id": event['id'],
                        "title": event['summary'],
                        "start_time": event['start'].get('dateTime', event['start'].get('date')),
                        "end_time": event['end'].get('dateTime', event['end'].get('date')),
                        "html_link": event.get('htmlLink'),
                        "calendar_id": calendar_id,
                        "created": event['created']
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Event creation failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_events(self, user_id: Optional[str] = None, calendar_id: str = 'primary',
                    time_min: Optional[str] = None, time_max: Optional[str] = None,
                    max_results: int = 10, query: Optional[str] = None, **kwargs) -> MCPToolResult:
        """List events from Google Calendar"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Build query parameters
            params = {
                'maxResults': min(max_results, 2500),
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            # Set time range (default to next 30 days)
            if time_min:
                params['timeMin'] = time_min
            else:
                params['timeMin'] = datetime.utcnow().isoformat() + 'Z'
            
            if time_max:
                params['timeMax'] = time_max
            else:
                # Default to 30 days from now
                end_time = datetime.utcnow() + timedelta(days=30)
                params['timeMax'] = end_time.isoformat() + 'Z'
            
            if query:
                params['q'] = query
            
            # Get events
            list_url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'
            response = requests.get(list_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('items', [])
                
                event_list = []
                for event in events:
                    event_info = {
                        "id": event['id'],
                        "title": event.get('summary', 'No Title'),
                        "start_time": event['start'].get('dateTime', event['start'].get('date')),
                        "end_time": event['end'].get('dateTime', event['end'].get('date')),
                        "description": event.get('description'),
                        "location": event.get('location'),
                        "html_link": event.get('htmlLink'),
                        "attendees": [a.get('email') for a in event.get('attendees', [])],
                        "status": event.get('status')
                    }
                    event_list.append(event_info)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "events": event_list,
                        "total_count": len(event_list),
                        "calendar_id": calendar_id,
                        "time_range": f"{params['timeMin']} to {params['timeMax']}"
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"List events failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error listing calendar events: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_event(self, event_id: str, user_id: Optional[str] = None,
                  calendar_id: str = 'primary', **kwargs) -> MCPToolResult:
        """Get specific event details"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get event
            event_url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
            response = requests.get(event_url, headers=headers)
            
            if response.status_code == 200:
                event = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "id": event['id'],
                        "title": event.get('summary', 'No Title'),
                        "start_time": event['start'].get('dateTime', event['start'].get('date')),
                        "end_time": event['end'].get('dateTime', event['end'].get('date')),
                        "description": event.get('description'),
                        "location": event.get('location'),
                        "html_link": event.get('htmlLink'),
                        "attendees": [a.get('email') for a in event.get('attendees', [])],
                        "status": event.get('status'),
                        "created": event.get('created'),
                        "updated": event.get('updated')
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Get event failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error getting calendar event: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _update_event(self, event_id: str, user_id: Optional[str] = None,
                     calendar_id: str = 'primary', title: Optional[str] = None,
                     start_time: Optional[str] = None, end_time: Optional[str] = None,
                     description: Optional[str] = None, location: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Update existing event"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get current event first
            event_url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
            get_response = requests.get(event_url, headers=headers)
            
            if get_response.status_code != 200:
                return MCPToolResult(
                    success=False,
                    error=f"Event not found: {get_response.text}"
                )
            
            event_data = get_response.json()
            
            # Update fields
            if title:
                event_data['summary'] = title
            if start_time:
                event_data['start'] = self._format_datetime(start_time)
            if end_time:
                event_data['end'] = self._format_datetime(end_time)
            if description is not None:  # Allow empty string
                event_data['description'] = description
            if location is not None:  # Allow empty string
                event_data['location'] = location
            
            # Update event
            response = requests.put(event_url, headers=headers, json=event_data)
            
            if response.status_code == 200:
                updated_event = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "event_id": updated_event['id'],
                        "title": updated_event.get('summary'),
                        "start_time": updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                        "end_time": updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                        "updated": updated_event.get('updated')
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Event update failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _delete_event(self, event_id: str, user_id: Optional[str] = None,
                     calendar_id: str = 'primary', **kwargs) -> MCPToolResult:
        """Delete event from calendar"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Delete event
            delete_url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
            response = requests.delete(delete_url, headers=headers)
            
            if response.status_code in [200, 204]:
                return MCPToolResult(
                    success=True,
                    data={
                        "event_id": event_id,
                        "deleted": True,
                        "calendar_id": calendar_id
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Delete event failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_calendars(self, user_id: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Get list of user's calendars"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get calendar list
            calendars_url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'
            response = requests.get(calendars_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                calendars = data.get('items', [])
                
                calendar_list = []
                for calendar in calendars:
                    calendar_info = {
                        "id": calendar['id'],
                        "summary": calendar.get('summary'),
                        "description": calendar.get('description'),
                        "time_zone": calendar.get('timeZone'),
                        "access_role": calendar.get('accessRole'),
                        "primary": calendar.get('primary', False),
                        "selected": calendar.get('selected', False)
                    }
                    calendar_list.append(calendar_info)
                
                return MCPToolResult(
                    success=True,
                    data={
                        "calendars": calendar_list,
                        "total_count": len(calendar_list)
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Get calendars failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error getting calendars: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _create_calendar(self, calendar_name: str, user_id: Optional[str] = None,
                        description: Optional[str] = None, time_zone: str = 'UTC', **kwargs) -> MCPToolResult:
        """Create new calendar"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare calendar data
            calendar_data = {
                'summary': calendar_name,
                'timeZone': time_zone
            }
            
            if description:
                calendar_data['description'] = description
            
            # Create calendar
            create_url = 'https://www.googleapis.com/calendar/v3/calendars'
            response = requests.post(create_url, headers=headers, json=calendar_data)
            
            if response.status_code in [200, 201]:
                calendar = response.json()
                
                return MCPToolResult(
                    success=True,
                    data={
                        "calendar_id": calendar['id'],
                        "summary": calendar['summary'],
                        "description": calendar.get('description'),
                        "time_zone": calendar['timeZone']
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Calendar creation failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error creating calendar: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_busy_times(self, start_time: str, end_time: str, user_id: Optional[str] = None,
                       calendar_ids: Optional[List[str]] = None, **kwargs) -> MCPToolResult:
        """Get busy times for specified time range"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return MCPToolResult(
                    success=False,
                    error="Failed to get Google Calendar access token"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare request data
            if not calendar_ids:
                calendar_ids = ['primary']
            
            request_data = {
                'timeMin': start_time,
                'timeMax': end_time,
                'items': [{'id': cal_id} for cal_id in calendar_ids]
            }
            
            # Get freebusy info
            freebusy_url = 'https://www.googleapis.com/calendar/v3/freeBusy'
            response = requests.post(freebusy_url, headers=headers, json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                busy_times = []
                for calendar_id, info in data.get('calendars', {}).items():
                    for busy_period in info.get('busy', []):
                        busy_times.append({
                            "calendar_id": calendar_id,
                            "start": busy_period['start'],
                            "end": busy_period['end']
                        })
                
                return MCPToolResult(
                    success=True,
                    data={
                        "time_range": f"{start_time} to {end_time}",
                        "busy_times": busy_times,
                        "calendars_checked": calendar_ids
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Get busy times failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error getting busy times: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _find_free_time(self, duration_minutes: int, user_id: Optional[str] = None,
                       start_date: Optional[str] = None, end_date: Optional[str] = None,
                       time_range: Optional[Dict[str, str]] = None, **kwargs) -> MCPToolResult:
        """Find free time slots of specified duration"""
        try:
            # Set default time range if not provided
            if not start_date:
                start_date = datetime.utcnow().isoformat() + 'Z'
            if not end_date:
                end_dt = datetime.utcnow() + timedelta(days=7)
                end_date = end_dt.isoformat() + 'Z'
            
            # Get busy times first
            busy_result = self._get_busy_times(start_date, end_date, user_id)
            
            if not busy_result.success:
                return busy_result
            
            busy_times = busy_result.data['busy_times']
            
            # Find free slots
            free_slots = []
            current_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            duration = timedelta(minutes=duration_minutes)
            
            # Apply working hours if specified
            work_start_hour = 9  # 9 AM
            work_end_hour = 17   # 5 PM
            
            if time_range:
                work_start_hour = int(time_range.get('start', '09:00').split(':')[0])
                work_end_hour = int(time_range.get('end', '17:00').split(':')[0])
            
            while current_time + duration <= end_time:
                # Check if within working hours
                if work_start_hour <= current_time.hour < work_end_hour:
                    slot_end = current_time + duration
                    
                    # Check if slot conflicts with busy times
                    is_free = True
                    for busy in busy_times:
                        busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                        
                        # Check for overlap
                        if current_time < busy_end and slot_end > busy_start:
                            is_free = False
                            break
                    
                    if is_free:
                        free_slots.append({
                            "start": current_time.isoformat(),
                            "end": slot_end.isoformat(),
                            "duration_minutes": duration_minutes
                        })
                
                # Move to next hour
                current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            return MCPToolResult(
                success=True,
                data={
                    "duration_requested": duration_minutes,
                    "search_range": f"{start_date} to {end_date}",
                    "free_slots": free_slots[:10],  # Return first 10 slots
                    "total_slots_found": len(free_slots)
                }
            )
            
        except Exception as e:
            logger.error(f"Error finding free time: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def health_check(self) -> MCPToolResult:
        """Check if Google Calendar tool is working properly"""
        try:
            # Test OAuth2 endpoint availability
            response = requests.get(f"{self.base_url}/health", timeout=5)
            
            if response.status_code == 200:
                return MCPToolResult(
                    success=True,
                    data={
                        "status": "healthy",
                        "oauth2_endpoint": "available",
                        "calendar_api": "ready"
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
    """Register the Google Calendar tool with the registry"""
    tool = GoogleCalendarTool()
    return registry.register_tool(tool)