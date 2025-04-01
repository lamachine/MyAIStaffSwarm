from typing import Annotated, Sequence, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama
import logging
from src.tools.google_aps_api.google_calendar_tools import GoogleCalendarTool
from src.tools.calendar_helper import CalendarHelper

from src.agents.pers_testdev_agent0.agent_0 import Agent0

# Configure logging
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are James, an AI valet with access to a calendar tool.

IMPORTANT: For ANY calendar-related questions, you must ONLY return a JSON object, nothing else.

Example user questions and your responses:

User: "What's on my calendar today?"
{
    "thought": "I need to check today's calendar events",
    "tool": "google_calendar",
    "tool_input": {
        "action": "view",
        "date": "today",
        "summary": "",
        "duration": ""
    }
}

User: "Schedule a meeting for tomorrow at 2pm"
{
    "thought": "I need to add a meeting to tomorrow's calendar",
    "tool": "google_calendar",
    "tool_input": {
        "action": "add",
        "date": "2024-02-21 14:00",
        "summary": "Meeting",
        "duration": "60 minutes"
    }
}

For non-calendar questions, respond conversationally without JSON.

CRITICAL: Calendar responses must be ONLY the JSON object, no other text or explanations."""

class AgentState(TypedDict):
    """Basic state for test graph."""
    messages: List[HumanMessage | AIMessage]
    session_id: str
    context: dict
    tool_states: dict

async def create_test_graph(llm):
    """Create test graph with Agent0 and tools."""
    logger.info("Creating test graph with Agent0")
    
    # Create tools
    calendar_tool = CalendarHelper()
    tools = [calendar_tool]
    
    # Initialize workflow
    workflow = StateGraph(AgentState)
    
    # Initialize agent with tools
    agent = Agent0(
        llm=llm,
        tools=tools
    )
    logger.info(f"Initialized Agent0: {agent.name}")
    
    # Add system message to state
    async def add_system_message(state):
        state["messages"].insert(0, SystemMessage(content=SYSTEM_PROMPT))
        return state
    
    workflow.add_node("system", add_system_message)
    workflow.add_node("agent", agent.process_message)
    
    # Set up graph
    workflow.set_entry_point("system")
    workflow.add_edge("system", "agent")
    workflow.add_edge("agent", END)
    
    logger.info("Test graph created successfully")
    return workflow.compile(), agent, SYSTEM_PROMPT