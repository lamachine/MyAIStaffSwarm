"""
Simple CLI interface for testing and developing the LangGraph workflow
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from uuid import uuid4

from langchain_core.messages import HumanMessage

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.langgraphs.main_graph import graph_executor, MainGraphState
from src.agents.pers_agent_valet_Ronan.config import Valet_Config

async def cli_for_test_and_dev():    
    """Main function to run the CLI."""
    state = MainGraphState()  # Initialize state as an instance of MainGraphState

    while True:
        active_agent = state.get("active_agent", Valet_Config.model_validate_json(Valet_Config().model_dump_json())) # Default to valet if not set

        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["/quit", "/exit", "/bye"]:
            break

        else:
            # Update state with user input
            state.messages.append(HumanMessage(content=user_input))
            state.user_input = user_input
            state.content = user_input
            state.target = "orchestrator_node"
            state.metadata["new_run"] = False # Set new_run to False for subsequent turns
            
            return state


