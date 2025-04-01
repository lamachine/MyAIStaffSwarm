"""
Shared state types for the graph system
"""

from typing import Annotated, Dict, List, Optional, Sequence, Any, NotRequired
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class MainGraphState(TypedDict):
    """State definition for the main graph"""
    # Required fields - must be present in every state update
    messages: Annotated[Sequence[BaseMessage], add_messages]
    sender: str
    target: str
    content: str
    session_id: str
    timestamp: str
    
    # Optional fields - may be omitted from state updates
    metadata: NotRequired[Dict[str, Any]]  # System info
    context: NotRequired[Dict[str, Any]]  # Session-specific
    tool_states: NotRequired[Dict[str, Any]]  # Persistent tool data 