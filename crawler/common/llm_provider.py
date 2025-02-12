from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI
from dataclasses import dataclass
import asyncio
import json

# Load environment variables first
load_dotenv(override=True)

# Only import Anthropic if configured
if os.getenv("ANTHROPIC_API_KEY"):
    from anthropic import AsyncAnthropic

@dataclass
class LLMResponse:
    content: str
    metadata: Dict[str, Any]

@dataclass
class EmbeddingResponse:
    embedding: List[float]
    model: str

class LLMProvider:
    def __init__(self):
        """Initialize the LLM provider with Ollama client."""
        self.ollama_client = httpx.AsyncClient()
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.LLM_MODEL = os.getenv("OLLAMA_PREFERRED_LLM_MODEL", "llama3.1:latest")
        self.EMBEDDING_MODEL = os.getenv("OLLAMA_PREFERRED_EMBEDDING_MODEL", "nomic-embed-text")
        self.llm_provider = "ollama"
        self.embedding_provider = "nomic-embed-text"

    async def get_completion(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Get a completion from Ollama."""
        try:
            # Combine prompts if system prompt is provided
            full_prompt = f"{system_prompt}\n\nIMPORTANT: Respond with ONLY a JSON object. No preamble, no explanation.\n\n{prompt}" if system_prompt else prompt
            
            response = await self.ollama_client.post(
                f"{self.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.LLM_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "stop": ["\n\n"]  # Stop at paragraph breaks
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if 'response' not in result:
                print(f"Unexpected response format: {result}")
                return LLMResponse(content="", metadata={})
                
            return LLMResponse(
                content=result['response'].strip(),
                metadata={"model": self.LLM_MODEL}
            )
            
        except Exception as e:
            print(f"Error getting completion: {e}")
            return LLMResponse(content="", metadata={})

    async def get_title_and_summary(self, chunk: str, url: str) -> Dict[str, str]:
        """Extract title and summary using separate Ollama requests."""
        
        async def get_title() -> str:
            """Get just the title."""
            prompt = """Create a brief, descriptive title (3-10 words) for this content.
            Respond with ONLY the title text - no quotes, no JSON, no explanation."""
            
            try:
                response = await self.ollama_client.post(
                    f"{self.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": self.LLM_MODEL,
                        "prompt": f"{prompt}\n\nContent:\n{chunk[:1000]}...",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "stop": ["\n"]
                        }
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result['response'].strip()
            except Exception as e:
                print(f"Error getting title: {e}")
                return "Error processing title"

        async def get_summary() -> str:
            """Get just the summary."""
            prompt = """Write a brief summary (10-20 words) of this content.
            Respond with ONLY the summary text - no quotes, no JSON, no explanation."""
            
            try:
                response = await self.ollama_client.post(
                    f"{self.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": self.LLM_MODEL,
                        "prompt": f"{prompt}\n\nContent:\n{chunk[:1000]}...",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "stop": ["\n"]
                        }
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result['response'].strip()
            except Exception as e:
                print(f"Error getting summary: {e}")
                return "Error processing summary"

        # Get title and summary in parallel
        title, summary = await asyncio.gather(get_title(), get_summary())
        
        return {
            "title": title,
            "summary": summary
        }

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector from Ollama."""
        try:
            response = await self.ollama_client.post(
                f"{self.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": self.EMBEDDING_MODEL, "prompt": text},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if 'embedding' not in data:
                print(f"Unexpected response format: {data}")
                raise ValueError(f"No embedding in response: {data}")
            
            embedding = data["embedding"]
            print(f"Successfully generated embedding of length: {len(embedding)}")
            
            # Pad if needed
            if len(embedding) < 1536:
                embedding.extend([0] * (1536 - len(embedding)))
                
            return embedding[:1536]  # Truncate if longer
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0] * 1536  # Return zero vector on error

    async def close(self):
        """Close the Ollama client."""
        await self.ollama_client.aclose()

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the provider and models being used."""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.LLM_MODEL,
            "embedding_provider": self.embedding_provider
        } 