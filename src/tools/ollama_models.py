from typing import Dict, Any
from enum import Enum

class OllamaModels(Enum):
    CHAT = {
        "model": "llama3.1",
        "temperature": 0.0,
        "context_window": 4096,
        "format": "text"
    }
    TOOL_USE = {
        "model": "llama3.1",
        "temperature": 0,
        "context_window": 4096,
        "format": "json",
        "system": "You are a helpful AI that returns structured JSON responses for tool usage.",
        "metadata": {
            "format": "json",
            "response_format": {"type": "json_object"}
        }
    }
    RAG = {
        "model": "llama3.1",
        "temperature": 0.1,
        "context_window": 4096,
        "format": "text"
    }

def get_model_config(model_type: str) -> Dict[str, Any]:
    """Get model configuration by type."""
    return OllamaModels[model_type].value 