import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add project root to Python path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Create logs directory if it doesn't exist
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging
log_file = LOGS_DIR / f"james_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Starting James AI Valet. Logging to {log_file}")

import streamlit as st
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from src.tools.llm_provider import LLMProvider
from src.langgraphs.test_graph import create_test_graph

# Force dark theme
st.set_page_config(
    page_title="James - AI Valet",
    page_icon="🤵",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# Custom CSS for dark theme
st.markdown("""
<style>
    /* Dark theme styles */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stChatMessage {
        background-color: #262730;
    }
    /* Additional dark theme customization */
    .stButton>button {
        background-color: #262730;
        color: #FAFAFA;
    }
    .stTextInput>div>div>input {
        background-color: #262730;
        color: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Create .streamlit/config.toml for port configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "config.toml")
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

with open(CONFIG_PATH, "w") as f:
    f.write("""
[server]
port = 8053
address = "localhost"

[browser]
serverAddress = "localhost"
serverPort = 8053
""")

# Initialize LLM with explicit settings
@st.cache_resource
def init_llm():
    return ChatOllama(
        model="llama3.1:latest",
        temperature=0.0,
        num_gpu=1,
        num_thread=8
    )

# Initialize workflow with the LLM
@st.cache_resource
def init_workflow():
    llm = init_llm()
    return create_test_graph(llm)  # Pass LLM to test_graph

def main():
    st.title("James - AI Valet")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if prompt := st.chat_input("How can I help you today?"):
        # Log the received prompt
        logger.info(f"Received prompt: {prompt}")
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            # Create state for workflow
            state = {
                "messages": [HumanMessage(content=prompt)],
                "session_id": "test_session",
                "context": {},
                "tool_states": {}
            }
            
            # Get AI response
            workflow = init_workflow()
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    logger.info("Processing through workflow...")
                    response = None
                    for event in workflow.stream(state):
                        logger.info(f"Workflow event: {event}")  # Log each event
                        if "messages" in event:  # Changed from checking agent
                            for msg in event["messages"]:
                                if isinstance(msg, AIMessage):
                                    response = msg.content
                                    st.markdown(response)
                                    st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": response
                                    })
                                    break
                    if not response:
                        logger.warning("No response generated from workflow")
                        st.error("I apologize, but I couldn't generate a response.")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()