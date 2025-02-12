"""Database type definitions."""

from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime
from .common_types import SourceType

@dataclass
class DocumentRecord:
    """Database record for a processed document."""
    id: int
    doc_id: str
    title: str
    summary: str
    source_type: SourceType
    vector_store_id: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime 