from typing import Dict, Any
from src.agents.personality_agent import PersonalityAgent
from pydantic import Field

class FrZophAgent(PersonalityAgent):
    """Fr. Zoph - Librarian and Research Specialist."""
    name: str = Field(default="Fr. Zoph", description="Research Librarian")
    type: str = Field(default="research_librarian", description="Research and knowledge management specialist")
    description: str = Field(
        default="Manages research tasks, handles RAG functions, and oversees documentation",
        description="Agent's core responsibilities"
    ) 