"""
UI node for handling user interaction.
Currently implements a simple CLI interface for testing.
"""

import json
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from src.core.logging_config import setup_logging
from src.core.graph_state import MainGraphState

LOGGER = setup_logging("ui_node")

def ui_node(state: MainGraphState) -> MainGraphState:
    """Handle user interaction through CLI
    
    The UI node:
    1. Displays messages to user if from orchestrator
    2. Gets user input if not displaying
    3. Updates state with user messages
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with user input
    """
    try:
        LOGGER.info("UI node received state: %s", state.get("content", ""))
        
        # If we have content to display from orchestrator, show it
        if state.get("content") and state.get("sender") == "orchestrator_node" and state.get("target") == "ui_node":
            try:
                content = json.loads(state["content"])
                if isinstance(content, dict) and "tool_input" in content:
                    message = content["tool_input"]
                    print(f"\nAssistant: {message}")
                    # Message already added to history by orchestrator
                    return state
                    
            except json.JSONDecodeError:
                LOGGER.warning("Invalid JSON content received: %s", state["content"])
                return state
                
        # Get user input if we're not displaying a message
        user_input = input("\nYou: ").strip()
        LOGGER.info("UI received input: %s", user_input)
        
        # Handle exit commands
        if user_input.lower() in ["/quit", "/exit"]:
            LOGGER.info("User requested exit")
            return {
                **state,
                "sender": "ui_node",
                "target": "orchestrator_node",
                "content": "/quit"
            }
            
        # Format user input as tool call to LLM
        # Note: Message will be added to history by orchestrator
        return {
            **state,
            "sender": "ui_node",
            "target": "orchestrator_node",
            "content": json.dumps({
                "tool": "llm_node",
                "tool_input": user_input
            })
        }
        
    except Exception as e:
        error_msg = f"UI error: {str(e)}"
        LOGGER.error(error_msg)
        return {
            **state,
            "sender": "ui_node",
            "target": "orchestrator_node",
            "content": json.dumps({
                "tool": "ui_node",
                "tool_input": error_msg
            })
        } 