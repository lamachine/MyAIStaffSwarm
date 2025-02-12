from typing import Dict, Type, Optional
from .base import BaseTool
from .rag.rag_tool import RAGTool
from .agent_swarm_pipe import AgentSwarmPipeTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance"""
        self._tools[tool.metadata.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a registered tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, str]:
        """List all registered tools and their descriptions"""
        return {
            name: tool.metadata.description 
            for name, tool in self._tools.items()
        } 

# Register all available tools
AVAILABLE_TOOLS: Dict[str, Type[BaseTool]] = {
    "rag_search": RAGTool,
    "agent_swarm": AgentSwarmPipeTool
}

def get_tool(tool_name: str) -> BaseTool:
    """Get a tool instance by name"""
    if tool_name not in AVAILABLE_TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
        
    return AVAILABLE_TOOLS[tool_name]() 