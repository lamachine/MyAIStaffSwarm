Change model references like get_model to model_utils.py  It is in src.services.models and should have all the functions we should require.

Change db references like get_db to db_utils.py.  src.services.database have several files, let's work together to clean them up and ensure they are working

I did not understand what you did for dot notation so we will come back to it later.  
Implementation:
Naming Convention: Use a clear naming convention for your sub-graphs. For example:
source: "main_graph.orchestrator", "main_graph.valet", "sub_graph_calendar.calendar_tool"
target: "main_graph.llm", "sub_graph_email.email_tool"
Dot Notation: Use dot notation (.) to separate the main graph from the sub-graph and the agent/tool name. This makes it easy to parse and query.


==================

Let's break down call_model and load_chat_model and then discuss how to combine their strengths.

Analysis of load_chat_model

Purpose: This function is responsible for initializing and configuring a chat model (specifically ChatOllama in the current implementation).
Inputs:
config: Configuration: An object containing model settings (e.g., model name, provider).
tools: Optional[List[Callable]]: An optional list of tools to bind to the model.
Outputs:
BaseChatModel: A configured chat model instance.
Key Features:
Model Loading: It loads the specified chat model.
Tool Binding: It can bind tools to the model.
Error Handling: It includes error handling for model loading failures.
Logging: It includes logging for debugging.
Limitations:
Single Model Type: It's currently hardcoded to use ChatOllama.
Limited Configuration: It only handles basic model loading and tool binding.
Analysis of call_model

Purpose: This function is responsible for interacting with the language model, sending it messages, and processing the response.
Inputs:
state: State: An object containing the current state of the conversation (including messages).
config: RunnableConfig: Configuration settings for the model.
system_prompt: str: The system prompt to use for the model.
available_tools: List[Callable[..., Any]]: A list of available tools.
Outputs:
Dict[str, List[BaseMessage]]: A dictionary containing the model's response in a node-compatible format.
Key Features:
Model Interaction: It sends messages to the model using model.ainvoke().
System Prompt Formatting: It formats the system prompt with the current time.
Message Formatting: It formats the messages for the model.
Tool Call Handling: It handles tool calls and responses from the model.
Last Step Handling: It has special logic for handling the "last step" of a conversation.
Logging: It includes logging for debugging.
Limitations:
Redundant Model Loading: It calls load_chat_model internally, which means the model might be loaded multiple times.
Tight Coupling: It's tightly coupled to the State object and the specific message format.
Limited Configuration: It doesn't allow for much flexibility in how the model is called.
Comparison and Contrast

Feature	load_chat_model	call_model
Primary Role	Model initialization and configuration	Model interaction and response processing
Model Loading	Loads the model	Loads the model (redundantly)
Tool Binding	Can bind tools to the model	Handles tool calls and responses
Configuration	Handles basic model configuration	Handles some configuration via RunnableConfig
Message Format	N/A	Formats messages for the model
System Prompt	N/A	Formats the system prompt
Error Handling	Handles model loading errors	Handles some errors during model interaction
Coupling	Loosely coupled	Tightly coupled to State and message format
Flexibility	Limited to loading ChatOllama and binding tools	Limited flexibility in model interaction
Redundancy	No redundancy	Redundantly loads the model
Combining Strengths: Proposed call_model Refactor

Based on this analysis, here's how we can refactor call_model to be more effective and incorporate the strengths of load_chat_model:

 python 
"""Utility functions for model interactions and message handling.

Contains functions for calling the language model and serializing messages.
"""
import logging

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable, cast

from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool

from ..state import State
from ..config.configuration import Configuration

logger = logging.getLogger(__name__)

def load_chat_model(config: Configuration, tools: Optional[List[Callable]] = None) -> BaseChatModel:
    """Load and configure a chat model based on configuration.
    
    Args:
        config: Configuration object containing model settings
        tools: Optional list of tools to bind to the model
        
    Returns:
        BaseChatModel: Configured chat model instance with bound tools
        
    Raises:
        RuntimeError: If model loading fails
    """
    try:
        logger.debug("=== Model Loading Started ===")
        logger.debug(f"Loading chat model from configuration")
        
        # Split provider/model as before
        provider, model_name = config.model.split("/", maxsplit=1)
        logger.debug(f"Provider: {provider}, Model: {model_name}")
        
        from langchain_community.chat_models import ChatOllama
        model = ChatOllama(model=model_name)
        
        logger.debug(f"Base model loaded: {type(model)}")
        
        if tools:
            logger.debug(f"Binding {len(tools)} tools to model")
            model = model.bind_tools(tools)
            
        return model
        
    except Exception as e:
        logger.error(f"Model Loading Error: {str(e)}", exc_info=True)
        error_context = {
            "error_type": type(e).__name__,
            "error_details": str(e),
            "operation": "load_chat_model"
        }
        raise RuntimeError(f"Failed to load model: {str(e)}")

