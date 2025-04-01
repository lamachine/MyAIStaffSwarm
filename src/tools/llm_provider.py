from langchain_ollama import ChatOllama
import logging
from typing import Optional
import os
from .ollama_models import get_model_config

class LLMProvider:
    _instance: Optional['LLMProvider'] = None
    
    def __init__(self):
        # Use TOOL_USE config for JSON responses
        config = get_model_config('TOOL_USE')
        self.llm = ChatOllama(**config)
        logging.info("LLM Provider initialized")
        
    @classmethod
    def get_instance(cls) -> 'LLMProvider':
        """Singleton pattern to ensure one LLM instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def generate_response(self, prompt: str) -> str:
        """Generate a response from the LLM."""
        try:
            response = await self.llm.ainvoke(prompt)
            return response
        except Exception as e:
            logging.error(f"LLM generation error: {str(e)}")
            return f"Error: {str(e)}"

    def get_llm(self):
        """Get LLM instance with proper configuration."""
        return ChatOllama(
            model="llama2",
            temperature=0,
            format="json",  # Force JSON output
            system="You are a helpful AI that returns structured JSON responses for tool usage."
        )

# Demo usage:
if __name__ == "__main__":
    async def main():
        llm = LLMProvider.get_instance()
        prompt = "Tell me a joke about programming."
        response = await llm.generate_response(prompt)
        print("LLM Response:", response)
    asyncio.run(main()) 