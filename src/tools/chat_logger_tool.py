import os
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from tools.base_tool import BaseTool

# Import Supabase client
from supabase import create_client, Client
# Import embedding function from LangChain Ollama integration
from langchain_ollama import OllamaEmbeddings

# Pydantic model for input validation
class ChatLoggerParameters(BaseModel):
    conversation_id: str
    user_id: str
    role: str
    content: str
    timestamp: str = None  # optional; if omitted, current time is used

class ChatLoggerTool(BaseTool):
    """
    ChatLoggerTool logs a chat message with vectorization.
    
    It computes an embedding for the message using OllamaEmbeddings, then logs the message
    (with the computed embedding and additional metadata) into the Supabase 'messages' table.
    """
    name = "chat_logger_tool"
    description = "Logs a chat message to the database and vectorizes the content for retrieval."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Unique identifier for the conversation."
            },
            "user_id": {
                "type": "string",
                "description": "ID of the user sending the message."
            },
            "role": {
                "type": "string",
                "description": "Role of the sender (e.g., 'user', 'assistant')."
            },
            "content": {
                "type": "string",
                "description": "The chat message content."
            },
            "timestamp": {
                "type": "string",
                "description": "Optional ISO timestamp of the message. Current time is used if not provided."
            }
        },
        "required": ["conversation_id", "user_id", "role", "content"]
    }
    required: List[str] = ["conversation_id", "user_id", "role", "content"]
    
    async def execute(self, **kwargs) -> str:
        # Validate and parse input parameters
        try:
            params = ChatLoggerParameters(**kwargs)
        except Exception as e:
            return f"Parameter validation error: {str(e)}"
        
        # Use provided timestamp or current time if omitted
        timestamp = params.timestamp or datetime.utcnow().isoformat()
        
        # Initialize Supabase client
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not SUPABASE_URL or not SUPABASE_KEY:
            return "Supabase configuration error."
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Initialize the embedding model using LangChain OllamaEmbeddings
        embedding_model = os.getenv("OLLAMA_PREFERRED_EMBEDDING_MODEL", "nomic-embed-text")
        base_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        try:
            embedding_instance = OllamaEmbeddings(model=embedding_model, base_url=base_url)
            # Assume embed_query is synchronous; wrap in asyncio.to_thread for async compatibility
            embedding = await asyncio.to_thread(embedding_instance.embed_query, params.content)
        except Exception as e:
            return f"Error computing embedding: {str(e)}"
        
        # Prepare record for insertion into the 'messages' table
        record = {
            "conversation_id": params.conversation_id,
            "user_id": params.user_id,
            "role": params.role,
            "content": params.content,
            "timestamp": timestamp,
            "embedding": embedding,
            "embedding_model": embedding_model,
            "metadata": {}  # Additional metadata can be added here
        }
        
        # Insert record into Supabase (using asyncio.to_thread to avoid blocking the event loop)
        try:
            insert_result = await asyncio.to_thread(
                lambda: supabase.table("messages").insert(record).execute()
            )
        except Exception as e:
            return f"Error inserting message into database: {str(e)}"
        
        return f"Message logged successfully. Insert result: {insert_result.data}"

# Demo usage for standalone testing:
if __name__ == "__main__":
    async def demo():
        tool = ChatLoggerTool()
        test_params = {
            "conversation_id": "test_conv_001",
            "user_id": "user_123",
            "role": "user",
            "content": "Hello, how can I improve my productivity?"
        }
        result = await tool.execute(**test_params)
        print(result)
    asyncio.run(demo()) 