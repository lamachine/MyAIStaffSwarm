"""Document processing tools."""

import logging
import uuid
import tempfile
import io
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from langchain.schema import Document as LangChainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader, UnstructuredExcelLoader,
    PythonLoader, PDFMinerLoader, CSVLoader, JSONLoader,
    UnstructuredEmailLoader
)
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain.chains.summarize import load_summarize_chain
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .common_types import SourceType
from .db_types import DocumentRecord
from .document_ingestion.sources import get_local_folder_source
from .document_ingestion.ingestion_service import DocumentIngestionService
from .document_ingestion.types import Document

logger = logging.getLogger(__name__)

def validate_document_content(content: str, max_size: int = 10 * 1024 * 1024) -> bool:
    """Validate document content for security.
    
    Args:
        content: Document content to validate
        max_size: Maximum allowed content size in bytes
        
    Returns:
        bool: True if content is valid, False otherwise
    """
    # Check content size
    if len(content.encode('utf-8')) > max_size:
        logger.warning(f"Document content exceeds maximum size of {max_size} bytes")
        return False
        
    # Check for potentially malicious content
    suspicious_patterns = [
        "eval(",
        "exec(",
        "<script",
        "import os",
        "import sys",
        "subprocess"
    ]
    
    for pattern in suspicious_patterns:
        if pattern in content.lower():
            logger.warning(f"Suspicious pattern found in document: {pattern}")
            return False
            
    return True

