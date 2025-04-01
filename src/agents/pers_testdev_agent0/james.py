from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from ..personality_agent import PersonalityAgent
from .config import JamesConfig
from langchain_core.messages import BaseMessage

class James(PersonalityAgent):
    """James: The valet and orchestrator of the agent swarm."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Configuration and state
    config: JamesConfig = Field(default_factory=JamesConfig)
    llm: Any = Field(description="LLM instance for generating responses")
    
    def __init__(self, llm, **kwargs):
        config = JamesConfig()
        super().__init__(
            llm=llm,
            name=config.title,
            type="orchestrator",
            description=f"{config.role}, coordinates all household operations",
            personality=f"""A {config.personality_type}: {config.core_traits['conscientiousness']}. 
            {config.core_traits['formality']}. {config.core_traits['reliability']}.""",
            communication_style=config.speech_style["tone"],
            relationship_dynamics={
                agent: data["interaction_style"] 
                for agent, data in config.staff_oversight.items()
            },
            user_preferences={
                "formal_address": True,
                "notification_frequency": "high",
                "priority_tasks": config.operational_standards["task_prioritization"]
            },
            **kwargs
        )
        self.config = config

    def route_request(self, state: Dict[str, Any]) -> str:
        """Determine which agent should handle a request."""
        # Extract the latest message
        latest_message = state["messages"][-1] if state["messages"] else None
        if not latest_message:
            return "error"
            
        # Basic routing logic (to be expanded)
        content = latest_message.content.lower()
        
        if any(word in content for word in ["research", "find", "search"]):
            return "Fr_Zoph"
        elif any(word in content for word in ["schedule", "appointment", "email"]):
            return "Rose"
        elif any(word in content for word in ["health", "exercise", "wellness"]):
            return "Dive_Master"
        
        # Default to handling it himself
        return "james"
    
    def process_message(self, message: BaseMessage, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with James's orchestration logic."""
        # First handle standard personality processing
        state_update = super().process_message(message, state)
        
        # Add orchestration-specific context
        next_agent = self.route_request(state)
        state_update["context"].update({
            "next_agent": next_agent,
            "orchestrator_status": "routing_complete",
            "staff_availability": {
                agent: "available" for agent in self.config.staff_oversight.keys()
            },
            "security_level": self.config.security_protocols["information_handling"]
        })
        
        return state_update
    
    def get_system_prompt(self) -> str:
        """Get James's specialized system prompt."""
        base_prompt = super().get_system_prompt()
        
        orchestrator_prompt = f"""
As the {self.config.role}, you:
1. {self.config.operational_standards['decision_making']}
2. Maintain {self.config.core_traits['formality']} and {self.config.core_traits['discretion']}
3. Ensure tasks are routed to appropriate specialists
4. Response time: {self.config.operational_standards['response_time']}
5. Security: {self.config.security_protocols['privacy_standards']}

Current staff roster:
{self._format_staff_roster()}
"""
        return f"{base_prompt}\n{orchestrator_prompt}"
    
    def _format_staff_roster(self) -> str:
        """Format staff roster for prompt."""
        return "\n".join([
            f"- {agent} ({data['role']}): {data['oversight_level']}"
            for agent, data in self.config.staff_oversight.items()
        ]) 