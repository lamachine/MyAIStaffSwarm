from __future__ import annotations
from typing import Literal, TypedDict
import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

import streamlit as st
import json
import logfire
from supabase import Client
from openai import AsyncOpenAI

# Import all the message part classes
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    RetryPromptPart,
    ModelMessagesTypeAdapter
)
from api.rag_ai_expert import rag_expert, RAGDeps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Configure logfire to suppress warnings (optional)
logfire.configure(send_to_logfire='never')

class ChatMessage(TypedDict):
    """Format of messages sent to the browser/API."""

    role: Literal['user', 'model']
    timestamp: str
    content: str


def display_message_part(part):
    """
    Display a single part of a message in the Streamlit UI.
    Customize how you display system prompts, user prompts,
    tool calls, tool returns, etc.
    """
    try:
        print(f"\n=== Displaying message part: {part.part_kind} ===")  # Debug
        
        # system-prompt
        if part.part_kind == 'system-prompt':
            print(f"System prompt content: {part.content[:200]}...")  # Debug
            st.markdown(f"**System**: {part.content}")
        # user-prompt
        elif part.part_kind == 'user-prompt':
            print(f"User prompt: {part.content}")  # Debug
            st.markdown(part.content)
        # tool-call
        elif part.part_kind == 'tool-call':
            print(f"Tool call: {part.tool_name}")  # Debug
            print(f"Parameters: {json.dumps(part.parameters, indent=2)}")  # Debug
            st.markdown(f"🔧 Using tool: **{part.tool_name}**\n\n```json\n{json.dumps(part.parameters, indent=2)}\n```")
        # tool-return
        elif part.part_kind == 'tool-return':
            print(f"Tool return length: {len(part.content)}")  # Debug
            print(f"Tool return preview: {part.content[:200]}...")  # Debug
            st.markdown(f"📄 Tool result:\n\n```\n{part.content}\n```")
        # text
        elif part.part_kind == 'text':
            print(f"Text content preview: {part.content[:200]}...")  # Debug
            st.markdown(part.content)          
    except Exception as e:
        print(f"ERROR in display_message_part: {str(e)}")  # Debug
        print(f"Error type: {type(e).__name__}")  # Debug
        print(f"Part type: {type(part).__name__}")  # Debug
        st.error(f"Error displaying message: {str(e)}")


async def run_agent_with_streaming(user_input: str):
    """
    Run the agent with streaming text for the user_input prompt,
    while maintaining the entire conversation in `st.session_state.messages`.
    """
    print("\n=== Starting new agent run ===")  # Debug
    print(f"Input query: {user_input}")  # Debug
    
    # Prepare dependencies
    deps = RAGDeps(
        supabase=supabase,
        openai_client=openai_client
    )

    try:
        # Run the agent in a stream
        async with rag_expert.run_stream(
            user_input,
            deps=deps,
            message_history=st.session_state.messages[:-1],  # pass entire conversation so far
        ) as result:
            print("\n=== Processing stream result ===")  # Debug
            print(f"Message history length: {len(st.session_state.messages)}")  # Debug
            
            # Create a container for the assistant's response
            with st.chat_message("assistant"):
                # Create placeholders for different parts of the response
                tool_placeholder = st.empty()
                message_placeholder = st.empty()
                
                # Variables to track state
                collected_parts = []
                partial_text = ""
                tool_parts = []
                
                # First process any tool calls or other messages
                print("\n=== Processing new messages ===")  # Debug
                for msg in result.new_messages():
                    print(f"Message type: {type(msg).__name__}")  # Debug
                    if isinstance(msg, (ModelRequest, ModelResponse)):
                        for part in msg.parts:
                            print(f"Part type: {part.part_kind}")  # Debug
                            if part.part_kind in ['tool-call', 'tool-return']:
                                tool_parts.append(part)
                            collected_parts.append(part)
                
                # Display tool parts if any
                if tool_parts:
                    with tool_placeholder:
                        for part in tool_parts:
                            display_message_part(part)
                
                # Stream text chunks
                try:
                    print("\n=== Starting text stream ===")  # Debug
                    chunk_count = 0
                    async for chunk in result.stream_text(delta=True):
                        if chunk:  # Only process non-empty chunks
                            chunk_count += 1
                            print(f"Chunk {chunk_count}: {chunk}")  # Debug
                            partial_text += chunk
                            message_placeholder.markdown(partial_text)
                    
                    print(f"\nStream complete. Total chunks: {chunk_count}")  # Debug
                    
                    # If we got any text, add it to history
                    if partial_text:
                        print("\n=== Adding to message history ===")  # Debug
                        print(f"Final text length: {len(partial_text)}")  # Debug
                        # Add the final text as a new part
                        collected_parts.append(TextPart(content=partial_text))
                        # Add everything to the message history
                        st.session_state.messages.append(
                            ModelResponse(parts=collected_parts)
                        )
                        print("Message added to session state")  # Debug
                    else:
                        print("WARNING: No text to add to history")  # Debug
                        
                except Exception as e:
                    print(f"ERROR in streaming loop: {str(e)}")  # Debug
                    print(f"Error type: {type(e).__name__}")  # Debug
                    print(f"Error details: {e.__dict__}")  # Debug
                    message_placeholder.error(f"Error during streaming: {str(e)}")
                    # Still try to save what we have
                    if partial_text:
                        collected_parts.append(TextPart(content=partial_text))
                        st.session_state.messages.append(
                            ModelResponse(parts=collected_parts)
                        )
    
    except Exception as e:
        print(f"ERROR in agent run: {str(e)}")  # Debug
        print(f"Error type: {type(e).__name__}")  # Debug
        print(f"Error details: {e.__dict__}")  # Debug
        st.error(f"Error running agent: {str(e)}")
    
    print("\n=== Agent run complete ===\n")  # Debug


async def main():
    st.title("RAG AI Expert")
    st.write("Ask any question about the documentation, and I'll help you find the answers.")

    # Initialize chat history in session state if not present
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a container for the chat history
    chat_container = st.container()
    
    # Display all messages from the conversation so far in the container
    with chat_container:
        for msg in st.session_state.messages:
            if isinstance(msg, ModelRequest) or isinstance(msg, ModelResponse):
                with st.chat_message("user" if isinstance(msg, ModelRequest) else "assistant"):
                    for part in msg.parts:
                        display_message_part(part)

    # Chat input for the user - place this at the bottom
    user_input = st.chat_input("What would you like to know about the documentation?")

    if user_input:
        # We append a new request to the conversation explicitly
        st.session_state.messages.append(
            ModelRequest(parts=[UserPromptPart(content=user_input)])
        )
        
        # Display user prompt in the UI
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

            # Actually run the agent now, streaming the text
            await run_agent_with_streaming(user_input)
        
        # Force a rerun to update the display with new messages
        st.rerun()


if __name__ == "__main__":
    asyncio.run(main())
