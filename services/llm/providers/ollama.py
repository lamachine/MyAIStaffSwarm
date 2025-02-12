import httpx
import json
from typing import Dict, List, AsyncGenerator
import logging
from .base import BaseLLMProvider, LLMRequest, LLMResponse
import asyncio

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation"""
    
    def _initialize(self) -> None:
        """Initialize the Ollama provider"""
        self.name = "ollama"
        host = self.config.get('host', 'ollama-gpu')
        port = self.config.get('port', 11434)
        self.base_url = f"http://{host}:{port}/api"
        logger.info(f"Initializing Ollama provider with base_url: {self.base_url}")
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30.0,     # connection timeout
                read=600.0,       # read timeout (10 minutes)
                write=30.0,       # write timeout
                pool=30.0         # pool timeout
            ),
            verify=False,  # Allow internal docker network communication
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self._available_models = self.config.get("available_models", ["llama2"])
        self.default_model = self.config.get("default_model", "llama2")
        self.model_config = self.config.get("model_config", {})
        self.max_retries = 5
        self.retry_delay = 30  # seconds
        logger.info(f"Ollama provider initialized with config: {self.config}")
    
    async def _wait_for_gpu(self) -> bool:
        """Wait for GPU resources to be available"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting GPU check {attempt + 1}/{self.max_retries}")
                response = await self.client.get(f"{self.base_url}/tags", timeout=30.0)
                logger.info(f"GPU check response status: {response.status_code}")
                if response.status_code == 200:
                    logger.info("GPU check successful")
                    return True
                logger.warning(f"GPU check failed with status {response.status_code}")
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.warning(f"GPU check attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        logger.error("All GPU check attempts failed")
        return False
    
    async def health_check(self) -> bool:
        """Check if Ollama is healthy and responding"""
        for _ in range(self.max_retries):
            try:
                response = await self.client.get(f"{self.base_url}/version")
                if response.status_code == 200:
                    # Also check GPU availability
                    if await self._wait_for_gpu():
                        return True
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Ollama health check failed: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        return False
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Ollama"""
        try:
            model_name = request.model or self.default_model
            logger.info(f"Starting generation with model: {model_name}")
            
            # Wait for GPU resources with increased timeout
            for attempt in range(self.max_retries):
                if await self._wait_for_gpu():
                    break
                logger.warning(f"GPU not available, attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
            else:
                raise Exception("GPU resources not available after all retries")

            # Get model-specific configuration
            model_cfg = self.model_config.get(model_name, {})
            
            payload = {
                "model": model_cfg.get("model_file", f"{model_name}:latest"),
                "prompt": request.prompt,
                "stream": True,  # Use streaming to avoid timeouts
                "options": {
                    "num_gpu": self.config.get("num_gpu", 1),
                    "num_thread": self.config.get("num_thread", 4),
                    "temperature": request.temperature or model_cfg.get("temperature", 0.7),
                    "top_p": model_cfg.get("top_p", 0.9),
                    "context_size": model_cfg.get("context_size", self.config.get("context_size", 4096)),
                    "gpu_layers": model_cfg.get("gpu_layers", self.config.get("gpu_layers", -1))
                }
            }

            logger.info(f"Sending request to {self.base_url}/generate with model config: {model_cfg}")
            full_response = ""
            
            # Use a longer timeout for the first request which might include model loading
            timeout = httpx.Timeout(600.0)  # 10 minutes
            async with self.client.stream(
                "POST",
                f"{self.base_url}/generate",
                json=payload,
                timeout=timeout
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                full_response += data["response"]
                            if "error" in data:
                                logger.error(f"Ollama error: {data['error']}")
                                raise Exception(f"Ollama error: {data['error']}")
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode response line: {line}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing response line: {str(e)}")
                            raise

            logger.info("Generation completed successfully")
            return LLMResponse(
                text=full_response,
                model=request.model,
                usage={"total_tokens": 0}  # Ollama doesn't provide token count
            )

        except Exception as e:
            logger.error(f"Generation failed: {str(e)}", exc_info=True)
            raise
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Ollama"""
        await self.validate_request(request)
        request = await self.preprocess_request(request)
        
        try:
            # Wait for GPU resources with increased timeout
            for attempt in range(self.max_retries):
                if await self._wait_for_gpu():
                    break
                logger.warning(f"GPU not available, attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
            else:
                raise Exception("GPU resources not available after all retries")

            payload = {
                "model": request.model or self.default_model,
                "prompt": request.prompt,
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens or self.config.get("max_tokens", 2000),
                    **(request.extra_params or {})
                }
            }
            
            timeout = httpx.Timeout(600.0)  # 10 minutes for model loading
            async with self.client.stream(
                "POST", 
                f"{self.base_url}/generate", 
                json=payload,
                timeout=timeout
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if "error" in data:
                                logger.error(f"Ollama error: {data['error']}")
                                raise Exception(f"Ollama error: {data['error']}")
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode Ollama stream response: {line}")
                            continue
                        
        except httpx.HTTPError as e:
            logger.error(f"Ollama stream request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama stream: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        return self._available_models
    
    def get_model_config(self, model: str) -> Dict:
        """Get configuration for a specific Ollama model"""
        return {
            "name": model,
            "max_tokens": self.config.get("max_tokens", 2000),
            "temperature_range": (0.0, 1.0),
            "default_temperature": 0.7,
            "supports_streaming": True
        } 