from pydantic import BaseModel
from typing import Optional, Dict, Any

class ToolMetadata(BaseModel):
    name: str
    description: str
    version: str = "0.1.0"
    config: Optional[Dict[str, Any]] = None

class BaseTool:
    metadata: ToolMetadata
    
    async def execute(self, **kwargs) -> Any:
        """Base execute method that all tools must implement"""
        raise NotImplementedError 