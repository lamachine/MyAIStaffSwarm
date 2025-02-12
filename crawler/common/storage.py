import os
from typing import List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

from .text_processing import ProcessedChunk

# Load environment variables first
load_dotenv(override=True)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def get_table_name() -> str:
    """Get the table name from environment variables."""
    return os.getenv("CURRENT_SOURCE_TABLE", "dev_docs_site_pages")

async def store_chunks(chunks: List[ProcessedChunk], content_type: str = "doc") -> bool:
    """Store processed chunks in the database. Returns True if successful."""
    table_name = get_table_name()
    success = True
    
    for chunk in chunks:
        try:
            # Base chunk data that's common across all types
            chunk_data = {
                "chunk_number": chunk.chunk_number,
                "title": chunk.title,
                "summary": chunk.summary,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": chunk.embedding,
                "embedding_model": chunk.embedding_model,
                "document_creation_date": chunk.document_creation_date,
                "document_crawl_date": chunk.document_crawl_date
            }

            # Handle different table schemas
            if table_name == "repo_content":
                # Repository content specific fields
                chunk_data.update({
                    "repo_url": os.getenv("CURRENT_SOURCE_BASE_URL"),
                    "file_path": chunk.metadata.get("file_path", ""),
                    "branch": os.getenv("CURRENT_SOURCE_BRANCH", "main")
                })
                conflict_key = "repo_url,file_path,branch,chunk_number"
                
            elif table_name == "media_content":
                # Media content specific fields
                chunk_data.update({
                    "media_url": chunk.url,
                    "media_type": chunk.metadata.get("media_type", "unknown"),
                    "description": chunk.metadata.get("description", ""),
                    "transcript": chunk.metadata.get("transcript", ""),
                    "duration": chunk.metadata.get("duration"),
                    "publish_date": chunk.metadata.get("publish_date")
                })
                conflict_key = "media_url,chunk_number"
                
            else:
                # Default doc content
                chunk_data["url"] = chunk.url
                conflict_key = "url,chunk_number"

            # Upsert the chunk with appropriate conflict key
            result = supabase.table(table_name).upsert(
                chunk_data,
                on_conflict=conflict_key
            ).execute()
            
            if not result.data:
                print(f"Warning: No data returned from upsert operation")
                success = False

        except Exception as e:
            print(f"Error storing chunk: {e}")
            print(f"Table: {table_name}")
            print(f"Data keys: {list(chunk_data.keys())}")
            success = False
            
    return success 