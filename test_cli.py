import logging
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from src.langgraphs.test_graph import create_test_graph

# Set up logging
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "test_cli.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Initialize LLM
    llm = ChatOllama(
        model="llama3.1:latest",
        temperature=0.0,
    )
    
    # Create workflow
    workflow = create_test_graph(llm)
    
    print("\nRonan AI Valet CLI Test")
    print("Type 'quit' to exit\n")
    
    while True:
        # Get user input
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
            
        try:
            # Create state
            state = {
                "messages": [HumanMessage(content=user_input)],
                "session_id": "test_session",
                "context": {},
                "tool_states": {}
            }
            
            # Process through workflow
            logger.info("Processing message through workflow...")
            result = workflow.invoke(state)
            logger.info(f"Workflow result: {result}")
            
            # Display response
            if "messages" in result:
                response = result["messages"][-1].content
                print(f"\nRonan: {response}\n")
            else:
                print("\nRonan: I apologize, but I couldn't generate a response.\n")
                
        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            print(f"\nError: {str(e)}\n")

if __name__ == "__main__":
    main() 