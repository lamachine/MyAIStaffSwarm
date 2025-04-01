from langchain_ollama import OllamaLLM

class LLMProvider:
    def __init__(self):
        self.llm = OllamaLLM(model="llama3.1:latest")

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        try:
            response = await self.llm.ainvoke(prompt)
            return response
        except Exception as e:
            return f"Error: {str(e)}" 