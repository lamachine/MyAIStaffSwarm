from typing import Dict, Any, Optional
from pydantic import BaseModel

class ConversationState(BaseModel):
    conversation_id: str
    current_context: str = ""
    message_history: list = []
    metadata: Dict[str, Any] = {}
    agent_states: Dict[str, Any] = {}

class GraphStateManager:
    def __init__(self):
        self.states: Dict[str, ConversationState] = {}
    
    async def get_current_state(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self.states:
            self.states[conversation_id] = ConversationState(
                conversation_id=conversation_id
            )
        return self.states[conversation_id]
    
    async def update_state(self, conversation_id: str, 
                          updates: Dict[str, Any]) -> ConversationState:
        state = await self.get_current_state(conversation_id)
        for key, value in updates.items():
            setattr(state, key, value)
        return state 