def compute_document_hash(content: str) -> str:
    """Compute SHA-256 hash of document content.
    
    Args:
        content: Document content
        
    Returns:
        str: Hex digest of content hash
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def to_langchain_document(doc: Document) -> LangChainDocument:
    """Convert our Document type to LangChain Document.
    
    Args:
        doc: Our custom Document instance
        
    Returns:
        LangChain Document instance
    """
    return LangChainDocument(
        page_content=doc.content,
        metadata={
            'doc_id': doc.doc_id,
            'title': doc.title,
            'source_type': doc.source_type.value,
            'content_hash': compute_document_hash(doc.content),
            **doc.metadata
        }
    )

def from_langchain_document(doc: LangChainDocument) -> Document:
    """Convert LangChain Document to our Document type.
    
    Args:
        doc: LangChain Document instance
        
    Returns:
        Our custom Document instance
    """
    metadata = doc.metadata.copy()
    doc_id = metadata.pop('doc_id', str(uuid.uuid4()))
    title = metadata.pop('title', '')
    source_type = SourceType(metadata.pop('source_type', SourceType.LOCAL_FOLDER.value))
    content_hash = metadata.pop('content_hash', '')
    
    # Validate content hash if present
    if content_hash:
        current_hash = compute_document_hash(doc.page_content)
        if current_hash != content_hash:
            logger.warning(f"Document content hash mismatch for {doc_id}")
            
    return Document(
        doc_id=doc_id,
        title=title,
        content=doc.page_content,
        source_type=source_type,
        metadata=metadata
    )

class UniversalTextLoader(TextLoader):
    """Text loader that tries multiple encodings."""
    
    def __init__(self, file_path: str):
        """Initialize with filepath."""
        super().__init__(file_path)
        self.encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16', 'ascii']
        
    def load(self) -> List[LangChainDocument]:
        """Load text from file, trying multiple encodings."""
        last_error = None
        file_size = Path(self.file_path).stat().st_size
        
        # First try to detect if it's a binary file
        try:
            with open(self.file_path, 'rb') as f:
                is_binary = b'\0' in f.read(1024)
            if is_binary:
                logger.warning(f"File appears to be binary: {self.file_path}")
                return []
        except Exception as e:
            logger.error(f"Error checking file type for {self.file_path}: {str(e)}")
            return []
            
        # Try each encoding
        for encoding in self.encodings:
            try:
                logger.debug(f"Trying {encoding} for {self.file_path}")
                with open(self.file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                    
                if not text.strip():
                    logger.warning(f"File is empty after reading with {encoding}: {self.file_path}")
                    continue
                    
                logger.info(f"Successfully loaded {self.file_path} using {encoding}")
                metadata = {
                    "source": self.file_path,
                    "encoding": encoding,
                    "size_bytes": file_size,
                    "filename": Path(self.file_path).name
                }
                return [LangChainDocument(page_content=text, metadata=metadata)]
                
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading {self.file_path} with {encoding}: {str(e)}")
                last_error = e
                continue
                
        logger.error(f"Failed to load {self.file_path}")
        logger.error(f"Tried encodings: {self.encodings}")
        logger.error(f"Last error: {str(last_error)}")
        return []

class ArduinoLoader(UniversalTextLoader):
    """Loader for Arduino/C files with special handling for comments and directives."""
    
    def load(self) -> List[LangChainDocument]:
        """Load and process Arduino/C file."""
        docs = super().load()
        if not docs:
            return []
            
        # Extract content with special handling
        content = docs[0].page_content
        metadata = {
            **docs[0].metadata,
            "includes": self._extract_includes(content),
            "defines": self._extract_defines(content),
            "functions": self._extract_functions(content)
        }
        
        return [LangChainDocument(
            page_content=content,
            metadata=metadata
        )]
        
    def _extract_includes(self, content: str) -> List[str]:
        """Extract #include directives."""
        includes = []
        for line in content.split('\n'):
            if line.strip().startswith('#include'):
                includes.append(line.strip())
        return includes
        
    def _extract_defines(self, content: str) -> List[str]:
        """Extract #define directives."""
        defines = []
        for line in content.split('\n'):
            if line.strip().startswith('#define'):
                defines.append(line.strip())
        return defines
        
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function declarations."""
        functions = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '(' in line and ')' in line and '{' in line:
                # Simple heuristic for function definitions
                functions.append(line.strip())
        return functions

class GoogleWorkspaceLoader:
    """Base loader for Google Workspace files."""
    
    def __init__(self, file_path: str, credentials: Credentials = None):
        """Initialize with file path and credentials."""
        self.file_path = file_path
        self.credentials = credentials
        self.temp_dir = Path(tempfile.mkdtemp())
        
    async def download_and_convert(self, mime_type: str) -> Optional[str]:
        """Download and convert Google Workspace file."""
        try:
            # Extract file ID from path or metadata
            file_id = self._extract_file_id(self.file_path)
            
            # Initialize Drive API
            service = build('drive', 'v3', credentials=self.credentials)
            
            # Download file in requested format
            request = service.files().export_media(
                fileId=file_id,
                mimeType=mime_type
            )
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            # Save to temp file
            temp_path = self.temp_dir / f"temp_export{Path(self.file_path).suffix}"
            with open(temp_path, 'wb') as f:
                f.write(fh.getvalue())
                
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Error downloading Google Workspace file: {str(e)}")
            return None
            
    def _extract_file_id(self, file_path: str) -> str:
        """Extract Google Drive file ID from path."""
        # For now, assume the path is the file ID
        # TODO: Add proper file ID extraction
        return Path(file_path).stem

class GoogleDocsLoader(GoogleWorkspaceLoader):
    """Loader for Google Docs files."""
    
    async def load(self) -> List[LangChainDocument]:
        """Load Google Doc as plain text."""
        temp_path = await self.download_and_convert('text/plain')
        if not temp_path:
            return []
            
        loader = UniversalTextLoader(temp_path)
        docs = loader.load()
        
        # Update metadata
        for doc in docs:
            doc.metadata.update({
                "source": self.file_path,
                "type": "google_doc"
            })
            
        return docs

class GoogleSheetsLoader(GoogleWorkspaceLoader):
    """Loader for Google Sheets files."""
    
    async def load(self) -> List[LangChainDocument]:
        """Load Google Sheet as CSV."""
        temp_path = await self.download_and_convert('text/csv')
        if not temp_path:
            return []
            
        loader = CSVLoader(temp_path)
        docs = loader.load()
        
        # Update metadata
        for doc in docs:
            doc.metadata.update({
                "source": self.file_path,
                "type": "google_sheet"
            })
            
        return docs

class GoogleSlidesLoader(GoogleWorkspaceLoader):
    """Loader for Google Slides files."""
    
    async def load(self) -> List[LangChainDocument]:
        """Load Google Slides as plain text."""
        temp_path = await self.download_and_convert('text/plain')
        if not temp_path:
            return []
            
        loader = UniversalTextLoader(temp_path)
        docs = loader.load()
        
        # Update metadata
        for doc in docs:
            doc.metadata.update({
                "source": self.file_path,
                "type": "google_slides"
            })
            
        return docs

class DocumentTools:
    """Tools for processing and retrieving documents."""
    
    # Default file type mappings
    DEFAULT_LOADERS = {
        # Text and Code Files
        ".txt": UniversalTextLoader,
        ".py": PythonLoader,
        ".ino": ArduinoLoader,
        ".c": ArduinoLoader,
        ".cpp": ArduinoLoader,
        ".h": ArduinoLoader,
        
        # Office Documents
        ".pdf": PDFMinerLoader,
        ".doc": UnstructuredWordDocumentLoader,
        ".docx": UnstructuredWordDocumentLoader,
        ".ppt": UnstructuredPowerPointLoader,
        ".pptx": UnstructuredPowerPointLoader,
        ".xls": UnstructuredExcelLoader,
        ".xlsx": UnstructuredExcelLoader,
        
        # Data Files
        ".csv": CSVLoader,
        ".json": JSONLoader,
        
        # Email Files
        ".eml": UnstructuredEmailLoader,
        ".msg": UnstructuredEmailLoader,
        
        # Google Workspace Files
        ".gdoc": GoogleDocsLoader,
        ".gsheet": GoogleSheetsLoader,
        ".gslides": GoogleSlidesLoader
    }
    
    def __init__(self, db_service):
        """Initialize document tools.
        
        Args:
            db_service: Database service for storing document metadata
        """
        self.db = db_service
        self.custom_loaders = {}  # For runtime-added loaders
        
        # Initialize embedding model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len
        )
        
        # Initialize LLM for summarization
        self.llm = ChatOllama(
            model="llama3.2:latest",
            temperature=0.3
        )
        
        # Initialize vector store path
        self.vector_store_path = Path("data/vector_store")
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Load or create vector store
        self._load_vector_store()
            
    def _load_vector_store(self, force_refresh: bool = False):
        """Load or create vector store.
        
        Args:
            force_refresh: If True, delete existing vector store and create new one
        """
        index_path = self.vector_store_path / "index.faiss"
        pkl_path = self.vector_store_path / "index.pkl"
        
        if force_refresh:
            logger.info("Forcing refresh - clearing existing vector store...")
            if index_path.exists():
                logger.info(f"Deleting {index_path}")
                index_path.unlink()
            if pkl_path.exists():
                logger.info(f"Deleting {pkl_path}")
                pkl_path.unlink()
            self.vector_store = None
            logger.info("Vector store cleared successfully")
            return
            
        if index_path.exists() and pkl_path.exists():
            try:
                logger.info("Loading existing vector store...")
                # Create new embeddings for verification
                temp_embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2"
                )
                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    temp_embeddings
                )
                logger.info("Loaded existing vector store successfully")
            except Exception as e:
                logger.warning(f"Could not load existing vector store, will create new one: {str(e)}")
                self.vector_store = None
        else:
            logger.info("No existing vector store found, will create new one when documents are processed")
            self.vector_store = None
            
    def register_loader(self, file_extension: str, loader_class: Type) -> None:
        """Register a new document loader for a file type.
        
        Args:
            file_extension: File extension (e.g., ".pdf")
            loader_class: Loader class to use for this file type
        """
        self.custom_loaders[file_extension.lower()] = loader_class
        logger.info(f"Registered loader for {file_extension}: {loader_class.__name__}")
        
    def get_loader_for_file(self, file_path: str) -> Optional[Type]:
        """Get appropriate loader for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Loader class if available, None otherwise
        """
        ext = Path(file_path).suffix.lower()
        
        # Check custom loaders first, then default loaders
        return self.custom_loaders.get(ext) or self.DEFAULT_LOADERS.get(ext)
            
    async def process_directory(self, folder_path: str, file_patterns: List[str], force_refresh: bool = True) -> Dict[str, Any]:
        """Process all documents in a directory.
        
        Args:
            folder_path: Path to directory containing documents
            file_patterns: List of glob patterns to match files
            force_refresh: If True, clear existing vector store before processing
            
        Returns:
            Dictionary with processing statistics
        """
        # Ensure vector store directory exists
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Always force refresh at the start of processing
        logger.info(f"Starting document processing for: {folder_path}")
        self._load_vector_store(force_refresh=True)
        
        try:
            folder_path = Path(folder_path).resolve()  # Get absolute path
            logger.debug(f"Processing directory: {folder_path}")
            
            all_documents = []
            skipped_files = []
            successful_files = []
            
            # Create local folder source for all patterns
            source = get_local_folder_source(str(folder_path), file_patterns)
            
            # Get all documents from source first
            async for doc in source.get_documents():
                try:
                    file_path = Path(doc.metadata['path'])
                    logger.debug(f"Processing file from source: {file_path}")
                    
                    # Get appropriate loader
                    loader_class = self.get_loader_for_file(str(file_path))
                    if loader_class is None:
                        logger.warning(f"No loader found for {file_path.name}")
                        skipped_files.append(str(file_path))
                        continue
                        
                    # Try to load the file content
                    try:
                        loader = loader_class(str(file_path))
                        langchain_docs = loader.load()
                        if langchain_docs:
                            # Validate content before processing
                            content = langchain_docs[0].page_content
                            if not validate_document_content(content):
                                logger.warning(f"Content validation failed for {file_path.name}")
                                skipped_files.append(str(file_path))
                                continue
                                
                            # Update document with content and metadata
                            doc.content = content
                            doc.metadata['content_hash'] = compute_document_hash(content)
                            doc.metadata.update(langchain_docs[0].metadata)
                            
                            all_documents.append(doc)
                            successful_files.append(file_path.name)
                            logger.info(f"Successfully loaded: {file_path.name}")
                        else:
                            logger.warning(f"No content extracted from: {file_path.name}")
                            skipped_files.append(str(file_path))
                    except Exception as e:
                        logger.error(f"Error loading file {file_path.name}: {str(e)}")
                        skipped_files.append(str(file_path))
                        
                except Exception as e:
                    logger.error(f"Error processing document: {str(e)}")
                    if 'path' in doc.metadata:
                        skipped_files.append(doc.metadata['path'])
                    continue
            
            # Log results
            if successful_files:
                logger.info("\nSuccessfully loaded files:")
                for file in successful_files:
                    logger.info(f"- {file}")
                    
            if skipped_files:
                logger.warning("\nSkipped files:")
                for file in skipped_files:
                    logger.warning(f"- {Path(file).name}")
                    
            logger.info(f"\nLoaded {len(all_documents)} documents")
            
            # If no documents were loaded, return early
            if not all_documents:
                return {
                    'num_documents': 0,
                    'num_chunks': 0,
                    'skipped_files': len(skipped_files),
                    'successful_files': len(successful_files)
                }
            
            # Process documents
            split_docs = []
            for doc in all_documents:
                chunks = self.text_splitter.split_text(doc.content)
                for i, chunk in enumerate(chunks):
                    # Create our Document type first
                    chunk_doc = Document(
                        doc_id=f"{doc.doc_id}_chunk_{i}",
                        title=doc.title,
                        content=chunk,
                        source_type=doc.source_type,
                        metadata={
                            **doc.metadata,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'parent_doc_id': doc.doc_id,
                            'content_hash': compute_document_hash(chunk)
                        }
                    )
                    # Convert to LangChain Document for vector store
                    split_docs.append(to_langchain_document(chunk_doc))
                    
            logger.info(f"Split into {len(split_docs)} chunks")
            
            # Create or update vector store
            if split_docs:
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(
                        split_docs,
                        self.embeddings
                    )
                    self.vector_store.save_local(str(self.vector_store_path))
                else:
                    self.vector_store.add_documents(split_docs)
                    self.vector_store.save_local(str(self.vector_store_path))
            
            return {
                'num_documents': len(all_documents),
                'num_chunks': len(split_docs),
                'skipped_files': len(skipped_files),
                'successful_files': len(successful_files)
            }
            
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}")
            raise
            
    def _get_loader_instance(self, file_path: str, skipped_files: List[str]) -> Optional[Any]:
        """Get loader instance for a file, tracking skipped files.
        
        Args:
            file_path: Path to the file
            skipped_files: List to track unsupported files
            
        Returns:
            Loader instance if available, None otherwise
        """
        loader_class = self.get_loader_for_file(file_path)
        if loader_class:
            return loader_class(file_path)
        else:
            skipped_files.append(file_path)
            return None
            
    async def _generate_summary(self, text: str) -> str:
        """Generate a summary of text using LLM.
        
        Args:
            text: Text to summarize
            
        Returns:
            Summary text
        """
        try:
            chain = load_summarize_chain(
                llm=self.llm,
                chain_type="stuff",
                verbose=True
            )
            
            # Create LangChain Document for summarization
            doc = LangChainDocument(page_content=text)
            summary = await chain.ainvoke({"input_documents": [doc]})
            return summary["output_text"]
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return ""
            
    async def search_documents(
        self,
        query: str,
        num_results: int = 5,
        file_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for documents similar to query.
        
        Args:
            query: Search query
            num_results: Number of results to return
            file_types: Optional list of file types to filter by
            
        Returns:
            List of similar documents with scores
        """
        if self.vector_store is None:
            return []
            
        try:
            results = self.vector_store.similarity_search_with_score(
                query,
                k=num_results
            )
            
            # Filter by file type if specified
            filtered_results = []
            for langchain_doc, score in results:
                if file_types:
                    file_ext = Path(langchain_doc.metadata.get('path', '')).suffix.lower()
                    if file_ext not in file_types:
                        continue
                        
                # Verify content hash
                content_hash = langchain_doc.metadata.get('content_hash')
                if content_hash:
                    current_hash = compute_document_hash(langchain_doc.page_content)
                    if current_hash != content_hash:
                        logger.warning(f"Content hash mismatch in search results")
                        continue
                        
                # Convert back to our Document type
                doc = from_langchain_document(langchain_doc)
                filtered_results.append({
                    'document': doc,
                    'score': score
                })
                
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return [] 