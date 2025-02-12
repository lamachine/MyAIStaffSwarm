"""Type definitions for document ingestion service."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from ..common_types import SourceType

@dataclass
class Document:
    """Represents a document to be processed."""
    doc_id: str
    title: str
    content: str
    source_type: SourceType
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class ProcessedDocument:
    """Represents a processed document ready for vector storage."""
    doc_id: str
    chunks: List[str]
    embeddings: Optional[List[List[float]]] = None
    metadata: Dict[str, Any] = None 