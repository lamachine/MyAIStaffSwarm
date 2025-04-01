"""
LLM node for processing messages through language models.
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from src.core.logging_config import setup_logging
from src.core.graph_state import MainGraphState
from dotenv import load_dotenv

LOGGER = setup_logging("llm_node")

# Load environment variables
load_dotenv()

# Parse default config
try:
    default_config = json.loads(os.getenv("OLLAMA_CHAT_CONFIG"))
except (json.JSONDecodeError, TypeError):
    LOGGER.error("Invalid or missing OLLAMA_CHAT_CONFIG")
    raise ValueError("OLLAMA_CHAT_CONFIG must be set in .env")

# LLM Mode configurations
LLM_MODES = {
    "chat": json.loads(os.getenv("OLLAMA_CHAT_CONFIG", "{}")),
    "code": json.loads(os.getenv("OLLAMA_CODE_CONFIG", "{}")),
    "research": json.loads(os.getenv("OLLAMA_RESEARCH_CONFIG", "{}")),
    "embedding": json.loads(os.getenv("OLLAMA_EMBEDDING_CONFIG", "{}"))
}

# System prompt for tool usage
SYSTEM_PROMPT = """You are an AI assistant that helps manage tasks, calendar, and email.
Always respond in JSON format with either a tool request or a response to the user.

For tool requests use:
{
    "tool": "calendar|email|tasks",
    "tool_input": {
        // tool specific parameters
    }
}

For user responses use:
{
    "ui_node": "Your message to the user"
}

Available tools:
- calendar: Manage calendar events
- email: Send and read emails
- tasks: Manage to-do items
"""

def get_llm(mode: str = "chat") -> ChatOllama:
    """Initialize LLM with appropriate configuration"""
    if mode not in LLM_MODES:
        LOGGER.warning(f"Unknown mode {mode}, falling back to chat")
        mode = "chat"
        
    config = LLM_MODES[mode]
    if not config:
        LOGGER.error(f"Missing configuration for mode {mode}")
        raise ValueError(f"Configuration for {mode} mode must be set in .env")
        
    return ChatOllama(**config)

def llm_node(state: MainGraphState) -> MainGraphState:
    """Process messages through LLM
    
    The LLM node:
    1. Gets mode from state metadata
    2. Initializes appropriate LLM
    3. Processes message with system prompt
    4. Returns JSON response for orchestrator
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with LLM response in JSON format
    """
    try:
        LOGGER.info("LLM processing message")
        
        # Get mode from metadata or default to chat
        mode = state.get("metadata", {}).get("llm_mode", "chat")
        llm = get_llm(mode)
        
        # Process with system prompt and message history
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        messages.extend(state.get("messages", []))  # Include full message history
        
        # Get LLM response
        llm_response = llm.invoke(messages)
        LOGGER.info("Raw LLM response type: %s", type(llm_response.content))
        LOGGER.info("Raw LLM response content: %s", llm_response.content)
        
        # Take only the first JSON object if multiple are returned
        response_text = llm_response.content.strip().split('\n\n')[0]
        
        try:
            # Parse response
            response_json = json.loads(response_text)
            LOGGER.debug("Parsed LLM response: %s", response_json)
            
            # If response has 'text' key but no 'tool', format as UI response
            if "text" in response_json and "tool" not in response_json:
                response_json = {
                    "tool": "ui",
                    "tool_input": response_json["text"]
                }
            
            # Validate tool_input format
            if not isinstance(response_json.get("tool_input"), str):
                LOGGER.warning("LLM returned invalid tool_input format: %s", response_json.get("tool_input"))
                if isinstance(response_json.get("tool_input"), dict):
                    response_json["tool_input"] = str(response_json["tool_input"])
            
            # Return updated state
            return {
                **state,
                "sender": "llm",
                "target": "orchestrator",
                "content": json.dumps(response_json),
                "metadata": {
                    **(state.get("metadata", {})),
                    "timestamp": datetime.now().isoformat(),
                    "llm_mode": mode,
                    "model": llm.model,
                    "token_usage": getattr(llm_response, "token_usage", {})
                }
            }
                
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing LLM response: {str(e)}"
            LOGGER.error(error_msg)
            error_response = {
                "tool": "ui",
                "tool_input": error_msg
            }
            return {
                **state,
                "sender": "llm",
                "target": "orchestrator",
                "content": json.dumps(error_response)
            }
            
    except Exception as e:
        LOGGER.error("LLM node error: %s", str(e))
        error_response = {
            "tool": "ui",
            "tool_input": f"LLM processing error: {str(e)}"
        }
        return {
            **state,
            "sender": "llm",
            "target": "orchestrator",
            "content": json.dumps(error_response)
        } 