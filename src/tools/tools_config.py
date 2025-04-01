"""Tool specifications and formats for the AI Staff Swarm"""

CALENDAR_TOOL_SPEC = {
    "tool": "calendar",
    "operations": {
        "view_events": {
            "required": ["date"],
            "optional": ["max_results", "time_min", "time_max"],
            "format": "{'action': 'view', 'date': 'YYYY-MM-DD'}"
        },
        "create_event": {
            "required": ["summary", "date", "start_time", "duration"],
            "optional": ["description", "location", "guests"],
            "format": "{'action': 'create', 'summary': 'Event name', 'date': 'YYYY-MM-DD', 'start_time': 'HH:MM', 'duration': minutes}"
        },
        "delete_event": {
            "required": ["event_id"],
            "format": "{'action': 'delete', 'event_id': 'id'}"
        }
    }
}

# Add other tool specs as we create them
TOOL_SPECS = {
    "calendar": CALENDAR_TOOL_SPEC
} 