"""LLM Service for Multiple Providers.

This module provides a unified interface for different LLM providers:
- OpenAI
- Anthropic
- Ollama
"""

from typing import Dict, List, Any, Optional
import logging
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import anthropic
import requests
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time

# Load environment variables
load_dotenv()

class LLMService:
    """Handles interactions with different LLM providers"""
    
    def __init__(self, provider: str = None):
        self.logger = logging.getLogger(__name__)
        self.provider = provider or os.getenv('LLM_PROVIDER', 'openai')
        self.logger.debug(f"Initializing LLM service with provider: {self.provider}")
        
        # Configure requests session with retries and timeouts
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Set embedding model based on provider
        if self.provider == 'openai':
            self.embedding_model = "text-embedding-3-small"
        elif self.provider == 'ollama':
            self.embedding_model = "mxbai-embed-large"
        # Anthropic doesn't provide embeddings yet
        
        self.setup_client()
        
    def setup_client(self):
        """Initialize the appropriate client based on provider"""
        try:
            if self.provider == 'openai':
                self.client = AsyncOpenAI(
                    api_key=os.getenv('OPENAI_API_KEY'),
                    organization=os.getenv('OPENAI_ORG_ID')
                )
                self.model = "gpt-4"
                self.logger.info("Initialized OpenAI client")
            elif self.provider == 'anthropic':
                self.client = anthropic.Anthropic(
                    api_key=os.getenv('ANTHROPIC_API_KEY')
                )
                self.model = "claude-2.1"
                self.logger.info("Initialized Anthropic client")
            elif self.provider == 'ollama':
                self.base_url = "http://localhost:11434"
                self.model = "llama3.2:latest"
                # Test Ollama connection with timeout
                try:
                    response = self.session.get(
                        f"{self.base_url}/api/tags",
                        timeout=5  # 5 second timeout
                    )
                    response.raise_for_status()
                    models = response.json()
                    self.logger.debug(f"Available Ollama models: {json.dumps(models, indent=2)}")
                    
                    # Verify our model is available
                    available_models = [m["name"] for m in models.get("models", [])]
                    if self.model not in available_models:
                        raise ValueError(f"Model {self.model} not found in available models: {available_models}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to get Ollama models: {str(e)}")
                    raise
                self.logger.info(f"Initialized Ollama client with model {self.model}")
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.provider} client: {str(e)}")
            raise
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embeddings for text using the configured provider."""
        try:
            if self.provider == 'openai':
                response = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
                
            elif self.provider == 'ollama':
                response = self.session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()["embedding"]
                
            else:
                raise ValueError(f"Embeddings not supported for provider: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise
            
    async def generate_response(self, 
                              prompt: str,
                              history: Optional[List[Dict[str, Any]]] = None,
                              system_prompt: Optional[str] = None,
                              additional_context: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response using the configured LLM provider"""
        try:
            self.logger.debug(f"Generating response with {self.provider}")
            
            # Add additional context to system prompt if provided
            effective_system_prompt = system_prompt or ""
            if additional_context:
                effective_system_prompt += f"\n\nAdditional Context:\n{additional_context}"
            
            if self.provider == 'openai':
                messages = []
                if effective_system_prompt:
                    messages.append({"role": "system", "content": effective_system_prompt})
                if history:
                    for msg in history:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                messages.append({"role": "user", "content": prompt})
                
                self.logger.debug(f"OpenAI messages: {json.dumps(messages, indent=2)}")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                
                return {
                    "content": response.choices[0].message.content,
                    "model": self.model,
                    "provider": self.provider
                }
                
            elif self.provider == 'anthropic':
                # Format conversation history
                conversation = ""
                if effective_system_prompt:
                    conversation += f"\n\nSystem: {effective_system_prompt}"
                if history:
                    for msg in history:
                        role = "Human" if msg["role"] == "user" else "Assistant"
                        conversation += f"\n\n{role}: {msg['content']}"
                conversation += f"\n\nHuman: {prompt}\n\nAssistant:"
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": conversation
                        }
                    ]
                )
                
                return {
                    "content": response.content[0].text,
                    "model": self.model,
                    "provider": self.provider
                }
                
            elif self.provider == 'ollama':
                # Format conversation for Ollama
                formatted_prompt = ""
                if effective_system_prompt:
                    formatted_prompt += f"System: {effective_system_prompt}\n\n"
                if history:
                    for msg in history:
                        role = "User" if msg["role"] == "user" else "Assistant"
                        formatted_prompt += f"{role}: {msg['content']}\n\n"
                formatted_prompt += f"User: {prompt}\n\nAssistant:"
                
                self.logger.debug(f"Sending request to Ollama:")
                self.logger.debug(f"URL: {self.base_url}/api/generate")
                self.logger.debug(f"Model: {self.model}")
                self.logger.debug(f"Prompt: {formatted_prompt}")
                
                start_time = time.time()
                try:
                    response = self.session.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": formatted_prompt,
                            "stream": False
                        },
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    end_time = time.time()
                    self.logger.debug(f"Ollama response received in {end_time - start_time:.2f} seconds")
                    self.logger.debug(f"Response: {json.dumps(result, indent=2)}")
                    
                    return {
                        "content": result["response"],
                        "model": self.model,
                        "provider": self.provider,
                        "timing": {
                            "total_seconds": end_time - start_time
                        }
                    }
                except requests.exceptions.Timeout:
                    raise TimeoutError(f"Ollama request timed out after 30 seconds")
                except Exception as e:
                    raise RuntimeError(f"Ollama request failed: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            self.logger.error("Full traceback:", exc_info=True)
            return {
                "error": str(e),
                "model": self.model,
                "provider": self.provider
            }

# Direct testing
if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\nTesting LLM Service:")
        
        try:
            # Test OpenAI
            print("\n1. Testing OpenAI:")
            openai_llm = LLMService('openai')
            response = await openai_llm.generate_response(
                prompt="Say hello!",
                system_prompt="You are a helpful assistant."
            )
            if "error" in response:
                print(f"❌ OpenAI test failed: {response['error']}")
            else:
                print("✓ OpenAI test successful")
                print(f"Response: {response['content']}")
            
            # Test Anthropic
            print("\n2. Testing Anthropic:")
            anthropic_llm = LLMService('anthropic')
            response = await anthropic_llm.generate_response(
                prompt="Say hello!",
                system_prompt="You are a helpful assistant."
            )
            if "error" in response:
                print(f"❌ Anthropic test failed: {response['error']}")
            else:
                print("✓ Anthropic test successful")
                print(f"Response: {response['content']}")
            
            # Test Ollama
            print("\n3. Testing Ollama:")
            ollama_llm = LLMService('ollama')
            response = await ollama_llm.generate_response(
                prompt="Say hello!",
                system_prompt="You are a helpful assistant."
            )
            if "error" in response:
                print(f"❌ Ollama test failed: {response['error']}")
            else:
                print("✓ Ollama test successful")
                print(f"Response: {response['content']}")
            
            print("\n✨ All tests completed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            import traceback
            print("\nFull test traceback:")
            print(traceback.format_exc())
    
    # Run the tests
    asyncio.run(run_tests()) 