import os
import asyncio
from typing import Any, Dict
from pydantic import BaseModel
from src.tools.base_tool import BaseTool
from supabase import create_client, Client

# Pydantic model for parameter validation
class ChatHistoryParameters(BaseModel):
    conversation_id: str
    limit: int = 10

class ChatHistoryTool(BaseTool):
    """
    ChatHistoryTool searches chat history from the 'messages' table in the database.
    
    Currently supports retrieving chat messages for a given conversation.
    """
    name = "chat_history_tool"
    description = "Searches chat history from the messages table in the database."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Conversation ID to search for chat history."
            },
            "limit": {
                "type": "integer",
                "description": "The maximum number of records to return.",
                "default": 10
            }
        },
        "required": ["conversation_id"]
    }
    required = ["conversation_id"]

    async def execute(self, **kwargs) -> str:
        try:
            params = ChatHistoryParameters(**kwargs)
        except Exception as e:
            return f"Parameter validation error: {str(e)}"

        # Initialize Supabase client
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not SUPABASE_URL or not SUPABASE_KEY:
            return "Supabase configuration error."

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        try:
            result = await asyncio.to_thread(
                lambda: supabase.table("messages")
                        .select("*")
                        .eq("conversation_id", params.conversation_id)
                        .order("timestamp", desc=True)
                        .limit(params.limit)
                        .execute()
            )
            return f"Chat history: {result.data}"
        except Exception as e:
            return f"Error retrieving chat history: {str(e)}" 