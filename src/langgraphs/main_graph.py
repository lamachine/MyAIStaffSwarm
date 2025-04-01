"""
Main orchestration graph for the AI Staff Swarm.
This implements the core routing and state management for the agent system.
"""
# MUST be at the top
from __future__ import annotations as _annotations

# General Imports
import asyncio
import os
import pytz
import sys

# Specific Imports
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from uuid import uuid4

# LangChain and LangGraph Imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Pydantic Imports
from pydantic import BaseModel, Field, validator
#                                      Depricated @validator
# use validator styles like @field_validator


# Local Imports, sys path allows for relative import references
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Agents
from src.agents.pers_agent_valet_Ronan import valet
from src.agents.pers_personal_assistant_Rose import personal_assistant
from src.agents.pers_health_coach_Dave import health_coach
from src.agents.pers_librarian_Leah import librarian
from src.agents.pers_tutor_Tina import tutor
from src.agents.pers_programmer_Paul import programmer
from src.agents.pers_research_librarian_FrZoph import research_librarian

from ..tools import tools

#from ..common

from ..config.configuration import Configuration

from ..core import graph_state, logging_config, state_manager

#from ..langgraphs

from ..services.database.db_config import DatabaseConfig
from ..services.logging import LoggingService
from ..services.models.model_utils import load_chat_model, call_model

from ..user_interface.cli import cli_for_test_and_dev


from ..user_interface import UserInterface


# Set up logging
LOGGER = setup_logging("main_graph")

# Configuration
config = Configuration()
model = load_chat_model(config) # Load the model once
db_config = DatabaseConfig()
db_client = db_config.get_client()  # Get the database client

# State
class MainGraphState(BaseModel):
    """
    Comprehensive state for the AI Staff Swarm LangGraph.
    """
    # --- Core State ---
    session_id: Optional[str] = Field(
        default=None, 
        description="Unique ID for the current conversation session"
        )
    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique ID for the current thread"
        )
    run_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique ID for the current run"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(
            pytz.timezone('America/Los_Angeles')
            ).strftime('%Y-%m-%d %H:%M:%S %Z'), 
        description="Timestamp of the current state"
        )
    user_input: Optional[str] = Field(
        default=None, 
        description="Raw text input from the user"
        )
    messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list, 
        description="Conversation history as a list of BaseMessage objects"
        )
    message_type: Optional[str] = Field(
        default=None,
        description="Type of message i.e. UserMessage or AIMessage"
    )
    
    # --- Agent Results ---
    responses: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary to store responses from different agents"
    )
    orchestrator_results: Optional[str] = Field(
        default=None,
        description="Results from synthesyzer_agent"
    )
    valet_results: Optional[str] = Field(
        default=None,
        description="Results from valet agent"
    )
    personal_assistant_results: Optional[str] = Field(
        default=None,
        description="Results from personal assistant agent"
    )
    health_coach_results: Optional[str] = Field(
        default=None,
        description="Results from health coach agent"
    )
    librarian_results: Optional[str] = Field(
        default=None,
        description="Results from librarian agent"
    )
    tutor_results: Optional[str] = Field(
        default=None,
        description="Results from tutor agent"
    )
    programmer_results: Optional[str] = Field(
        default=None,
        description="Results from programmer agent"
    )
    subgraph_name: Optional[str] = Field(
        default=None,
        description="Name of the subgraph being executed"
)

    # --- User Preferences ---
    general_user_pref: List[str] = Field(
        default_factory=list,
        description="General user preferences"
    )
    user_graph_prefs: List[str] = Field(
        default_factory=list,
        description="User preferences specific to the graph"
    )


    # --- Metadata ---
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the state"
    )
    sender: Optional[str] = Field(
        default=None,
        description="Name of the node that sent the message"
    )
    target: Optional[str] = Field(
        default=None,
        description="Name of the node that should receive the message"
    )
    content: Optional[str] = Field(
        default=None,
        description="Content of the message"
    )
    tool_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input for tools"
    )
    response: Optional[str] = Field(
        default=None,
        description="Response from the LLM or tool"
    )
    active_agent: str = Field(
        default=valet,
        description="Who the user is currently interacting with"
    )

    # --- Logging ---
    log_entries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of log entries for debugging and tracking"
    )

    def add_log_entry(self, entry: Dict[str, Any]) -> None:
        """Add a log entry to the state."""
        self.log_entries.append(entry)

    def get_current_timestamp(self) -> str:
        """Get current timestamp in Pacific timezone"""
        tz = pytz.timezone('America/Los_Angeles')
        return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')

