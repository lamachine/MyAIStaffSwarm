from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from supabase import Client
from langchain_core.messages import BaseMessage

LOGGER = logging.getLogger(__name__)

class DatabaseService:
    """Handles database operations for the AI Staff Swarm."""
    
    def __init__(self, client: Client):
        self.client = client

    def store_message(self, message_data: Dict[str, Any]) -> bool:
        """Store a message in the swarm_messages table."""
        try:
            data = {
                "session_id": message_data["session_id"],
                "role": message_data["role"],  # 'human' or 'assistant'
                "content": message_data["content"],
                "agent_name": message_data.get("agent_name", "Agent0"),
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": message_data.get("metadata", {})
            }
            
            result = self.client.table("swarm_messages").insert(data).execute()
            LOGGER.info(f"Stored message: {result.data}")
            return True
        except Exception as e:
            LOGGER.error(f"Error storing message: {e}", exc_info=True)
            return False

    def save_checkpoint(
        self,
        graph_id: str,
        conversation_id: str,
        state_data: Dict[str, Any],
        summary: str = "",
        checkpoint_type: str = "auto"
    ) -> bool:
        """Save a graph state checkpoint."""
        try:
            data = {
                "graph_id": graph_id,
                "conversation_id": conversation_id,
                "state_data": state_data,
                "summary": summary,
                "checkpoint_type": checkpoint_type,
                "is_stable": True,
                "created_at": datetime.utcnow().isoformat(),
                "error_context": state_data.get("error_context", None)
            }
            
            result = self.client.table("graph_checkpoints").insert(data).execute()
            LOGGER.info(f"Checkpoint saved successfully: {result.data}")
            return True
        except Exception as e:
            LOGGER.error(f"Error saving checkpoint: {e}", exc_info=True)
            return False

    def save_messages(self, messages: List[BaseMessage], conversation_id: str, user_id: str = "default") -> bool:
        """Save chat messages to the database."""
        try:
            data = [
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "role": msg.__class__.__name__.replace("Message", "").lower(),
                    "content": msg.content,
                    "metadata": {
                        "additional_kwargs": msg.additional_kwargs
                    },
                    "created_at": datetime.utcnow().isoformat(),
                    "error_context": getattr(msg, "error_context", None)
                }
                for msg in messages
            ]
            
            result = self.client.table("messages").insert(data).execute()
            LOGGER.info(f"Messages saved successfully: {len(result.data)} records")
            return True
        except Exception as e:
            LOGGER.error(f"Error saving messages: {e}", exc_info=True)
            return False

    def get_messages_by_conversation(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve all messages for a specific conversation."""
        try:
            result = self.client.table("messages").select("*").eq("conversation_id", conversation_id).execute()
            LOGGER.info(f"Retrieved {len(result.data)} messages for conversation_id={conversation_id}")
            return result.data
        except Exception as e:
            LOGGER.error(f"Error retrieving messages for conversation_id={conversation_id}: {e}", exc_info=True)
            return None

    def search_messages_by_content(self, keyword: str) -> Optional[List[Dict[str, Any]]]:
        """Search for messages containing a specific keyword."""
        try:
            result = self.client.table("messages").select("*").ilike("content", f"%{keyword}%").execute()
            LOGGER.info(f"Retrieved {len(result.data)} messages containing keyword='{keyword}'")
            return result.data
        except Exception as e:
            LOGGER.error(f"Error searching messages with keyword='{keyword}': {e}", exc_info=True)
            return None

    def get_checkpoints_by_graph(self, graph_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve all checkpoints for a specific graph."""
        try:
            result = self.client.table("graph_checkpoints").select("*").eq("graph_id", graph_id).execute()
            LOGGER.info(f"Retrieved {len(result.data)} checkpoints for graph_id={graph_id}")
            return result.data
        except Exception as e:
            LOGGER.error(f"Error retrieving checkpoints for graph_id={graph_id}: {e}", exc_info=True)
            return None

    def execute_custom_query(self, table: str, query: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Execute a custom query on a specific table."""
        try:
            result = self.client.table(table).select("*").match(query).execute()
            LOGGER.info(f"Custom query on table={table} returned {len(result.data)} records")
            return result.data
        except Exception as e:
            LOGGER.error(f"Error executing custom query on table={table}: {e}", exc_info=True)
            return None