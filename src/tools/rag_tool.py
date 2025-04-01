import os
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from src.tools.base_tool import BaseTool
from supabase import create_client, Client

# Dummy RAG service implementation.
# Replace with your full implementation as needed.
class RAGService:
    def ingest_documents(self, folder_path: str, patterns: Optional[List[str]] = None) -> bool:
        # In production, this would process documents and build a vector store.
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder not found: {folder_path}")
        # Simulate processing delay
        import time; time.sleep(1)
        return True

    def query_documents(self, query: str, num_results: int = 5) -> Optional[str]:
        # In production, this would retrieve relevant documents.
        return f"Simulated results for query: '{query}' (up to {num_results} results)"

# Pydantic model for parameter validation
class RAGParameters(BaseModel):
    action: str
    folder_path: Optional[str] = None
    patterns: Optional[List[str]] = None
    query: Optional[str] = None
    num_results: int = 5
    conversation_id: Optional[str] = None
    limit: int = 10

class RAGTool(BaseTool):
    """
    RAGTool provides retrieval-augmented generation (RAG) functionality:
     - ingest: Process documents from a folder (vectorize and store embeddings).
     - query: Search the document store.
     - chat_history: Retrieve chat history from the 'messages' table.
     - repo_latest: Retrieve the latest crawled repository content.
    
    Supported actions:
     - ingest: requires 'folder_path' (and optional 'patterns').
     - query:   requires 'query' (and optional 'num_results').
     - chat_history: requires 'conversation_id' (with optional 'limit').
     - repo_latest: no additional parameters.
    """
    name = "rag_tool"
    description = "Provides RAG operations for document ingestion, querying, chat history, and latest repo content."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Operation: 'ingest', 'query', 'chat_history', or 'repo_latest'.",
                "enum": ["ingest", "query", "chat_history", "repo_latest"]
            },
            "folder_path": {
                "type": "string",
                "description": "Path to folder containing documents for ingestion."
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of file patterns (e.g., ['*.txt', '*.md'])."
            },
            "query": {
                "type": "string",
                "description": "Search query for document retrieval."
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return when querying.",
                "default": 5
            },
            "conversation_id": {
                "type": "string",
                "description": "Conversation ID to retrieve chat history."
            },
            "limit": {
                "type": "integer",
                "description": "Number of records to return for chat history (default 10).",
                "default": 10
            }
        },
        "required": ["action"]
    }
    required: List[str] = ["action"]

    async def execute(self, **kwargs) -> str:
        try:
            params = RAGParameters(**kwargs)
        except Exception as e:
            return f"Parameter validation error: {str(e)}"

        # Initialize our RAG service (replace with your actual implementation)
        rag_service = RAGService()

        if params.action == "ingest":
            if not params.folder_path:
                return "Error: 'folder_path' is required for ingestion."
            try:
                success = await asyncio.to_thread(
                    rag_service.ingest_documents, params.folder_path, params.patterns
                )
                if success:
                    return f"Documents ingested successfully from {params.folder_path}."
                else:
                    return "Ingestion failed."
            except Exception as e:
                return f"Error during ingestion: {str(e)}"
        elif params.action == "query":
            if not params.query:
                return "Error: 'query' parameter is required for querying."
            try:
                result = await asyncio.to_thread(
                    rag_service.query_documents, params.query, params.num_results
                )
                return result
            except Exception as e:
                return f"Error during query: {str(e)}"
        elif params.action == "chat_history":
            if not params.conversation_id:
                return "Error: 'conversation_id' is required for chat history retrieval."
            try:
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                if not SUPABASE_URL or not SUPABASE_KEY:
                    return "Supabase configuration error."
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                query_result = await asyncio.to_thread(
                    lambda: supabase.table("messages")
                            .select("*")
                            .eq("conversation_id", params.conversation_id)
                            .order("timestamp", desc=True)
                            .limit(params.limit)
                            .execute()
                )
                return f"Chat history: {query_result.data}"
            except Exception as e:
                return f"Error retrieving chat history: {str(e)}"
        elif params.action == "repo_latest":
            try:
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                if not SUPABASE_URL or not SUPABASE_KEY:
                    return "Supabase configuration error."
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                table_name = os.getenv("CURRENT_SOURCE_TABLE", "repo_content")
                query_result = await asyncio.to_thread(
                    lambda: supabase.table(table_name)
                            .select("*")
                            .order("document_crawl_date", desc=True)
                            .limit(1)
                            .execute()
                )
                return f"Latest repo crawled: {query_result.data}"
            except Exception as e:
                return f"Error retrieving latest repo content: {str(e)}"
        else:
            return f"Unsupported action: {params.action}" 