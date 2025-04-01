from typing import Dict, Any
from supabase import create_client, Client
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.services.logging.logging_config import get_logger
from src.tools.llm.ollama_embeddings import OllamaEmbeddings

LOGGER = get_logger(__name__)

class MessageLogger:
    """Centralized message logging service."""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_KEY", "")
        )
        self.embeddings = OllamaEmbeddings()
    
    async def store_message(self, message_data: Dict[str, Any]) -> bool:
        """Store a message in the swarm_messages table."""
        try:
            LOGGER.debug(f"Storing message: {message_data}")
            # Store message logic
            # Generate embedding
            embedding = self.embeddings.embed_query(message_data["content"])
            
            data = {
                "session_id": message_data["session_id"],
                "sender": message_data["sender"],
                "target": message_data["target"],
                "content": message_data["content"],
                "embedding": embedding,
                "metadata": message_data.get("metadata", {})
            }
            
            result = self.supabase.table("swarm_messages").insert(data).execute()
            LOGGER.info("Message stored successfully")
            return True
            
        except Exception as e:
            print(f"Error storing message: {str(e)}")
            return False 