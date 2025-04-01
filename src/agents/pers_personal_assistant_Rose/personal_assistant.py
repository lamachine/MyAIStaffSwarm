import logging
import json

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage


from src.agents.personality_agent import PersonalityAgent
from src.agents.pers_personal_assistant_Rose.config import PersonalAssistantConfig
from src.tools.calendar_helper import CalendarHelper


class Personal_Assistant(PersonalityAgent):
    """Key point of contact for the agent swarm, defers to valet."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Configuration and state
    config: PersonalAssistantConfig = Field(default_factory=PersonalAssistantConfig)
    llm: Any = Field(description="LLM instance for generating responses")
    
    def __init__(self, llm, **kwargs):
        config = PersonalAssistantConfig()
        
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