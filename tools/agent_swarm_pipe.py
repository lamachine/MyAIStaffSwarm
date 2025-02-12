"""
title: Agent Swarm Pipe Function
version: 0.1.0

This module defines a Pipe class that connects OpenWebUI to the Agent Swarm API
"""

from typing import Optional, Callable, Awaitable, List
from pydantic import BaseModel, Field
import httpx
import time
from datetime import datetime
import json
from uuid import uuid4
import logging
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    filename='logs/agent_swarm_pipe.log',  # Relative path
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(console_handler)

def extract_event_info(event_emitter) -> tuple[Optional[str], Optional[str]]:
    if not event_emitter or not event_emitter.__closure__:
        return None, None
    for cell in event_emitter.__closure__:
        if isinstance(request_info := cell.cell_contents, dict):
            chat_id = request_info.get("chat_id")
            message_id = request_info.get("message_id")
            return chat_id, message_id
    return None, None

class Message(BaseModel):
    role: str
    content: str
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

class Pipe:
    class Valves(BaseModel):
        api_url: str = Field(
            default="http://host.docker.internal:8088",  # Use Docker host networking
            description="Agent Swarm API endpoint"
        )
        emit_interval: float = Field(
            default=2.0,
            description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True,
            description="Enable or disable status indicator emissions"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "agent_swarm_pipe"
        self.name = "Agent Swarm Pipe"
        self.valves = self.Valves()
        self.last_emit_time = 0

    async def emit_status(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        level: str,
        message: str,
        done: bool,
    ):
        current_time = time.time()
        if (
            __event_emitter__
            and self.valves.enable_status_indicator
            and (current_time - self.last_emit_time >= self.valves.emit_interval or done)
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> Optional[dict]:
        logging.info("\n=== Agent Swarm Pipe Debug ===")
        logging.info(f"Request body: {json.dumps(body, indent=2)}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.api_url}/api/chat",
                    json=body,
                    timeout=5.0
                )
                logging.info(f"Response status: {response.status_code}")
                logging.info(f"Raw response: {response.text}")
                
                if response.status_code == 200:
                    await self.emit_status(
                        __event_emitter__, "info", "Got response from Agent Swarm", True
                    )
                    return response.json()

        except Exception as e:
            logging.error(f"Error in agent_swarm_pipe: {str(e)}", exc_info=True)
            await self.emit_status(
                __event_emitter__,
                "error",
                f"Error: {str(e)}",
                True,
            )
            return {"error": str(e)} 