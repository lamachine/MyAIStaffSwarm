from typing import List, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.llms import Ollama
from src.agents.pers_agent_orchestrator_James.james import James

def test_james_basic():
    """Basic test of James's functionality."""
    
    # Initialize James with Ollama
    llm = Ollama(model="llama2")  # or your preferred model
    james = James(llm=llm)
    
    # Create a test session state
    session_state = {
        "session_id": "test_session_001",
        "messages": [],
        "context": {},
        "tool_states": {},
    }
    
    # Test basic interaction
    user_message = HumanMessage(content="Hello James, I hope you're well today.")
    
    # Process the message
    state_update = james.process_message(user_message, session_state)
    
    # Generate response using LLM
    messages = [
        HumanMessage(content=james.get_system_prompt()),
        user_message
    ]
    
    response = llm.invoke(messages)
    print(f"James's response: {response}")
    
    return state_update

if __name__ == "__main__":
    test_james_basic() 