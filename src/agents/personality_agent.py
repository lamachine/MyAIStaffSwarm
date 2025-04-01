import logging

from typing import Dict, Any, Optional

from pydantic import Field

from langchain_core.messages import BaseMessage

from src.agents.base_agent import Agent

logger = logging.getLogger(__name__)

class PersonalityAgent(Agent):
    """Base class for agents with personality traits."""
    
    # Personality traits
    communication_style: str = Field(default="professional", description="Agent's communication style")
    formality_level: str = Field(default="formal", description="Level of formality in responses")
    empathy_level: str = Field(default="moderate", description="Level of empathy in responses")
    
    # User preferences
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences for interaction"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load any personality-specific configuration here
        self.load_personality_config()

    def load_personality_config(self):
        """Load personality configuration from files or environment."""
        try:
            # Could load from JSON files, environment variables, etc.
            # For now, using defaults
            pass
        except Exception as e:
            logger.warning(f"Could not load personality config: {e}")

    def modify_response_for_personality(self, response: str) -> str:
        """Modify response based on personality traits."""
        # This could be enhanced with more sophisticated text processing
        return response

    def process_message(self, message: BaseMessage, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with personality considerations."""
        # Get base response from parent class
        response = super().process_message(message, state)
        
        # If there's an error, return as is
        if "error" in response.get("context", {}):
            return response
            
        # Modify the response based on personality
        if response.get("messages"):
            original_message = response["messages"][0]
            modified_content = self.modify_response_for_personality(original_message.content)
            response["messages"][0].content = modified_content
            
        return response

    def get_system_prompt(self) -> str:
        """Get personality-aware system prompt."""
        base_prompt = super().get_system_prompt()
        personality_prompt = f"""
Communication Style: {self.communication_style}
Formality Level: {self.formality_level}
Empathy Level: {self.empathy_level}

Please maintain this personality in all interactions.
"""
        return f"{base_prompt}\n{personality_prompt}" 