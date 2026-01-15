"""
Calendar Handler - Google Calendar API operations

CLAUDE.md COMPLIANT:
- Complete Calendar API integration
- Event creation, updating, deletion
- Smart date/time parsing
- Fault-tolerant error handling
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import pytz

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
except ImportError:
    pass

logger = logging.getLogger(__name__)


class CalendarHandler:
    """Google Calendar API operations handler"""
    
    def __init__(self, credentials: 'Credentials'):
        self.credentials = credentials
        self.service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Calendar handler initialized")
    
    async def list_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """List calendar events"""
        try:
            logger.info(f"📅 Listing {max_results} events from calendar: {calendar_id}")
            
            # Default time range - next 7 days if not specified
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
            
            # Build request parameters
            request_params = {
                'calendarId': calendar_id,
                'timeMin': time_min,
                'timeMax': time_max,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if query:
                request_params['q'] = query
            
            # Get events
            events_result = self.service.events().list(**request_params).execute()
            events = events_result.get('items', [])
            
            # Format events for better readability
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                event_info = {
                    "id": event['id'],
                    "title": event.get('summary', 'No Title'),
                    "description": event.get('description', ''),
                    "start": start,
                    "end": end,
                    "location": event.get('location', ''),
                    "attendees": [
                        {
                            "email": attendee.get('email', ''),
                            "name": attendee.get('displayName', ''),
                            "status": attendee.get('responseStatus', 'needsAction')
                        }
                        for attendee in event.get('attendees', [])
                    ],
                    "created": event.get('created', ''),
                    "updated": event.get('updated', ''),
                    "html_link": event.get('htmlLink', '')
                }
                
                formatted_events.append(event_info)
            
            return {
                "success": True,
                "events": formatted_events,
                "count": len(formatted_events),
                "calendar_id": calendar_id,
                "message": f"Listed {len(formatted_events)} events successfully"
            }
            
        except HttpError as e:
            logger.error(f"Calendar list API error: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {str(e)}",
                "message": "Failed to list calendar events"
            }
        except Exception as e:
            logger.error(f"Calendar list failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list calendar events"
            }
    
    async def create_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = 'primary',
        timezone: str = 'UTC'
    ) -> Dict[str, Any]:
        """Create new calendar event"""
        try:
            logger.info(f"📝 Creating event: {title}")
            
            # Parse start time
            if 'T' not in start_time:
                # All-day event
                start_dt = {'date': start_time}
                end_dt = {'date': end_time or start_time}
            else:
                # Timed event
                start_dt = {
                    'dateTime': start_time,
                    'timeZone': timezone
                }
                
                if not end_time:
                    # Default 1 hour duration
                    end_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_datetime += timedelta(hours=1)
                    end_time = end_datetime.isoformat()
                
                end_dt = {
                    'dateTime': end_time,
                    'timeZone': timezone
                }
            
            # Build event object
            event = {
                'summary': title,
                'start': start_dt,
                'end': end_dt
            }
            
            if description:
                event['description'] = description
            
            if location:
                event['location'] = location
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Create event
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_url": created_event.get('htmlLink'),
                "title": title,
                "start": start_time,
                "end": end_time,
                "message": f"Event '{title}' created successfully"
            }
            
        except HttpError as e:
            logger.error(f"Calendar create API error: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {str(e)}",
                "message": f"Failed to create event '{title}'"
            }
        except Exception as e:
            logger.error(f"Calendar create failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create event '{title}'"
            }
    
    async def update_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        **updates
    ) -> Dict[str, Any]:
        """Update existing calendar event"""
        try:
            logger.info(f"📝 Updating event: {event_id}")
            
            # Get existing event
            existing_event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Apply updates
            if 'title' in updates:
                existing_event['summary'] = updates['title']
            
            if 'description' in updates:
                existing_event['description'] = updates['description']
            
            if 'location' in updates:
                existing_event['location'] = updates['location']
            
            if 'start_time' in updates:
                if 'T' in updates['start_time']:
                    existing_event['start'] = {
                        'dateTime': updates['start_time'],
                        'timeZone': updates.get('timezone', 'UTC')
                    }
                else:
                    existing_event['start'] = {'date': updates['start_time']}
            
            if 'end_time' in updates:
                if 'T' in updates['end_time']:
                    existing_event['end'] = {
                        'dateTime': updates['end_time'],
                        'timeZone': updates.get('timezone', 'UTC')
                    }
                else:
                    existing_event['end'] = {'date': updates['end_time']}
            
            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=existing_event
            ).execute()
            
            return {
                "success": True,
                "event_id": event_id,
                "event_url": updated_event.get('htmlLink'),
                "message": f"Event {event_id} updated successfully"
            }
            
        except HttpError as e:
            logger.error(f"Calendar update API error: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {str(e)}",
                "message": f"Failed to update event {event_id}"
            }
        except Exception as e:
            logger.error(f"Calendar update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update event {event_id}"
            }
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """Delete calendar event"""
        try:
            logger.info(f"🗑️ Deleting event: {event_id}")
            
            # Delete event
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Event {event_id} deleted successfully"
            }
            
        except HttpError as e:
            logger.error(f"Calendar delete API error: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {str(e)}",
                "message": f"Failed to delete event {event_id}"
            }
        except Exception as e:
            logger.error(f"Calendar delete failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to delete event {event_id}"
            }
    
    async def get_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """Get specific event details"""
        try:
            logger.info(f"📖 Getting event: {event_id}")
            
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            event_info = {
                "id": event['id'],
                "title": event.get('summary', 'No Title'),
                "description": event.get('description', ''),
                "start": start,
                "end": end,
                "location": event.get('location', ''),
                "attendees": [
                    {
                        "email": attendee.get('email', ''),
                        "name": attendee.get('displayName', ''),
                        "status": attendee.get('responseStatus', 'needsAction')
                    }
                    for attendee in event.get('attendees', [])
                ],
                "created": event.get('created', ''),
                "updated": event.get('updated', ''),
                "html_link": event.get('htmlLink', ''),
                "calendar_id": calendar_id
            }
            
            return {
                "success": True,
                "event": event_info,
                "message": "Event details retrieved successfully"
            }
            
        except HttpError as e:
            logger.error(f"Calendar get API error: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {str(e)}",
                "message": f"Failed to get event {event_id}"
            }
        except Exception as e:
            logger.error(f"Calendar get failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get event {event_id}"
            }