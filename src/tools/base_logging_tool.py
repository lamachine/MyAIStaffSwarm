from langchain.tools import BaseTool
from typing import Any, Dict
from src.tools.credentials_handler import get_credentials
from supabase import create_client, Client
from pydantic import BaseModel, Field
import os
import json

class BaseLoggingTool(BaseTool):
    """Base tool with logging capabilities."""
    
    # Add supabase as a proper field
    supabase: Client = Field(default_factory=lambda: create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_KEY", "")
    ))
    
    async def store_message(self, message_data: Dict[str, Any]) -> bool:
        """Store a tool message in the swarm_messages table."""
        try:
            data = {
                "session_id": message_data["session_id"],
                "sender": message_data["sender"],
                "target": message_data["target"],
                "content": message_data["content"],
                "metadata": message_data.get("metadata", {})
            }
            
            result = self.supabase.table("swarm_messages").insert(data).execute()
            return True
            
        except Exception as e:
            print(f"Error storing tool message: {str(e)}")
            return False
    
    async def _arun(self, tool_input: Dict[str, Any]) -> str:
        """Execute the tool with logging."""
        try:
            # Log tool request
            await self.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": "James",
                "target": self.name,
                "content": json.dumps(tool_input)
            })
            
            # Execute tool
            result = await self.execute(tool_input)
            
            # Log result
            await self.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": self.name,
                "target": "James",
                "content": str(result)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            await self.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": self.name,
                "target": "James",
                "content": error_msg
            })
            return error_msg

    async def execute(self, tool_input: Dict[str, Any]) -> str:
        """Tool-specific execution logic to be implemented by subclasses."""
        raise NotImplementedError 