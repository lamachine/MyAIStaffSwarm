"""Local folder document source implementation."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, AsyncIterator, List
from datetime import datetime

from .base_source import DocumentSource
from ..types import Document, SourceType

logger = logging.getLogger(__name__)

class LocalFolderSource(DocumentSource):
    """Document source that reads from a local folder."""
    
    def _validate_config(self) -> None:
        """Validate source configuration."""
        required_fields = ['folder_path', 'file_patterns']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
                
        folder_path = Path(self.config['folder_path'])
        if not folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
            
        if not isinstance(self.config['file_patterns'], list):
            raise ValueError("file_patterns must be a list")
            
    async def connect(self) -> None:
        """No connection needed for local folder."""
        pass
        
    async def disconnect(self) -> None:
        """No disconnection needed for local folder."""
        pass
        
    async def get_documents(self) -> AsyncIterator[Document]:
        """Retrieve documents from the local folder.
        
        Yields:
            Document objects one at a time
        """
        folder_path = Path(self.config['folder_path'])
        file_patterns = self.config['file_patterns']
        
        for pattern in file_patterns:
            for file_path in folder_path.glob(pattern):
                try:
                    if file_path.is_file():
                        # Get file metadata
                        stats = file_path.stat()
                        created = datetime.fromtimestamp(stats.st_ctime)
                        modified = datetime.fromtimestamp(stats.st_mtime)
                        
                        metadata = {
                            'path': str(file_path),
                            'size': stats.st_size,
                            'created': created.isoformat(),
                            'modified': modified.isoformat(),
                            'extension': file_path.suffix.lower()
                        }
                        
                        # Create document
                        doc = Document(
                            doc_id=str(file_path),
                            title=file_path.name,
                            content="",  # Content will be loaded by document tools
                            source_type=self.source_type,
                            metadata=metadata,
                            created_at=created,
                            updated_at=modified
                        )
                        
                        yield doc
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    continue
                    
    async def get_document_by_id(self, doc_id: str) -> Document:
        """Retrieve a specific document by ID.
        
        Args:
            doc_id: Document identifier (file path in this case)
            
        Returns:
            Document object
            
        Raises:
            DocumentNotFoundError if document doesn't exist
        """
        file_path = Path(doc_id)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Document not found: {doc_id}")
            
        # Get file metadata
        stats = file_path.stat()
        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)
        
        metadata = {
            'path': str(file_path),
            'size': stats.st_size,
            'created': created.isoformat(),
            'modified': modified.isoformat(),
            'extension': file_path.suffix.lower()
        }
        
        return Document(
            doc_id=str(file_path),
            title=file_path.name,
            content="",  # Content will be loaded by document tools
            source_type=self.source_type,
            metadata=metadata,
            created_at=created,
            updated_at=modified
        )
        
    @property
    def source_type(self) -> SourceType:
        """Get the type of this document source."""
        return SourceType.LOCAL_FOLDER

def get_local_folder_source(folder_path: str, file_patterns: List[str]) -> LocalFolderSource:
    """Create a local folder source.
    
    Args:
        folder_path: Path to folder containing documents
        file_patterns: List of glob patterns to match files
        
    Returns:
        Configured LocalFolderSource instance
    """
    config = {
        'folder_path': folder_path,
        'file_patterns': file_patterns
    }
    return LocalFolderSource(config) 