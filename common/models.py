from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from passlib.context import CryptContext
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def set_password(self, password: str):
        self.hashed_password = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

class MessageType(str, Enum):
    TASK = "task"
    STATUS = "status"
    DATA = "data"
    RESULT = "result"
    ERROR = "error"
    CONTROL = "control"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BaseMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: MessageType
    priority: Priority = Priority.MEDIUM
    sender: str
    receiver: str
    content: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class TaskMessage(BaseMessage):
    type: MessageType = MessageType.TASK
    task_id: Optional[str] = None
    deadline: Optional[datetime] = None
    dependencies: Optional[list[str]] = None

class StatusMessage(BaseMessage):
    type: MessageType = MessageType.STATUS
    status: str
    progress: Optional[float] = None

class ErrorMessage(BaseMessage):
    type: MessageType = MessageType.ERROR
    error_code: str
    error_details: Dict[str, Any]
    severity: str 