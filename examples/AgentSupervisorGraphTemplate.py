
"""
This is a template for a LangGraph based supervisor graph.

It is an mvp with the following features:

1. UI node for user input, currently working through CLI

2. Orchestrator node for routing messages.  This is the bulk
of the logic for routing messages to the correct tool nodes.
All messages at top level move through orchestrator and all
are formatted in json, basically as tool requests. Basically
everything that comes into the orchestrator is routed to the 
LLM, and LLM is the only node that can direct a message to the
UI node.  Routing is handled by helper function route_next.

3. Database node for database operations.  It has a lot of
logic in it to demonstrate functionality, but most is expected
to be move to a specific database tool file.  It has a helper
function log_message_to_db

4. LLM node for LLM operations.  Because the message paradigm
is moving everything as tool requests, the LLM node has system
prompting to format the messages correctly.

5. Dummy nodes for research and assistant.  These are 
placeholders for the real agents to be added, but demonstrate 
agent functionality.  It is expected that these will be moved
to their own files, and act as supervisors for their agents
and tools because there will be ongoing or longer term activities
they will manage and then report up to the orchestrator.  

.env file for environment variables

Extensive logging and debugging

Local Supabase connectivity

System prompt complete with tools to demonstrate functionality.  
Expected to be modularized by tool and agent type dynamically.
    Future build user profile prompts, build personality prompts,
    build tool information prompts to allow more tools to a
    single agent by catagory.

In graph build, all nodes from the orchestrator are standard 
but only correct one is selected by logic.

__main__ functionality included for testing, but is commented out.
"""



import json
import logging
import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
from typing import (
    Literal, 
    TypedDict, 
    Annotated, 
    List, 
    Dict, 
    Union,
    Any
)

from supabase import create_client

from langchain_core.messages import (
    HumanMessage, 
    SystemMessage, 
    AIMessage, 
    ToolMessage, 
    FunctionMessage, 
    BaseMessage, 
    AnyMessage 
)
from langchain_ollama import ChatOllama

from langgraph.graph import (
    StateGraph, 
    START, 
    END
)
from langgraph.graph.message import add_messages  
from langgraph.types import Command

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter
)

####################################
# Debugging and Logging
class CustomFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        # Full format for DEBUG and ERROR
        self.detailed_fmt = '%(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        # Simpler format for INFO and WARNING
        self.simple_fmt = '%(name)s - %(levelname)s - %(message)s'

    def format(self, record):
        # Choose format based on level
        if record.levelno in [logging.DEBUG, logging.ERROR]:
            self.fmt = self.detailed_fmt
        else:
            self.fmt = self.simple_fmt
        
        return super().format(record)

# At the top of hierarchical_supervisor.py, after imports
LOGGER = logging.getLogger(__name__)

# Create and configure handler
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())

# Configure logging levels
LOG_LEVEL = logging.DEBUG  # Changed from INFO to DEBUG
LOGGER.setLevel(LOG_LEVEL)
LOGGER.addHandler(handler)

# Configure logging levels for different components
logging.getLogger('langgraph').setLevel(LOG_LEVEL)
logging.getLogger('httpcore').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.DEBUG)  # Add urllib3 logging
logging.getLogger('postgrest').setLevel(logging.DEBUG)  # Add postgrest client logging
logging.getLogger('supabase').setLevel(logging.DEBUG)  # Add supabase client logging

# Ensure all handlers use our custom formatter
for logger_name in ['langgraph', 'httpcore', 'httpx', 'urllib3', 'postgrest', 'supabase']:
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logger.addHandler(handler)
    for existing_handler in logger.handlers:
        existing_handler.setFormatter(CustomFormatter())

# System prompt as a constant
SYSTEM_PROMPT = """You are an AI assistant that always responds in JSON format.
For normal conversation, use the format:
{
    "tool": "ui_node",
    "tool_input": "your message to the user"
}

For database queries, use:
{
    "tool": "database_node",
    "tool_input": {
        "action": "count|select|search",
        "table": "messages|dev_docs_site_pages",
        "limit": 10  // Optional, for select queries
    }
}

Available Database Operations:
1. Count records: 
   {"action": "count", "table": "messages"}
2. Select records: 
   {"action": "select", "table": "dev_docs_site_pages", "limit": 5}
3. Vector search: 
   {"action": "search", "table": "messages"} or {"action": "search", "table": "dev_docs_site_pages"}

For other special actions, use the appropriate tool name (research_graph, assistant_graph) with relevant tool_input.

IMPORTANT RULES:
1. Never respond in plain text
2. Always use the JSON format specified above
3. Never include HTML tags or styling in your responses
4. Keep responses simple and direct
5. For tool_input, only use plain text without any formatting
6. For database queries, always specify both action and table

Example good responses:
{
    "tool": "ui_node",
    "tool_input": "Hello! How can I help you today?"
}

{
    "tool": "database_node",
    "tool_input": {"action": "count", "table": "messages"}
}

Example bad responses:
{
    "tool": "ui_node",
    "tool_input": "<div style='color:blue'>Hello!</div>"
}

{
    "tool": "database_node",
    "tool_input": "SELECT * FROM messages"
}"""

