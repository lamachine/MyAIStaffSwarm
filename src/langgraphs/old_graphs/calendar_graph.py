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



Missing pydantic import:
"""


from typing import Annotated, Any, Dict, Literal, List, Optional, TypedDict, Union,
from datetime import datetime

import time
import uuid
import json
import logging
import os
import pytz

from supabase import create_client

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent, RunContext

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from langgraph.prebuilt import ToolNode

from langgraph.graph import StateGraph, START, END, GraphViewer
from langgraph.graph.message import add_messages, RemoveMessage


from src.tools.google_aps_api.google_calendar_tools import (
    CalendarStateTool, 
    CreateEventTool,
    CALENDAR_TOOL_INSTRUCTIONS
)


from src.tools.tools_config import TOOL_SPECS




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
SYSTEM_PROMPT = """You are an AI Agent swarm acting as household staff for Mr. O'Donnell and his family.  You are capable of answering user queries and using external tools when necessary.  

Keep responses helpful but concise. 
Always maintain a professional tone.
If you don't know an answer, say you don't know rather than hallucinate.
If a query to a tool returns nothing, say so rather than making up an answer.

You have access to the following tools:

google_mail_tools: Retrieves emails lists, retrieves specific emails, sends specific emails.
google_calendar_tool: Checks scheduled events, appointments, and availability.
google_task_tools: Retrieves, adds, updates, or removes tasks from a to-do list.

When handling tool-related requests:
1. ALWAYS request tool specifications first by responding with exactly:
   {"request": "tool_info", "tool": "calendar"}
2. After receiving specifications, you will format tool requests according to those specifications.  The task is the last user input.
3. Do not ask permission or explain that you need tool specifications. Just request the tool spec immediately for any calendar-related query.


Recognize when a tool is needed: If a user request involves checking email, scheduling, or managing tasks, call the appropriate tool.
Format the tool request correctly: Clearly state which tool to use and what information is needed.
Respond directly if no tool is required: Answer normally if the question doesn't need external data.
Ask for clarification if needed: If the request is vague, ask the user for more details before calling a tool.

Examples:
User: "What's the weather like in New York?"
AI: Uses Weather tool to get the forecast for New York.
User: "Do I have any meetings tomorrow?"
AI: Uses Calendar tool to check for scheduled events on the requested date.
User: "Add 'buy groceries' to my to-do list."
AI: Uses Tasks tool to add the item to the list.
User: "How does photosynthesis work?"
AI: Answers directly without using a tool.
Always prioritize accuracy and clarity when deciding whether to use a tool.
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

        # Keep existing session_id
        session_id = state.get("session_id")
        
        # Return state with original session_id
        return {
            **state,  # Keep all original state
            "sender": "llm",
            "target": "orchestrator",
            "content": response.content,
            "metadata": {
                "token_usage": token_usage,
                "timestamp": datetime.now().isoformat()
            },
            "response": response.content,  # Add response here
            "messages": messages
        }

    except Exception as e:
        print(f"LLM Error: {str(e)}")
        return {**state, "error": str(e)}

# Update orchestrator to handle tool info requests
async def handle_tool_request(state: LanggraphState) -> LanggraphState:
    """Orchestrator node that handles tool info requests and routing"""
    try:
        content = state.get("content", "")
        print("\nOrchestrator received content:", content)
        
        # Route everything to LLM unless it came from LLM
        if state.get("sender") != "llm":
            return {
                **state,
                "sender": "orchestrator",
                "target": "llm",
                "metadata": {
                    "source": "orchestrator",
                    "message_type": "initial_request"
                }
            }
            
        # Handle LLM responses
        # Tool info request
        if "request" in content and "tool_info" in content:
            try:
                request = json.loads(content)
                tool_name = request.get("tool")
                if tool_name == "calendar":
                    tool_info = CalendarStateTool.get_tool_info()
                    return {
                        **state,
                        "sender": "orchestrator",
                        "target": "llm",
                        "content": json.dumps(tool_info, indent=2),
                        "metadata": {
                            "source": "orchestrator", 
                            "message_type": "tool_specs",
                            "tool": tool_name
                        }
                    }
            except json.JSONDecodeError:
                pass
                
        # Tool action request
        if "action" in content:
            return {
                **state,
                "sender": "orchestrator",
                "target": "calendar",
                "metadata": {
                    "source": "orchestrator",
                    "message_type": "tool_request"
                }
            }
            
        # Normal response
        return {
            **state,
            "sender": "orchestrator",
            "target": "ui",
            "metadata": {
                "source": "orchestrator",
                "message_type": "user_response"
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
    def should_use_tool(state):
        content = state.get("content", "")
        
        # Skip tool processing for quit commands
        if content.lower() in ["/quit", "/exit"]:
            return END
        
        # Tool info requests go to orchestrator
        if "request" in content and "tool_info" in content:
            return "orchestrator"
        
        # Tool execution requests go to specific tool
        if "action" in content:
            return state.get("metadata", {}).get("tool")
        
        # Normal responses go to UI
        return "ui"
    
    # Add edges with conditional routing
    workflow.add_edge("orchestrator", "llm")
    workflow.add_conditional_edges(
        "llm",
        should_use_tool,
        {
            "orchestrator": "orchestrator",
            "calendar": "calendar",
            "ui": "ui",
            END: END
        }
    )
    workflow.add_edge("calendar", "orchestrator")
    
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
            "sender": "ui",
            "target": "orchestrator",
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
                "content": "/quit",
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