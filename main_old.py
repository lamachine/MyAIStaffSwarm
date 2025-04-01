import sys, os
import signal
import asyncio
import requests
from time import sleep
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, Graph
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama  # Changed to ChatOllama for test

# Original imports (commented out)
# from src.agents.pers_agent_orchestrator_Ronan.Ronan import Ronan
# from core.state_manager import GraphStateManager
# from tools.llm_provider import LLMProvider
# from src.langgraphs.main_graph import create_main_graph

# Test imports
from src.agents.pers_testdev_agent0.agent_0 import Agent0
from src.langgraphs.test_graph import create_test_graph

# Input model for chat endpoint
class ChatInput(BaseModel):
    message: str
    conversation_id: str = "default"

# Define the state type for our graph
class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    context: dict
    tool_states: dict

# Initialize LLM for testing
llm = ChatOllama(
    model="llama3.1:latest",
    temperature=0.7,
    num_gpu=1,
    num_thread=8
)

# Add at top after imports:
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("=== Starting up MyAiStaffSwarm ===")
    logging.info("Initializing components...")
    
    try:
        # Original initialization (commented out)
        # app.state.llm_provider = LLMProvider()
        # app.state.state_manager = GraphStateManager()
        # GRAPH = create_main_graph()
        
        # Test initialization
        logging.info("Creating Test LangGraph workflow...")
        app.state.workflow = create_test_graph(llm)
        app.state.initialized = True
        logging.info("Test workflow created successfully")
        logging.info("=== Startup complete ===")
            
    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        app.state.initialized = False
        raise

    yield
    logging.info("=== Shutting down MyAiStaffSwarm ===")

app = FastAPI(title="MyAiStaffSwarm Application", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

@app.post("/chat", tags=["Chat"])
async def chat(chat_input: ChatInput):
    try:
        # Create test state
        state = AgentState(
            messages=[HumanMessage(content=chat_input.message)],
            session_id="test_session",
            context={},
            tool_states={}
        )
        
        # Process through test graph
        async for event in app.state.workflow.astream(state):
            if "agent" in event and "messages" in event["agent"]:
                messages = event["agent"]["messages"]
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        return {
                            "response": msg.content,
                            "state": event["agent"]
                        }
                        
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "AI Staff Swarm Running"}

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down gracefully...")
    # Stop uvicorn
    if hasattr(signal_handler, 'server'):
        signal_handler.server.should_exit = True
    sys.exit(0)

async def stream_graph_updates(user_input: str):
    """Process user input through the graph and stream responses."""
    try:
        print("\nProcessing message...")
        
        # Create proper state with all required keys
        state = AgentState(
            messages=[HumanMessage(content=user_input)],
            session_id="test_session",
            context={},
            tool_states={}
        )
        
        # Use the already initialized workflow from app.state
        logging.info("Processing through test graph...")
        async for event in app.state.workflow.astream(state):
            logging.info("Processing through graph...")
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
    logging.info("=== Main process starting ===")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start FastAPI server
    fastapi_port = int(os.getenv("FASTAPI_PORT", "8083"))
    logging.info(f"Configuring server on port {fastapi_port}")
    
    config = uvicorn.Config(
        "main:app", 
        host="0.0.0.0", 
        port=fastapi_port, 
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    signal_handler.server = server
    
    # Run both server and console interface
    async def run_server():
        logging.info("Starting FastAPI server...")
        try:
            await server.serve()
            logging.info("Server started successfully")
        except Exception as e:
            logging.error(f"Server startup error: {e}")
            raise

    async def run_all():
        try:
            # Start server first
            server_task = asyncio.create_task(run_server())
            logging.info("Starting FastAPI server...")
            
            # Wait for initial server startup
            await asyncio.sleep(2)  # Give server time to initialize
            
            # Wait for server to be ready
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Try to connect to health endpoint
                    response = requests.get(f"http://localhost:8083/health", timeout=2)
                    if response.status_code == 200:
                        logging.info("FastAPI server is ready!")
                        break
                except (requests.ConnectionError, requests.Timeout):
                    retry_count += 1
                    logging.info(f"Waiting for server to be ready... ({retry_count}/{max_retries})")
                    await asyncio.sleep(1)
            
            if retry_count >= max_retries:
                logging.error("Server failed to start properly")
                return
            
            # Start console interface
            logging.info("Starting console interface...")
            console_task = asyncio.create_task(main())
            
            # Wait for both tasks
            await asyncio.gather(server_task, console_task)
        except Exception as e:
            logging.error(f"Error in main process: {e}")
            raise
    
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logging.info("Received shutdown signal")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        logging.info("=== Shutdown complete ===") 