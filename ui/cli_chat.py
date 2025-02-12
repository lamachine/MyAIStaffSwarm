import os
import asyncio
import json
from datetime import datetime
import pytz
from dotenv import load_dotenv
from .supabase_chat_memory import add_message, get_conversation_history
from ..tools.tool_handler import ToolHandler
from ..agents.common import LLM_MODEL, get_ollama_response
from ..tools.pydantic_supabase_rag_tools import ListDocumentationPages, RetrieveRelevantContent

# Load environment variables
load_dotenv(override=True)

# Constants
USER_ID = "TestUser"
LA_TIMEZONE = pytz.timezone('America/Los_Angeles')

async def main():
    """Main chat loop."""
    # Initialize tool handler
    tool_handler = ToolHandler()
    
    # Register tools
    tool_handler.register_tool(ListDocumentationPages())
    tool_handler.register_tool(RetrieveRelevantContent())
    
    # Get current LA time
    current_time = datetime.now(LA_TIMEZONE)
    print(f"Starting chat with {LLM_MODEL} at {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print("Type 'exit' to quit, 'history' to see conversation history")
    
    # Create a new conversation with LA timezone timestamp
    conversation_id = f"{USER_ID}_{current_time.strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize conversation history
    messages = []
    
    # Add system message with current time context
    system_message = {
        'role': 'system',
        'content': f"""You are {LLM_MODEL}, a helpful AI assistant. 
Current time: {current_time.strftime('%I:%M %p')}
Current date: {current_time.strftime('%A, %B %d, %Y')}
Location: San Jose, CA, USA

You have access to the following tools:
- list_documentation_pages: Lists all available documentation pages in the RAG database
- retrieve_relevant_content: Searches for specific information in the RAG database

Please use these tools when asked about documentation or when searching for specific information."""
    }
    messages.append(system_message)
    
    # Store system message in Supabase
    await add_message(
        user_id=USER_ID,
        conversation_id=conversation_id,
        role="system",
        content=system_message['content']
    )
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Handle commands
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        elif user_input.lower() == 'history':
            history = await get_conversation_history(USER_ID, conversation_id)
            print("\nConversation history:")
            print("=" * 50)
            for msg in history:
                if msg["role"] != "system":
                    print(f"{msg['role'].title()}: {msg['content']}")
            print("=" * 50)
            continue
        
        # Add user message to history
        messages.append({'role': 'user', 'content': user_input})
        
        # Store user message in Supabase
        await add_message(
            user_id=USER_ID,
            conversation_id=conversation_id,
            role="user",
            content=user_input
        )
        
        try:
            # Get response from model
            print("\nAssistant: ", end="", flush=True)
            response = await get_ollama_response(
                messages=messages,
                tools=tool_handler.get_tool_definitions()
            )
            
            tool_results = []
            if 'tool_calls' in response['message']:
                for tool_call in response['message']['tool_calls']:
                    result = await tool_handler.execute_tool_call(tool_call)
                    tool_results.append({
                        'tool': tool_call['function']['name'],
                        'result': result
                    })
                    
                # Add tool results to conversation
                messages.append({
                    'role': 'tool',
                    'content': json.dumps(tool_results)
                })
                
                # Get final response incorporating tool results
                response = await get_ollama_response(messages=messages)
            
            assistant_message = response['message']['content']
            print(assistant_message)
            
            # Add assistant response to history
            messages.append({'role': 'assistant', 'content': assistant_message})
            
            # Store assistant response in Supabase
            await add_message(
                user_id=USER_ID,
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                metadata={"tool_calls": tool_results} if tool_results else None
            )
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await add_message(
                user_id=USER_ID,
                conversation_id=conversation_id,
                role="assistant",
                content=error_message
            )

if __name__ == "__main__":
    asyncio.run(main()) 