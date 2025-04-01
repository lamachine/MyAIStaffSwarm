"""
Orchestrator node for routing messages between components.
"""

import json
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.core.logging_config import setup_logging
from src.core.graph_state import MainGraphState

LOGGER = setup_logging("orchestrator_node")

def orchestrator_node(state: MainGraphState) -> MainGraphState:
    """Route messages between nodes and maintain state
    
    Args:
        state: Current graph state with messages: Annotated[list, add_messages]
        
    Returns:
        Updated state with routing information
    """
    try:
        # Log received state
        LOGGER.info("Orchestrator received: %s", state.get("content", ""))
        
        try:
            content = json.loads(state["content"])
            if isinstance(content, dict) and "tool" in content and "tool_input" in content:
                # Update routing
                state["target"] = content["tool"]
                state["sender"] = "orchestrator_node"
                
                # Update messages based on source/target
                if state.get("sender") == "ui_node":
                    state["messages"].append(HumanMessage(content=content["tool_input"]))
                elif state.get("sender") == "llm_node":
                    state["messages"].append(AIMessage(content=content["tool_input"]))
                
                LOGGER.info("Orchestrator routing to %s: %s", state["target"], content["tool_input"])
                return state
            else:
                raise ValueError("Message missing required fields: tool, tool_input")
                
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Invalid message format: {str(e)}"
            LOGGER.error(error_msg)
            
            # Add error to message history
            state["messages"].append(ToolMessage(
                content=error_msg,
                tool_name="orchestrator",
                tool_call_id="error"
            ))
            
            state["target"] = "ui_node"
            state["sender"] = "orchestrator_node"
            state["content"] = json.dumps({
                "tool": "ui_node",
                "tool_input": error_msg
            })
            
            LOGGER.info("Orchestrator sent error: %s", error_msg)
            return state
            
    except Exception as e:
        error_msg = f"Orchestrator error: {str(e)}"
        LOGGER.error(error_msg)
        
        # Add error to message history
        state["messages"].append(ToolMessage(
            content=error_msg,
            tool_name="orchestrator",
            tool_call_id="error"
        ))
        
        return {
            **state,
            "sender": "orchestrator_node",
            "target": "ui_node",
            "content": json.dumps({
                "tool": "ui_node",
                "tool_input": error_msg
            })
        } 