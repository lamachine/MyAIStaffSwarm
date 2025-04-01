from IPython.display import Image, display
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List, Any
from langgraph.config import get_stream_writer
from langgraph.types import interrupt


class TutorialState(TypedDict):
    # Messages have the type list. The add_messages function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

# Define node functions
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

def create_tutorial_graph():
    """Create the workflow graph"""
    workflow = StateGraph(TutorialState)
    
    # add nodes (removed START/END)
    workflow.add_node("node_1", node_1)
    workflow.add_node("node_2", node_2)
    workflow.add_node("node_3", node_3)

    # Set entry point and edges
    workflow.set_entry_point("node_1")
    workflow.add_conditional_edges(
        "node_1",
        decide_mood,
        {
            "node_2": "node_2",
            "node_3": "node_3"
        }
    )
    
    return workflow.compile()

if __name__ == "__main__":
    graph = create_tutorial_graph()
    print("Graph created successfully!")
    # Uncomment to display graph (requires proper environment)
    display(Image(graph.get_graph().draw_mermaid_png()))
    
    # Save graph to file
    graph_image = graph.get_graph().draw_mermaid_png()
    with open("tutorial_graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved as tutorial_graph.png")
    # Test the graph

    result = graph.invoke({"messages": []})

    print("\nResult:", result)