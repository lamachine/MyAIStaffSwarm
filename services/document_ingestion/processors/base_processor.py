"""Base interface for document processors."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..types import Document, ProcessedDocument

class DocumentProcessor(ABC):
    """Abstract base class for document processors."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the document processor.
        
        Args:
            config: Processor-specific configuration
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate processor configuration."""
        pass
    
    @abstractmethod
    async def process_document(self, document: Document) -> ProcessedDocument:
        """Process a single document.
        
        Args:
            document: Document to process
            
        Returns:
            ProcessedDocument with chunks and optional embeddings
        """
        pass
    
    @abstractmethod
    async def generate_summary(self, document: Document) -> str:
        """Generate a summary of the document.
        
        Args:
            document: Document to summarize
            
        Returns:
            Summary text
        """
        pass
    
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Get list of supported document formats.
        
        Returns:
            List of format identifiers (e.g., ["text", "pdf", "email"])
        """
        pass 