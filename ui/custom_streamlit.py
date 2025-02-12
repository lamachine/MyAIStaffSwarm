import os
import asyncio
import streamlit as st
from typing import Optional, List
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import AsyncOpenAI

from crawl_any_docs import CrawlSource, get_urls_for_source, crawl_parallel
from custom_ai_expert import custom_ai_expert, CustomAIDeps
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from llm_provider import LLMProvider

load_dotenv()

# Initialize clients
llm_provider = LLMProvider()
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_source" not in st.session_state:
        st.session_state.current_source = None
    if "crawl_status" not in st.session_state:
        st.session_state.crawl_status = None

async def test_source_availability(source: CrawlSource) -> bool:
    """Test if a source can be crawled by checking for available URLs."""
    urls = get_urls_for_source(source)
    return len(urls) > 0

async def display_source_setup():
    """Display the source setup interface."""
    st.header("Add New Documentation Source")
    
    with st.form("source_setup"):
        name = st.text_input("Source Name (e.g., 'python_docs')")
        base_url = st.text_input("Base URL (e.g., 'https://docs.python.org/3/')")
        sitemap_url = st.text_input("Sitemap URL (optional)")
        url_patterns = st.text_area("URL Patterns (optional, one per line)")
        exclude_patterns = st.text_area("Exclude Patterns (optional, one per line)")
        
        submitted = st.form_submit_button("Test Source")
        
        if submitted and name and base_url:
            # Convert patterns from text to lists
            url_patterns_list = [p.strip() for p in url_patterns.split('\n') if p.strip()] if url_patterns else None
            exclude_patterns_list = [p.strip() for p in exclude_patterns.split('\n') if p.strip()] if exclude_patterns else None
            
            source = CrawlSource(
                name=name,
                base_url=base_url,
                sitemap_url=sitemap_url if sitemap_url else None,
                url_patterns=url_patterns_list,
                exclude_patterns=exclude_patterns_list
            )
            
            with st.spinner("Testing source availability..."):
                is_available = await test_source_availability(source)
                
                if is_available:
                    st.success("Source is available for crawling!")
                    st.session_state.current_source = source
                    st.session_state.crawl_status = "ready"
                else:
                    st.error("No URLs found. Please check your configuration.")

async def display_crawl_interface():
    """Display the crawling interface."""
    st.header("Crawl Documentation")
    
    if st.session_state.current_source:
        source = st.session_state.current_source
        st.write(f"Current source: {source.name}")
        
        if st.button("Start Crawling"):
            st.session_state.crawl_status = "crawling"
            
            urls = get_urls_for_source(source)
            st.write(f"Found {len(urls)} URLs to crawl")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                await crawl_parallel(urls, source)
                st.session_state.crawl_status = "completed"
                status_text.write("Crawling completed successfully!")
            except Exception as e:
                st.error(f"Error during crawling: {str(e)}")
                st.session_state.crawl_status = "error"

async def display_chat_interface():
    """Display the chat interface for querying documentation."""
    st.header("Query Documentation")
    
    # Source selector
    sources = await custom_ai_expert.run_tool(
        "list_available_sources",
        deps=CustomAIDeps(supabase=supabase, llm_provider=llm_provider)
    )
    
    selected_source = st.selectbox(
        "Select Documentation Source",
        ["All Sources"] + sources
    )
    
    # Display chat messages
    for message in st.session_state.messages:
        if isinstance(message, ModelRequest):
            with st.chat_message("user"):
                for part in message.parts:
                    if part.part_kind == 'user-prompt':
                        st.markdown(part.content)
        elif isinstance(message, ModelResponse):
            with st.chat_message("assistant"):
                for part in message.parts:
                    if part.part_kind == 'text':
                        st.markdown(part.content)
    
    # Chat input
    if prompt := st.chat_input("Ask about the documentation"):
        source_filter = None if selected_source == "All Sources" else selected_source
        
        # Add user message to chat
        st.session_state.messages.append(
            ModelRequest(parts=[UserPromptPart(content=prompt)])
        )
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                deps = CustomAIDeps(
                    supabase=supabase,
                    llm_provider=llm_provider,
                    source_name=source_filter
                )
                
                result = await custom_ai_expert.run(prompt, deps=deps)
                st.markdown(result.data)
                
                # Add response to chat history
                st.session_state.messages.append(
                    ModelResponse(parts=[TextPart(content=result.data)])
                )

async def main():
    st.title("Documentation Crawler and Query System")
    
    # Initialize session state
    init_session_state()
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Setup Source", "Crawl Docs", "Query Docs"])
    
    with tab1:
        await display_source_setup()
        
    with tab2:
        await display_crawl_interface()
        
    with tab3:
        await display_chat_interface()

if __name__ == "__main__":
    asyncio.run(main()) 