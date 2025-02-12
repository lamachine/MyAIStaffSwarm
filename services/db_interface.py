"""Database interface definition."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from .common_types import SourceType
from .db_types import DocumentRecord

class DatabaseInterface(ABC):
    """Interface for database operations needed by services."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize database connection."""
        pass
        
    @abstractmethod
    async def store_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source_type: SourceType,
        vector_store_id: str,
        metadata: Dict[str, Any],
        summary: Optional[str] = None
    ) -> DocumentRecord:
        """Store a document in the database."""
        pass
        
    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        pass
        
    @abstractmethod
    async def update_document(
        self,
        doc_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a document's metadata."""
        pass 