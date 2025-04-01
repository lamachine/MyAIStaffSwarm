# Added get_current_datetime function to get current datetime in UTC.
# Added format_date function to format datetime as YYYY-MM-DD.
# Changed list events to asynch
# Created google calendar tool class
# Created google calendar state tool class
# created google calendar event tool class
# Added calendar tool instructions
# LTB2 uses universal tool handler


import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Union
import sys
from ...tools.credentials_handler import get_credentials
from googleapiclient.discovery import build
from functools import lru_cache
import pytz
from langchain.tools import BaseTool
from src.tools.base_logging_tool import BaseLoggingTool

@lru_cache(maxsize=1)
def get_calendar_service():
    """Get and cache the Calendar service."""
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)

def get_current_datetime():
    """Get current datetime in UTC."""
    return datetime.now(pytz.UTC)

def format_date(dt: datetime) -> str:
    """Format datetime as YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d")

async def list_events(max_results: int = 10, time_min: str = None) -> str:
    """List calendar events."""
    try:
        if time_min is None:
            time_min = get_current_datetime().isoformat()
            
        service = get_calendar_service()
        
        # If no date specified, use today
        if not time_min:
            time_min = datetime.now().strftime("%Y-%m-%d")
            
        # Set time range for the full day in LA timezone
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min + 'T00:00:00-07:00',
            timeMax=time_min + 'T23:59:59-07:00',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        # Format events consistently
        events = events_result.get('items', [])
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                'summary': event.get('summary', 'No title'),
                'start': start
            })
            
        return str(formatted_events)
    except Exception as e:
        return f"Error listing events: {str(e)}"

def create_event(summary: str, date: str, duration: int = 60) -> str:
    """
    Create a new calendar event.
    
    Args:
        summary: Event title
        date: Date in format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
        duration: Duration in minutes (default: 60)
    
    Returns:
        str: Success or error message
    """
    try:
        service = get_calendar_service()
        
        # Parse date and time
        if ' ' in date:
            start_date, start_time = date.split(' ')
        else:
            start_date = date
            start_time = '09:00'  # Default to 9 AM
            
        # Create start and end times
        start = f"{start_date}T{start_time}:00-07:00"
        
        # Calculate end time
        dt = datetime.fromisoformat(start)
        end = (dt + timedelta(minutes=duration)).isoformat()

        event = {
            'summary': summary,
            'start': {
                'dateTime': start,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end,
                'timeZone': 'America/Los_Angeles',
            }
        }

        event = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return str({
            'summary': event.get('summary', 'No title'),
            'start': event['start'].get('dateTime', event['start'].get('date'))
        })
    except Exception as e:
        return f"Error creating event: {str(e)}"

def delete_event(event_id: str) -> str:
    """Delete a calendar event."""
    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        return str({'status': 'deleted', 'event_id': event_id})
    except Exception as e:
        return f"Error deleting event: {str(e)}"

def update_event(event_id: str, summary: Optional[str] = None, 
                date: Optional[str] = None, duration: Optional[int] = None) -> str:
    """
    Update an existing calendar event.
    
    Args:
        event_id: ID of event to update
        summary: New event title
        date: New date in format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
        duration: New duration in minutes
    """
    try:
        service = get_calendar_service()
        
        # Get existing event
        event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        if summary:
            event['summary'] = summary
            
        if date:
            # Parse date and time
            if ' ' in date:
                start_date, start_time = date.split(' ')
            else:
                start_time = event['start']['dateTime'].split('T')[1]
                start_date = date
                
            # Update start time
            start = f"{start_date}T{start_time}"
            event['start']['dateTime'] = start
            
            # Update end time if duration provided
            if duration:
                dt = datetime.fromisoformat(start)
                end = (dt + timedelta(minutes=duration)).isoformat()
                event['end']['dateTime'] = end

        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()

        return str({
            'summary': updated_event.get('summary', 'No title'),
            'start': updated_event['start'].get('dateTime', updated_event['start'].get('date'))
        })
    except Exception as e:
        return f"Error updating event: {str(e)}"

# ACL (Access Control) Functions
def manage_calendar_acl(action: str, calendar_id: str = 'primary', 
                       rule_id: Optional[str] = None, 
                       role: Optional[str] = None,
                       scope_type: Optional[str] = None,
                       scope_value: Optional[str] = None) -> str:
    """
    Manage calendar access control rules.
    
    Args:
        action: One of 'list', 'get', 'insert', 'delete', 'update'
        calendar_id: Calendar ID (default: primary)
        rule_id: ACL rule ID for specific operations
        role: Role for insert/update (reader, writer, owner)
        scope_type: Scope type for insert/update (user, group, domain)
        scope_value: Email or domain for the scope
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            acl = service.acl().list(calendarId=calendar_id).execute()
            return json.dumps(acl.get('items', []), indent=2)
            
        elif action == "get" and rule_id:
            rule = service.acl().get(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            return json.dumps(rule, indent=2)
            
        elif action == "insert" and role and scope_type and scope_value:
            rule = {
                'role': role,
                'scope': {
                    'type': scope_type,
                    'value': scope_value
                }
            }
            result = service.acl().insert(
                calendarId=calendar_id,
                body=rule
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and rule_id:
            service.acl().delete(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            return f"ACL rule {rule_id} deleted successfully"
            
        elif action == "update" and rule_id and role:
            rule = service.acl().get(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            rule['role'] = role
            result = service.acl().update(
                calendarId=calendar_id,
                ruleId=rule_id,
                body=rule
            ).execute()
            return json.dumps(result, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing ACL: {str(e)}"

# Calendar List Functions
def manage_calendar_list(action: str, calendar_id: Optional[str] = None,
                        summary: Optional[str] = None,
                        color_id: Optional[str] = None,
                        hidden: Optional[bool] = None) -> str:
    """
    Manage user's calendar list.
    
    Args:
        action: One of 'list', 'get', 'insert', 'delete', 'update'
        calendar_id: Calendar ID for specific operations
        summary: Calendar summary for updates
        color_id: Color ID for updates
        hidden: Whether to hide the calendar
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            calendars = service.calendarList().list().execute()
            return json.dumps(calendars.get('items', []), indent=2)
            
        elif action == "get" and calendar_id:
            calendar = service.calendarList().get(
                calendarId=calendar_id
            ).execute()
            return json.dumps(calendar, indent=2)
            
        elif action == "insert" and calendar_id:
            result = service.calendarList().insert(
                body={'id': calendar_id}
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and calendar_id:
            service.calendarList().delete(
                calendarId=calendar_id
            ).execute()
            return f"Calendar {calendar_id} removed from list"
            
        elif action == "update" and calendar_id:
            calendar = service.calendarList().get(
                calendarId=calendar_id
            ).execute()
            if summary:
                calendar['summaryOverride'] = summary
            if color_id:
                calendar['colorId'] = color_id
            if hidden is not None:
                calendar['hidden'] = hidden
            result = service.calendarList().update(
                calendarId=calendar_id,
                body=calendar
            ).execute()
            return json.dumps(result, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing calendar list: {str(e)}"

# Calendar Management Functions
def manage_calendar(action: str, calendar_id: Optional[str] = None,
                   summary: Optional[str] = None,
                   description: Optional[str] = None,
                   time_zone: Optional[str] = None) -> str:
    """
    Manage calendars.
    
    Args:
        action: One of 'get', 'insert', 'delete', 'update', 'clear'
        calendar_id: Calendar ID for specific operations
        summary: Calendar summary for create/update
        description: Calendar description for create/update
        time_zone: Calendar time zone for create/update
    """
    try:
        service = get_calendar_service()
        
        if action == "get" and calendar_id:
            calendar = service.calendars().get(
                calendarId=calendar_id
            ).execute()
            return json.dumps(calendar, indent=2)
            
        elif action == "insert" and summary:
            calendar = {
                'summary': summary,
                'timeZone': time_zone or 'America/Los_Angeles'
            }
            if description:
                calendar['description'] = description
            result = service.calendars().insert(body=calendar).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and calendar_id:
            service.calendars().delete(calendarId=calendar_id).execute()
            return f"Calendar {calendar_id} deleted"
            
        elif action == "update" and calendar_id:
            calendar = service.calendars().get(
                calendarId=calendar_id
            ).execute()
            if summary:
                calendar['summary'] = summary
            if description:
                calendar['description'] = description
            if time_zone:
                calendar['timeZone'] = time_zone
            result = service.calendars().update(
                calendarId=calendar_id,
                body=calendar
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "clear" and calendar_id:
            service.calendars().clear(calendarId=calendar_id).execute()
            return f"Calendar {calendar_id} cleared"
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing calendar: {str(e)}"

# Enhanced Event Functions
def quick_add_event(calendar_id: str, text: str) -> str:
    """
    Quickly add an event using natural language.
    
    Args:
        calendar_id: Calendar ID (use 'primary' for primary calendar)
        text: Natural language text describing the event
    """
    try:
        service = get_calendar_service()
        event = service.events().quickAdd(
            calendarId=calendar_id,
            text=text
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error quick adding event: {str(e)}"

def move_event(calendar_id: str, event_id: str, destination_id: str) -> str:
    """
    Move an event to a different calendar.
    
    Args:
        calendar_id: Source calendar ID
        event_id: Event to move
        destination_id: Destination calendar ID
    """
    try:
        service = get_calendar_service()
        event = service.events().move(
            calendarId=calendar_id,
            eventId=event_id,
            destination=destination_id
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error moving event: {str(e)}"

def get_event_instances(calendar_id: str, event_id: str, 
                       time_min: Optional[str] = None,
                       time_max: Optional[str] = None,
                       max_results: int = 10) -> str:
    """
    Get instances of a recurring event.
    
    Args:
        calendar_id: Calendar ID
        event_id: Recurring event ID
        time_min: Start time in ISO format
        time_max: End time in ISO format
        max_results: Maximum number of instances to return
    """
    try:
        service = get_calendar_service()
        instances = service.events().instances(
            calendarId=calendar_id,
            eventId=event_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results
        ).execute()
        return json.dumps(instances.get('items', []), indent=2)
    except Exception as e:
        return f"Error getting event instances: {str(e)}"

def import_event(calendar_id: str, ical_data: str) -> str:
    """
    Import an event from iCal data.
    
    Args:
        calendar_id: Calendar ID
        ical_data: iCal event data
    """
    try:
        service = get_calendar_service()
        event = service.events().import_(
            calendarId=calendar_id,
            body={'iCalUID': ical_data}
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error importing event: {str(e)}"

# Freebusy Functions
def query_freebusy(time_min: str, time_max: str, calendar_ids: List[str]) -> str:
    """
    Query free/busy information for calendars.
    
    Args:
        time_min: Start time in ISO format
        time_max: End time in ISO format
        calendar_ids: List of calendar IDs to query
    """
    try:
        service = get_calendar_service()
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }
        freebusy = service.freebusy().query(body=body).execute()
        return json.dumps(freebusy, indent=2)
    except Exception as e:
        return f"Error querying freebusy: {str(e)}"

# Settings Functions
def manage_settings(action: str, setting_id: Optional[str] = None) -> str:
    """
    Manage user settings.
    
    Args:
        action: One of 'list', 'get'
        setting_id: Setting ID for 'get' action
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            settings = service.settings().list().execute()
            return json.dumps(settings.get('items', []), indent=2)
            
        elif action == "get" and setting_id:
            setting = service.settings().get(
                setting=setting_id
            ).execute()
            return json.dumps(setting, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing settings: {str(e)}"

# Colors Function
def get_calendar_colors() -> str:
    """Get color definitions for calendars and events."""
    try:
        service = get_calendar_service()
        colors = service.colors().get().execute()
        return json.dumps(colors, indent=2)
    except Exception as e:
        return f"Error getting colors: {str(e)}"

def find_event(summary: str = None, date: str = None) -> str:
    """
    Find events by summary and/or date.
    
    Args:
        summary: Event title to search for
        date: Date in YYYY-MM-DD format
    
    Returns:
        str: JSON string with matching events including IDs
    """
    try:
        service = get_calendar_service()
        
        # Set time range for the day if date provided
        if date:
            time_min = f"{date}T00:00:00-07:00"
            time_max = f"{date}T23:59:59-07:00"
        else:
            # Default to searching today
            time_min = datetime.now().strftime("%Y-%m-%dT00:00:00-07:00")
            time_max = datetime.now().strftime("%Y-%m-%dT23:59:59-07:00")
            
        # Get events for the time range
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        # Filter by summary if provided
        events = events_result.get('items', [])
        if summary:
            events = [e for e in events if summary.lower() in e.get('summary', '').lower()]
            
        # Format response
        formatted_events = []
        for event in events:
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date'))
            })
            
        return str(formatted_events)
    except Exception as e:
        return f"Error finding events: {str(e)}"

class GoogleCalendarTool(BaseLoggingTool):
    name: str = "google_calendar"
    description: str = """Use this tool to view or add calendar events.
    
    For viewing events:
    {
        "action": "view",
        "date": "today or YYYY-MM-DD",
        "summary": "",
        "duration": ""
    }
    
    For adding events:
    {
        "action": "add",
        "date": "YYYY-MM-DD HH:MM",
        "summary": "event description",
        "duration": "duration in minutes"
    }
    """

    def _get_service(self):
        """Get authenticated calendar service."""
        creds = get_credentials()
        return build('calendar', 'v3', credentials=creds)

    def _run(self, tool_input: Dict[str, Any]) -> str:
        service = self._get_service()
        
        if tool_input["action"] == "view":
            # Parse date
            if tool_input["date"] == "today":
                date = datetime.now().date()
            else:
                date = datetime.strptime(tool_input["date"], "%Y-%m-%d").date()
            
            # Get start/end of day
            time_min = datetime.combine(date, datetime.min.time()).isoformat() + 'Z'
            time_max = datetime.combine(date, datetime.max.time()).isoformat() + 'Z'
            
            # Get events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            if not events:
                return "No events found."
                
            # Format events
            response = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                response.append(f"{start}: {event['summary']}")
            return "\n".join(response)
            
        elif tool_input["action"] == "add":
            # Parse date and duration
            start_time = datetime.strptime(tool_input["date"], "%Y-%m-%d %H:%M")
            duration = int(tool_input["duration"].split()[0])  # Assumes "X minutes"
            end_time = start_time + timedelta(minutes=duration)
            
            # Create event
            event = {
                'summary': tool_input["summary"],
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/New_York',
                }
            }
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {event.get('htmlLink')}"

class CalendarStateTool(BaseTool):
    """Base class for calendar tools with state handling"""
    name: str = "calendar"
    description: str = "Manage calendar events"

    @staticmethod
    def get_tool_info() -> dict:
        """Return tool instructions and specifications"""
        return CALENDAR_TOOL_INSTRUCTIONS

    def _handle_state(self, state: Dict[str, Any], result: Any) -> Dict[str, Any]:
        """Handle calendar tool state updates"""
        tool_state = {
            "session_id": state["session_id"],
            "timestamp": datetime.now().isoformat(),
            "sender": "calendar",
            "target": "graph",
            "content": str(result) if result else "No result",
            "metadata": {
                "source": "calendar",
                "message_type": "tool_response",
                "tool": "calendar",
                "operation": self.name
            },
            "tool_input": state.get("tool_input", {}),
            "response": str(result) if result else "No result",
            "messages": state.get("messages", [])
        }

        # Print only calendar state changes
        if tool_state["sender"] == "calendar":
            print("\nState Update - Calendar Tool:")
            print("---------------------------")
            print(json.dumps(tool_state, indent=2, default=str))
            print("---------------------------\n")
        
        return tool_state

class CreateEventTool(CalendarStateTool):
    name: str = "create_event"
    description: str = "Create a calendar event"

    def _run(self, summary: str, date: str, duration: int = 60) -> str:
        return create_event(summary, date, duration)

def get_tool_info():
    return CALENDAR_TOOL_INSTRUCTIONS

# Test the functions if run directly
if __name__ == "__main__":
    print("\nTesting Calendar functions:")
    try:
        # Test listing calendars
        print("\n1. Testing manage_calendar_list():")
        calendars = manage_calendar_list(action="list")
        print(calendars)
        
        # Test getting calendar colors
        print("\n2. Testing get_calendar_colors():")
        colors = get_calendar_colors()
        print(colors)
        
        # Test listing events
        print("\n3. Testing list_events():")
        events = list_events(max_results=3)
        print(events)
        
        # Test creating an event for today at 7pm PST
        print("\n4. Testing create_event():")
        today = datetime.now()
        start_time = today.replace(hour=19, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        # Format times in ISO format with PST timezone
        start_iso = start_time.strftime("%Y-%m-%dT19:00:00-07:00")
        end_iso = end_time.strftime("%Y-%m-%dT20:00:00-07:00")
        
        event_result = create_event(
            summary="Test Event - Today at 7pm",
            date=f"{today.strftime('%Y-%m-%d')} {today.strftime('%H:%M')}",
            duration=60
        )
        print(event_result)
        
        # Extract event ID from the result
        event_id = event_result.split("Event ID: ")[-1].strip()
        
        # Test quick add event
        print("\n5. Testing quick_add_event():")
        quick_event = quick_add_event(
            calendar_id="primary",
            text="Meeting with Team tomorrow at 2pm for 1 hour"
        )
        print(quick_event)
        
        # Test updating the event
        print("\n6. Testing update_event():")
        update_result = update_event(
            event_id=event_id,
            summary="Updated Test Event",
            date=f"{today.strftime('%Y-%m-%d')} {today.strftime('%H:%M')}",
            duration=60
        )
        print(update_result)
        
        # Test querying free/busy
        print("\n7. Testing query_freebusy():")
        tomorrow = today + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
        
        freebusy = query_freebusy(
            time_min=tomorrow_start.isoformat() + "Z",
            time_max=tomorrow_end.isoformat() + "Z",
            calendar_ids=["primary"]
        )
        print(freebusy)
        
        # Test getting calendar settings
        print("\n8. Testing manage_settings():")
        settings = manage_settings(action="list")
        print(settings)
        
        # Test getting ACL rules
        print("\n9. Testing manage_calendar_acl():")
        acl_rules = manage_calendar_acl(action="list")
        print(acl_rules)
        
        # Test listing events again to verify changes
        print("\n10. Verifying event creation - listing events again:")
        updated_events = list_events(max_results=5)
        print(updated_events)
        
        # Clean up by deleting the test event
        print("\n11. Cleaning up - deleting test event:")
        delete_result = delete_event(event_id)
        print(delete_result)
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())

CALENDAR_TOOL_INSTRUCTIONS = {
    "name": "google_calendar_tool",
    "description": "Manages calendar events, appointments, and availability",
    "capabilities": [
        "View events for a specific date",
        "Create new events",
        "Update existing events",
        "Delete events",
        "Check availability (free/busy)",
        "Quick add events from text",
        "Manage calendar settings and access"
    ],
    "date_handling": {
        "format": "YYYY-MM-DD",
        "relative_dates": {
            "today": "current date",
            "tomorrow": "current date + 1 day",
            "next [day]": "next occurrence of specified day"
        },
        "time_format": "HH:MM (24-hour)",
        "timezone": "Local system timezone"
    },
    "operations": {
        "view_events": {
            "description": "List events for a specific date",
            "parameters": {
                "date": "YYYY-MM-DD",
                "max_results": "optional, default 10"
            },
            "example": {"request": {"action": "view_events", "date": "2024-02-23"}}
        },
        "create_event": {
            "description": "Create a new calendar event",
            "parameters": {
                "summary": "Event title/name",
                "date": "YYYY-MM-DD",
                "start_time": "HH:MM",
                "duration": "minutes (integer)"
            },
            "example": {
                "request": {
                    "action": "create_event",
                    "summary": "Team Meeting",
                    "date": "2024-02-23",
                    "start_time": "14:30",
                    "duration": 60
                }
            }
        },
        "update_event": {
            "description": "Update an existing event",
            "parameters": {
                "event_id": "Event ID to update",
                "summary": "optional - new title",
                "date": "optional - YYYY-MM-DD",
                "start_time": "optional - HH:MM",
                "duration": "optional - minutes"
            }
        },
        "delete_event": {
            "description": "Delete an event",
            "parameters": {"event_id": "Event ID to delete"}
        },
        "query_freebusy": {
            "description": "Check availability in a time range",
            "parameters": {
                "time_min": "Start time (ISO format)",
                "time_max": "End time (ISO format)"
            }
        },
        "quick_add": {
            "description": "Create event from natural language text",
            "parameters": {
                "text": "Event description (e.g. 'Meeting tomorrow at 3pm')"
            }
        }
    }
} 