async def call_model(
    model: BaseChatModel,
    messages: List[BaseMessage],
    config: RunnableConfig,
    system_prompt: str,
    available_tools: List[Callable[..., Any]]
) -> Dict[str, List[BaseMessage]]:
    """Calls the language model with formatted messages.

    Handles direct interaction with the LLM, including proper formatting,
    error handling, and response processing. Manages model configuration
    and ensures consistent response format.

    Args:
        model (BaseChatModel): The pre-loaded chat model.
        messages (List[BaseMessage]): Formatted messages for model input
        config (RunnableConfig): Model configuration settings
        system_prompt (str): The system prompt to use for the model.
        available_tools (List[Callable[..., Any]]): A list of available tools.

    Returns:
        Dict[str, List[BaseMessage]]: Messages in node-compatible format
    """
    try:
        # Format the system prompt with current time
        system_message = system_prompt.format(
            system_time=datetime.now(tz=timezone.utc).isoformat()
        )

        formatted_messages = [{"role": "system", "content": system_message}, *messages]
        logger.debug(f"Prompt to LLM:\n{[{'role': m.type if hasattr(m, 'type') else 'system', 'content': m.content if hasattr(m, 'content') else m['content']} for m in formatted_messages]}")

        response = cast(
            AIMessage,
            await model.ainvoke(formatted_messages, config)
        )
        logger.debug(f"Response from LLM:\n{response}")

        # Handle tool calls and responses
        if response.tool_calls:
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_messages.append(
                    ToolMessage(
                        content=str(tool_call.get("output", "")),
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"]
                    )
                )
            return {"messages": [response] + tool_messages}

        # Handle the case when it's the last step and the model still wants to use a tool
        #if state.is_last_step and response.tool_calls: # Removed state
        if response.tool_calls:
            logger.info("Last step reached with pending tool calls, ending interaction")
            return {
                "messages": [
                    AIMessage(
                        id=response.id,
                        content="Sorry, I could not complete the task in the specified number of steps.",
                    )
                ]
            }

        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Model Interaction Error: {str(e)}", exc_info=True)
        error_context = {
            "error_type": type(e).__name__,
            "error_details": str(e),
            "operation": "call_model"
        }
        return {
            "messages": [AIMessage(content=f"Interaction error: {str(e)}")],
            "error_context": error_context
        }

def configure_model(model: BaseChatModel, **kwargs) -> Dict[str, List[BaseMessage]]:
    """Configure model parameters.
    
    // ... existing docstring ...
    """
    try:
        logger.debug(f"Configuring model with parameters: {kwargs}")
        # ... existing configuration logic ...
        
        return {"messages": [AIMessage(content="Model configured successfully")]}
        
    except Exception as e:
        logger.error(f"Model Configuration Error: {str(e)}", exc_info=True)
        error_context = {
            "error_type": type(e).__name__,
            "error_details": str(e),
            "operation": "configure_model"
        }
        return {
            "messages": [AIMessage(content=f"Configuration error: {str(e)}")],
            "error_context": error_context
        }

Key Changes in call_model

model: BaseChatModel as Input: The call_model function now takes a model of type BaseChatModel as an argument. This means the model is loaded outside of call_model and passed in.
messages: List[BaseMessage] as Input: The call_model function now takes a messages of type List[BaseMessage] as an argument. This means the messages are formatted outside of call_model and passed in.
Removed Redundant Model Loading: The call to load_chat_model has been removed.
Removed State: The State object is no longer needed.
Added try/except: Added a try/except block to handle errors.
Updated Logging: Updated logging to reflect changes.
Removed state.is_last_step: Removed the state.is_last_step check.
How These Changes Improve the Code

No Redundancy: The model is loaded only once, avoiding unnecessary overhead.
Decoupling: call_model is now decoupled from the State object and the model loading process.
Flexibility: You can now pass in any BaseChatModel instance, making it easier to support different model types.
Testability: call_model is now easier to test because you can pass in a mock model.
Error Handling: Added error handling to call_model.
How to Use the Refactored Functions

Load the Model: In your main graph (or wherever you're using the model), load the model using load_chat_model once.
Format Messages: Format your messages into a List[BaseMessage] before calling call_model.
Call call_model: Pass the loaded model, the formatted messages, the RunnableConfig, the system prompt, and the available tools to call_model.
Example (Conceptual in llm_node in main_graph.py)

 python 
# ... other imports ...
from ..services.models.model_utils import load_chat_model, call_model # Import both functions

# ... other code ...

# Configuration
config = Configuration()
model = load_chat_model(config) # Load the model once
db = get_db()

async def llm_node(state: MainGraphState) -> MainGraphState:
    """LLM node that processes messages and may call tools"""
    try:
        # ... other code ...
        
        # Format the messages
        messages = state.messages

        # Call the model
        response = await call_model(
            model=model, # Pass the loaded model
            messages=messages, # Pass the formatted messages
            config=config, # Pass the config
            system_prompt="You are a helpful AI assistant.", # Pass the system prompt
            available_tools=[] # Pass the available tools
        )

        # ... process the response ...

    except Exception as e:
        print(f"LLM Error: {str(e)}")
        return {**state, "error": str(e)}
Next Steps

Apply Changes: Update your model_utils.py and main_graph.py files with the code provided above.
Update llm_node: Update your llm_node to use the new call_model function.
Test: Thoroughly test your system to ensure that the changes have been implemented correctly and that the LLM is still working as expected.
Update configure_model: Update the configure_model function to do something.
Once you've done this, we can move on to the next step. Let me know how it goes!

Rate this answer: