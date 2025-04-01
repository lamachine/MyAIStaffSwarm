"""
Development graph:
1. Self contained graph with hard coded data to read calendar "today".
2. Self contained graph with hard coded data to write new calendar entry.
3. Graph with hard coded data to write new entry sent to google calendar tool.
4. Graph updated to add printing state to cli.
5. Graph updated to add LLM using ollama.
6. Graph updated to add UI chat node.
7. Added state variables needed for logging and chat memory.
8. Tested chat and debugged reporting feature to show sender nodes only.
9. Added orchestrator node for entry point to eliminate extra logging with state of tool being ready.
10. Added token usage tracking from LLM for limiting chat history in prompt.  
    Selected limit by token and set at 3000
11. Added token usage tracking to state.
12. Added tool info request handling to orchestrator.
13. Added chat memory to state
13. Added tool info request handling to orchestrator.

Current implementation:
- Basic chat functionality with state tracking
- Orchestrator routes messages to LLM
- Calendar tool defined but not connected
- State changes tracked through graph flow
"""

from typing import TypedDict, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, RemoveMessage
from src.tools.google_aps_api.google_calendar_tools import create_event, get_current_datetime, format_date, CreateEventTool
from datetime import datetime
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import uuid
from src.tools.tools_config import TOOL_SPECS
import json
from langgraph.prebuilt import ToolNode
import time

# State definition with consistent naming
class LanggraphState(TypedDict):
    session_id: str
    timestamp: str
    sender: str  # Values: "orchestrator", "llm", "calendar", "ui"
    target: str  # Values: "orchestrator", "llm", "calendar", "ui"
    content: str
    metadata: dict  # source will match sender names
    tool_input: dict
    response: str
    messages: Annotated[list, add_messages]

# Add after imports
SYSTEM_PROMPT = """You are an AI Agent swarm acting as household staff for Mr. O'Donnell.
If you don't know an answer, say you don't know rather than hallucinate.
If a query to a tool returns nothing, say so rather than making up an answer.

Available Tools:
- Calendar: Manage appointments, meetings, and schedule

When handling calendar-related requests:
1. First request tool specifications: {"request": "tool_info", "tool": "calendar"}
2. Convert relative dates to YYYY-MM-DD format:
   - "tonight" = current date
   - "tomorrow" = current date + 1 day
   - "Sunday" = next Sunday's date
3. Format the calendar request as JSON:
   {
     "action": "create_event",
     "summary": "Event Name",
     "date": "YYYY-MM-DD",
     "start_time": "HH:MM",
     "duration": minutes_as_integer
   }

Keep responses helpful but concise. Always maintain a professional tone.
"""

# Create calendar tool node with proper tool
calendar_tools = [CreateEventTool()]
calendar_node = ToolNode(tools=calendar_tools)

# Create LLM tool node
async def use_llm_tool(state: LanggraphState) -> LanggraphState:
    """LLM node that processes messages and may call tools"""
    try:
        # Debug print incoming state
        debug_state = state.copy()
        debug_state["messages"] = [str(m) for m in state["messages"]]
        print("\nState Update - From Orchestrator to LLM:")
        print(json.dumps(debug_state, indent=2, default=str))

        # Process with LLM
        llm = ChatOllama(model="llama3.1", temperature=0.0)
        response = await llm.ainvoke(state["messages"])
        
        # Print token counts directly
        print(f"\nToken Counts:")
        print(f"Prompt tokens = {response.response_metadata.get('prompt_eval_count', 0)}")
        print(f"Response tokens = {response.response_metadata.get('eval_count', 0)}")
        
        # Create token usage from response metadata
        token_usage = {
            "prompt_tokens": response.response_metadata.get('prompt_eval_count', 0),
            "completion_tokens": response.response_metadata.get('eval_count', 0),
            "total_tokens": response.response_metadata.get('prompt_eval_count', 0) + response.response_metadata.get('eval_count', 0)
        }

        # Add AI response as proper Message object
        messages = list(state["messages"])
        messages.append(AIMessage(content=response.content))

        # Create updated state with detailed metadata
        updated_state = {
            **state,
            "sender": "llm",
            "target": "orchestrator",
            "content": response.content,
            "metadata": {
                "token_usage": token_usage,
                "timestamp": datetime.now().isoformat()
            },
            "messages": messages
        }

        # Debug print outgoing state with full metadata
        debug_out = updated_state.copy()
        debug_out["messages"] = [str(m) for m in messages]
        print("\nState Update - From LLM to Orchestrator:")
        print(json.dumps(debug_out, indent=2, default=str))

        return updated_state

    except Exception as e:
        print(f"LLM Error: {str(e)}")
        return {**state, "error": str(e)}

# Update orchestrator to handle tool info requests
async def handle_tool_request(state: LanggraphState) -> LanggraphState:
    """Orchestrator node that handles initial routing"""
    try:
        return {
            **state,
            "sender": "orchestrator",  # Be consistent with sender name
            "target": "llm",
            "metadata": {
                "source": "orchestrator",  # Be consistent in metadata
                "message_type": "tool_request"
            }
        }
    except Exception as e:
        print(f"Orchestrator Error: {str(e)}")
        return {**state, "error": str(e)}

