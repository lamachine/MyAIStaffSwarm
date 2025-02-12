"""Interface for vector stores."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..types import ProcessedDocument, Document

class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the vector store.
        
        Args:
            config: Store-specific configuration
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate store configuration."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the store."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the store."""
        pass
    
    @abstractmethod
    async def store_document(self, processed_doc: ProcessedDocument) -> str:
        """Store a processed document.
        
        Args:
            processed_doc: Document to store
            
        Returns:
            Vector store ID for the stored document
        """
        pass
    
    @abstractmethod
    async def delete_document(self, vector_store_id: str) -> None:
        """Delete a document from the store.
        
        Args:
            vector_store_id: ID of document to delete
        """
        pass
    
    @abstractmethod
    async def search_similar(
        self, 
        query: str, 
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query: Search query
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of similar documents with scores
        """
        pass 