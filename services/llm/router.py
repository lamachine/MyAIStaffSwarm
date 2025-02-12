from typing import Dict, List, Optional, Type, AsyncGenerator
import logging
from .config import LLMServiceConfig
from .providers.base import BaseLLMProvider, LLMRequest, LLMResponse
from .providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

class LLMRouter:
    """Routes requests to appropriate LLM providers based on configuration"""
    
    def __init__(self, config: LLMServiceConfig):
        self.config = config
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize enabled providers"""
        provider_classes = {
            "ollama": OllamaProvider,
            # Add other providers here as they're implemented
        }
        
        for provider_name, provider_config in self.config.models.items():
            if provider_config.get("enabled", False):
                if provider_name in provider_classes:
                    try:
                        self.providers[provider_name] = provider_classes[provider_name](provider_config)
                        logger.info(f"Initialized {provider_name} provider")
                    except Exception as e:
                        logger.error(f"Failed to initialize {provider_name} provider: {str(e)}")
                else:
                    logger.warning(f"Provider {provider_name} not implemented")
    
    async def route_request(self, request: LLMRequest) -> LLMResponse:
        """Route a request to the appropriate provider"""
        if request.model:
            # If model is specified, find the provider that supports it
            provider = self._find_provider_for_model(request.model)
            if not provider:
                raise ValueError(f"No provider available for model {request.model}")
            return await provider.generate(request)
        
        # If no model specified, use routing strategy
        return await self._route_by_strategy(request)
    
    async def route_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Route a streaming request to the appropriate provider"""
        if request.model:
            provider = self._find_provider_for_model(request.model)
            if not provider:
                raise ValueError(f"No provider available for model {request.model}")
            async for chunk in provider.generate_stream(request):
                yield chunk
        else:
            async for chunk in self._route_stream_by_strategy(request):
                yield chunk
    
    def _find_provider_for_model(self, model: str) -> Optional[BaseLLMProvider]:
        """Find a provider that supports the specified model"""
        for provider in self.providers.values():
            if model in provider.get_available_models():
                return provider
        return None
    
    async def _route_by_strategy(self, request: LLMRequest) -> LLMResponse:
        """Route request based on configured strategy"""
        strategy = self.config.routing["strategy"]
        
        if strategy == "priority":
            return await self._route_by_priority(request)
        elif strategy == "round-robin":
            return await self._route_round_robin(request)
        elif strategy == "load-based":
            return await self._route_by_load(request)
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")
    
    async def _route_stream_by_strategy(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Route streaming request based on configured strategy"""
        strategy = self.config.routing["strategy"]
        
        if strategy == "priority":
            provider = await self._get_priority_provider()
            async for chunk in provider.generate_stream(request):
                yield chunk
        else:
            # For other strategies, default to priority for now
            provider = await self._get_priority_provider()
            async for chunk in provider.generate_stream(request):
                yield chunk
    
    async def _route_by_priority(self, request: LLMRequest) -> LLMResponse:
        """Route request based on priority order"""
        provider = await self._get_priority_provider()
        return await provider.generate(request)
    
    async def _get_priority_provider(self) -> BaseLLMProvider:
        """Get the highest priority available provider"""
        for provider_name in self.config.routing["priority_order"]:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.health_check():
                    return provider
                
        raise RuntimeError("No healthy providers available")
    
    async def _route_round_robin(self, request: LLMRequest) -> LLMResponse:
        """Route request using round-robin strategy"""
        # TODO: Implement round-robin routing
        return await self._route_by_priority(request)
    
    async def _route_by_load(self, request: LLMRequest) -> LLMResponse:
        """Route request based on provider load"""
        # TODO: Implement load-based routing
        return await self._route_by_priority(request)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        health_status = {}
        for name, provider in self.providers.items():
            health_status[name] = await provider.health_check()
        return health_status
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get all available models across providers"""
        available_models = {}
        for name, provider in self.providers.items():
            available_models[name] = provider.get_available_models()
        return available_models 