# State definition with consistent naming
class LanggraphState(TypedDict, total=False):  # Make fields optional
    session_id: str
    timestamp: str
    sender: str  # Values: "orchestrator", "llm", "calendar", "ui"
    target: str  # Values: "orchestrator", "llm", "calendar", "ui"
    content: str # Only the last message content
    messages: Annotated[list, add_messages]

# Initialize components
chatllm = ChatOllama(model="llama3.1", temperature=0.1)
reasonerllm = ChatOllama(model="deepseek-r1", temperature=0.1)
programmerllm = ChatOllama(model="mistral", temperature=0.1)
embeddingllm = ChatOllama(model="nomic-embed-text", temperature=0.1)

# Load environment variables
load_dotenv()

# Validate required environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Missing required environment variables. Please ensure SUPABASE_URL and SUPABASE_KEY "
        "are set in your .env file"
    )

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

################################

def get_current_timestamp() -> str:
    """Get current UTC timestamp and convert to Pacific time"""
    utc_now = datetime.now(pytz.UTC)
    pacific_tz = pytz.timezone('America/Los_Angeles')
    pacific_time = utc_now.astimezone(pacific_tz)
    return pacific_time.isoformat()

def generate_session_id() -> str:
    """Generate a unique conversation ID using UUID4"""
    from uuid import uuid4
    return f"conv_{uuid4().hex[:16]}"  # Prefix with conv_ and use first 16 chars of hex

def log_message_to_db(state: LanggraphState) -> None:
    """Log message to the database with all relevant metadata"""
    try:
        # Extract actual message content from JSON if possible
        try:
            content_json = json.loads(state["content"])
            message_text = content_json.get("tool_input", state["content"])
            if isinstance(message_text, dict):
                message_text = json.dumps(message_text)
        except json.JSONDecodeError:
            message_text = state["content"]

        # Generate embedding
        embedding_response = embeddingllm.embed_query(message_text)
        
        message_data = {
            "conversation_id": state["session_id"],
            "user_id": "system",  # Default user ID
            "role": "system",  # Default role
            "message": message_text,
            "embedding": embedding_response,  # Add embedding vector
            "embedding_model": "nomic-embed-text",  # Record model used
            "metadata": {
                "sender": state["sender"],
                "target": state["target"],
                "timestamp": state["timestamp"]
            }
        }

        # Determine role based on content
        try:
            if isinstance(content_json, dict):
                if content_json.get("tool") == "ui_node":
                    if state["sender"] == "ui_node":
                        message_data["role"] = "user"
                        message_data["user_id"] = "user"  # You can customize this
                    else:
                        message_data["role"] = "assistant"
                else:
                    message_data["role"] = "tool"
        except (NameError, json.JSONDecodeError):
            pass

        # Insert into database
        result = supabase.table("messages").insert(message_data).execute()
        LOGGER.debug("Message logged to database: %s", {
            **message_data,
            "embedding": f"<vector with {len(message_data['embedding'])} dimensions>"
        })
        
    except Exception as e:
        LOGGER.error("Failed to log message to database: %s", str(e))

def orchestrator(state: LanggraphState) -> LanggraphState:
    """Process messages and update state"""
    current_sender = state["sender"]
    LOGGER.info("Orchestrator received: sender=%s, target=%s, content=%s", 
                        state["sender"], state["target"], state["content"])

    try:
        # Try to parse incoming content as JSON
        message_json = json.loads(state["content"])
        
        # If from UI, add system prompt before sending to LLM
        if current_sender == "ui_node":
            LOGGER.debug("Processing UI message, preparing LLM command")
            # Add user message to history
            state["messages"].append(HumanMessage(content=message_json.get("tool_input")))
            
            # Prepare LLM command
            llm_message = {
                "tool": "llm_node",
                "tool_input": message_json.get("tool_input")
            }
            state["target"] = "llm_node"
            state["sender"] = "orchestrator"
            state["timestamp"] = get_current_timestamp()
            state["content"] = json.dumps(llm_message)
            LOGGER.debug("Orchestrator processed UI message: %s", state)

        # For all other messages, maintain JSON structure
        else:
            LOGGER.debug("Processing non-UI message from %s", current_sender)
            state["sender"] = "orchestrator"
            state["target"] = message_json.get("tool", "ui_node")
            state["timestamp"] = get_current_timestamp()
            # Keep the full JSON structure
            state["content"] = json.dumps(message_json)
            LOGGER.debug("Orchestrator processed message: %s", state)

        # Log message after processing
        log_message_to_db(state)

    except json.JSONDecodeError:
        LOGGER.error("Invalid JSON received: %s", state["content"])
        state["target"] = "ui_node"
        state["content"] = json.dumps({
            "tool": "ui_node",
            "tool_input": "Error: Received malformed message"
        })
        state["sender"] = "orchestrator"
        state["timestamp"] = get_current_timestamp()
        log_message_to_db(state)
    
    return state