class GraphState(TypedDict):
    # Message to or from other nodes (tools, functions, agents, etc.)
    message: str

    # IDs for tracking
    session_id: str
    thread_id: str
    parent_thread_id: Optional[str]
    run_id: str
    parent_run_id: Optional[str]

    # metadata if needed for target node
    metadata: Dict[str, Any]

### --- ORCHESTRATOR FUNCTIONS --- ###
async def orchestrator_node(state: MainGraphState) -> MainGraphState:
    """
    Orchestrator node that routes requests to the appropriate staff member or handles conversational responses.
    """
    LOGGER.info("Orchestrator processing request...")

    # Get the latest user message
    user_message = state.messages[-1] if state.messages else HumanMessage(content="")

    # Log the user message for debugging
    LOGGER.debug(f"User message received: {user_message.content}")

    # Format the user message and append it to the conversation history
    if user_message.content:
        state.messages.append(HumanMessage(content=user_message.content))
        state.content = user_message.content  # Update the state content with the user message

    # Invoke the LLM to process the user message
    LOGGER.info("Routing to LLM for processing...")
    response = await call_model(
        model=model,  # Pass the loaded model
        messages=state.messages,  # Pass the conversation history
        config=config,  # Pass the configuration
        SYSTEM_PROMPT="You are a helpful AI assistant.",  # System prompt for the LLM
        available_tools=[]  # List of tools available to the LLM
    )

    # Process the LLM's response
    if response:
        ai_message = AIMessage(content=response)
        state.messages.append(ai_message)  # Append the LLM's response to the conversation history
        state.content = response  # Update the state content with the LLM's response
        state.responses["orchestrator"] = response  # Store the response in the orchestrator's responses

        # Determine if the response is an agent request or a conversational response
        if "agent_request" in response.lower():
            # Extract the agent name from the response (example logic)
            agent_name = extract_agent_name(response)  # Implement this function to parse the agent name
            LOGGER.info(f"Routing to agent: {agent_name}")

            # Inform the user that the request was sent to the agent
            state.messages.append(AIMessage(content=f"Your request has been sent to {agent_name}."))
            state.content = f"Your request has been sent to {agent_name}."

            # Route to the subgraph for the agent
            subgraph_result = await handle_subtask(state, agent_name)
            state.messages.extend(subgraph_result.get("messages", []))
            state.responses.update(subgraph_result.get("responses", {}))
            state.metadata.update(subgraph_result.get("metadata", {}))
        else:
            # Conversational response: Route back to the UI
            LOGGER.info("Returning conversational response to the user.")
            state.target = "ui_node"  # Route back to the UI for the next user input

    return state

def extract_agent_name(response: str) -> str:
    """
    Extract the agent name from the LLM response.
    Example: "Please send this request to the librarian."
    """
    # Example logic to extract agent name
    for agent in ["valet", "personal_assistant", "health_coach", "librarian", "tutor", "programmer"]:
        if agent in response.lower():
            return agent
    return "valet"  # Default to valet if no agent is found

def convert_to_graph_state(main_state: MainGraphState) -> GraphState:
    """Convert MainGraphState to GraphState."""
    return GraphState(
        # Extract the latest message content
        message=main_state.messages[-1].content if main_state.messages else "",
        
        # IDs for tracking
        session_id=main_state.session_id or "",
        thread_id=main_state.thread_id,
        parent_thread_id=main_state.metadata.get("parent_thread_id", None),  # Use metadata if applicable
        run_id=main_state.run_id,
        parent_run_id=main_state.metadata.get("parent_run_id", None),  # Use metadata if applicable
        
        # Metadata
        metadata=main_state.metadata
    )

