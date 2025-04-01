import json
from typing import TypedDict, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages, RemoveMessage

import src.tools.google_aps_api.google_calendar_tools as google_calendar_tools
#import src.tools.google_aps_api.google_tasks_tools as google_tasks_tools
#import src.tools.google_aps_api.google_mail_tools as google_mail_tools


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

# Define state - Why is this needed?
class ChatState(TypedDict):
    messages: list

async def get_user_input(state: ChatState) -> ChatState:
    """Get input from user."""
    user_input = input("\nYou: ")
    state["messages"] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input)
    ]
    return state

def get_tool_info(tool: str) -> str:
    print(f"\nTool Requested: {tool}")
    if tool == "calendar":
        print(f"\nGetting Calendar Tool Info")
        return google_calendar_tools.get_tool_info()
    elif tool == "tasks":
        print(f"\nGetting Tasks Tool Info")
        #return google_tasks_tools.get_tool_info()
    elif tool == "email":
        print(f"\nGetting Email Tool Info")
        #return google_mail_tools.get_tool_info()
    else:
        return "Tool not found"
    
def RouteMessage(state: ChatState) -> ChatState: 
    response = state["messages"][-1]
    content = response.content
    try:
        json_response = json.loads(content)
        if "request" in json_response and json_response["request"] == "tool_info":
                tool = json_response.get("tool")
                print(f"\nTool Requested: {tool}")
                #print(json.dumps(json_response, indent=2))
                tool_info = get_tool_info(tool)
                print(f"\nTool Info from process_message: ")
                #print(json.dumps(tool_info, indent=2))
        else:
                print(f"\nOther JSON Received: {content}")
                #print(json.dumps(json_response, indent=2))



    except json.JSONDecodeError:
        print(f"\nAssistant: {response.content}")
        state["messages"].append(AIMessage(content=response.content))


async def UseLLM_Tool(state: ChatState) -> ChatState:
    """Process message with LLM."""
    try:
        llm = ChatOllama(model="llama3.1", temperature=0.0)
        response = await llm.ainvoke(state["messages"])
        content = response.content

        # Add AI response as proper Message object
        messages = list(state["messages"])
        messages.append(AIMessage(content))

        # Keep existing session_id
        session_id = state.get("session_id")
        
        # Print token counts directly
        print(f"\nToken Counts:")
        print(f"Prompt tokens = {response.response_metadata.get('prompt_eval_count', 0)}")
        print(f"Response tokens = {response.response_metadata.get('eval_count', 0)}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        return state

def create_chat_graph():
    """Create the conversational graph."""
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("user_input", get_user_input)
    workflow.add_node("llm_process", UseLLM_Tool)
    workflow.add_node("orchestrator", RouteMessage)
    workflow.add_node("calendar", calendar_node)
    workflow.add_node("ui", update_ui)

    # Set entry point
    workflow.set_entry_point("user_input")
    workflow.add_edge("user_input", "process")
    workflow.add_edge("process", "user_input")
    return workflow.compile()

async def run_chat():
    """Run the chat loop."""
    print("\nChat Ready! (type 'quit' to exit)")
    graph = create_chat_graph()
    state = {"messages": []}
    
    while True:
        state = await graph.ainvoke(state)
        if state["messages"][0].content.lower() == "quit":
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_chat()) 