def route_next(state: LanggraphState) -> str:
    """Route based on last message content"""
    LOGGER.info("Routing decision for state: messages=%s", state.get("messages", []))
    
    if not state.get("messages"):
        return "ui_node"
        
    last_message = state["messages"][-1]
    LOGGER.info("Routing based on last message type: %s", type(last_message))
    
    if isinstance(last_message, HumanMessage):
        return "llm_node"
    elif isinstance(last_message, AIMessage):
        try:
            # Try to parse as JSON to check for tool requests
            response = json.loads(last_message.content)
            return response.get("tool", "ui_node")
        except json.JSONDecodeError:
            # If not JSON, send to UI
            return "ui_node"
    elif isinstance(last_message, ToolMessage):
        return "llm_node"
    
    # Default to UI if we can't determine
    return "ui_node"

def ui_node(state: LanggraphState) -> LanggraphState:
    # Initialize state if this is first run
    if not state.get("session_id"):
        state["session_id"] = generate_session_id()
        state["timestamp"] = get_current_timestamp()
        state["messages"] = []
    
    # If we have content to display, show it first
    if state.get("target") == "ui_node" and state.get("content"):
        LOGGER.info("UI node received: sender=%s, target=%s, content=%s", 
                    state["sender"], state["target"], state["content"])
        
        message_data = json.loads(state["content"])
        tool_input = message_data.get("tool_input", {})
        print(f"\nResponse: {tool_input}")

    # Then get user input
    user_input = input("\nUser Input: ")
    
    if user_input:
        state["timestamp"] = get_current_timestamp()
        state["sender"] = "ui_node"
        state["target"] = "orchestrator"
        # Format user input as JSON tool request
        tool_request = {
            "tool": "llm_node",
            "tool_input": user_input
        }
        state["content"] = json.dumps(tool_request)  # Convert dict to JSON string
        state["messages"].append(user_input)  # Store actual user input
        LOGGER.debug("UI node: sender=%s, target=%s, content=%s", 
                    state["sender"], state["target"], state["content"])
    
    return state

def database_node(state: LanggraphState) -> LanggraphState:
    LOGGER.debug("Database node received: sender=%s, target=%s, content=%s", 
                 state.get("sender"), state.get("target"), state.get("content"))
    
    # Set response metadata
    state["sender"] = "database_node"
    state["target"] = "orchestrator"
    
    try:
        # Parse the incoming query
        content = json.loads(state.get("content", "{}"))
        query_data = json.loads(content.get("tool_input", "{}"))
        
        # Validate table name
        valid_tables = ["messages", "dev_docs_site_pages"]
        table = query_data.get("table")
        
        if not table or table not in valid_tables:
            response = {
                "tool": "ui_node",
                "tool_input": f"Invalid table. Available tables: {', '.join(valid_tables)}"
            }
            LOGGER.warning("Invalid table requested: %s", table)
            
        # Execute query based on type
        elif query_data.get("action") == "count":
            result = supabase.table(table).select("*", count='exact').execute()
            count = result.count
            response = {
                "tool": "ui_node",
                "tool_input": f"Found {count} records in table '{table}'"
            }
            
        elif query_data.get("action") == "select":
            limit = min(query_data.get("limit", 10), 50)  # Cap at 50 records
            result = supabase.table(table).select("*").limit(limit).execute()
            response = {
                "tool": "ui_node",
                "tool_input": f"Query results from {table}:\n{json.dumps(result.data, indent=2)}"
            }
            
        elif query_data.get("action") == "search":
            # Handle vector similarity search using stored procedures
            if table == "messages":
                response = {
                    "tool": "ui_node",
                    "tool_input": "Use match_messages() for similarity search in messages table"
                }
            elif table == "dev_docs_site_pages":
                response = {
                    "tool": "ui_node", 
                    "tool_input": "Use match_dev_docs_site_pages() for similarity search in docs table"
                }
                
        else:
            response = {
                "tool": "ui_node",
                "tool_input": "Available actions: count, select, search"
            }
            
    except Exception as e:
        LOGGER.error("Database error: %s", str(e))
        response = {
            "tool": "ui_node",
            "tool_input": f"Database error: {str(e)}"
        }
    
    # Add response as a ToolMessage
    state["messages"].append(
        ToolMessage(
            content=response["tool_input"],
            tool_name="database",
            tool_call_id="db_response_1"
        )
    )
    
    state["content"] = json.dumps(response)
    return state

