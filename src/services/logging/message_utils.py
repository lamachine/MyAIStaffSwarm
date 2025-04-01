import logging
import os
import sys

from functools import wraps
from typing import Any, Callable, Optional, Union, Dict, List
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage



sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.langgraphs.main_graph import MainGraphState
from src.services.logging.logging_config import get_logger

LOGGER = get_logger(__name__)

state = MainGraphState()  # Initialize state as an instance of MainGraphState

def handle_errors(logger: Optional[logging.Logger] = None):
    """Decorator for standardized error handling across all components.

    Ensures all errors are:
    1. Logged at ERROR level with contextual information.
    2. Added to state as user-friendly messages when possible.
    3. Re-raised with additional context for non-state functions.

    Args:
        logger: Optional logger instance. If None, uses the default LOGGER.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Union[Dict[str, List[BaseMessage]], str]:
            try:
                # Execute the wrapped function
                result = await func(*args, **kwargs)

                # Log successful execution for node tracking
                log = logger or LOGGER
                log.debug(
                    f"{func.__name__} completed successfully",
                    extra={"node_type": kwargs.get("node_type", "unknown")}
                )

                return result
            except Exception as e:
                # Get component name and full error details
                component_name = func.__name__
                error_msg = f"{component_name} failed: {str(e)}"

                error_context = {
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "operation": component_name,
                    "node_type": kwargs.get("node_type", "unknown")
                }

                # Log error to both file and console
                log = logger or LOGGER
                log.error(error_msg, exc_info=True, extra=error_context)

                # If we have state, add user-friendly message
                state = kwargs.get("state")  # Pass state explicitly in kwargs
                if state and isinstance(state, MainGraphState):
                    error_response = AIMessage(
                        content=f"I apologize, but an error occurred in {component_name}: {str(e)}. "
                                "Please try again or contact support if the issue persists."
                    )

                    # Return the error message and context
                    return {
                        "messages": [error_response],
                        "error_context": error_context
                    }

                # For non-state functions (tools, utilities, etc.)
                # Re-raise with logged context
                raise type(e)(f"{error_msg} - See logs for details.") from e

        return wrapper
    return decorator


def serialize_message(obj):
    """Serializes message objects for storage and transmission.

    Converts BaseMessage objects into a standardized dictionary format
    that can be stored or transmitted while preserving all relevant
    message attributes and metadata.

    Args:
        obj (BaseMessage): Message object to serialize
        
    Returns:
        dict: Serialized message in standard format
    """
    if isinstance(obj, (AIMessage, HumanMessage)):
        serialized = {
            "type": obj.__class__.__name__,
            "content": obj.content,
            "additional_kwargs": obj.additional_kwargs
        }
        # Add error context if present
        if hasattr(obj, "error_context"):
            serialized["error_context"] = obj.error_context
        return serialized
    return str(obj)