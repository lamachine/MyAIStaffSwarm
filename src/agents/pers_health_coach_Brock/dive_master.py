from typing import Dict, Any
from ..personality_agent import PersonalityAgent
from pydantic import Field

class DiveMasterAgent(PersonalityAgent):
    """Dive Master - Health and Fitness Coach."""
    name: str = Field(default="Dive Master", description="Health and Fitness Coach")
    type: str = Field(default="health_coach", description="Health and wellness specialist")
    description: str = Field(
        default="Tracks health metrics, provides wellness consultations, and monitors fitness progress",
        description="Agent's core responsibilities"
    ) 