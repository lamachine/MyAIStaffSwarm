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
from langgraph.types import interrupt

llm = ChatOllama(model="llama3.1", temperature=0.0)


class TutorialState(TypedDict):
    # Messages have the type list. The add_messages function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

# Define node functions
def chatbot(state: TutorialState) -> TutorialState:
    print("Processing in chatbot")
    return {"messages": [llm.invoke(state["messages"])]}

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
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)



def create_tutorial_graph():
    """Create the workflow graph"""
    workflow = StateGraph(TutorialState)
    
    # add nodes (removed START/END)
    workflow.add_node("chatbot", chatbot)
    # workflow.add_node("node_1", node_1)
    # workflow.add_node("node_2", node_2)
    # workflow.add_node("node_3", node_3)

    # Set entry point and edges
    workflow.set_entry_point("chatbot")
    #workflow.add_conditional_edges(
        #"node_1",
        #decide_mood,
        #{
            #"node_2": "node_2",
            #"node_3": "node_3"
        #}
    #)
    
    return workflow.compile()


if __name__ == "__main__":
    graph = create_tutorial_graph()
    # Uncomment to display graph (requires proper environment)
    #display(Image(graph.get_graph().draw_mermaid_png()))
    
    # Save graph to file
    #graph_image = graph.get_graph().draw_mermaid_png()
    #with open("tutorial_graph.png", "wb") as f:
    #    f.write(graph_image)
    #print("Graph saved as tutorial_graph.png")
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
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
        