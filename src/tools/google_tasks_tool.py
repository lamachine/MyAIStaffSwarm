import os
import json
import asyncio
from functools import lru_cache
from typing import Any, Dict, List

from googleapiclient.discovery import build
from pydantic import BaseModel
from src.tools.base_tool import BaseTool

# Import credentials handler
from src.tools.credentials_handler import get_credentials

@lru_cache(maxsize=1)
def get_tasks_service():
    """
    Get and cache the Google Tasks API service.
    """
    creds = get_credentials()
    return build('tasks', 'v1', credentials=creds)

# Pydantic model to validate incoming parameters
class GoogleTasksParameters(BaseModel):
    action: str
    tasklist_id: str = None
    title: str = None
    task_id: str = None
    notes: str = None
    due: str = None
    max_results: int = 100
    parent: str = None
    previous: str = None

class GoogleTasksTool(BaseTool):
    """
    GoogleTasksTool interacts with the Google Tasks API to manage task lists and tasks.
    Supported actions:
      - list_tasklists
      - insert_tasklist
      - delete_tasklist
      - list_tasks
      - insert_task
      - delete_task
      - get_task
      - update_task
      - patch_task
      - move_task
      - clear_tasks
    """
    name = "google_tasks_tool"
    description = "Manage Google Tasks: task lists and tasks operations (list, insert, delete, update, patch, move, clear)."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The operation to perform on Google Tasks.",
                "enum": [
                    "list_tasklists",
                    "insert_tasklist",
                    "delete_tasklist",
                    "list_tasks",
                    "insert_task",
                    "delete_task",
                    "get_task",
                    "update_task",
                    "patch_task",
                    "move_task",
                    "clear_tasks"
                ]
            },
            "tasklist_id": {
                "type": "string",
                "description": "ID of the task list (required for certain actions)."
            },
            "title": {
                "type": "string",
                "description": "Title for creating a task list or task."
            },
            "task_id": {
                "type": "string",
                "description": "ID of the task (required for deletion or update operations)."
            },
            "notes": {
                "type": "string",
                "description": "Notes for task creation or update."
            },
            "due": {
                "type": "string",
                "description": "Due date/time in ISO format for task creation or update."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results for listing tasks."
            },
            "parent": {
                "type": "string",
                "description": "Parent task ID for moving a task (optional)."
            },
            "previous": {
                "type": "string",
                "description": "Previous task ID for moving a task (optional)."
            }
        },
        "required": ["action"]
    }
    required: List[str] = ["action"]

    async def execute(self, **kwargs) -> str:
        """
        Execute the specified Google Tasks operation.
        """
        try:
            params = GoogleTasksParameters(**kwargs)
        except Exception as e:
            return f"Parameter validation error: {str(e)}"

        action = params.action
        service = get_tasks_service()

        # Helper to run blocking Google API calls asynchronously.
        async def run_in_thread(func, *args, **kw):
            return await asyncio.to_thread(lambda: func(*args, **kw))

        if action == "list_tasklists":
            try:
                result = await run_in_thread(service.tasklists().list().execute)
                items = result.get('items', [])
                return json.dumps(items, indent=2)
            except Exception as e:
                return f"Error listing task lists: {str(e)}"

        elif action == "insert_tasklist":
            if not params.title:
                return "Error: 'title' parameter is required for insert_tasklist."
            try:
                insert_call = service.tasklists().insert(body={"title": params.title})
                result = await run_in_thread(insert_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error inserting task list: {str(e)}"

        elif action == "delete_tasklist":
            if not params.tasklist_id:
                return "Error: 'tasklist_id' is required for delete_tasklist."
            try:
                delete_call = service.tasklists().delete(tasklist=params.tasklist_id)
                await run_in_thread(delete_call.execute)
                return f"Task list {params.tasklist_id} deleted successfully."
            except Exception as e:
                return f"Error deleting task list: {str(e)}"

        elif action == "list_tasks":
            if not params.tasklist_id:
                return "Error: 'tasklist_id' is required for list_tasks."
            try:
                list_call = service.tasks().list(
                    tasklist=params.tasklist_id,
                    maxResults=params.max_results,
                    showCompleted=True,
                    showDeleted=False,
                    showHidden=True
                )
                result = await run_in_thread(list_call.execute)
                tasks = result.get("items", [])
                return json.dumps(tasks, indent=2)
            except Exception as e:
                return f"Error listing tasks: {str(e)}"

        elif action == "insert_task":
            if not params.tasklist_id or not params.title:
                return "Error: 'tasklist_id' and 'title' are required for insert_task."
            body = {"title": params.title, "notes": params.notes or ""}
            if params.due:
                body["due"] = params.due
            try:
                insert_call = service.tasks().insert(tasklist=params.tasklist_id, body=body)
                result = await run_in_thread(insert_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error inserting task: {str(e)}"

        elif action == "delete_task":
            if not params.tasklist_id or not params.task_id:
                return "Error: 'tasklist_id' and 'task_id' are required for delete_task."
            try:
                delete_call = service.tasks().delete(tasklist=params.tasklist_id, task=params.task_id)
                await run_in_thread(delete_call.execute)
                return f"Task {params.task_id} deleted successfully from task list {params.tasklist_id}."
            except Exception as e:
                return f"Error deleting task: {str(e)}"

        elif action == "get_task":
            if not params.tasklist_id or not params.task_id:
                return "Error: 'tasklist_id' and 'task_id' are required for get_task."
            try:
                get_call = service.tasks().get(tasklist=params.tasklist_id, task=params.task_id)
                result = await run_in_thread(get_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error getting task: {str(e)}"

        elif action == "update_task":
            if not params.tasklist_id or not params.task_id or not params.title:
                return "Error: 'tasklist_id', 'task_id', and 'title' are required for update_task."
            body = {"title": params.title, "notes": params.notes or ""}
            if params.due:
                body["due"] = params.due
            try:
                update_call = service.tasks().update(tasklist=params.tasklist_id, task=params.task_id, body=body)
                result = await run_in_thread(update_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error updating task: {str(e)}"

        elif action == "patch_task":
            if not params.tasklist_id or not params.task_id:
                return "Error: 'tasklist_id' and 'task_id' are required for patch_task."
            body = {}
            if params.title is not None:
                body["title"] = params.title
            if params.notes is not None:
                body["notes"] = params.notes
            if params.due is not None:
                body["due"] = params.due
            try:
                patch_call = service.tasks().patch(tasklist=params.tasklist_id, task=params.task_id, body=body)
                result = await run_in_thread(patch_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error patching task: {str(e)}"

        elif action == "move_task":
            if not params.tasklist_id or not params.task_id:
                return "Error: 'tasklist_id' and 'task_id' are required for move_task."
            try:
                move_call = service.tasks().move(
                    tasklist=params.tasklist_id,
                    task=params.task_id,
                    parent=params.parent,
                    previous=params.previous
                )
                result = await run_in_thread(move_call.execute)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error moving task: {str(e)}"

        elif action == "clear_tasks":
            if not params.tasklist_id:
                return "Error: 'tasklist_id' is required for clear_tasks."
            try:
                clear_call = service.tasks().clear(tasklist=params.tasklist_id)
                await run_in_thread(clear_call.execute)
                return f"Completed tasks cleared successfully for task list {params.tasklist_id}."
            except Exception as e:
                return f"Error clearing tasks: {str(e)}"

        else:
            return f"Error: Unknown action '{action}'." 