from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator
from pydantic import BaseModel

class LLMRequest(BaseModel):
    """Model for LLM requests"""
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    stream: bool = False
    stop_sequences: Optional[List[str]] = None
    extra_params: Optional[Dict] = None

class LLMResponse(BaseModel):
    """Model for LLM responses"""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    extra_info: Optional[Dict] = None

class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.name = "base"
        self._initialize()
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the provider with configuration"""
        pass
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for a given prompt"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response for a given prompt"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and available"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass
    
    @abstractmethod
    def get_model_config(self, model: str) -> Dict:
        """Get configuration for a specific model"""
        pass
    
    async def validate_request(self, request: LLMRequest) -> None:
        """Validate a request before processing"""
        if request.model and request.model not in self.get_available_models():
            raise ValueError(f"Model {request.model} not available for provider {self.name}")
        
        if request.max_tokens and request.max_tokens > self.config.get("max_tokens", 2000):
            raise ValueError(f"max_tokens exceeds limit of {self.config.get('max_tokens', 2000)}")
    
    async def preprocess_request(self, request: LLMRequest) -> LLMRequest:
        """Preprocess a request before sending to the provider"""
        if not request.model:
            request.model = self.config.get("default_model")
        return request
    
    async def postprocess_response(self, response: LLMResponse) -> LLMResponse:
        """Postprocess a response before returning to the client"""
        return response 