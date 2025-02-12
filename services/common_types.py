"""Common type definitions shared across services."""

from enum import Enum

class SourceType(Enum):
    """Supported document source types."""
    GMAIL = "gmail"
    YAHOO = "yahoo"
    LOCAL_FOLDER = "local_folder"
    GDRIVE = "gdrive" 