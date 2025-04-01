from typing import Annotated
import json
import logging
import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from src.langgraphs.test_graph import create_test_graph, AgentState

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize LLM
llm = ChatOllama(
    model="llama3.1:latest",
    temperature=0.7,
    num_gpu=1,  # Enable GPU
    num_thread=8  # Optimize threading
)

async def stream_graph_updates(user_input: str):
    """Process user input through the graph and stream responses."""
    try:
        print("\nProcessing message...")  # Visual feedback
        
        # Create proper state with all required keys
        state = AgentState(
            messages=[HumanMessage(content=user_input)],
            session_id="test_session",
            context={},
            tool_states={}
        )
        
        # Log LLM initialization
        logging.info("Initializing graph with LLM...")
        graph = create_test_graph(llm)
        
        # Process through graph using async API
        async for event in graph.astream(state):
            logging.info("Processing through graph...")  # Keep this log
            if "agent" in event and "messages" in event["agent"]:
                messages = event["agent"]["messages"]
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        print("\nAssistant:", msg.content)
                        return

    except Exception as e:
        logging.error(f"Error in stream_graph_updates: {str(e)}")
        raise

async def main():
    """Main async function."""
    logging.info("Initializing LLM with model: llama3.1:latest")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!\n")
                break
            
            if user_input.strip():
                await stream_graph_updates(user_input)
                
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            break

if __name__ == "__main__":
    asyncio.run(main())