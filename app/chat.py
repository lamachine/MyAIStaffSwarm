# Configure logging FIRST
import logging
logging.basicConfig(
    level=logging.INFO,
    force=True  # This will reconfigure any existing loggers
)
logger = logging.getLogger(__name__)

# Then do other imports
from langchain_core.messages import HumanMessage, AIMessage
import sys, os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.langgraphs.test_graph import create_test_graph
from langchain_ollama import ChatOllama

async def main():
    # Initialize LLM and workflow
    llm = ChatOllama(
        model="llama3.1:latest",
        temperature=0.0,
        num_gpu=1,
        num_thread=8
    )

    # Get workflow, agent and system prompt
    workflow, agent, system_prompt = await create_test_graph(llm)
    
    logger.info(f"Initializing James with system prompt:\n{system_prompt}")
    
    # Store initial system message with full context
    await agent.store_message({
        "session_id": "test_session",
        "sender": "system",
        "target": "James",
        "content": system_prompt,
        "metadata": {
            "message_type": "system_prompt",
            "agent_name": "James",
            "agent_type": "valet_orchestrator"
        }
    })
    
    print("\nJames AI Valet")
    print("Type 'quit' to exit\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
            
        try:
            state = {
                "messages": [HumanMessage(content=user_input)],
                "session_id": "test_session",
                "context": {},
                "tool_states": {}
            }
            
            result = await workflow.ainvoke(state)
            
            if "messages" in result:
                response = result["messages"][-1].content
                print(f"\nJames: {response}\n")
            else:
                print("\nJames: I apologize, but I couldn't generate a response.\n")
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"\nError: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(main()) 