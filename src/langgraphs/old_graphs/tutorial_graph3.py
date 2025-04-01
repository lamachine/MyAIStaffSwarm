import os

from IPython.display import Image, display
from typing import TypedDict, Annotated, List, Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langchain_ollama import ChatOllama

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt

llm = ChatOllama(model="llama3.1", temperature=0.0)


class TutorialState(TypedDict):
    # Messages have the type list. The add_messages function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

# Define node functions
def chatbot(state: TutorialState) -> TutorialState:
    """Process messages with tool-enabled LLM"""
    print("Processing in chatbot")
    return {"messages": [llm.bind_tools([multiply]).invoke(state["messages"])]}

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    print(f"Multiplying {a} and {b}")
    return a * b

llm_with_tools = llm.bind_tools([multiply])
'''
def node_1(state: TutorialState) -> TutorialState:
    print("Processing in node 1")
    return state

def node_2(state: TutorialState) -> TutorialState:
    print("Processing in node 2")
    return state

def node_3(state: TutorialState) -> TutorialState:
    print("Processing in node 3")
    return state

def decide_mood(state: TutorialState) -> str:
    """Decide which node to route to next"""
    return "node_2"  # or "node_3"
'''
def stream_graph_updates(user_input: str):
    """Stream updates from the graph execution"""
    messages = [HumanMessage(content=user_input)]
    for event in graph.stream({"messages": messages}):
        for value in event.values():
            if "messages" in value and value["messages"]:
                last_message = value["messages"][-1]
                if isinstance(last_message, AIMessage):
                    print("Assistant:", last_message.content)



def create_tutorial_graph():
    """Create the workflow graph"""
    workflow = StateGraph(TutorialState)
    
    # Add nodes
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("tools", ToolNode([multiply]))

    # Set entry point
    workflow.set_entry_point("chatbot")
    
    # Add edges with proper routing
    workflow.add_conditional_edges(
        "chatbot",
        tools_condition,
        {
            True: "tools",    # If tools_condition returns True, go to tools
            False: "chatbot"  # If tools_condition returns False, go back to chatbot
        }
    )
    
    # Add edge from tools back to chatbot
    workflow.add_edge("tools", "chatbot")
    
    return workflow.compile()


if __name__ == "__main__":
    graph = create_tutorial_graph()
    
    # Get Mermaid representation
    mermaid_text = graph.get_graph().draw_mermaid()
    print("\nGraph Structure (Mermaid):")
    print(mermaid_text)
    
    # Try to save PNG if possible
    try:
        graph_image = graph.get_graph().draw_mermaid_png()
        with open("tutorial_graph.png", "wb") as f:
            f.write(graph_image)
        print("\nGraph saved as tutorial_graph.png")
    except Exception as e:
        print(f"\nCouldn't save PNG: {e}")
        print("You can copy the Mermaid text above into a Mermaid viewer")
    # Test the graph
    #result = llm.aiinvoke({"messages": []})

    #print("\nResult:", result)
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            stream_graph_updates(user_input)
        except Exception as e:
            print(f"Error: {str(e)}")
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
        