from supabase import create_client, Client
from typing import List, Dict, Any
import os
from datetime import datetime
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector from Ollama using nomic-embed-text.
    Pads the 768-dimensional vector to 1536 dimensions by repeating and adding zeros.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text}
            )
            embedding = response.json()["embedding"]
            
            # Pad to 1536 dimensions
            if len(embedding) == 768:
                # First repeat the vector
                padded = embedding * 2
                # If we need more dimensions, pad with zeros
                if len(padded) < 1536:
                    padded.extend([0.0] * (1536 - len(padded)))
                return padded
            return embedding
            
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536  # Return zero vector on error

async def add_message(user_id: str, conversation_id: str, role: str, content: str, parent_message_id: str = None, metadata: Dict[str, Any] = None):
    """
    Add a message to the chat history.
    
    Args:
        user_id: ID of the user who owns this message
        conversation_id: Unique identifier for the conversation
        role: 'user', 'assistant', or 'system'
        content: Message content
        parent_message_id: ID of the parent message if this is a reply
        metadata: Additional metadata about the message
    """
    try:
        # Get embedding for the content
        embedding = await get_embedding(content)
        
        # Create message data
        message_data = {
            "user_id": user_id,  # Add user_id to message data
            "role": role,
            "content": content,
            "conversation_id": conversation_id,
            "parent_message_id": parent_message_id,
            "metadata": {
                **(metadata or {}),
                "user_id": user_id  # Also add to metadata for filtering
            },
            "embedding": embedding,
            "embedding_model": "nomic-embed-text",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into messages table
        result = supabase.table("messages").insert(message_data).execute()
        
        if not result.data:
            print(f"Warning: No data returned when adding message")
            return None
            
        return result.data[0]
        
    except Exception as e:
        print(f"Error adding message: {e}")
        return None

async def get_conversation_history(user_id: str, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get the conversation history for a specific conversation.
    
    Args:
        user_id: ID of the user requesting the history
        conversation_id: The conversation to get history for
        limit: Maximum number of messages to return
    
    Returns:
        List of messages in chronological order
    """
    try:
        result = (supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)  # Only get messages for this user
            .order("created_at", desc=False)
            .limit(limit)
            .execute())
            
        return result.data if result.data else []
        
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

async def get_relevant_messages(user_id: str, conversation_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Get messages relevant to a query using vector similarity search.
    
    Args:
        user_id: ID of the user requesting the messages
        conversation_id: The conversation to search in
        query: The search query
        top_k: Number of relevant messages to return
    
    Returns:
        List of relevant messages with similarity scores
    """
    try:
        # Get embedding for query
        query_embedding = await get_embedding(query)
        
        # Use Supabase's vector similarity search with user filtering
        result = supabase.rpc(
            'match_messages',
            {
                'query_embedding': query_embedding,
                'match_count': top_k,
                'filter': {
                    'conversation_id': conversation_id,
                    'user_id': user_id  # Only match messages for this user
                }
            }
        ).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"Error getting relevant messages: {e}")
        return []

async def list_user_conversations(user_id: str) -> List[Dict[str, Any]]:
    """
    Get a list of all conversations for a user.
    
    Args:
        user_id: The user to get conversations for
        
    Returns:
        List of unique conversation IDs and their metadata
    """
    try:
        result = supabase.table("messages")\
            .select("conversation_id", "created_at")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
            
        # Get unique conversations
        conversations = {}
        for msg in result.data:
            if msg["conversation_id"] not in conversations:
                conversations[msg["conversation_id"]] = {
                    "conversation_id": msg["conversation_id"],
                    "last_updated": msg["created_at"]
                }
                
        return list(conversations.values())
        
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return []

# Example usage:
"""
# User information
user_id = "user123"
conversation_id = f"{user_id}_session456"

# Add some messages
await add_message(
    user_id=user_id,
    conversation_id=conversation_id,
    role="system",
    content="You are a helpful assistant."
)

await add_message(
    user_id=user_id,
    conversation_id=conversation_id,
    role="user",
    content="Hello, how are you?"
)

# Get user's conversations
conversations = await list_user_conversations(user_id)
for conv in conversations:
    print(f"Conversation: {conv['conversation_id']}, Last updated: {conv['last_updated']}")

# Get conversation history
history = await get_conversation_history(user_id, conversation_id)
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

# Get relevant messages for a query
relevant = await get_relevant_messages(user_id, conversation_id, "How are you doing?")
for msg in relevant:
    print(f"Relevant message: {msg['content']}")
"""