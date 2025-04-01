from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from datetime import datetime, timedelta
import pytz
from src.tools.base_logging_tool import BaseLoggingTool
from src.tools.google_aps_api.google_calendar_tools import list_events, create_event
import json

class CalendarInput(BaseModel):
    """Schema for calendar tool input"""
    action: str = Field(description="Action to perform (view/add)")
    date: str = Field(default="today", description="Date for the action")
    summary: str = Field(default="", description="Event summary for add action")
    duration: str = Field(default="", description="Duration in minutes")

class CalendarHelper(BaseTool):
    """Calendar management tool."""
    name: str = "google_calendar"
    description: str = "View or add calendar events"
    args_schema: Type[BaseModel] = CalendarInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._timezone = pytz.timezone("UTC")

    async def _arun(self, tool_input: str) -> str:
        """Execute the tool."""
        try:
            # Parse input as dict if it's a string
            if isinstance(tool_input, str):
                tool_input = json.loads(tool_input)
                
            if tool_input["action"] == "view":
                start_time = self.parse_relative_time(tool_input["date"])
                return await list_events(max_results=10, time_min=start_time.isoformat())
            elif tool_input["action"] == "add":
                event_time = self.parse_relative_time(tool_input["date"])
                duration = int(tool_input["duration"].split()[0]) if tool_input["duration"] else 60
                return await create_event(
                    summary=tool_input["summary"],
                    start_time=event_time.isoformat(),
                    duration_minutes=duration
                )
            return "Error: Unknown action"
        except Exception as e:
            return f"Calendar Error: {str(e)}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Calendar operations are async only")

    def parse_relative_time(self, expression: str) -> datetime:
        """Convert relative time expressions to datetime."""
        now = datetime.now(self._timezone)
        
        if expression.lower() == "today":
            return now
        elif expression.lower() == "tomorrow":
            return now + timedelta(days=1)
        elif expression.lower() == "next week":
            return now + timedelta(weeks=1)
            
        return now

    async def get_calendar_events(self, time_range: str = "today") -> str:
        """Get calendar events for a time range."""
        start_time = self.parse_relative_time(time_range)
        return list_events(max_results=10, time_min=start_time.isoformat())
        
    async def add_calendar_event(
        self, 
        summary: str, 
        start_time: str, 
        duration: int = 60, 
        description: str = ""
    ) -> str:
        """Add a calendar event."""
        event_time = self.parse_relative_time(start_time)
        return create_event(
            summary=summary,
            start_time=event_time.isoformat(),
            duration_minutes=duration,
            description=description
        ) 