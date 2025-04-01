from langchain_ollama import OllamaLLM
from pydantic_ai import Agent, RunContext
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages    
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, FunctionMessage, BaseMessage, AnyMessage
from typing import TypedDict, Annotated, List, Any
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from supabase import Client, create_client
import os
from dotenv import load_dotenv

# Import the message classes from Pydantic AI
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter
)
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
    scope: str

# Initialize components
chatllm = OllamaLLM(model="llama3.1")
reasonerllm = OllamaLLM(model="deepseek-r1")
programmerllm = OllamaLLM(model="mistral")
embeddingllm = OllamaLLM(model="nomic-embed-text")

# Define agents
reasoner_agent = Agent(
    system_prompt='You are an expert at scoping the coding of AI agents with Pydantic AI to run in LangGraph.'
)


router_agent = Agent( 
    system_prompt='Your job is to route the user message either to the end of the conversation or to continue coding the AI agent.',  
)

end_conversation_agent = Agent(  
    chatllm,
    system_prompt='Your job is to end a conversation for creating an AI agent by giving instructions for how to execute the agent and they saying a nice goodbye to the user.',  
)

programmer_agent = Agent(  
    programmerllm,
    system_prompt='Your job is basic coding with python using Pydantic AI and LangGraph.',  
)

embedding_agent = Agent(  
    embeddingllm,
    system_prompt='Your job is vectorizing text for embedding in a vector database.',  
)

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def programmer_agent(state: AgentState, writer):
    # Prepare dependencies
    deps = PydanticAIDeps(
        supabase=supabase,
        reasoner_output=state['scope']
    )
    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))

    if is_ollama:
        writer = get_stream_writer()
        result = await pydantic_ai_coder.run(state['latest_user_message'], deps=deps, message_history= message_history)
        writer(result.data)

    return {"messages": [result.new_messages_json()]}

# Interrupt the graph to get the user's next message
def get_next_user_message(state: AgentState):
    value = interrupt({})

    # Set the user's latest message for the LLM to continue the conversation
    return {
        "latest_user_message": value
    }

# Determine if the user is finished creating their AI agent or not
async def route_user_message(state: AgentState):
    prompt = f"""
    The user has sent a message: 
    
    {state['latest_user_message']}

    If the user wants to end the conversation, respond with just the text "finish_conversation".
    If the user wants to continue coding the AI agent, respond with just the text "coder_agent".
    """

    result = await router_agent.run(prompt)
    next_action = result.data

    if next_action == "finish_conversation":
        return "finish_conversation"
    else:
        return "coder_agent"

# End of conversation agent to give instructions for executing the agent
async def finish_conversation(state: AgentState, writer):    
    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))

    # Run the agent in a stream
    if is_ollama:
        writer = get_stream_writer()
        result = await end_conversation_agent.run(state['latest_user_message'], message_history= message_history)
        writer(result.data)   
    else: 
        async with end_conversation_agent.run_stream(
            state['latest_user_message'],
            message_history= message_history
        ) as result:
            # Stream partial text as it arrives
            async for chunk in result.stream_text(delta=True):
                writer(chunk)

    return {"messages": [result.new_messages_json()]}        

# Build workflow
builder = StateGraph(LanggraphState)

# Add nodes
builder.add_node("define_scope_with_reasoner", define_scope_with_reasoner)
builder.add_node("coder_agent", coder_agent)
builder.add_node("get_next_user_message", get_next_user_message)
builder.add_node("finish_conversation", finish_conversation)

# Set edges
builder.add_edge(START, "define_scope_with_reasoner")
builder.add_edge("define_scope_with_reasoner", "coder_agent")
builder.add_edge("coder_agent", "get_next_user_message")
builder.add_conditional_edges(
    "get_next_user_message",
    route_user_message,
    {"coder_agent": "coder_agent", "finish_conversation": "finish_conversation"}
)
builder.add_edge("finish_conversation", END)

# Configure persistence
memory = MemorySaver()
agentic_flow = builder.compile(checkpointer=memory)

# Add this after your graph is compiled (at the bottom of the file)
viewer = GraphViewer()
viewer.add(agentic_flow)
viewer.show()  # This will open the graph visualization in your browser

# Add this before compiling the graph
builder.set_graph_viewer(viewer)
