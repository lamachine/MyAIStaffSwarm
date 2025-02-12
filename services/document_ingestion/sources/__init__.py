"""Document source implementations."""

from .base_source import DocumentSource
from .local_folder import get_local_folder_source

__all__ = [
    'DocumentSource',
    'get_local_folder_source'
] 