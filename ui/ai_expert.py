from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client
from typing import List, Optional
from llm_provider import LLMProvider

load_dotenv()

llm = os.getenv('LLM_MODEL', 'gpt-4o-mini')
model = OpenAIModel(llm)

logfire.configure(send_to_logfire='if-token-present')

# Initialize LLM provider
llm_provider = LLMProvider()

@dataclass
class CustomAIDeps:
    supabase: Client
    llm_provider: LLMProvider
    source_name: Optional[str] = None

system_prompt = """
You are an expert at retrieving and analyzing documentation from various sources that have been processed
and stored in a vector database. You can help users find information across multiple documentation sources
and provide detailed, accurate answers based on the stored content.

Your job is to assist with querying and analyzing this documentation. You'll always specify which source
you're pulling information from to maintain clarity.

Don't ask the user before taking an action, just do it. Always make sure you look at the documentation 
with the provided tools before answering the user's question unless you have already.

When you first look at the documentation, always start with RAG.
Then also always check the list of available documentation pages and retrieve the content of page(s) if it'll help.

Always let the user know when you didn't find the answer in the documentation or the right URL - be honest.
"""

custom_ai_expert = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=CustomAIDeps,
    retries=2
)

async def get_embedding(text: str, llm_provider: LLMProvider) -> List[float]:
    """Get embedding vector from configured LLM provider."""
    return await llm_provider.get_embedding(text)

@custom_ai_expert.tool
async def retrieve_relevant_documentation(
    ctx: RunContext[CustomAIDeps], 
    user_query: str,
    source_filter: Optional[str] = None
) -> str:
    """
    Retrieve relevant documentation chunks based on the query with RAG.
    
    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query
        source_filter: Optional source name to filter results
        
    Returns:
        A formatted string containing the top 5 most relevant documentation chunks
    """
    try:
        query_embedding = await get_embedding(user_query, ctx.deps.llm_provider)
        
        filter_obj = {}
        if source_filter or ctx.deps.source_name:
            filter_obj['source'] = source_filter or ctx.deps.source_name
        
        result = ctx.deps.supabase.rpc(
            'match_site_pages',
            {
                'query_embedding': query_embedding,
                'match_count': 5,
                'filter': filter_obj
            }
        ).execute()
        
        if not result.data:
            return "No relevant documentation found."
            
        formatted_chunks = []
        for doc in result.data:
            source = doc['metadata'].get('source', 'Unknown Source')
            chunk_text = f"""
# [{source}] {doc['title']}

{doc['content']}
"""
            formatted_chunks.append(chunk_text)
            
        return "\n\n---\n\n".join(formatted_chunks)
        
    except Exception as e:
        print(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}"

@custom_ai_expert.tool
async def list_documentation_pages(
    ctx: RunContext[CustomAIDeps],
    source_filter: Optional[str] = None
) -> List[str]:
    """
    Retrieve a list of all available documentation pages.
    
    Args:
        ctx: The context including the Supabase client
        source_filter: Optional source name to filter results
        
    Returns:
        List[str]: List of unique URLs for all documentation pages
    """
    try:
        query = ctx.deps.supabase.from_('site_pages').select('url, metadata->source')
        
        if source_filter or ctx.deps.source_name:
            filter_name = source_filter or ctx.deps.source_name
            query = query.eq('metadata->>source', filter_name)
            
        result = query.execute()
        
        if not result.data:
            return []
            
        # Extract unique URLs with their sources
        urls = sorted(set(f"[{doc['metadata']['source']}] {doc['url']}" for doc in result.data))
        return urls
        
    except Exception as e:
        print(f"Error retrieving documentation pages: {e}")
        return []

@custom_ai_expert.tool
async def get_page_content(ctx: RunContext[CustomAIDeps], url: str) -> str:
    """
    Retrieve the full content of a specific documentation page.
    
    Args:
        ctx: The context including the Supabase client
        url: The URL of the page to retrieve
        
    Returns:
        str: The complete page content with all chunks combined in order
    """
    try:
        query = ctx.deps.supabase.from_('site_pages') \
            .select('title, content, chunk_number, metadata->source') \
            .eq('url', url)
            
        if ctx.deps.source_name:
            query = query.eq('metadata->>source', ctx.deps.source_name)
            
        result = query.order('chunk_number').execute()
        
        if not result.data:
            return f"No content found for URL: {url}"
            
        source = result.data[0]['metadata']['source']
        page_title = result.data[0]['title'].split(' - ')[0]
        formatted_content = [f"# [{source}] {page_title}\n"]
        
        for chunk in result.data:
            formatted_content.append(chunk['content'])
            
        return "\n\n".join(formatted_content)
        
    except Exception as e:
        print(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"

@custom_ai_expert.tool
async def list_available_sources(ctx: RunContext[CustomAIDeps]) -> List[str]:
    """
    List all available documentation sources in the database.
    
    Returns:
        List[str]: List of unique source names
    """
    try:
        result = ctx.deps.supabase.from_('site_pages') \
            .select('metadata->source') \
            .execute()
        
        if not result.data:
            return []
        
        # Extract unique source names
        sources = sorted(set(doc['metadata']['source'] for doc in result.data))
        return sources
        
    except Exception as e:
        print(f"Error listing sources: {e}")
        return [] 