# Update graph
def create_calendar_graph():
    """Create the workflow graph with orchestrator as central node"""
    workflow = StateGraph(LanggraphState)
    
    # Add nodes
    workflow.add_node("orchestrator", handle_tool_request)
    workflow.add_node("llm", use_llm_tool)
    workflow.add_node("calendar", calendar_node)
    workflow.add_node("ui", update_ui)
    
    # Define conditional routing
    def should_continue(state):
        # Check for quit command
        if state.get("content") in ["/quit", "/exit"]:
            return None  # End the graph
        return "llm"
    
    def should_use_tool(state):
        if state["sender"] == "llm" and state.get("metadata", {}).get("tool_call"):
            return "calendar"
        return "ui"
    
    # Add edges with conditional routing
    workflow.add_edge("orchestrator", "llm")
    
    workflow.add_conditional_edges(
        "llm",
        should_use_tool,
        {
            "calendar": "calendar",
            "ui": "ui"
        }
    )
    
    workflow.add_edge("calendar", "ui")
    
    # Add conditional edge from UI that can end the graph
    workflow.add_conditional_edges(
        "ui",
        should_continue,
        {
            "llm": "llm",
            None: END  # This properly ends the graph
        }
    )
    
    workflow.set_entry_point("orchestrator")
    return workflow.compile()

async def run_chat():
    """Run the chat loop."""
    print("\nChat Ready! (type '/quit' or '/exit' to end)")
    graph = create_calendar_graph()
    session_id = str(uuid.uuid4())
    
    # Initialize message history
    message_history = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["/quit", "/exit"]:
            print("Exiting chat...")
            break
            
        # Create proper Message objects
        current_message = HumanMessage(content=user_input)
        message_history.append(current_message)
        
        # Debug print
        print("\nMessage History Types:")
        for msg in message_history:
            print(f"Message type: {type(msg)}, content: {msg.content[:30]}...")
            
        # User -> Graph state
        state = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "sender": "user",
            "target": "graph",
            "content": user_input,
            "metadata": {
                "source": "cli",
                "message_type": "user_input"
            },
            "tool_input": {},
            "response": "",
            "messages": message_history
        }
        
        # Print only user state changes
        if state["sender"] == "user":
            print("\nState Update - User:")
            print("-------------------")
            print(json.dumps(state, indent=2, default=str))
            print("-------------------\n")
        
        # Graph -> LLM handled in use_llm_tool
        result = await graph.ainvoke(state)
        
        # Check if graph signaled quit
        if result.get("content") in ["/quit", "/exit"]:
            print("Exiting chat...")
            break
        
        # Graph -> UI state
        ui_state = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "sender": "graph",
            "target": "ui",
            "content": result["response"],
            "metadata": {
                "source": "graph",
                "message_type": "ui_update",
                "display_type": "chat_message"
            },
            "tool_input": result["tool_input"],
            "response": result["response"],
            "messages": result["messages"]
        }
        
        # Print only graph to UI state changes
        if ui_state["sender"] == "graph" and ui_state["target"] == "ui":
            print("\nState Update - Graph:")
            print("--------------------")
            print(json.dumps(ui_state, indent=2, default=str))
            print("--------------------\n")
        
        print(f"\nAssistant: {result['response']}")
        
        # Update history with AI response
        message_history.append(AIMessage(content=result["response"]))

async def update_ui(state: LanggraphState) -> LanggraphState:
    """UI node that handles user interaction"""
    try:
        # Update UI with response
        print(f"\nAI: {state['content']}")
        
        # Get user input
        user_input = input("\nUser: ").strip()
        
        # Handle quit commands
        if user_input.lower() in ["/quit", "/exit"]:
            print("\nExiting chat...")
            return {
                **state,
                "sender": "ui",
                "target": None,
                "content": "/quit",  # Use consistent command
                "metadata": {
                    "source": "ui",
                    "message_type": "quit_command"
                }
            }
            
        # Add user message
        messages = list(state["messages"])
        messages.append(HumanMessage(content=user_input))
        
        return {
            **state,
            "sender": "ui",
            "target": "orchestrator",
            "content": user_input,
            "metadata": {
                "source": "ui",
                "message_type": "user_input"
            },
            "messages": messages
        }

    except Exception as e:
        print(f"UI Error: {str(e)}")
        return {**state, "error": str(e)}

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_chat())

"""
Example Calendar Operations:

1. View Events for a Day:
   Function: list_events
   Parameters:
     time_min: 2025-02-21
     max_results: 10
   API call:
     GET /calendar/v3/calendars/primary/events
     timeMin: 2025-02-21T00:00:00-07:00
     timeMax: 2025-02-21T23:59:59-07:00

2. Create Event (current implementation):
   Function: create_event
   Parameters:
     summary: Eat dinner
     date: 2025-02-21 18:00
     duration: 60
   API call:
     POST /calendar/v3/calendars/primary/events
     start: 2025-02-21T18:00:00-07:00
     end: 2025-02-21T19:00:00-07:00

3. Delete Event:
   Function: delete_event
   Parameters:
     event_id: [event_id]
   API call:
     DELETE /calendar/v3/calendars/primary/events/[event_id]

4. Test: Create Dinner Event Using Tool (working implementation):
   # Get today's date
   today = datetime.now().strftime("%Y-%m-%d")
   
   Request Details:
   -------------------------
   Function: create_event
   Parameters:
     summary: Eat dinner
     date: {today} 18:00
     duration: 60
   Expected API call:
     POST /calendar/v3/calendars/primary/events
     start: {today}T18:00:00-07:00
     end: {today}T19:00:00-07:00
   -------------------------

   Code:
   response = create_event(
       summary="Eat dinner",
       date=f"{today} 18:00",
       duration=60
   )
""" 