"""Webhook service for handling incoming requests.

This module provides a WebhookService class that handles incoming webhook
requests with standardized processing and built-in testing.
"""

from typing import Callable, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import asyncio
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class WebhookPayload(BaseModel):
    """Standardized webhook payload model"""
    source: str
    message_type: str
    content: Dict[str, Any]

class WebhookService:
    """Handles incoming webhook requests with standardized processing"""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.app: Optional[FastAPI] = None
        
    async def initialize(self):
        """Initialize the FastAPI application"""
        try:
            self.app = FastAPI(title="Webhook Service")
            self.logger.info(f"Initialized FastAPI app on {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize FastAPI: {str(e)}")
            return False
    
    async def register_handler(self, path: str, handler: Callable):
        """Register a new webhook handler for a specific path"""
        try:
            if path in self.handlers:
                self.logger.warning(f"Overwriting existing handler for path: {path}")
            self.handlers[path] = handler
            self.logger.info(f"Registered new webhook handler for path: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register handler: {str(e)}")
            return False
    
    async def handle_webhook(self, path: str, payload: WebhookPayload) -> Dict[str, Any]:
        """Process incoming webhook data"""
        try:
            if not self.app:
                raise RuntimeError("Service not initialized")
                
            if path not in self.handlers:
                self.logger.error(f"No handler for path: {path}")
                raise HTTPException(status_code=404, detail=f"No handler for path: {path}")
            
            handler = self.handlers[path]
            self.logger.debug(f"Processing webhook for path: {path}")
            result = await handler(payload)
            
            self.logger.info(f"Successfully processed webhook for path: {path}")
            return {
                "status": "success",
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# Direct testing
if __name__ == "__main__":
    print("\nTesting Webhook Service:")
    
    async def run_tests():
        try:
            # Initialize service
            print("1. Testing service initialization...")
            service = WebhookService(host="localhost", port=8000)
            initialized = await service.initialize()
            assert initialized, "Service initialization failed"
            print("✓ Service initialized successfully")
            
            # Test handler registration
            print("\n2. Testing handler registration...")
            async def test_handler(payload: WebhookPayload):
                return {"processed": payload.content}
            
            registered = await service.register_handler("/test", test_handler)
            assert registered, "Handler registration failed"
            print("✓ Handler registered successfully")
            
            # Test webhook handling
            print("\n3. Testing webhook processing...")
            test_payload = WebhookPayload(
                source="test",
                message_type="test_message",
                content={"test": "data"}
            )
            
            result = await service.handle_webhook("/test", test_payload)
            assert result["status"] == "success"
            assert result["data"]["processed"]["test"] == "data"
            print("✓ Webhook processed successfully")
            
            # Test error handling
            print("\n4. Testing error handling...")
            try:
                await service.handle_webhook("/nonexistent", test_payload)
                print("✗ Should have raised an exception")
            except HTTPException as e:
                assert e.status_code == 404
                print("✓ Error handled correctly")
            
            print("\nAll tests completed successfully!")
            
        except Exception as e:
            print(f"\nTest failed: {str(e)}")
            import traceback
            print("\nFull traceback:")
            print(traceback.format_exc())
            sys.exit(1)
    
    # Run the tests
    asyncio.run(run_tests()) 