def update_main_graph_state_from_graph_state(main_state: MainGraphState, graph_state: GraphState) -> MainGraphState:
    """Update MainGraphState using data from GraphState."""
    # Update IDs
    main_state.session_id = graph_state["session_id"]
    main_state.thread_id = graph_state["thread_id"]
    main_state.metadata["parent_thread_id"] = graph_state.get("parent_thread_id", None)
    main_state.run_id = graph_state["run_id"]
    main_state.metadata["parent_run_id"] = graph_state.get("parent_run_id", None)
    
    # Update metadata
    main_state.metadata.update(graph_state["metadata"])
    
    # Update messages (append the message from GraphState)
    if "message" in graph_state and graph_state["message"]:
        main_state.messages.append(HumanMessage(content=graph_state["message"]))
    
    return main_state

async def handle_subtask(state: MainGraphState, agent_name: str) -> Dict[str, Any]:
    """Handles subtask creation and execution."""
    subgraph_name = f"sub_graph_{agent_name.lower()}"
    sub_run_id = str(uuid4())
    sub_parent_run_id = state.run_id

    subgraph_initial_state = {
        "subgraph_name": subgraph_name,
        "user_input": state.user_input,
        "message": [],
        "session_id": state.session_id,
        "thread_id": state.thread_id,
        "run_id": sub_run_id,
        "parent_run_id": sub_parent_run_id,
        "general_user_pref": state.general_user_pref,
        "user_graph_prefs": state.user_graph_prefs,
    }

    # Invoke subgraph (replace with actual subgraph invocation)
    #subgraph_result = await agent_subgraph.ainvoke(subgraph_initial_state)  # Placeholder
    # Simulate subgraph execution and return a dummy response
    subgraph_result = {
        "messages": [
            AIMessage(content=f"Subgraph successfully returned {subgraph_name}")
        ],
        "responses": {
            "subgraph_result": f"Subgraph {subgraph_name} executed successfully."
        },
        "metadata": {
            "subgraph_name": subgraph_name,
            "run_id": sub_run_id,
            "parent_run_id": sub_parent_run_id,
            "status": "success"
        }
    }    
    return subgraph_result

### --- SERVICE FUNCTIONS --- ###

async def llm_node(state: MainGraphState) -> MainGraphState:
    """LLM node that processes messages and may call tools"""
    try:
        # ... other code ...
        
        # Format the messages
        messages = state.messages

        # Call the model
        response = await call_model(
            model=model, # Pass the loaded model
            messages=messages, # Pass the formatted messages
            config=config, # Pass the config
            system_prompt="You are a helpful AI assistant.", # Pass the system prompt
            available_tools=[] # Pass the available tools
        )

        # ... process the response ...

    except Exception as e:
        print(f"LLM Error: {str(e)}")
        return {**state, "error": str(e)}
    
### --- STAFF FUNCTIONS --- ###

async def valet_task(state: MainGraphState) -> MainGraphState:
    """Handles delegation and high-level coordination."""
    LOGGER.info("Valet processing request...")
    print("Valet handling request...")

    # Get user message
    user_message = state.messages[-1] if state.messages else HumanMessage(content="")

    # Handle monitoring requests
    if "monitor" in user_message.content.lower():
        monitoring_info = await get_monitoring_info(state)
        response_message = f"Here's a summary of current tasks:\n{monitoring_info}"
        state.messages.append(AIMessage(content=response_message))
        state.content = response_message
        state.responses["valet"] = response_message
    # Handle other requests (delegate or default)
    else:
        state.messages.append(AIMessage(content="I'll need to check with the staff on that."))
        state.content = "I'll need to check with the staff on that."
        state.responses["valet"] = "I'll need to check with the staff on that."
        state.target = "orchestrator_node"

    return state 

async def get_monitoring_info(state: MainGraphState) -> str:
    """Dummy implementation for monitoring information."""
    # Simulate monitoring data
    monitoring_data = [
        {"task": "Research", "status": "In Progress", "agent": "Librarian"},
        {"task": "Health Check", "status": "Completed", "agent": "Health Coach"},
        {"task": "Code Review", "status": "Pending", "agent": "Programmer"},
    ]

    # Format the monitoring data into a readable string
    monitoring_info = "\n".join(
        [f"- Task: {item['task']}, Status: {item['status']}, Agent: {item['agent']}" for item in monitoring_data]
    )

    return monitoring_info

def personal_assistant_task(state: MainGraphState) -> MainGraphState:
    """Manages calendar, email, and social media."""
    print("Personal Assistant handling request...")
    state.responses["personal_assistant"] = "Task managed."
    return state

