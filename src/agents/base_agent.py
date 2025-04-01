import os
import json
import logging


from datetime import datetime
from dataclasses import dataclass, field

from supabase import create_client, Client
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, AIMessage


from src.services.logging.message_logger import MessageLogger
from src.tools.llm.ollama_embeddings import OllamaEmbeddings

logger = logging.getLogger(__name__)

class AgentState(BaseModel):
    """State management for agents."""
    messages: List[BaseMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    tool_states: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = Field(..., description="Current session identifier")

class Agent(BaseModel):
    """Base class for all agents in the system."""
    
    # Identity (consistent with BaseTool)
    name: str = Field(..., description="Name of the agent")
    type: str = Field(..., description="Type of agent (e.g., 'orchestrator', 'memory')")
    description: str = Field(..., description="Agent's purpose and capabilities")
    version: str = Field(default="1.0.0", description="Agent version number")
    
    # Agent-specific configuration
    available_tools: List[BaseTool] = Field(
        default_factory=list,
        description="Tools available to this agent"
    )
    state_management: Dict[str, Any] = Field(
        default_factory=lambda: {
            "required_keys": ["messages", "context", "task_stack"],
            "updatable_keys": ["messages", "context", "task_stack", "agent_state"]
        },
        description="State management configuration"
    )
    
    # Embeddings model
    embeddings: Optional[OllamaEmbeddings] = Field(default=None)
    
    # LLM
    llm: Any = None
    
    # Supabase
    supabase: Client = Field(default_factory=lambda: create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_KEY", "")
    ))
    
    # Tools
    tools: List[BaseTool] = []
    
    # Message Logger
    logger: MessageLogger = Field(default_factory=MessageLogger)
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True  # Allow custom classes like OllamaEmbeddings
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.embeddings is None:
            self.embeddings = OllamaEmbeddings()
    
    def validate_state(self, state: Dict[str, Any]) -> bool:
        """Validate required state keys exist."""
        required_keys = ["session_id", "messages", "context", "tool_states"]
        return all(key in state for key in required_keys)
    
    async def get_relevant_context(self, query: str, threshold: float = 0.7, limit: int = 5) -> List[Dict]:
        """Get relevant messages from history using vector similarity."""
        try:
            # Generate embedding for query
            if not self.embeddings:
                logging.warning("No embeddings model set - skipping context retrieval")
                return []
                
            query_embedding = self.embeddings.embed_query(query)
            
            # Call match_swarm_messages function
            result = self.supabase.rpc(
                'match_swarm_messages',
                {
                    'query_embedding': query_embedding,
                    'similarity_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data
            
        except Exception as e:
            logging.error(f"Error getting relevant context: {e}")
            return []

    async def store_message(self, message_data: Dict[str, Any]) -> bool:
        """Store a message in the swarm_messages table."""
        return await self.logger.store_message(message_data)

    def process_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and handle tool usage."""
        try:
            # Get response from LLM
            message = state["messages"][-1]
            response = self.llm.invoke(message.content)
            response_text = str(response)
            
            # Log the raw response
            logger.info(f"[{self.name}] Raw LLM response: {response_text}")
            
            # Extract content
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Add response to messages using AIMessage
            state["messages"].append(AIMessage(content=response_text))
            return state

        except Exception as e:
            logger.error(f"[{self.name}] Error: {str(e)}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "session_id": state.get("session_id", "error"),
                "context": {"error": str(e)},
                "tool_states": {}
            }

    def _create_response(self, content: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standard response structure."""
        return {
            "messages": [AIMessage(content=content)],
            "session_id": state.get("session_id", "test"),
            "context": state.get("context", {}),
            "tool_states": state.get("tool_states", {})
        }

    def _create_error_response(self, error: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create an error response structure."""
        return {
            "messages": [AIMessage(content=f"Error: {error}")],
            "session_id": state.get("session_id", "error"),
            "context": {"error": error},
            "tool_states": {}
        }
    
    def execute_tool(self, tool_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool operation with current state."""
        # Validate state access
        if not self.validate_state(state):
            raise ValueError("Invalid state: missing required keys")
            
        # Find requested tool
        tool = next((t for t in self.available_tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
            
        try:
            # Execute tool
            result = tool.invoke(state["context"])
            
            # Return state modifications
            return {
                "tool_calls": [{
                    "tool": tool_name,
                    "status": "success",
                    "result": result
                }],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Tool execution error: {str(e)}")
            return {
                "tool_calls": [{
                    "tool": tool_name,
                    "status": "error",
                    "error": str(e)
                }],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return f"""You are {self.name}, a {self.type} agent.
        
Description: {self.description}

Available tools: {[t.name for t in self.available_tools]}"""

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and return updates."""
        # Validate required state exists
        for key in self.state_management["required_keys"]:
            if key not in state:
                raise ValueError(f"Missing required state key: {key}")
        
        # Agent processing logic here - to be implemented by subclasses
        raise NotImplementedError("Subclasses must implement process()") 