import os
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file and retrieve configuration.
load_dotenv()  
load_dotenv(override=True)
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8080"))
LOG_DIR = os.getenv("LOG_DIR", "./logs")
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Create Supabase client using the API endpoint in SUPABASE_URL (see Agent_0.py for reference)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY not found in environment variables")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.on_event("startup")
async def startup():
    pass

@app.on_event("shutdown")
async def shutdown():
    pass

# Pydantic models from before
class ChatMessage(BaseModel):
    user_id: str = Field(..., description="ID of the user sending the message")
    role: str = Field(..., description="Role of the sender (e.g., 'user', 'assistant')")
    content: str = Field(..., description="The message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time of the message")

class ChatLog(BaseModel):
    conversation_id: str = Field(..., description="Unique identifier for the conversation")
    messages: List[ChatMessage] = Field(default_factory=list, description="List of chat messages")

# In-memory store for demonstration; replace with a database or file system as needed.
conversations = {}

@app.post("/log_message")
async def log_message(conversation_id: str, message: ChatMessage):
    # Get existing conversation or create new one.
    if conversation_id not in conversations:
        conversations[conversation_id] = ChatLog(conversation_id=conversation_id)
    conversations[conversation_id].messages.append(message)
    # Construct the output file path based on configuration.
    output_file = os.path.join(LOG_DIR, f"{conversation_id}.json")
    try:
        with open(output_file, "w") as f:
            f.write(conversations[conversation_id].json(indent=2))
        logger.info(f"Conversation {conversation_id} logged to {output_file}")
    except Exception as e:
        logger.error(f"Error writing conversation {conversation_id} to file: {e}")
        return {"status": "error", "error": str(e)}

    # Insert the new message into the messages table using the Supabase client.
    values = {
        "user_id": message.user_id,
        "role": message.role,
        "content": message.content,
        "embedding": None,
        "embedding_model": "default",  # Default placeholder
        "conversation_id": conversation_id,
        "parent_message_id": None,
        "metadata": {}  # Use an empty JSON object as default
    }
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: supabase.table("messages").insert(values).execute())
        logger.info(f"Message from user {message.user_id} inserted into the database. Result: {result}")
    except Exception as db_err:
        logger.error(f"Error inserting message into database: {db_err}")
        return {"status": "error", "error": str(db_err)}

    return {"status": "logged"}

# Example middleware that could capture messages from Cursor Composer
@app.middleware("http")
async def capture_cursor_messages(request: Request, call_next):
    # Add logic to determine if the request is from Cursor Composer if needed.
    response = await call_next(request)
    return response

# This endpoint is for the Composer to send its messages.
@app.post("/cursor_composer_hook")
async def cursor_composer_hook(payload: dict):
    # Extract conversation information from the payload
    conversation_id = payload.get("conversation_id", "default_conv")
    message_data = payload.get("message", {})
    # Construct a ChatMessage from the payload (ensure it matches structure)
    message = ChatMessage(
        user_id=message_data.get("user_id", "unknown"),
        role=message_data.get("role", "unknown"),
        content=message_data.get("content", "")
    )
    # Log the message using the above function
    await log_message(conversation_id, message)
    return {"status": "logged from Cursor Composer"}

# Run your FastAPI app, ensuring the correct module is referenced.
if __name__ == "__main__":
    import uvicorn
    # Update the module name below to match this file's name "ComposerChatLog"
    uvicorn.run("ComposerChatLog:app", host=APP_HOST, port=APP_PORT, reload=True)