def health_coach_task(state: MainGraphState) -> MainGraphState:
    """Tracks fitness, diet, and health plans."""
    print("Health Coach handling request...")
    state.responses["health_coach"] = "Health data updated."
    return state

def librarian_task(state: MainGraphState) -> MainGraphState:
    """Finds and summarizes research materials."""
    print("Librarian handling request...")
    state.responses["librarian"] = "Research complete."
    return state

def tutor_task(state: MainGraphState) -> MainGraphState:
    """Teaches and provides learning resources."""
    print("Tutor handling request...")
    state.responses["tutor"] = "Lesson prepared."
    return state

def programmer_task(state: MainGraphState) -> MainGraphState:
    """Assists with coding and debugging."""
    print("Programmer handling request...")
    state.responses["programmer"] = "Code reviewed."
    return state

def route_next(state: MainGraphState) -> str:
    """Determine the next node in the workflow based on the current state."""
    # Route based on the target set in the state
    if state.target:
        return state.target

    # Default routing logic (fallback)
    return "ui_node"  # Default to the UI node if no target is set

# Initialize graph with our state type including messages
workflow = StateGraph(MainGraphState)
    
# Add core nodes
workflow.add_node("ui", cli_for_test_and_dev)
workflow.add_node("orchestrator_node", orchestrator_node)
workflow.add_node("valet", valet_task)
workflow.add_node("personal_assistant", personal_assistant_task)
workflow.add_node("health_coach", health_coach_task)
workflow.add_node("librarian", librarian_task)
workflow.add_node("tutor", tutor_task)
workflow.add_node("programmer", programmer_task)
    

# Add entry point - start with UI
workflow.add_edge(START, "ui_node")

# TODO: Add these nodes once implemented
# workflow.add_node("database", database_node)
# Add tool nodes
# workflow.add_node("calendar", calendar_node)
# workflow.add_node("email", email_node)
# workflow.add_node("tasks", task_node)
    
# Add edges - all nodes route through orchestrator
workflow.add_edge("ui_node", "orchestrator_node")
workflow.add_edge("orchestrator_node", "llm_node")
workflow.add_edge("llm_node", "orchestrator_node")
workflow.add_edge("orchestrator_node", "valet")
workflow.add_edge("orchestrator_node", "personal_assistant")
workflow.add_edge("orchestrator_node", "health_coach")
workflow.add_edge("orchestrator_node", "librarian")
workflow.add_edge("orchestrator_node", "tutor")
workflow.add_edge("orchestrator_node", "programmer")

workflow.add_conditional_edges(
    "orchestrator_node",
    route_next,
    {
        "ui_node": "ui_node",
        "llm_node": "llm_node",
        END: END  # Allow graph to end when requested
    }
)
    
# Compile the graph
graph_executor = workflow.compile()

### --- RUN GRAPH --- ###
if __name__ == "__main__":
    print("Welcome to the AI Staff Swarm!")

    # Initialize the state
    state = MainGraphState(
        session_id=str(uuid4()),
        thread_id=str(uuid4()),
        run_id=str(uuid4()),
        timestamp=datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z'),
        user_input=None,
        messages=[],
        metadata={"new_run": True, "active_agent": "valet"},
        active_agent="valet",
        active_agent_prompt="Agent Error >>>"
    )

     # Log the initialized state
    LOGGER.info(f"Initialized state: {state.model_dump()}")

    # Log a message indicating the program is ready for user input
    LOGGER.info("AI Staff Swarm is ready for user input.")

    # Main program loop
    while True:
        try:
            # Get user input
            user_input = input("\nUser: ").strip()

            # Handle quit commands
            if user_input.lower() in ["/quit", "/exit", "/bye"]:
                print("\nExiting the AI Staff Swarm. Goodbye!")
                break

            # Update state with user input
            state.user_input = user_input
            state.messages.append(HumanMessage(content=user_input))
            state.target = "orchestrator_node"

            # Invoke the graph executor
            output = graph_executor.invoke(state)

            # Display the AI's response
            print(f"\nAI: {output.responses.get('orchestrator', 'No response')}")

        except Exception as e:
            print(f"Error: {str(e)}")

    print("Welcome to the AI Staff Swarm!")