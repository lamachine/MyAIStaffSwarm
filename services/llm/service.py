from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
import jwt
from jose import JWTError
import os
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import LLMServiceConfig
from .router import LLMRouter
from .providers.base import LLMRequest, LLMResponse
from ...agents.orchestrator.agent import JarvisAgent

# Custom middleware for request timing and connection handling
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-256-bit-secret")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

app = FastAPI(title="LLM Service")

# Add custom middleware
app.add_middleware(TimingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = LLMServiceConfig()
router = LLMRouter(config)
jarvis = JarvisAgent()

class ChatMessage(BaseModel):
    """Chat message from user"""
    message: str

@app.get("/auth/status")
async def auth_status(token: str = Depends(oauth2_scheme)):
    """Check authentication status"""
    try:
        # Verify the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload:
            return {"authenticated": False}
        return {"authenticated": True}
    except JWTError:
        return {"authenticated": False}
    except Exception:
        return {"authenticated": False}

@app.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint"""
    # For demo, accept any credentials
    access_token = jwt.encode({"sub": form_data.username}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/chat")
async def chat(message: ChatMessage, token: str = Depends(oauth2_scheme)):
    """Process chat message through Jarvis"""
    try:
        response = await jarvis.process_message(message.message)
        return JSONResponse(content={"response": response})
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="I apologize, but I'm having trouble processing your request at the moment."
        )

@app.get("/api/health")
async def health_check():
    """Check health of LLM service and Jarvis"""
    try:
        llm_health = await router.health_check()
        return {
            "status": "healthy" if any(llm_health.values()) else "unhealthy",
            "llm_providers": llm_health,
            "jarvis": "initialized"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "llm_providers": {},
            "jarvis": "error"
        }

@app.get("/api/models")
async def get_available_models(token: str = Depends(oauth2_scheme)):
    """Get available LLM models"""
    try:
        return {"providers": router.get_available_models()}
    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get available models")

@app.on_event("startup")
async def startup_event():
    """Initialize service and Jarvis on startup"""
    logger.info("Starting LLM service with Jarvis")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on service shutdown"""
    logger.info("Shutting down LLM service")