from typing import Dict, Any
from pydantic import Field
from src.agents.base_agent import Agent

class TaskAgent(Agent):
    """Template for functional support agents."""
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Metrics to track agent performance"
    )
    error_handling: Dict[str, str] = Field(
        default_factory=dict, 
        description="Error handling protocols"
    )
    retry_policy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_retries": 3,
            "delay": 1.0,
            "backoff_factor": 2.0
        },
        description="Retry configuration for failed operations"
    )
    monitoring_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "log_level": "INFO",
            "metrics_enabled": True,
            "alert_thresholds": {
                "error_rate": 0.01,
                "response_time": 5.0
            }
        },
        description="Monitoring and logging configuration"
    )
    
    def get_system_prompt(self) -> str:
        """Get the task-focused system prompt."""
        return f"""You are {self.name}, a {self.type} agent.
Your purpose is: {self.description}

Focus on efficiency and accuracy in your tasks.
Monitor and report performance metrics.
Follow error handling protocols strictly.

Available tools: {[t.name for t in self.available_tools]}"""
    
    def process_message(self, message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with task-specific handling."""
        # First log the message using parent's processing
        state_update = super().process_message(message, state)
        
        # Add task-specific monitoring
        state_update["context"].update({
            "performance_metrics": self.performance_metrics,
            "monitoring_config": self.monitoring_config
        })
        
        return state_update
    
    def execute_tool(self, tool_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with retry logic and monitoring."""
        retries = 0
        delay = self.retry_policy["delay"]
        
        while retries < self.retry_policy["max_retries"]:
            try:
                result = super().execute_tool(tool_name, state)
                
                # Add monitoring data
                result["monitoring"] = {
                    "attempt": retries + 1,
                    "success": True,
                    "timestamp": result["timestamp"]
                }
                
                return result
                
            except Exception as e:
                retries += 1
                if retries == self.retry_policy["max_retries"]:
                    raise e
                
                delay *= self.retry_policy["backoff_factor"]
                # Would add actual delay here in async implementation 