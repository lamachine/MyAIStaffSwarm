from typing import Dict, Any
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from ..personality_agent import PersonalityAgent
import logging
import json

logger = logging.getLogger(__name__)

class Agent0(PersonalityAgent):
    """Basic test agent for development."""
    
    def __init__(self, llm=None, tools=None):
        super().__init__(
            name="James",
            type="valet_orchestrator",
            description="Head Valet and Orchestrator for the household",
            llm=llm,
            tools=tools or []
        )

    def get_system_prompt(self) -> str:
        """Get James's system context."""
        tool_list = "\n".join([f"- {t.name}: {t.description}" for t in self.tools]) if self.tools else "None"
        
        return f"""You are James, the Head Valet and Orchestrator. You embody:
- Personality: Proper English valet - formal yet warm, highly professional
- Role: Coordinate household operations and staff
- Communication: Clear, respectful, and service-oriented
- Core traits: Efficient, discrete, and meticulously organized

You maintain appropriate formality while being helpful and approachable.

Available tools:
{tool_list}"""

    async def process_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process messages with James's personality."""
        try:
            system_prompt = self.get_system_prompt()
            
            # Debug log what we're about to send to LLM
            print("\nSending to LLM:")
            print(f"System: {system_prompt}")
            print(f"User: {state['messages'][-1].content}")
            
            messages = [
                SystemMessage(content=system_prompt),
                *state["messages"]
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            print("\nRaw LLM Response:", response_text)
            
            # Try to parse as JSON first
            try:
                json_text = response_text.strip()
                if json_text.startswith('{'):
                    response_json = json.loads(json_text)
                    if isinstance(response_json, dict) and "tool" in response_json:
                        tool = next((t for t in self.tools if t.name == response_json["tool"]), None)
                        if tool:
                            # Execute tool directly
                            tool_response = await tool.arun(response_json["tool_input"])
                            response_text = f"I checked your calendar: {tool_response}"
                        else:
                            response_text = f"Error: Tool {response_json['tool']} not found"
            except Exception as e:
                response_text = f"Error executing tool: {str(e)}"
            
            # Store final response
            await self.store_message({
                "session_id": state["session_id"],
                "sender": "James",
                "target": "user",
                "content": response_text
            })
            
            state["messages"].append(AIMessage(content=response_text))
            return state
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "session_id": state.get("session_id", "error"),
                "context": {"error": str(e)},
                "tool_states": {}
            } 