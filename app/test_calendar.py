import asyncio
from src.langgraphs.calendar_graph import create_calendar_graph

async def main():
    # Create the test state
    initial_state = {
        "tool_input": {
            "action": "view",
            "date": "today",
            "summary": "",
            "duration": ""
        }
    }

    # Create and run graph
    print("Creating calendar graph...")
    graph = create_calendar_graph()
    
    print("\nSending request to calendar...")
    result = await graph.ainvoke(initial_state)
    
    print("\nCalendar Response:")
    print(result["response"])

if __name__ == "__main__":
    asyncio.run(main()) 