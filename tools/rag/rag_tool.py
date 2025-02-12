"""
title: RAG Search Tool
version: 0.1.0

This module provides RAG functionality using Supabase and Ollama embeddings
"""

from ..base import BaseTool, ToolMetadata
from pydantic import BaseModel
from typing import List, Optional, Any
from enum import Enum
import os
from supabase import create_client, Client
import httpx
from dotenv import load_dotenv
import logging

# Force reload of .env
load_dotenv(override=True)

# Debug print
print(f"Supabase URL: {os.getenv('SUPABASE_URL')}")
print(f"Supabase Key: {os.getenv('SUPABASE_KEY', '')[:10]}...")

class ContentType(str, Enum):
    DOCS = "docs"
    MEDIA = "media"
    REPO = "repo"
    SOCIAL_POSTS = "social_posts"
    SOCIAL_COMMENTS = "social_comments"
    SOCIAL_ARTICLES = "social_articles"

class RAGTool(BaseTool):
    def __init__(self):
        self.metadata = ToolMetadata(
            name="rag_search",
            description="Search and retrieve documentation using RAG",
            config={
                "supabase_url": os.getenv("SUPABASE_URL", ""),
                "supabase_key": os.getenv("SUPABASE_KEY", ""),
                "embedding_model": "nomic-embed-text:latest"
            }
        )
        self.supabase: Optional[Client] = None
        
    def _init_supabase(self):
        """Initialize Supabase client if not already done"""
        if not self.supabase:
            try:
                supabase_url = os.getenv("SUPABASE_URL", "http://localhost:8000")
                supabase_key = os.getenv("SUPABASE_KEY", "")

                print(f"Connecting to Supabase at {supabase_url}")
                self.supabase = create_client(supabase_url, supabase_key)

            except Exception as e:
                print(f"Supabase connection error: {e}")
                self.supabase = None
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector from Ollama"""
        # Use OLLAMA_HOST_URL since we're running on host
        ollama_url = os.getenv("OLLAMA_HOST_URL", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ollama_url}/api/embeddings",
                json={
                    "model": self.metadata.config["embedding_model"],
                    "prompt": text
                }
            )
            return response.json()["embedding"]
    
    CONTENT_TYPE_MAPPINGS = {
        ContentType.DOCS: {
            "table": "dev_docs_site_pages",
            "match_function": "match_dev_docs_site_pages"
        },
        ContentType.MEDIA: {
            "table": "media_content",
            "match_function": "match_media_content"
        },
        ContentType.REPO: {
            "table": "repo_content",
            "match_function": "match_repo_content"
        },
        ContentType.SOCIAL_POSTS: {
            "table": "social_posts",
            "match_function": "match_social_posts"
        },
        ContentType.SOCIAL_COMMENTS: {
            "table": "social_comments",
            "match_function": "match_social_comments"
        },
        ContentType.SOCIAL_ARTICLES: {
            "table": "social_articles",
            "match_function": "match_social_articles"
        }
    }

    async def retrieve_content(
        self, 
        query: str, 
        content_types: List[ContentType] = [ContentType.DOCS],
        limit: int = 5
    ) -> str:
        """Retrieve relevant content from specified sources"""
        if not self.metadata.config["supabase_url"] or not self.metadata.config["supabase_key"]:
            return "Error: Supabase configuration missing. Please check environment variables."
        
        try:
            self._init_supabase()
            if not self.supabase:
                return "Error: Could not initialize Supabase connection"
            
            results = []
            
            for content_type in content_types:
                mapping = self.CONTENT_TYPE_MAPPINGS[content_type]
                
                try:
                    query_embedding = await self.get_embedding(query)
                    
                    result = self.supabase.rpc(
                        mapping["match_function"],
                        {
                            'query_embedding': query_embedding,
                            'match_count': limit,
                            'filter': {}
                        }
                    ).execute()
                    
                    if result.data:
                        for doc in result.data:
                            chunk_text = f"""
Source: {content_type.value}
# {doc['title']}

{doc['content']}

Summary: {doc.get('summary', 'N/A')}
URL: {doc.get('url') or doc.get('post_url') or doc.get('article_url')}
Relevance: {doc['similarity']:.2f}
"""
                            results.append((doc['similarity'], chunk_text))
                
                except Exception as e:
                    print(f"Error retrieving {content_type} content: {e}")
                
            if not results:
                return "No relevant content found."
            
            # Sort by similarity and format
            results.sort(reverse=True, key=lambda x: x[0])
            return "\n\n---\n\n".join(chunk for _, chunk in results)
        
        except Exception as e:
            print(f"Error retrieving content: {e}")
            return "An error occurred while retrieving content."

    async def list_content(
        self,
        content_type: ContentType = ContentType.DOCS
    ) -> List[str]:
        """List available content from a specific source"""
        logging.info(f"Listing content for type: {content_type}")
        
        if not self.supabase:
            logging.info("Initializing Supabase connection...")
            self._init_supabase()
        
        mapping = self.CONTENT_TYPE_MAPPINGS[content_type]
        logging.info(f"Using table: {mapping['table']}")
        
        try:
            # Query for unique titles and URLs
            logging.info("Executing Supabase query...")
            result = self.supabase.from_(mapping["table"]) \
                .select('title, url') \
                .execute()
            
            logging.info(f"Query result: {result}")
            
            if not result.data:
                logging.warning("No data found in query result")
                return []
            
            # Format results nicely
            content_list = []
            for doc in result.data:
                title = doc.get('title', 'Untitled')
                url = doc.get('url', 'No URL')
                content_list.append(f"{title} ({url})")
            
            logging.info(f"Found {len(content_list)} items")
            return sorted(set(content_list))
            
        except Exception as e:
            logging.error(f"Error listing {content_type} content: {e}", exc_info=True)
            return []
    
    async def execute(self, action: str, **kwargs) -> Any:
        """Execute the requested RAG action"""
        actions = {
            "retrieve": self.retrieve_content,
            "list": self.list_content
        }
        
        if action not in actions:
            raise ValueError(f"Unknown action: {action}")
            
        return await actions[action](**kwargs) 