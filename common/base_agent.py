from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from .models import BaseMessage, MessageType, Priority

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str, role: str):
        self.metadata = {
            "id": agent_id,
            "name": name,
            "role": role,
            "version": "1.0.0"
        }
        
        self.capabilities = {
            "tools": [],
            "permissions": [],
            "communication_modes": ["http"]
        }
        
        self.state = {
            "status": "idle",
            "current_task": None,
            "last_active": datetime.utcnow(),
            "memory": {
                "short_term": [],
                "context_window": []
            }
        }

    @abstractmethod
    async def process_message(self, message: BaseMessage) -> BaseMessage:
        """Process incoming message and return response"""
        pass

    @abstractmethod
    async def handle_task(self, task: BaseMessage) -> BaseMessage:
        """Handle specific task assignment"""
        pass

    async def update_state(self, status: str, task: Optional[str] = None):
        """Update agent's current state"""
        self.state["status"] = status
        self.state["current_task"] = task
        self.state["last_active"] = datetime.utcnow()

    async def add_to_memory(self, item: Any, memory_type: str = "short_term"):
        """Add item to specified memory store"""
        if memory_type in self.state["memory"]:
            self.state["memory"][memory_type].append(item)

    async def handle_error(self, error: Exception) -> BaseMessage:
        """Handle and format error responses"""
        return BaseMessage(
            type=MessageType.ERROR,
            priority=Priority.HIGH,
            sender=self.metadata["id"],
            receiver="system",
            content=str(error),
            metadata={"error_type": type(error).__name__}
        )

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent resources"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources"""
        pass 