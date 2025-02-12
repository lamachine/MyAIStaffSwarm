"""
title: Ollama Pipe Function
version: 0.1.2

This module defines a Pipe class that connects OpenWebUI to Ollama
"""

from typing import Optional, Callable, Awaitable
from pydantic import BaseModel, Field
import httpx
import time
from datetime import datetime
import json
from uuid import uuid4

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
        ollama_url: str = Field(
            default="http://localhost:11434",
            description="Ollama API endpoint"
        )
        model: str = Field(
            default="llama2",
            description="Ollama model to use"
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
        self.id = "ollama_pipe"
        self.name = "Ollama Pipe"
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
        await self.emit_status(
            __event_emitter__, "info", "Connecting to Ollama...", False
        )

        messages = body.get("messages", [])
        if not messages:
            await self.emit_status(
                __event_emitter__,
                "error",
                "No messages found in the request body",
                True,
            )
            return {"error": "No messages found in the request body"}

        try:
            # Get the latest message
            current_message = messages[-1]
            conversation_id = body.get("conversation_id", str(uuid4()))
            parent_message_id = current_message.get("message_id", str(uuid4()))

            # Create user message
            user_message = Message(
                role="user",
                content=current_message["content"],
                conversation_id=conversation_id,
                parent_message_id=parent_message_id,
                metadata={"user": __user__} if __user__ else {}
            )

            # Send to Ollama
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.ollama_url}/api/generate",
                    json={
                        "model": self.valves.model,
                        "prompt": user_message.content
                    }
                )

                if response.status_code == 200:
                    # Handle streaming response
                    full_response = ""
                    for line in response.text.strip().split('\n'):
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            if chunk.get("done", False):
                                break
                            full_response += chunk.get("response", "")
                        except json.JSONDecodeError:
                            continue

                    # Format response for OpenWebUI
                    response_message = {
                        "role": "assistant",
                        "content": full_response.strip(),
                        "message_id": str(uuid4()),
                        "parent_message_id": user_message.message_id,
                        "conversation_id": conversation_id
                    }

                    await self.emit_status(
                        __event_emitter__, "info", "Got response from Ollama", True
                    )

                    return {
                        "model": self.valves.model,
                        "messages": messages + [response_message],
                        "choices": [{
                            "message": response_message,
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": len(user_message.content.split()),
                            "completion_tokens": len(full_response.split()),
                            "total_tokens": len(user_message.content.split()) + len(full_response.split())
                        }
                    }
                else:
                    raise Exception(f"Error: {response.status_code} - {response.text}")

        except Exception as e:
            await self.emit_status(
                __event_emitter__,
                "error",
                f"Error during Ollama call: {str(e)}",
                True,
            )
            return {"error": str(e)}