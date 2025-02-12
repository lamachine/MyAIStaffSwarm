"""Database service for AI memory management."""

import logging
import json
from typing import Dict, List, Any, Optional
import asyncpg
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

from .common_types import SourceType
from .db_types import DocumentRecord
from .db_interface import DatabaseInterface

class DatabaseService(DatabaseInterface):
    """Handles database operations for AI memory"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self.pool = None
        self.has_vector_extension = False
        self._init_db_config()
        
    def _init_db_config(self):
        """Initialize database configuration from environment variables"""
        self.logger.debug("PostgreSQL Connection Details:")
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = os.getenv('POSTGRES_DB', 'ai_memory')
        self.user = os.getenv('POSTGRES_USER', 'root')
        self.password = os.getenv('POSTGRES_PASSWORD', 'password')
        
        self.logger.debug(f"Host: {self.host}")
        self.logger.debug(f"Port: {self.port}")
        self.logger.debug(f"Database: {self.database}")
        self.logger.debug(f"User: {self.user}")
        
    async def cleanup(self):
        """Clean up database connections"""
        if self.pool:
            self.logger.debug("Closing database pool...")
            await self.pool.close()
            self.pool = None
            self.logger.debug("Database pool closed")
        self._initialized = False
            
    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            # If already initialized, clean up first
            if self._initialized:
                await self.cleanup()
                
            self.logger.debug("Testing connection...")
            try:
                conn = await asyncpg.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
                await conn.close()
                self.logger.debug("Test connection successful")
            except Exception as e:
                self.logger.error(f"Failed to connect to database: {str(e)}")
                return False
                
            self.logger.debug("Creating connection pool...")
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    min_size=1,
                    max_size=10
                )
                self.logger.info("Successfully created connection pool")
            except Exception as e:
                self.logger.error(f"Failed to create connection pool: {str(e)}")
                return False
                
            # Try to create vector extension, but don't require it
            self.has_vector_extension = False
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                    self.has_vector_extension = True
                    self.logger.info("PostgreSQL vector extension enabled")
            except Exception as e:
                self.logger.info("PostgreSQL vector extension not available - will use alternative storage for vectors")
                
            self.logger.debug("Creating conversations table...")
            await self._create_conversations_table()
            
            self.logger.debug("Creating memory_vectors table...")
            await self._create_memory_vectors_table()
            
            self.logger.debug("Creating files table...")
            await self._create_files_table()
            
            self.logger.debug("Creating user_info table...")
            await self._create_user_info_table()
            
            self.logger.debug("Creating document_records table...")
            await self._create_document_records_table()
            
            self._initialized = True
            self.logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            await self.cleanup()
            return False
            
    async def _create_conversations_table(self):
        """Create the conversations table if it doesn't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB
                );
            ''')
            
    async def _create_memory_vectors_table(self):
        """Create the memory_vectors table if it doesn't exist"""
        async with self.pool.acquire() as conn:
            if self.has_vector_extension:
                # Create table with vector extension support
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS memory_vectors (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
            else:
                # Create table without vector extension
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS memory_vectors (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        embedding_json JSONB,  -- Store vectors as JSON arrays
                        metadata JSONB,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
            
    async def _create_files_table(self):
        """Create the files table if it doesn't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
    async def _create_user_info_table(self):
        """Create the user_info table if it doesn't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_info (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL DEFAULT 'Unknown User',
                    expertise_level TEXT NOT NULL DEFAULT 'beginner',
                    goals TEXT NOT NULL DEFAULT 'Not specified',
                    preferences JSONB DEFAULT '{}',
                    context JSONB DEFAULT '{}',
                    os_version TEXT,
                    workspace_path TEXT,
                    shell_path TEXT,
                    additional_info JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
    async def store_user_info(self, session_id: str, 
                            name: str = None,
                            expertise_level: str = None,
                            goals: str = None,
                            preferences: Dict = None,
                            context: Dict = None,
                            os_version: str = None, 
                            workspace_path: str = None, 
                            shell_path: str = None,
                            additional_info: Dict = None) -> Dict:
        """Store user information in the database"""
        try:
            self.logger.debug(f"Storing user info for session {session_id}")
            # Set default values for required fields
            name = name or 'Unknown User'
            expertise_level = expertise_level or 'beginner'
            goals = goals or 'Not specified'
            preferences = preferences or {}
            context = context or {}
            additional_info = additional_info or {}
            
            self.logger.debug("Handling JSON fields")
            # Handle JSON fields
            if isinstance(preferences, str):
                preferences = json.loads(preferences)
            if isinstance(context, str):
                context = json.loads(context)
            if isinstance(additional_info, str):
                additional_info = json.loads(additional_info)
            
            self.logger.debug("Acquiring database connection")
            async with self.pool.acquire() as conn:
                self.logger.debug("Executing database query")
                result = await conn.fetchrow(
                    '''
                    INSERT INTO user_info 
                    (session_id, name, expertise_level, goals, preferences, context,
                     os_version, workspace_path, shell_path, additional_info)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (session_id) 
                    DO UPDATE SET 
                        name = COALESCE(EXCLUDED.name, user_info.name),
                        expertise_level = COALESCE(EXCLUDED.expertise_level, user_info.expertise_level),
                        goals = COALESCE(EXCLUDED.goals, user_info.goals),
                        preferences = COALESCE(EXCLUDED.preferences, user_info.preferences),
                        context = COALESCE(EXCLUDED.context, user_info.context),
                        os_version = COALESCE(EXCLUDED.os_version, user_info.os_version),
                        workspace_path = COALESCE(EXCLUDED.workspace_path, user_info.workspace_path),
                        shell_path = COALESCE(EXCLUDED.shell_path, user_info.shell_path),
                        additional_info = COALESCE(EXCLUDED.additional_info, user_info.additional_info),
                        timestamp = CURRENT_TIMESTAMP
                    RETURNING id, session_id, name, expertise_level, goals, preferences, context,
                             os_version, workspace_path, shell_path, additional_info, timestamp;
                    ''',
                    session_id,
                    name,
                    expertise_level,
                    goals,
                    json.dumps(preferences),
                    json.dumps(context),
                    os_version,
                    workspace_path,
                    shell_path,
                    json.dumps(additional_info)
                )
                
                self.logger.debug("Query executed, processing result")
                return {
                    "id": result['id'],
                    "session_id": result['session_id'],
                    "name": result['name'],
                    "expertise_level": result['expertise_level'],
                    "goals": result['goals'],
                    "preferences": result['preferences'],
                    "context": result['context'],
                    "os_version": result['os_version'],
                    "workspace_path": result['workspace_path'],
                    "shell_path": result['shell_path'],
                    "additional_info": result['additional_info'],
                    "timestamp": result['timestamp'].isoformat()
                }
        except Exception as e:
            self.logger.error(f"Failed to store user info: {str(e)}")
            raise
            
    async def get_user_info(self, session_id: str) -> Optional[Dict]:
        """Retrieve user information from the database"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    SELECT id, session_id, name, expertise_level, goals, preferences, context,
                           os_version, workspace_path, shell_path, additional_info, timestamp
                    FROM user_info
                    WHERE session_id = $1;
                    ''',
                    session_id
                )
                
                if result:
                    # Parse JSON fields
                    preferences = result['preferences'] if result['preferences'] else {}
                    context = result['context'] if result['context'] else {}
                    additional_info = result['additional_info'] if result['additional_info'] else {}
                    
                    return {
                        "id": result['id'],
                        "session_id": result['session_id'],
                        "name": result['name'],
                        "expertise_level": result['expertise_level'],
                        "goals": result['goals'],
                        "preferences": preferences,
                        "context": context,
                        "os_version": result['os_version'],
                        "workspace_path": result['workspace_path'],
                        "shell_path": result['shell_path'],
                        "additional_info": additional_info,
                        "timestamp": result['timestamp'].isoformat()
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve user info: {str(e)}")
            raise
            
    async def store_message(self, role: str, content: str, metadata: Optional[Dict] = None, session_id: Optional[str] = None) -> Dict:
        """Store a conversation message in the database"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    INSERT INTO conversations (role, content, metadata, session_id)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, session_id, role, content, metadata, timestamp;
                    ''',
                    role,
                    content,
                    json.dumps(metadata) if metadata else None,
                    session_id or str(uuid.uuid4())  # Generate new session_id if not provided
                )
                
                return {
                    "id": result['id'],
                    "session_id": result['session_id'],
                    "role": result['role'],
                    "content": result['content'],
                    "metadata": result['metadata'],
                    "timestamp": result['timestamp'].isoformat()
                }
        except Exception as e:
            self.logger.error(f"Failed to store message: {str(e)}")
            raise
            
    async def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent conversation messages"""
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    '''
                    SELECT id, role, content, metadata, timestamp
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT $1;
                    ''',
                    limit
                )
                
                return [
                    {
                        "id": r['id'],
                        "role": r['role'],
                        "content": r['content'],
                        "metadata": r['metadata'],
                        "timestamp": r['timestamp'].isoformat()
                    }
                    for r in results
                ]
        except Exception as e:
            self.logger.error(f"Failed to retrieve messages: {str(e)}")
            raise
            
    async def store_file(self, file_path: str, content: str, metadata: Optional[Dict] = None) -> Dict:
        """Store a file's contents in the database"""
        try:
            # Calculate file hash
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    INSERT INTO files (file_path, file_hash, content, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (file_path) 
                    DO UPDATE SET 
                        file_hash = EXCLUDED.file_hash,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        timestamp = CURRENT_TIMESTAMP
                    RETURNING id, file_path, file_hash, metadata, timestamp;
                    ''',
                    file_path,
                    file_hash,
                    content,
                    json.dumps(metadata) if metadata else None
                )
                
                return {
                    "id": result['id'],
                    "file_path": result['file_path'],
                    "file_hash": result['file_hash'],
                    "metadata": result['metadata'],
                    "timestamp": result['timestamp'].isoformat()
                }
        except Exception as e:
            self.logger.error(f"Failed to store file: {str(e)}")
            raise
            
    async def get_file(self, file_path: str) -> Optional[Dict]:
        """Retrieve a file's contents from the database"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    SELECT id, file_path, file_hash, content, metadata, timestamp
                    FROM files
                    WHERE file_path = $1;
                    ''',
                    file_path
                )
                
                if result:
                    return {
                        "id": result['id'],
                        "file_path": result['file_path'],
                        "file_hash": result['file_hash'],
                        "content": result['content'],
                        "metadata": result['metadata'],
                        "timestamp": result['timestamp'].isoformat()
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve file: {str(e)}")
            raise
            
    async def _create_document_records_table(self):
        """Create the documents table if it doesn't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    doc_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    source_type TEXT NOT NULL,
                    vector_store_id TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
    async def store_document_record(self, record: DocumentRecord) -> DocumentRecord:
        """Store a document record in the database.
        
        Args:
            record: Document record to store
            
        Returns:
            Stored document record with database ID
        """
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    INSERT INTO document_records 
                    (doc_id, title, summary, source_type, vector_store_id, 
                     metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (doc_id) 
                    DO UPDATE SET 
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        source_type = EXCLUDED.source_type,
                        vector_store_id = EXCLUDED.vector_store_id,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING *;
                    ''',
                    record.doc_id,
                    record.title,
                    record.summary,
                    record.source_type.value,
                    record.vector_store_id,
                    json.dumps(record.metadata),
                    record.created_at,
                    record.updated_at
                )
                
                # Parse metadata JSON string back into dictionary
                metadata = json.loads(result['metadata']) if result['metadata'] else {}
                
                return DocumentRecord(
                    id=result['id'],
                    doc_id=result['doc_id'],
                    title=result['title'],
                    summary=result['summary'],
                    source_type=SourceType(result['source_type']),
                    vector_store_id=result['vector_store_id'],
                    metadata=metadata,  # Use parsed metadata
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                )
                
        except Exception as e:
            self.logger.error(f"Failed to store document record: {str(e)}")
            raise

    async def get_document_record(self, doc_id: str) -> Optional[DocumentRecord]:
        """Retrieve a document record from the database.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document record if found, None otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    '''
                    SELECT * FROM document_records
                    WHERE doc_id = $1;
                    ''',
                    doc_id
                )
                
                if result:
                    # Parse metadata JSON string back into dictionary
                    metadata = json.loads(result['metadata']) if result['metadata'] else {}
                    
                    return DocumentRecord(
                        id=result['id'],
                        doc_id=result['doc_id'],
                        title=result['title'],
                        summary=result['summary'],
                        source_type=SourceType(result['source_type']),
                        vector_store_id=result['vector_store_id'],
                        metadata=metadata,  # Use parsed metadata
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve document record: {str(e)}")
            raise

    async def get_documents_by_source(
        self, 
        source_type: SourceType,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentRecord]:
        """Retrieve document records by source type.
        
        Args:
            source_type: Type of document source
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of document records
        """
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    '''
                    SELECT * FROM document_records
                    WHERE source_type = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3;
                    ''',
                    source_type.value,
                    limit,
                    offset
                )
                
                return [
                    DocumentRecord(
                        id=r['id'],
                        doc_id=r['doc_id'],
                        title=r['title'],
                        summary=r['summary'],
                        source_type=SourceType(r['source_type']),
                        vector_store_id=r['vector_store_id'],
                        metadata=json.loads(r['metadata']) if r['metadata'] else {},
                        created_at=r['created_at'],
                        updated_at=r['updated_at']
                    )
                    for r in results
                ]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve documents by source: {str(e)}")
            raise

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
        try:
            query = """
                INSERT INTO documents (
                    doc_id, title, content, source_type, 
                    vector_store_id, metadata, summary,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
                RETURNING id, doc_id, title, summary, source_type::text, 
                          vector_store_id, metadata, created_at, updated_at
            """
            
            now = datetime.now()
            row = await self.pool.fetchrow(
                query,
                doc_id,
                title,
                content,
                source_type.value,
                vector_store_id,
                json.dumps(metadata),
                summary or "",
                now
            )
            
            return DocumentRecord(
                id=row['id'],
                doc_id=row['doc_id'],
                title=row['title'],
                summary=row['summary'],
                source_type=SourceType(row['source_type']),
                vector_store_id=row['vector_store_id'],
                metadata=row['metadata'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store document: {str(e)}")
            raise
            
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        try:
            query = """
                SELECT id, doc_id, title, content, summary,
                       source_type::text, vector_store_id, metadata,
                       created_at, updated_at
                FROM documents
                WHERE doc_id = $1
            """
            
            row = await self.pool.fetchrow(query, doc_id)
            if not row:
                return None
                
            return {
                "id": row['id'],
                "doc_id": row['doc_id'],
                "title": row['title'],
                "content": row['content'],
                "summary": row['summary'],
                "source_type": SourceType(row['source_type']),
                "vector_store_id": row['vector_store_id'],
                "metadata": row['metadata'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get document: {str(e)}")
            raise
            
    async def update_document(
        self,
        doc_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a document's metadata."""
        try:
            # Build update query dynamically based on provided fields
            set_clauses = []
            values = [doc_id]
            param_count = 1
            
            for key, value in updates.items():
                if key in ['metadata', 'summary', 'vector_store_id']:
                    set_clauses.append(f"{key} = ${param_count + 1}")
                    values.append(
                        json.dumps(value) if key == 'metadata' else value
                    )
                    param_count += 1
                    
            if not set_clauses:
                return False
                
            # Add updated_at timestamp
            set_clauses.append(f"updated_at = ${param_count + 1}")
            values.append(datetime.now())
            
            query = f"""
                UPDATE documents
                SET {', '.join(set_clauses)}
                WHERE doc_id = $1
                RETURNING id
            """
            
            result = await self.pool.fetchval(query, *values)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Failed to update document: {str(e)}")
            raise

# Direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("\nTesting Database Service:")
    
    async def run_tests():
        try:
            # Initialize database service
            print("\n1. Testing initialization:")
            logger.info("Creating database service instance...")
            db = DatabaseService()
            logger.info("Initializing database...")
            await db.initialize()
            print("✓ Database initialized")
            
            # Test document record operations
            print("\n2. Testing document record operations:")
            
            # Create test record
            from datetime import datetime
            from services.document_ingestion.types import DocumentRecord, SourceType
            
            logger.info("Creating test record...")
            test_record = DocumentRecord(
                id=0,  # Will be set by database
                doc_id="test123",
                title="Test Document",
                summary="This is a test document",
                source_type=SourceType.LOCAL_FOLDER,
                vector_store_id="vec123",
                metadata={"test_key": "test_value"},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store record
            logger.info("Storing test record...")
            stored = await db.store_document_record(test_record)
            print(f"✓ Stored document record with ID: {stored.id}")
            assert stored.doc_id == test_record.doc_id, "Stored doc_id doesn't match"
            assert stored.title == test_record.title, "Stored title doesn't match"
            
            # Retrieve record
            logger.info("Retrieving test record...")
            retrieved = await db.get_document_record(test_record.doc_id)
            print("✓ Retrieved document record")
            assert retrieved is not None, "Retrieved record is None"
            assert retrieved.doc_id == test_record.doc_id, "Retrieved doc_id doesn't match"
            assert retrieved.title == test_record.title, "Retrieved title doesn't match"
            assert retrieved.metadata["test_key"] == "test_value", "Retrieved metadata doesn't match"
            
            # Update record
            logger.info("Updating test record...")
            updated_record = DocumentRecord(
                id=stored.id,
                doc_id=stored.doc_id,
                title="Updated Title",
                summary="Updated summary",
                source_type=stored.source_type,
                vector_store_id=stored.vector_store_id,
                metadata={"updated_key": "updated_value"},
                created_at=stored.created_at,
                updated_at=datetime.now()
            )
            
            updated = await db.store_document_record(updated_record)
            print("✓ Updated document record")
            assert updated.title == "Updated Title", "Updated title doesn't match"
            assert updated.metadata["updated_key"] == "updated_value", "Updated metadata doesn't match"
            
            # Test get_documents_by_source
            logger.info("Testing get_documents_by_source...")
            docs = await db.get_documents_by_source(SourceType.LOCAL_FOLDER)
            print(f"✓ Retrieved {len(docs)} documents by source")
            assert len(docs) > 0, "No documents retrieved by source"
            assert docs[0].source_type == SourceType.LOCAL_FOLDER, "Wrong source type retrieved"
            
            # Test non-existent document
            logger.info("Testing non-existent document retrieval...")
            nonexistent = await db.get_document_record("nonexistent")
            print("✓ Correctly handled non-existent document")
            assert nonexistent is None, "Non-existent document should return None"
            
            # Clean up test data
            print("\n3. Cleaning up test data:")
            logger.info("Cleaning up test records...")
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM document_records WHERE doc_id = $1",
                    test_record.doc_id
                )
            print("✓ Test data cleaned up")
            
            print("\nAll tests completed successfully!")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())
            raise
        finally:
            if hasattr(db, 'pool'):
                logger.info("Closing database pool...")
                await db.pool.close()
    
    # Run tests
    asyncio.run(run_tests())