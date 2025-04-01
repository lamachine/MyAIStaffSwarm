"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Annotated, Optional, Dict, Any, List

from langchain_core.runnables import RunnableConfig, ensure_config
from langchain_core.messages import BaseMessage, AIMessage
import logging

from src.langgraphs.main_graph import SYSTEM_PROMPT  # or whatever prompts you need

logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

def validate_log_level(level: str) -> str:
    if level.upper() not in VALID_LOG_LEVELS:
        raise ValueError(f"Invalid log level: {level}. Must be one of {VALID_LOG_LEVELS}.")
    return level.upper()

@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    system_prompt: str = field(
        default=SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="ollama/llama3.1",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    temperature: float = field(
        default=0.1,
        metadata={
            "description": "Temperature for model responses. Lower values (like 0.1) give more focused, "
            "deterministic outputs."
        },
    )

    context_window: int = field(
        default=16384,  # 16k context
        metadata={
            "description": "Maximum context window size for the model."
        },
    )

    max_tokens: int = field(
        default=2000,  # 2 to 4k is a good range for most models, limits the response length.
        metadata={
            "description": "Maximum number of tokens in model responses."
        },
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    source: str = field(
        default="cli",
        metadata={
            "description": "The interface source for the interaction. "
            "Can be 'cli', 'api', or 'ui'."
        },
    )

    thread_id: str = field(
        default="default",
        metadata={
            "description": "Unique identifier for the conversation thread."
        },
    )

    debug_level: str = field(
        default="INFO",
        metadata={
            "description": "Logging level for the application. Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        },
    )

    console_level: str = field(
        default="ERROR",
        metadata={
            "description": "Logging level for the console output. Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        },
    )

    file_level: str = field(
        default="DEBUG",
        metadata={
            "description": "Logging level for the file output. Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        },
    )

    error_handling: Dict[str, Any] = field(
        default_factory=lambda: {
            "tool": {
                "max_retries": 2,
                "backoff_factor": 1.5,
                "error_message": "Tool execution failed. Please try again."
            },
            "routing": {
                "default_node": "conversation",
                "error_message": "Unable to determine appropriate agent."
            },
            "agent": {
                "max_steps": 10,
                "timeout": 30
            }
        },
        metadata={
            "description": "Granular configuration for error handling across different components"
        },
    )

    node_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "conversation": {"timeout": 30},
            "search": {"timeout": 45},
            "analysis": {"timeout": 60}
        },
        metadata={
            "description": "Node-specific configuration parameters"
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        try:
            config = ensure_config(config)
            configurable = config.get("configurable") or {}
            _fields = {f.name for f in fields(cls) if f.init}
            instance = cls(**{k: v for k, v in configurable.items() if k in _fields})
            logger.debug("Configuration loaded from runnable config")
            return instance
        except Exception as e:
            logger.error(f"Configuration loading error: {str(e)}", exc_info=True)
            error_context = {
                "error_type": type(e).__name__,
                "error_details": str(e),
                "operation": "configuration_loading"
            }
            # Return default configuration
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        try:
            return self.dict()
        except Exception as e:
            logger.error(f"Configuration serialization error: {str(e)}", exc_info=True)
            return {}
