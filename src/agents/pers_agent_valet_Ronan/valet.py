import logging
import json

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage

from src.agents.personality_agent import PersonalityAgent
from src.agents.pers_agent_valet_Ronan.config import ValetConfig
from src.tools.calendar_helper import CalendarHelper


class Valet(PersonalityAgent):
    """Valet: The principal point of contact for the agent swarm."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Configuration and state
    config: ValetConfig = Field(default_factory=ValetConfig)
    llm: Any = Field(description="LLM instance for generating responses")
    
    def __init__(self, llm, **kwargs):
        config = ValetConfig()
        
        # Initialize tools
        self.calendar_helper = CalendarHelper()  # Will update with user settings later
        
        super().__init__(
            llm=llm,
            name=config.title,
            type="orchestrator",
            description=f"{config.role}, coordinates all household operations",
            # Add calendar tool to available tools
            available_tools=[self.calendar_helper],
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


    def get_system_prompt(self) -> str:
        """Get Valet's specialized system prompt."""
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