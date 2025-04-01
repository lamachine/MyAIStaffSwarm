from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool as LangchainBaseTool
import logging
from src.services.logging.message_logger import MessageLogger
import json

class BaseTool(LangchainBaseTool):
    """Base class for all tools in the system."""
    
    # Identity (consistent with Agent)
    name: str = Field(..., description="Name of the tool")
    category: str = Field(..., description="Tool category (e.g., 'calendar', 'email')")
    description: str = Field(..., description="Tool's purpose and capabilities")
    version: str = Field(default="1.0.0", description="Tool version number")
    
    # Tool-specific configuration
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool configuration parameters"
    )
    error_handling: Dict[str, str] = Field(
        default_factory=lambda: {
            "retry_on_error": ["ConnectionError", "TimeoutError"],
            "fail_fast_on": ["AuthenticationError", "ValidationError"]
        },
        description="Error handling protocols"
    )
    retry_policy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_retries": 3,
            "delay": 1.0,
            "exponential_backoff": True
        },
        description="Retry configuration for failed operations"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async run with error handling and retries."""
        try:
            return await self._aexecute(*args, **kwargs)
        except Exception as e:
            logging.error(f"Tool execution error: {str(e)}")
            return f"Error executing {self.name}: {str(e)}"
    
    def _run(self, *args, **kwargs) -> str:
        """Sync run with error handling."""
        raise NotImplementedError("All tools should implement async operations")
    
    async def _aexecute(self, *args, **kwargs) -> str:
        """Main execution logic - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _aexecute")

class BaseLoggingTool(BaseTool):
    """Base tool with logging capabilities."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = MessageLogger()
    
    async def _arun(self, tool_input: Dict[str, Any]) -> str:
        """Run tool with logging."""
        try:
            # Log tool request
            await self.logger.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": "James",
                "target": self.name,
                "content": json.dumps(tool_input)
            })
            
            # Run tool
            result = self._run(tool_input)
            
            # Log tool response
            await self.logger.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": self.name,
                "target": "James",
                "content": str(result)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            await self.logger.store_message({
                "session_id": tool_input.get("session_id", "unknown"),
                "sender": self.name,
                "target": "James",
                "content": error_msg
            })
            return error_msg 