def llm_node(state: LanggraphState) -> LanggraphState:
    try:
        state["sender"] = "llm_node"
        state["target"] = "orchestrator"
        
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        messages.extend(state.get("messages", []))
        
        # Log the exact messages being sent to LLM
        LOGGER.debug("Sending messages to LLM:")
        for msg in messages:
            LOGGER.debug("Message type: %s, content: %s", type(msg), msg.content)
        
        llm_response = chatllm.invoke(messages)
        LOGGER.info("Raw LLM response type: %s", type(llm_response.content))
        LOGGER.info("Raw LLM response content: %s", llm_response.content)
        
        # Take only the first JSON object if multiple are returned
        response_text = llm_response.content.strip().split('\n\n')[0]
        
        # Add response as proper message type and set content
        try:
            response_json = json.loads(response_text)
            LOGGER.debug("Parsed LLM response: %s", response_json)
            
            # Validate response format
            if not isinstance(response_json.get("tool_input"), str):
                LOGGER.warning("LLM returned invalid tool_input format: %s", response_json.get("tool_input"))
                # Convert to proper format
                if isinstance(response_json.get("tool_input"), dict) and "text" in response_json["tool_input"]:
                    response_json["tool_input"] = response_json["tool_input"]["text"]
                    LOGGER.debug("Converted tool_input to: %s", response_json["tool_input"])
            
            if response_json["tool"] == "ui_node":
                state["messages"].append(AIMessage(content=response_json["tool_input"]))
                state["content"] = json.dumps(response_json)  # Set content for UI display
            else:
                state["messages"].append(AIMessage(content=json.dumps(response_json)))
                state["content"] = json.dumps(response_json)
                
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error: {str(e)}"
            state["messages"].append(AIMessage(content=error_msg))
            state["content"] = json.dumps({
                "tool": "ui_node",
                "tool_input": error_msg
            })
            
        return state
    except (json.JSONDecodeError, KeyError) as e:
        error_response = {
            "tool": "ui_node",
            "tool_input": f"Error processing LLM request: {str(e)}"
        }
        state["sender"] = "llm_node"
        state["target"] = "orchestrator"
        state["content"] = json.dumps(error_response)
        state["messages"].append(AIMessage(content=error_response["tool_input"]))
        LOGGER.error("LLM node error: %s", str(e))
    
    return state

def dummy_node(state: LanggraphState) -> LanggraphState:
    LOGGER.info("Dummy node received: sender=%s, target=%s, content=%s", 
                    state["sender"], state["target"], state["content"])
    
    # Format response in expected JSON structure
    response = {
        "tool": "llm_node",
        "tool_input": "Nothing new here"
    }
    
    # Update state with consistent naming
    state["sender"] = state["target"]  # Use the target from orchestrator as sender
    state["target"] = "orchestrator"
    state["content"] = json.dumps(response)
    
    # Add as ToolMessage to messages
    state["messages"].append(
        ToolMessage(
            content=response["tool_input"],
            tool_name="dummy",
            tool_call_id="dummy_1"  # Required parameter
        )
    )
    
    LOGGER.debug("Dummy node response: %s", response)
    return state

################################
# Build the graph
builder = StateGraph(LanggraphState)

# Add nodes
builder.add_node("orchestrator", orchestrator)
builder.add_node("ui_node", ui_node)
builder.add_node("database_node", database_node)
builder.add_node("llm_node", llm_node)
builder.add_node("research_graph", dummy_node)
builder.add_node("assistant_graph", dummy_node)

# Add START edge to ui_node
builder.add_edge(START, "ui_node")

# All nodes go to orchestrator first
builder.add_edge("ui_node", "orchestrator")
builder.add_edge("database_node", "orchestrator")
builder.add_edge("llm_node", "orchestrator")
builder.add_edge("research_graph", "orchestrator")
builder.add_edge("assistant_graph", "orchestrator")

# Orchestrator routes conditionally
builder.add_conditional_edges(
    "orchestrator",
    route_next
)

graph = builder.compile()

"""
if __name__ == "__main__":
    # Initialize minimum required state
    state = {
        "messages": [],
        "sender": "",
        "target": "ui_node",  # Start at UI node
        "content": "",
        "session_id": "test_session",
        "timestamp": get_current_timestamp()
    }
    
    # Run the graph and maintain state
    next_step = graph.stream(state)
    try:
        while True:
            state = next(next_step)
    except StopIteration:
        pass
"""