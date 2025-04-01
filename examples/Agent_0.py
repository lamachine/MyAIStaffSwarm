from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
import httpx
import asyncpg
import logfire

from dotenv import load_dotenv

# Adjust the imports for tools and agents based on the new structure.
from src.tools.base_tool import BaseTool, ToolMetadata
from src.tools.RAG_tools import ListDocumentsTool, SearchSimilarDocumentsTool, RetrieveDocumentsTool
from src.tools.utils import get_embedding  # Assuming this exists
from src.agents.base_agent import AgentMetadata, BaseAgent

# Force reload environment variables from .env
env_path = Path('.env')
if not env_path.exists():
    env_path = Path('../.env')  # Try one directory up
if not env_path.exists():
    env_path = Path('../../.env')  # Try two directories up
if not env_path.exists():
    raise FileNotFoundError("Could not find .env file in current or parent directories")

print(f"Loading .env from: {env_path.absolute()}")
load_dotenv(env_path, override=True)  # Force override existing env vars

# Get Supabase credentials with fallbacks.
SUPABASE_URL = os.getenv('SUPABASE_URL')
print(f"Found SUPABASE_URL: {'Yes' if SUPABASE_URL else 'No'}")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL not found in environment variables")

SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
print(f"Found SUPABASE_KEY: {'Yes' if SUPABASE_KEY else 'No'}")
if not SUPABASE_KEY:
    raise ValueError("No Supabase key found. Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")

SUPABASE_KEY = SUPABASE_KEY.strip()
if not SUPABASE_KEY.startswith('ey'):
    raise ValueError("Invalid Supabase key format. Key should start with 'ey'")

print(f"SUPABASE_URL starts with: {SUPABASE_URL[:10]}...")
print(f"SUPABASE_KEY starts with: {SUPABASE_KEY[:10]}...")

from supabase import create_client, Client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Successfully created Supabase client")
except Exception as e:
    print(f"Error creating Supabase client: {str(e)}")
    raise

# Set up LLM model.
llm = os.getenv("LLM_MODEL", "llama3.1:latest")
base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
os.environ["OPENAI_API_KEY"] = "dummy-key-for-ollama"

from pydantic_ai.models.openai import OpenAIModel
model = OpenAIModel(
    llm,
    base_url=base_url,
    api_key="dummy-key-for-ollama"
)

logfire.configure(send_to_logfire="if-token-present")

# Database connection settings.
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=disable"
)
print(f"Connecting to database at: {POSTGRES_HOST}:{POSTGRES_PORT}")

@dataclass
class Deps:
    client: httpx.AsyncClient
    supabase: Client
    db_pool: asyncpg.Pool

async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/v1/embeddings",
            json={"input": text, "model": "text-embedding-3-small"}
        )
    return response.json()["data"][0]["embedding"]

# Define Agent0 metadata and create an instance.
metadata = AgentMetadata(
    name="Agent0",
    description="Handles webhook requests and performs RAG-based queries.",
    personality="A helpful AI that retrieves relevant documents."
)

Agent0 = BaseAgent(metadata)
Agent0.add_tool(ListDocumentsTool())
Agent0.add_tool(SearchSimilarDocumentsTool())
Agent0.add_tool(RetrieveDocumentsTool())

async def main():
    try:
        async with httpx.AsyncClient() as client:
            pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10
            )
            if pool:
                print("Successfully connected to database")
                deps = Deps(client=client, supabase=supabase, db_pool=pool)
                docs = await Agent0.use_tool("list_documents", deps)
                similar_docs = await Agent0.use_tool("search_similar", deps, "AI agents in Pydantic")
                specific_docs = await Agent0.use_tool("retrieve_documents", deps, [1, 2, 3])
                print(f"List of documents: {docs}")
                print(f"Similar documents: {similar_docs}")
                print(f"Specific documents: {specific_docs}")
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 