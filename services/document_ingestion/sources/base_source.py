"""Base interface for document sources."""

from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Dict, Any
from ..types import Document, SourceType

class DocumentSource(ABC):
    """Abstract base class for document sources."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the document source.
        
        Args:
            config: Source-specific configuration
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate source configuration."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the source."""
        pass
    
    @abstractmethod
    async def get_documents(self) -> AsyncIterator[Document]:
        """Retrieve documents from the source.
        
        Yields:
            Document objects one at a time
        """
        pass
    
    @abstractmethod
    async def get_document_by_id(self, doc_id: str) -> Document:
        """Retrieve a specific document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document object
            
        Raises:
            DocumentNotFoundError if document doesn't exist
        """
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Get the type of this document source."""
        pass 